# Spec: Whistle Flow (Production Release)

## Objective
Package, document, and publish **Whistle Flow** as an open-source, production-ready local AI voice dictation tool for Windows. It provides a pixel-perfect, ambient floating capsule UI (inspired by Wispr Flow) powered by ultra-fast local speech-to-text (~80ms via Whistle / `cactus-needle`), per-pixel alpha layered window rendering, real-time 21-bar audio waveform animation, and zero-focus-loss auto-pasting into any active text field.

---

## Tech Stack
- **Language & Runtime:** Python 3.10+ (Windows 10/11)
- **STT Engine:** `cactus-needle` (Whistle local 16.9 MB engine)
- **Audio Capture:** `sounddevice`, `numpy` (16 kHz mono float32)
- **Window & Graphics:** `tkinter`, `PIL` (Pillow), Win32 API (`UpdateLayeredWindow`, GDI `CreateDIBSection`, per-pixel alpha)
- **Hotkeys & Input:** `keyboard`, Win32 `keybd_event` (for simulated clipboard paste)
- **Process Launcher:** VBScript / Windows Script Host (`wscript.exe`) for detached background execution

---

## Commands
- **Install dependencies:** `pip install -r requirements.txt`
- **Run application:** `python whisper_flow.py`
- **Silent launcher:** `wscript run_pill.vbs`
- **Run test verification:** `python -m unittest discover tests`
- **Lint/Check:** `python -m py_compile whisper_flow.py`

---

## Project Structure
A minimal, clean repository without dead scratch prototypes:
```text
├── .gitignore               → Git ignore patterns (__pycache__, logs, models, venv)
├── LICENSE                  → Open source license (MIT)
├── README.md                → Full production documentation, architecture, install & usage guide
├── SPEC.md                  → This specification
├── requirements.txt         → Minimal pinned dependencies
├── run_pill.vbs             → Zero-console background launcher for Windows
├── whisper_flow.py          → Core application (Layered UI, STT, hotkeys, auto-paste)
├── docs/
│   └── active_context.md    → Project context, decisions, and history
└── tests/
    └── test_smoke.py        → Unit and smoke tests for STT and audio pipeline
```
*(Legacy prototype scratch scripts `whistle_flow_widget.py`, `simple_whistle.py`, `record_and_transcribe.py`, `whisperflow.py`, `launch_widget.bat` will be cleaned up/removed to ensure a clean public repo).*

---

## Code Style & Conventions
- Single responsibility modules with minimal boilerplate.
- Suppress external noisy telemetry/warnings at startup before imports:
  ```python
  os.environ["NEEDLE_TELEMETRY"] = "0"
  os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
  ```
- Windows API calls typed via `ctypes.wintypes`.
- Explicit resource management for audio streams and GDI handles.

---

## Testing Strategy
- **Smoke test:** Headless verification that `needle` model loads and transcribes silent numpy arrays in `< 150ms`.
- **Audio test:** Verify `sounddevice` input stream initializes at 16 kHz without hardware crash.
- **Surface test:** Verify `LayeredSurface` GDI allocation and composite generation without memory leaks.

---

## Boundaries
- **Always:** Keep local offline privacy intact (zero external network requests for audio).
- **Always:** Maintain non-intrusive focus (`WS_EX_NOACTIVATE`) so user typing is never interrupted.
- **Never:** Commit credentials, tokens, temporary wave recordings, or virtual environment files.
- **Ask first:** Before pushing to GitHub, confirm repository name and remote URL.

---

## Success Criteria
1. Clean repository with obsolete scratch scripts removed and tracked files organized.
2. `requirements.txt`, `README.md`, `LICENSE`, and `tests/` present.
3. Tests pass cleanly via `python -m unittest`.
4. Git commit created with all clean documentation.
5. GitHub remote configured and repository published.

---

## Open Questions & Assumptions
1. **GitHub Repository Name & URL:** What repository name should we use on your GitHub (e.g. `https://github.com/hermon/whistle-flow.git`)? Have you already created the empty repo on GitHub, or do you have a personal access token / SSH key set up?
2. **Scratch file cleanup:** Confirm removing early prototype scripts (`record_and_transcribe.py`, `simple_whistle.py`, `whisperflow.py`, `whistle_flow_widget.py`) so your public repository contains only the clean production files.
