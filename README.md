
<div align="center">
  <img src="assets/icon.png" width="144" height="144" alt="Quill" />
  <h1>Quill</h1>

  <p><strong>Dictation bridge that types your voice into any app</strong></p>

  <p>
    <img src="https://img.shields.io/badge/version-1.1.0-blue" alt="version" />
    <img src="https://img.shields.io/badge/license-MIT-green" alt="license" />
    <img src="https://img.shields.io/badge/platform-Windows-lightgrey" alt="platform" />
    <img src="https://img.shields.io/badge/python-3.12-blue" alt="python" />
  </p>
</div>

---

Quill runs in your system tray. Press a global hotkey, speak, and it types the transcribed text into your active window—code editor, browser, chat app, anywhere.

## What it does

**Dictation**
- Types directly into any active window using keyboard simulation
- Audio cue (configurable beep) signals when listening and when transcription completes

**STT providers**
- NVIDIA NIM (Parakeet-1.1b)
- Groq (Whisper V3, Whisper Flash)

**Architecture**
- Free API tiers, no heavy local compute required
- Global hotkey listener runs silently in the background
- Switch providers and models in settings

## Where config lives

| Platform | Path |
| :--- | :--- |
| **Windows** | `%APPDATA%/QuillApp` |

## Install

**Requirements**
- [Python 3.12](https://www.python.org/)
- API keys for NVIDIA or Groq

```bash
git clone https://github.com/noahain/quill
cd quill
py -3.12 -m pip install -r requirements.txt
py -3.12 main.py
```

## Tech stack

Python 3.12 · `pywebview` · HTML/CSS/JS · NVIDIA NIM · Groq

## Development story

- **Lead:** Noahain - product vision, logic direction
- **Primary developer:** OpenCode (Kimi K2.6) - global hotkey listeners, API integrations, frontend state
- **Technical consultant:** DeepSeek V4 Pro - architecture, audio buffer handling, keyboard simulation

## License

MIT

