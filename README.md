![Quill Banner](assets/banner.png)

**Quill** is a lightweight, low-latency dictation bridge that brings enterprise-grade Speech-to-Text to any application. By leveraging high-performance AI models, it transforms your voice into keystrokes instantly, providing a seamless "talk-to-type" experience via a global system hotkey.

## 🚀 Advanced Features

### 🧠 Intelligent Dictation
- **Universal Input**: Types directly into your active window—whether it's a code editor, browser, or chat app—simulating natural keyboard input.
- **Multimodal STT Support**: Choose between **NVIDIA NIM** (Parakeet-1.1b) or **Groq** (OpenAI Whisper V3 & Flash) for lightning-fast transcription.
- **Auditory Cues**: Immediate SFX feedback (configurable beep) to signal when the app is "listening" and when transcription is complete.

### 🔒 Privacy & Architecture
- **API-Driven Efficiency**: Utilizes free-tier limits from NVIDIA and Groq, ensuring high-performance ASR without the heavy local compute requirements.
- **Global Hotkey Listener**: Runs silently in the background, listening for your custom key combination to trigger the recording session.
- **Dynamic Configuration**: Easily swap between providers and models in the settings to optimize for speed or accuracy.

### 📂 Data & Configuration
Quill maintains a minimal footprint on your system:
- **Default Directory:** `%APPDATA%/QuillApp`

---

## 🛠️ Tech Stack

Quill is built using a modern, lightweight desktop architecture:
- **Backend**: **Python 3.12** handling global hotkey hooks, audio recording, and API orchestration.
- **Frontend**: **HTML5/CSS3/JS** bundled within a **pywebview** window for a native, Electron-free experience.
- **AI Integration**: REST clients for NVIDIA NIM and Groq API endpoints.
- **System Integration**: Keyboard simulation for automated typing across the Windows environment.

---

## 📥 Installation

### 1. Prerequisites
Ensure you have [Python 3.12](https://www.python.org/) installed and your API keys ready (NVIDIA/Groq).

### 2. Setup
```bash
# Clone the repository
git clone https://github.com/noahain/quill

# Enter the project folder
cd quill

# Install dependencies
py -3.12 -m pip install -r requirements.txt

# Run the app
py -3.12 main.py
```

---

## 🤖 Agentic Development

Quill was developed through an advanced **Human-AI Collaboration** workflow:
- **Lead Architect:** Noahain (Product Vision & Logic Direction)
- **Primary Developer:** **OpenCode** (Powered by **Kimi K2.6**) - Implemented the global hotkey listeners, API integrations, and the core frontend state management.
- **Technical Consultant:** **DeepSeek V4 Pro MAX** - Provided architectural guidance, optimized audio buffer handling, and refined the keyboard simulation logic.

---

## ⚖️ License & Disclaimer

**License:** MIT 

Built with ❤️ and Artificial Intelligence.

