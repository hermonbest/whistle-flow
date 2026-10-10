# 🎙️ Whistle Flow

An ambient, lightweight, ultra-fast local voice dictation pill for Windows — inspired by the design and fluid physics of **Wispr Flow**, powered on-device with **INT8 Vector Acceleration** (`faster-whisper` + Whistle).

Speak into any application on your machine and have your words transcribed and typed into your active text box in under **half a second** after releasing the key — with **zero cloud dependencies** and **no focus loss**.

---

## ✨ Features

- **Ambient Layered Capsule UI:** Pixel-perfect floating capsule using Windows per-pixel alpha (`UpdateLayeredWindow`), GDI DIBSection, and soft Gaussian drop shadows.
- **Push-To-Talk & Tap-To-Lock:** Hold <kbd>Ctrl</kbd> + <kbd>Space</kbd> to talk, release to paste. Quick tap locks into hands-free mode.
- **Hardware INT8 Vector Acceleration:** Uses Intel AVX-512 VNNI neural vector instructions via `faster-whisper` (CTranslate2 INT8) to decode 15 seconds of speech in just **`~500 ms`**!
- **Dynamic Silence Trimming:** Energy-based RMS silence gating trims dead air to avoid Whisper hallucinations on quiet speech and keep latency ultra-low.
- **Spring-Damper Dynamics:** Smooth, elastic animation that expands from a compact idle pill ($70 \times 26\text{px}$) to an active dictation bar ($190 \times 46\text{px}$) with natural physics.
- **21-Bar Real-Time Aurora Waveform:** Dynamic multi-harmonic audio visualizer reacting in real-time to your voice volume with aurora gradient sweeps during processing.
- **Never Steals Focus (`WS_EX_NOACTIVATE`):** Click or hotkey-trigger the pill without pulling keyboard focus away from Word, Slack, Discord, Chrome, or your IDE.
- **100% Offline & Private:** Audio never leaves your machine. Telemetry and cloud network checks are completely disabled.

---

## 🏗️ Architecture

```
User Voice (16 kHz) ──→ sounddevice (InputStream)
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
       21-Bar Aurora Wave              Audio Buffer (FIFO)
     (PIL Supersampling DIB)                   │
               │                               ▼
               ▼                     RMS Energy Silence Gating
   Windows Layered Surface                     │
    (UpdateLayeredWindow)                      ▼
                                      faster-whisper (INT8)
                                     (AVX-512 VNNI Acceleration)
                                               │
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
git clone https://github.com/hermonbest/whistle-flow.git
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

### 4. Automatic Startup with Windows (Ambient Mode)

Whistle Flow is designed to be an ambient desktop companion that is always ready without requiring you to manually open a terminal or run a script:

- Copy `run_pill.vbs` into your Windows Startup folder (`shell:startup`), or run this one-liner in PowerShell:

```powershell
Copy-Item "run_pill.vbs" "$([Environment]::GetFolderPath('Startup'))\Whistle_Flow.vbs"
```

Once installed, Whistle Flow automatically starts up with Windows in the background. A built-in Windows named mutex (`WhistleFlowSingleInstanceMutex`) guarantees only one background instance runs at any time, preventing duplicate collisions.

---

## ⌨️ Controls & Hotkeys

| Action | Control | Description |
| :--- | :--- | :--- |
| **Push-To-Talk** | Hold <kbd>Ctrl</kbd> + <kbd>Space</kbd> ($> 300\text{ms}$) | Speak while holding; release to immediately stop and paste |
| **Hands-Free Lock** | Tap <kbd>Ctrl</kbd> + <kbd>Space</kbd> ($< 300\text{ms}$) | Quick tap locks recording on; tap again when finished |
| **Fallback Toggle** | <kbd>F8</kbd> | Classic toggle shortcut |
| **Click / Drag** | Mouse Left-Click & Drag | Click to toggle; drag anywhere to reposition |
| **Cancel** | <kbd>Esc</kbd> | Immediately discard audio clip without pasting |
| **Close** | Right-click on pill | Clean exit |

---

## 🧪 How to Test It

### A. Live Interactive Test (Try it now)

1. **Launch the pill:**
   Run `python whisper_flow.py` (or double-click the desktop shortcut `Whistle Flow (Voice to Cursor)`).
   You will see the small dark pill floating above your taskbar.

2. **Test Push-To-Talk (Hold to Speak):**
   - Click your text cursor into **Notepad**, a browser address bar, Slack, or any text field.
   - **Press and hold** <kbd>Ctrl</kbd> + <kbd>Space</kbd>.
   - Notice the pill springs open, turns white, and the 21 waveform bars dance to your voice.
   - Say: *"This is a test of Whistle Flow push to talk."*
   - **Release** <kbd>Ctrl</kbd> + <kbd>Space</kbd>.
   - The pill pulses green, and the text appears directly in your cursor field in under **50 ms**!

3. **Test Hands-Free Mode (Tap-to-Lock):**
   - Quickly **tap** <kbd>Ctrl</kbd> + <kbd>Space</kbd> (under 300 ms) and let go.
   - The pill stays open in recording mode hands-free.
   - Speak your sentence.
   - Tap <kbd>Ctrl</kbd> + <kbd>Space</kbd> again to finish and paste.

4. **Test Cancel:**
   - Hold <kbd>Ctrl</kbd> + <kbd>Space</kbd>, then press <kbd>Esc</kbd> — the recording will cancel without pasting.

---

### B. Automated Smoke Test Suite

Run the unit tests from the terminal:

```bash
python -m unittest discover tests
```

Tests cover:
- Headless model transcription latency (`< 150ms`).
- LayeredSurface GDI DIBSection memory allocation.
- Push-to-Talk vs Tap-to-Lock state transitions.
- Leading/trailing silence energy gating.

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

## 📄 License

This project is licensed under the [MIT License](LICENSE).
