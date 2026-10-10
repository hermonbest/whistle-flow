# Spec: Whistle Flow - Push-To-Talk & Streaming Transcription Upgrade

## Objective
Upgrade Whistle Flow's core UX to match the responsive feel of **Wispr Flow**:
1. **Fluid Push-To-Talk & Hands-Free Tap-To-Lock:**
   - Replace the legacy two-click/two-press interaction with natural push-to-talk.
   - Hold <kbd>Right Ctrl</kbd> (or configurable key) for $> 300\text{ms}$ $\rightarrow$ speak $\rightarrow$ release to paste immediately.
   - Short tap ($< 300\text{ms}$) $\rightarrow$ locks into hands-free dictation mode (tap again to finish).
   - <kbd>Esc</kbd> cancels dictation at any time with a cancel sound cue.
2. **Low-Latency Streaming Chunk Transcription & Silence Trimming:**
   - Stream audio buffers in ~1.0s increments into `needle.stream()` in real time as the user speaks.
   - Leading and trailing silence trimmed via dynamic energy/RMS threshold to eliminate Whisper hallucinations and reduce wasted inference.
   - On key release, only the small final buffer ($< 0.3\text{s}$) is processed, dropping perceived release-to-paste latency to under $50\text{ms}$.

---

## Assumptions
1. Key selection: Default to <kbd>Right Ctrl</kbd> (`right ctrl`) since Windows cannot intercept the proprietary hardware `Fn` key, and `Right Ctrl` does not interfere with standard typing or shortcuts.
2. Secondary hotkeys: Retain <kbd>F8</kbd> and <kbd>Ctrl+Shift+Space</kbd> as fallback toggle shortcuts.
3. Streaming STT: Use Whistle's built-in `needle.stream(chunks)` generator rather than introducing new heavyweight external streaming servers.
4. Silence trimming: Implement zero-dependency NumPy RMS/energy gating to keep execution ultra-fast and self-contained.

---

## Tech Stack
- **Language & Runtime:** Python 3.10+ (Windows 10/11)
- **STT Engine:** `cactus-needle` (`needle.stream` live streaming chunk generator)
- **Audio Capture & VAD:** `sounddevice`, `numpy` (16 kHz mono float32 with RMS threshold gating)
- **Window & Graphics:** `tkinter`, `PIL` (Pillow), Win32 API (`UpdateLayeredWindow`, GDI DIBSection)
- **Input & Hotkeys:** `keyboard` (`on_press_key`, `on_release_key`), Win32 `keybd_event`

---

## Commands
- **Run Application:** `python whisper_flow.py`
- **Run Silent Launcher:** `wscript run_pill.vbs`
- **Run Verification Suite:** `python -m unittest discover tests`

---

## Project Structure
```text
├── .gitignore               → Git ignore patterns
├── LICENSE                  → MIT License
├── README.md                → Documentation with PTT & streaming usage
├── SPEC.md                  → This specification
├── requirements.txt         → Production dependencies
├── run_pill.vbs             → Zero-console background launcher
├── whisper_flow.py          → Application with PTT listener, streaming STT, and layered UI
├── docs/
│   └── active_context.md    → Project context & milestones
└── tests/
    └── test_smoke.py        → Unit tests for streaming chunk generator and VAD
```

---

## Code Style & Implementation Details
- **PTT State Machine:**
  ```python
  # Push-to-Talk vs Tap-to-Lock state logic
  HOLD_THRESHOLD = 0.30  # 300 ms

  def on_key_down(e):
      self.press_time = time.perf_counter()
      if not self.is_recording:
          self.start_recording()

  def on_key_up(e):
      duration = time.perf_counter() - self.press_time
      if duration >= HOLD_THRESHOLD:
          # Held down: Push-To-Talk -> finish and paste
          self.stop_and_paste()
      else:
          # Short tap: Lock in hands-free mode (toggle)
          if self.is_locked:
              self.stop_and_paste()
              self.is_locked = False
          else:
              self.is_locked = True
  ```
- **Streaming Pipeline:**
  A dedicated background worker feeds incoming 16 kHz buffers to `needle.stream(chunk_generator)` as they arrive, accumulating confirmed text tokens in real time.

---

## Testing Strategy
- Unit test streaming chunk generation (`tests/test_smoke.py`): verify feeding three 1.0s numpy arrays to `needle.stream` yields tokens and closes cleanly without deadlock.
- Unit test RMS silence trim logic: verify silence buffers are properly clipped without corrupting audio amplitude.

---

## Boundaries
- **Always:** Keep processing 100% on-device and local.
- **Always:** Preserve the smooth per-pixel alpha capsule UI and dynamic 21-bar waveform.
- **Never:** Block the main GUI/animation loop on audio inference threads.
- **Ask first:** Before changing the default trigger key from <kbd>Right Ctrl</kbd>.

---

## Success Criteria
1. Holding <kbd>Right Ctrl</kbd> records; releasing immediately stops and pastes.
2. Tapping <kbd>Right Ctrl</kbd> (< 300ms) locks hands-free recording; tapping again finishes and pastes.
3. Transcription is streamed in real time during speech so release-to-paste latency is $< 50\text{ms}$.
4. Tests pass cleanly via `python -m unittest discover tests`.
5. Code committed and ready for push.

---

## Open Questions
1. Is **<kbd>Right Ctrl</kbd>** the preferred default key for push-to-talk, or would you prefer **<kbd>Caps Lock</kbd>** or **<kbd>Right Alt</kbd>**?
2. Do you want the live transcribed partial words displayed above the waveform in real time while speaking, or keep the pill clean with only the animated aurora wave?
