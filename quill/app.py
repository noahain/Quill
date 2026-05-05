import logging
import os
import queue
import threading
import time
import winsound
from pathlib import Path

import webview
from pynput import keyboard

from quill.config import DEFAULTS, SettingsStore
from quill.audio import AudioRecorder
from quill.transcription import NvidiaTranscriptionService, GroqTranscriptionService
from quill.typer import Typer
from quill.tray import TrayManager

# Configure logging so user can see what's happening in the console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("quill")
logging.getLogger("quill").setLevel(logging.DEBUG)

EVENT_START = "start"
EVENT_TYPE = "type"
EVENT_ERROR = "error"
EVENT_EXIT = "exit"

STATE_IDLE = "idle"
STATE_LISTENING = "listening"
STATE_TRANSCRIBING = "transcribing"
STATE_TYPING = "typing"

BEEP_DELAY = 0.3
QUEUE_TIMEOUT = 0.5


class _ShortcutMatcher:
    """Custom hotkey matcher that normalises left/right modifier keys."""

    _NORMALIZE = {
        keyboard.Key.ctrl_l: keyboard.Key.ctrl,
        keyboard.Key.ctrl_r: keyboard.Key.ctrl,
        keyboard.Key.shift_l: keyboard.Key.shift,
        keyboard.Key.shift_r: keyboard.Key.shift,
        keyboard.Key.alt_l: keyboard.Key.alt,
        keyboard.Key.alt_r: keyboard.Key.alt,
        keyboard.Key.cmd_l: keyboard.Key.cmd,
        keyboard.Key.cmd_r: keyboard.Key.cmd,
    }

    def __init__(self, keys, on_activate, on_deactivate=None):
        self._keys = frozenset(keys)
        self._on_activate = on_activate
        self._on_deactivate = on_deactivate
        self._state: set = set()
        self._active = False

    def _norm(self, key):
        key = self._NORMALIZE.get(key, key)
        if isinstance(key, keyboard.KeyCode) and key.vk is not None:
            key = keyboard.KeyCode(vk=key.vk)
        return key

    def press(self, key):
        normalized = self._norm(key)
        logger.debug("Matcher press: raw=%s norm=%s state_before=%s expected=%s", key, normalized, self._state, self._keys)
        self._state.add(normalized)
        if not self._active and self._state == self._keys:
            self._active = True
            logger.debug("Matcher: all keys matched! firing activate")
            self._on_activate()
        else:
            logger.debug("Matcher: state=%s != expected=%s", self._state, self._keys)

    def release(self, key):
        normalized = self._norm(key)
        logger.debug("Matcher release: raw=%s norm=%s", key, normalized)
        self._state.discard(normalized)
        if self._active and self._state != self._keys:
            self._active = False
            if self._on_deactivate:
                logger.debug("Matcher: combo released, firing deactivate")
                self._on_deactivate()


class Api:
    """JavaScript API bridge for pywebview settings window."""

    def __init__(self, app):
        self._app = app

    def get_settings(self):
        logger.debug("JS API: get_settings called")
        return {
            "api_key": self._app.settings.get("api_key"),
            "groq_api_key": self._app.settings.get("groq_api_key"),
            "groq_model": self._app.settings.get("groq_model"),
            "shortcut": self._app.settings.get("shortcut"),
            "provider": self._app.settings.get("provider"),
        }

    def save_settings(self, settings):
        logger.info("JS API: save_settings called")
        self._app.settings.set("api_key", settings.get("api_key", ""))
        self._app.settings.set("groq_api_key", settings.get("groq_api_key", ""))
        self._app.settings.set("groq_model", settings.get("groq_model", "whisper-large-v3"))
        self._app.settings.set("shortcut", settings.get("shortcut", DEFAULTS["shortcut"]))
        self._app.settings.set("provider", settings.get("provider", "nvidia"))
        self._app.settings.save()
        self._app.reload_shortcut()

    def close_window(self):
        logger.debug("JS API: close_window called")
        self._app.close_window()


class App:
    def __init__(self):
        logger.info("App initializing…")
        self.settings = SettingsStore()
        self._state = STATE_IDLE
        self._queue = queue.Queue()
        self._tray = TrayManager(on_settings=self._open_settings, on_exit=self._exit)
        self._typer = Typer()
        self._settings_window = None
        self._keepalive = None
        self._window_lock = threading.Lock()
        self._shortcut_listener = None
        self._worker_thread = None
        self._stop_event = threading.Event()
        self._recording_stop: threading.Event | None = None
        logger.info(
            "App initialized — shortcut=%s api_key_set=%s",
            self.settings.get("shortcut"),
            bool(self.settings.get("api_key")),
        )

    # --- State Machine ---

    def _set_state(self, state: str):
        if self._state != state:
            logger.info("State: %s → %s", self._state, state)
        self._state = state
        titles = {
            STATE_IDLE: "Quill - Idle",
            STATE_LISTENING: "Quill - Listening…",
            STATE_TRANSCRIBING: "Quill - Transcribing…",
            STATE_TYPING: "Quill - Typing…",
        }
        self._tray.update_title(titles.get(state, "Quill"))

    @staticmethod
    def _beep(freq=1000, duration=200):
        try:
            winsound.Beep(freq, duration)
            logger.debug("Beep played (%d Hz)", freq)
        except Exception:
            logger.warning("Could not play beep")

    # --- Threads ---

    def _run_worker(self):
        logger.info("Worker thread started")
        while not self._stop_event.is_set():
            try:
                event = self._queue.get(timeout=QUEUE_TIMEOUT)
            except queue.Empty:
                continue
            logger.debug("Worker received event: %s", event)
            if event == EVENT_START:
                self._handle_start()
            elif event == EVENT_EXIT:
                logger.info("Worker thread exiting")
                break
            elif isinstance(event, tuple):
                event_type, payload = event
                if event_type == EVENT_TYPE:
                    logger.info("Typing transcript: %r", payload)
                    self._set_state(STATE_TYPING)
                    self._typer.type_text(payload)
                    self._set_state(STATE_IDLE)
                elif event_type == EVENT_ERROR:
                    logger.error("Error event: %s", payload)
                    self._tray.notify(str(payload), "Quill Error")
                    self._set_state(STATE_IDLE)
        logger.info("Worker thread stopped")

    def _handle_start(self):
        if self._state != STATE_IDLE:
            logger.warning("Shortcut pressed but state is %s, ignoring", self._state)
            return
        self._set_state(STATE_LISTENING)
        self._beep()
        time.sleep(BEEP_DELAY)

        stop_recording = self._recording_stop
        if stop_recording is None:
            stop_recording = threading.Event()

        logger.info("Recording audio (push-to-talk)…")
        recorder = AudioRecorder()
        try:
            wav_path = recorder.record_to_wav(stop_event=stop_recording)
            logger.info("Audio recorded to %s", wav_path)
        except Exception as e:
            logger.exception("Mic error")
            self._recording_stop = None
            self._beep(400, 300)
            self._queue.put((EVENT_ERROR, f"Mic error: {e}"))
            self._set_state(STATE_IDLE)
            return
        finally:
            recorder.close()

        self._recording_stop = None
        self._beep(400, 200)
        logger.info("Recording stopped, transcribing…")

        try:
            self._set_state(STATE_TRANSCRIBING)
            provider = self.settings.get("provider")
            if provider == "groq":
                api_key = self.settings.get("groq_api_key")
                if not api_key:
                    logger.error("No Groq API key configured")
                    self._beep(400, 200)
                    self._queue.put((EVENT_ERROR, "Groq API key missing. Open Settings."))
                    self._set_state(STATE_IDLE)
                    return
                logger.info("Sending audio to Groq for transcription…")
                groq_model = self.settings.get("groq_model")
                service = GroqTranscriptionService(api_key, model=groq_model)
            else:
                api_key = self.settings.get("api_key")
                if not api_key:
                    logger.error("No NVIDIA API key configured")
                    self._beep(400, 200)
                    self._queue.put((EVENT_ERROR, "API key missing. Open Settings."))
                    self._set_state(STATE_IDLE)
                    return
                logger.info("Sending audio to NVIDIA NIM for transcription…")
                service = NvidiaTranscriptionService(api_key)
            text = service.transcribe(wav_path)
            logger.info("Transcription result: %r", text)
        except Exception as e:
            logger.exception("Transcription failed")
            self._beep(400, 300)
            self._queue.put((EVENT_ERROR, f"Transcription failed: {e}"))
            self._set_state(STATE_IDLE)
            return
        finally:
            try:
                os.remove(wav_path)
                logger.debug("Deleted temp WAV: %s", wav_path)
            except OSError:
                pass

        if text:
            self._queue.put((EVENT_TYPE, text))
        else:
            logger.info("Transcript is empty, returning to idle")
            self._beep(400, 200)
            self._set_state(STATE_IDLE)

    # --- Shortcut ---

    def _parse_shortcut(self, shortcut_str: str):
        parts = shortcut_str.lower().replace(" ", "").split("+")
        keys = []
        for p in parts:
            p = p.strip("<>")
            if p in ("ctrl", "control"):
                keys.append(keyboard.Key.ctrl)
            elif p == "shift":
                keys.append(keyboard.Key.shift)
            elif p == "alt":
                keys.append(keyboard.Key.alt)
            elif p == "win":
                keys.append(keyboard.Key.cmd)
            elif len(p) == 1 and p.isalpha():
                # Use vk only (canonical) so it matches under modifiers (Ctrl+D -> '\x04', vk=68)
                vk = ord(p.upper()) - ord("A") + 0x41
                keys.append(keyboard.KeyCode(vk=vk))
            elif len(p) == 1 and p.isdigit():
                keys.append(keyboard.KeyCode(vk=ord(p)))
            else:
                keys.append(keyboard.KeyCode.from_char(p))
        return keys

    def _register_shortcut(self):
        shortcut_str = self.settings.get("shortcut")
        logger.info("Registering global shortcut: %s", shortcut_str)
        try:
            keys = self._parse_shortcut(shortcut_str)
            logger.info("Parsed keys: %s", keys)
            matcher = _ShortcutMatcher(
                keys,
                on_activate=self._on_shortcut_pressed,
                on_deactivate=self._on_shortcut_released,
            )

            def on_press(k):
                logger.debug("Key pressed: %s", k)
                matcher.press(k)

            def on_release(k):
                logger.debug("Key released: %s", k)
                matcher.release(k)

            self._shortcut_listener = keyboard.Listener(
                on_press=on_press, on_release=on_release
            )
            self._shortcut_listener.start()
            logger.info("Shortcut listener started (daemon=%s)", self._shortcut_listener.daemon)
        except Exception as e:
            logger.exception("Failed to register shortcut")
            self._tray.notify(f"Failed to register shortcut: {e}", "Quill Error")

    def _on_shortcut_pressed(self):
        logger.info("Shortcut pressed!")
        self._recording_stop = threading.Event()
        self._queue.put(EVENT_START)

    def _on_shortcut_released(self):
        logger.info("Shortcut released!")
        if self._recording_stop:
            self._recording_stop.set()

    def reload_shortcut(self):
        logger.info("Reloading shortcut…")
        if self._shortcut_listener:
            self._shortcut_listener.stop()
        self._register_shortcut()

    # --- UI ---

    def _create_settings_window(self, hidden=False):
        """Create the pywebview settings window."""
        ui_path = Path(__file__).parent / "ui" / "index.html"
        api = Api(self)
        self._settings_window = webview.create_window(
            "Quill Settings",
            str(ui_path.resolve()),
            width=520,
            height=660,
            resizable=False,
            js_api=api,
            hidden=hidden,
        )
        self._settings_window.events.closed += self._on_settings_window_closed
        logger.debug("Settings window created (hidden=%s)", hidden)

    def _on_settings_window_closed(self):
        """Mark settings window as destroyed so it can be recreated later."""
        logger.debug("Settings window destroyed")
        with self._window_lock:
            self._settings_window = None

    def close_window(self):
        """Hide the settings window (called from JS bridge)."""
        with self._window_lock:
            if self._settings_window is not None:
                try:
                    self._settings_window.hide()
                    logger.debug("Settings window hidden")
                except Exception:
                    pass

    def _open_settings(self):
        """Show the settings window, reloading form data."""
        logger.info("Opening settings window…")
        with self._window_lock:
            if self._settings_window is None:
                self._create_settings_window(hidden=False)
            else:
                try:
                    self._settings_window.show()
                except Exception:
                    self._settings_window = None
                    self._create_settings_window(hidden=False)
                else:
                    try:
                        self._settings_window.evaluate_js("window.quillInit?.()")
                    except Exception:
                        pass

    def _exit(self):
        """Gracefully shut down the application."""
        logger.info("Exiting Quill…")
        with self._window_lock:
            if self._settings_window is not None:
                try:
                    self._settings_window.destroy()
                except Exception:
                    pass
                self._settings_window = None
            if self._keepalive is not None:
                try:
                    self._keepalive.destroy()
                except Exception:
                    pass
        self._stop_event.set()
        self._queue.put(EVENT_EXIT)
        self._tray.stop()
        if self._shortcut_listener is not None:
            self._shortcut_listener.stop()
        if self._worker_thread is not None:
            self._worker_thread.join(timeout=5.0)
        logger.info("Quill exited")

    # --- Lifecycle ---

    def run(self):
        logger.info("Starting Quill…")
        self._set_state(STATE_IDLE)
        self._worker_thread = threading.Thread(target=self._run_worker, daemon=True)
        self._worker_thread.start()
        self._register_shortcut()

        # Create a tiny hidden keepalive window so webview.start() never exits
        self._keepalive = webview.create_window(
            "_keepalive",
            html="<html></html>",
            width=1,
            height=1,
            hidden=True,
        )

        # Create hidden settings window before starting webview
        self._create_settings_window(hidden=True)

        # pystray on the main thread — non-daemon keeps process alive
        tray_thread = threading.Thread(target=self._tray.start, daemon=False)
        tray_thread.start()
        logger.info("Tray thread started")

        # webview.start must run on the main thread
        logger.info("Entering webview main loop…")
        webview.start()
