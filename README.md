# 🎙️ Whistle Flow

An ambient, lightweight, ultra-fast local voice dictation pill for Windows — inspired by the design and fluid physics of **Wispr Flow**, powered entirely on-device by **Whistle** (`cactus-needle`).

Speak into any application on your machine and have your words transcribed and typed into your active text box in under **100 milliseconds** — with **zero cloud dependencies** and **no focus loss**.

---

## ✨ Features

- **Ambient Layered Capsule UI:** Pixel-perfect floating capsule using Windows per-pixel alpha (`UpdateLayeredWindow`), GDI DIBSection, and soft Gaussian drop shadows.
- **Spring-Damper Dynamics:** Smooth, elastic animation that expands from a compact idle pill ($70 \times 26\text{px}$) to an active dictation bar ($190 \times 46\text{px}$) with natural physics.
- **21-Bar Real-Time Aurora Waveform:** Dynamic multi-harmonic audio visualizer reacting in real-time to your voice volume with aurora gradient sweeps during processing.
- **Ultra-Fast Local Transcription:** Powered by Whistle's compact 16.9 MB local model. Transcription latencies consistently average **~80 ms** on standard PC hardware.
- **Never Steals Focus (`WS_EX_NOACTIVATE`):** Click or hotkey-trigger the pill without pulling keyboard focus away from Word, Slack, Discord, Chrome, or your IDE.
- **System-Wide Hotkeys:** Push-to-talk or tap-to-talk anywhere using <kbd>F8</kbd> or <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>Space</kbd> (<kbd>Esc</kbd> to cancel).
- **100% Offline & Private:** Audio never leaves your machine. Telemetry is explicitly disabled.

---

## 🏗️ Architecture

```
User Voice (16 kHz) ──→ sounddevice (InputStream)
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
       21-Bar Aurora Wave              Whistle STT Engine
     (PIL Supersampling DIB)         (~80ms Local Model)
               │                               │
               ▼                               ▼
   Windows Layered Surface               Text Output
    (UpdateLayeredWindow)                      │
                                               ▼
                                    Win32 Auto-Paste
                              (Clipboard + Ctrl+V Injection)
```

---

## 🚀 Quick Start

### 1. Requirements
- Windows 10 or Windows 11
- Python 3.10+
- Working microphone

### 2. Installation

Clone this repository and install the minimal dependencies:

```bash
git clone https://github.com/hermon/whistle-flow.git
cd whistle-flow
pip install -r requirements.txt
```

### 3. Run

To launch the interactive floating pill:

```bash
python whisper_flow.py
```

Or run silently in the background (no console window):

```cmd
wscript run_pill.vbs
```

---

## ⌨️ Controls & Hotkeys

| Action | Control | Description |
| :--- | :--- | :--- |
| **Start / Stop Dictation** | <kbd>F8</kbd> or <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>Space</kbd> | Toggle speech recording on or off |
| **Click to Dictate** | Left-click on pill | Alternate mouse toggle |
| **Move Pill** | Click and drag | Reposition the pill anywhere on your screen |
| **Cancel** | <kbd>Esc</kbd> | Discard current audio clip without pasting |
| **Close App** | Right-click on pill | Clean exit |

---

## 📦 File Structure

```text
├── .gitignore          # Git ignore rules
├── LICENSE             # MIT License
├── README.md           # Documentation
├── SPEC.md             # Technical design specification
├── requirements.txt    # Pinned production dependencies
├── run_pill.vbs        # Background Windows script host launcher
├── whisper_flow.py     # Main application engine
├── docs/
│   └── active_context.md # Development history and context
└── tests/
    └── test_smoke.py   # Automated smoke test suite
```

---

## 🧪 Testing

Run the test suite:

```bash
python -m unittest discover tests
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
