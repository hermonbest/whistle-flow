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
- **2026-10-10:** Resolved long-speech truncation: implemented full audio tail flushing, removed premature 600ms worker join timeout (increased to 4.0s drain), protected single-model C memory with `needle_lock`, captured uncommitted pending tail on stream completion, and added 5th automated test in `tests/test_smoke.py`.
- **2026-10-10:** Repository published and synced to `https://github.com/hermonbest/whistle-flow.git`.

## Status
- Fully operational and running ambiently in background. Auto-starts with Windows. High fidelity on long dictations.
