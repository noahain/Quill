import json
import logging
import threading
from pathlib import Path
from platformdirs import user_data_dir

logger = logging.getLogger("quill.config")

DEFAULTS = {
    "api_key": "",
    "groq_api_key": "",
    "groq_model": "whisper-large-v3",
    "shortcut": "<ctrl>+<shift>+d",
    "output_language": "en-US",
    "provider": "nvidia",
}


class SettingsStore:
    def __init__(self, path: Path | None = None):
        if path is None:
            data_dir = Path(user_data_dir("Quill", "QuillApp"))
            data_dir.mkdir(parents=True, exist_ok=True)
            path = data_dir / "settings.json"
        self._path = Path(path)
        self._data = dict(DEFAULTS)
        self._lock = threading.RLock()
        self._load()

    def _load(self):
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                self._data.update(loaded)
                logger.info("Loaded settings from %s", self._path)
            except (json.JSONDecodeError, IOError):
                logger.warning("Failed to load settings from %s", self._path)
        else:
            logger.info("No settings file at %s, using defaults", self._path)

    def save(self):
        with self._lock:
            safe_data = dict(self._data)
            for key in ("api_key", "groq_api_key"):
                if safe_data.get(key):
                    safe_data[key] = safe_data[key][:4] + "\u2026"
            logger.info("Saving settings to %s: %s", self._path, json.dumps(safe_data))
            try:
                with open(self._path, "w", encoding="utf-8") as f:
                    json.dump(self._data, f, indent=2)
            except (IOError, OSError) as e:
                logger.error("Failed to write settings: %s", e)

    def get(self, key: str):
        with self._lock:
            return self._data.get(key, DEFAULTS.get(key))

    def set(self, key: str, value):
        with self._lock:
            self._data[key] = value

    def update(self, values: dict, *, save: bool = True) -> None:
        """Atomically update multiple settings and persist."""
        with self._lock:
            self._data.update(values)
            if save:
                safe_data = dict(self._data)
                for k in ("api_key", "groq_api_key"):
                    if safe_data.get(k):
                        safe_data[k] = safe_data[k][:4] + "\u2026"
                logger.info("Saving settings to %s: %s", self._path, json.dumps(safe_data))
                try:
                    with open(self._path, "w", encoding="utf-8") as f:
                        json.dump(self._data, f, indent=2)
                        f.flush()
                except (IOError, OSError) as e:
                    logger.error("Failed to write settings: %s", e)
