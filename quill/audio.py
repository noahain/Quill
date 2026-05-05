import logging
import math
import os
import struct
import tempfile
import threading
import wave
import pyaudio

logger = logging.getLogger("quill.audio")

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
SILENCE_THRESHOLD = 500
SILENCE_CHUNKS = 30
MAX_RECORD_SECONDS = 30


class AudioRecorder:
    def __init__(self):
        self._audio = pyaudio.PyAudio()

    def _is_silence(self, data: bytes) -> bool:
        if len(data) < 2:
            return True
        count = len(data) // 2
        fmt = f"{count}h"
        samples = struct.unpack(fmt, data[:count * 2])
        rms = math.sqrt(sum(s * s for s in samples) / count)
        return rms < SILENCE_THRESHOLD

    def record_chunk(self, stop_event: threading.Event | None = None) -> bytes:
        logger.info("Starting audio recording (push-to-talk=%s)…", stop_event is not None)
        stream = self._audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )
        frames: list[bytes] = []
        max_chunks = int(RATE / CHUNK * MAX_RECORD_SECONDS)

        if stop_event is not None:
            # Push-to-talk: record until stop_event is set
            for _ in range(max_chunks):
                if stop_event.is_set():
                    logger.info("Stop event received, stopping recording")
                    break
                try:
                    data = stream.read(CHUNK, exception_on_overflow=False)
                except OSError:
                    logger.warning("OSError during stream.read, stopping")
                    break
                if not data:
                    break
                frames.append(data)
        else:
            # Silence-detection mode
            silent_chunks = 0
            for i in range(max_chunks):
                try:
                    data = stream.read(CHUNK, exception_on_overflow=False)
                except OSError:
                    logger.warning("OSError during stream.read, stopping")
                    break
                if not data:
                    break
                frames.append(data)
                if self._is_silence(data):
                    silent_chunks += 1
                    if silent_chunks >= SILENCE_CHUNKS:
                        logger.info("Silence detected after %d chunks, stopping", i)
                        break
                else:
                    silent_chunks = 0

        stream.stop_stream()
        stream.close()
        logger.info("Recorded %d frames (%d bytes)", len(frames), len(b"".join(frames)))
        return b"".join(frames)

    def record_to_wav(self, stop_event: threading.Event | None = None) -> str:
        frames = self.record_chunk(stop_event=stop_event)
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        with wave.open(path, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(self._audio.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(frames)
        logger.info("WAV saved to %s", path)
        return path

    def close(self):
        logger.debug("Terminating PyAudio")
        self._audio.terminate()
