# Active Context

## Current Status
Implemented and verified:
1. Push-To-Talk and Tap-To-Lock state machine with primary hotkey <kbd>Ctrl + Space</kbd> (hold $> 300\text{ms}$ = PTT, tap $< 300\text{ms}$ = hands-free lock).
2. Live streaming chunk transcription (`needle.stream`) and RMS silence trimming for instantaneous (< 50ms) release-to-paste latency.
3. Preserved full visual 21-bar real-time aurora waveform animation and per-pixel alpha layered window.

## Completed Milestones
- **2026-10-10:** Verified Python 3.11 and installed `cactus-needle` 3.1.4.
- **2026-10-10:** Implemented layered window Wispr Flow design with spring physics and 21-bar aurora visualizer.
- **2026-10-10:** Upgraded interaction to Push-To-Talk via <kbd>Ctrl + Space</kbd> and real-time streaming STT.
- **2026-10-10:** Added PTT and silence trimming tests to `tests/test_smoke.py` (all tests passing).
- **2026-10-10:** Integrated Windows named single-instance mutex (`WhistleFlowSingleInstanceMutex`) preventing duplicate colliding processes.
- **2026-10-10:** Configured ambient auto-launch on boot via Windows Startup folder (`Whistle_Flow.vbs`).
- **2026-10-10:** Successfully tested and verified live dictation by user ("it works").
- **2026-10-10:** Resolved long-speech truncation: implemented full audio tail flushing, removed premature 600ms worker join timeout, protected single-model C memory with `needle_lock`, captured uncommitted pending tail on stream completion, and added 5th automated test in `tests/test_smoke.py`.
- **2026-10-10:** Fixed 20s delay & 3-4s lag: enforced 100% offline mode by pinning local `.cact` weights and `HF_HUB_OFFLINE=1` (eliminating Hugging Face network timeouts), replaced polling queue loop with instant teardown in `chunk_generator`, added millisecond-accurate structured file logging to `whisper_flow.log`, and reduced test suite execution from 22.2s to 0.073s.
- **2026-10-10:** Ponytail simplification: diagnosed quadratic CPU streaming bottleneck and mutex deadlock from `whisper_flow.log`, eliminated complex background streaming threads, locks, queues, and timeouts. Replaced with lean, single-pass atomic `needle.transcribe` with RMS silence trimming on release.
- **2026-10-10:** Integrated `faster-whisper` INT8 vector acceleration with AVX-512 VNNI: reduced 14s speech decode latency from 7,011ms down to 518ms (~13x speedup). Updated smoke tests and requirements.
- **2026-10-10:** Integrated `pycaw` background audio muting (mutes Spotify, Discord, YouTube, Edge while recording) and synthesized subtle tactile clicks via `sounddevice` to replace harsh PC beeps.
- **2026-10-10:** Built automated 1-click startup installer (`setup_autostart.py` & `install_startup.bat`) auto-detecting `pythonw.exe` and configuring `HKCU\Run` + `shell:startup`.
- **2026-10-10:** Completed `/ponytail-audit` pruning: eliminated legacy fallback code, dropped `cactus-needle` dependency, removed stale assets, simplified startup forwarder.
- **2026-10-10:** Updated `README.md` to accurately document the streamlined, single-engine architecture and 1-click installer.
- **2026-10-10:** Repository published and synced to `https://github.com/hermonbest/whistle-flow.git`.
- **2026-10-16:** Integrated Fermion Research **Phonon-2** as a secondary speech engine alongside `faster-whisper`.
- **2026-10-16:** Implemented Option 1 (WebSocket live streaming preview): streams audio over `/v1/audio/stream`, displaying live words in real time on the smoothly expanding capsule with animated cursor dot and near-zero release-to-paste latency.
- **2026-10-16:** Added on-the-fly engine toggle (<kbd>F9</kbd> hotkey and `--engine` CLI argument) with visual toast notifications and persistent `config.json`.
- **2026-10-16:** Expanded smoke test suite in `tests/test_smoke.py` to 9 tests covering config, streaming framing, and live text rendering.

## Status
- Fully operational with dual-engine comparison: toggle between Faster-Whisper (INT8 multilingual atomic) and Phonon-2 (TDT live streaming preview) with <kbd>F9</kbd>.
