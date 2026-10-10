# Active Context

## Current Status
Replaced the interface with the requested per-pixel alpha layered window implementation (`UpdateLayeredWindow` + PIL supersampling + DIBSection + spring physics).

## Completed Milestones
- **2026-10-10:** Verified Python 3.11 and installed `cactus-needle` 3.1.4.
- **2026-10-10:** Implemented layered window Wispr Flow design:
  - True Windows per-pixel alpha rendering (`UpdateLayeredWindow`, GDI DIBSection)
  - Gaussian blur soft drop shadow & dynamic glow
  - 3x supersampling anti-aliased PIL rendering
  - Spring-damper physics for smooth expansion from idle (70x26) to active (190x46)
  - 21 dynamic audio waveform bars with harmonic envelope, breathing animation, and aurora gradient transitions
  - Never-steals-focus window style (`WS_EX_NOACTIVATE | WS_EX_LAYERED | WS_EX_TOOLWINDOW`)
  - Auto-paste via clipboard and simulated `Ctrl+V`
  - Hotkey toggle (<kbd>F8</kbd>, <kbd>Ctrl+Shift+Space</kbd>, <kbd>Esc</kbd> to cancel) and click-drag

## Immediate Next Steps
- Verify live user interaction with the spring-animated layered pill.
