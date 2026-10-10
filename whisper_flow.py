import os
import sys
import time
import queue
import threading
import winsound
import subprocess
import ctypes
import numpy as np
import sounddevice as sd
import tkinter as tk
import keyboard
import needle

# Suppress HuggingFace / telemetry notices
os.environ["NEEDLE_TELEMETRY"] = "0"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

user32 = ctypes.windll.user32
SAMPLE_RATE = 16000

class WhisperFlowApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Whistle Flow")
        self.root.attributes("-topmost", True)
        self.root.config(bg="#09090b")

        # Window size & position (bottom-center of screen)
        self.w, self.h = 340, 90
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        sx = (sw - self.w) // 2
        sy = sh - self.h - 120
        self.root.geometry(f"{self.w}x{self.h}+{sx}+{sy}")
        self.root.resizable(False, False)

        # State
        self.is_recording = False
        self.is_transcribing = False
        self.audio_queue = queue.Queue()
        self.stream = None
        self.last_target_hwnd = 0
        self.current_volume = 0.0

        self.build_ui()
        self.setup_hotkeys()

        # Warm up STT in background thread
        threading.Thread(target=self.warmup, daemon=True).start()

        # Window focus tracking
        self.track_focus()
        self.animate_wave()

    def build_ui(self):
        self.canvas = tk.Canvas(self.root, width=self.w, height=self.h, bg="#09090b", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Status text
        self.status_text = self.canvas.create_text(
            self.w // 2, 24,
            text="🎙️ Ready (Press F8 or Click)",
            font=("Segoe UI", 11, "bold"),
            fill="#a1a1aa"
        )

        # Waveform animation bars (7 bars)
        self.bars = []
        bar_w = 6
        spacing = 14
        start_x = (self.w - (7 * spacing)) // 2
        for i in range(7):
            bx = start_x + i * spacing
            bar = self.canvas.create_rectangle(
                bx, 55, bx + bar_w, 65,
                fill="#3f3f46", outline=""
            )
            self.bars.append((bar, bx, bar_w))

        # Click anywhere on canvas to toggle
        self.canvas.bind("<Button-1>", lambda e: self.toggle())

    def setup_hotkeys(self):
        try:
            keyboard.add_hotkey("f8", self.toggle, suppress=False)
            keyboard.add_hotkey("ctrl+shift+space", self.toggle, suppress=False)
        except Exception as e:
            print(f"[!] Hotkey error: {e}")

    def warmup(self):
        try:
            needle.transcribe(np.zeros(SAMPLE_RATE, dtype=np.float32))
        except Exception:
            pass

    def track_focus(self):
        fg = user32.GetForegroundWindow()
        my_hwnd = self.root.winfo_id()
        parent = user32.GetParent(my_hwnd) or my_hwnd
        if fg and fg != my_hwnd and fg != parent:
            self.last_target_hwnd = fg
        self.root.after(100, self.track_focus)

    def play_sound(self, freq, duration):
        def _b():
            try:
                winsound.Beep(freq, duration)
            except Exception:
                pass
        threading.Thread(target=_b, daemon=True).start()

    def toggle(self):
        if self.is_transcribing:
            return
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_and_paste()

    def start_recording(self):
        self.is_recording = True
        self.play_sound(1250, 90)

        # UI update
        self.canvas.itemconfig(self.status_text, text="🔴 Listening... Speak now", fill="#f87171")
        for bar, _, _ in self.bars:
            self.canvas.itemconfig(bar, fill="#ef4444")

        # Clear audio queue
        while not self.audio_queue.empty():
            self.audio_queue.get_nowait()

        def audio_cb(indata, frames, time_info, status):
            if self.is_recording:
                self.audio_queue.put(indata.copy())
                # Measure audio volume for live wave animation
                self.current_volume = float(np.max(np.abs(indata)))

        self.stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=audio_cb)
        self.stream.start()

    def stop_and_paste(self):
        self.is_recording = False
        self.is_transcribing = True
        self.current_volume = 0.0
        self.play_sound(750, 90)

        # UI update
        self.canvas.itemconfig(self.status_text, text="⚡ Pasting into text box...", fill="#38bdf8")
        for bar, _, _ in self.bars:
            self.canvas.itemconfig(bar, fill="#38bdf8")

        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        target = self.last_target_hwnd

        def _worker():
            chunks = []
            while not self.audio_queue.empty():
                chunks.append(self.audio_queue.get_nowait())

            if chunks:
                audio = np.concatenate(chunks, axis=0).flatten()
                if len(audio) >= int(SAMPLE_RATE * 0.4):
                    try:
                        res = needle.transcribe(audio)
                        text = (res.get("text") or "").strip()
                        if text:
                            # 1. Copy to clipboard
                            subprocess.run(["clip"], input=text.encode("utf-16le"), check=True)
                            # 2. Restore active window
                            if target and user32.IsWindow(target):
                                try:
                                    user32.SetForegroundWindow(target)
                                except Exception:
                                    pass
                            time.sleep(0.1)
                            # 3. Simulate Ctrl + V
                            user32.keybd_event(0x11, 0, 0, 0)
                            user32.keybd_event(0x56, 0, 0, 0)
                            user32.keybd_event(0x56, 0, 0x0002, 0)
                            user32.keybd_event(0x11, 0, 0x0002, 0)
                    except Exception as err:
                        print(f"[!] Transcribe error: {err}")

            self.root.after(200, self.reset_ui)

        threading.Thread(target=_worker, daemon=True).start()

    def reset_ui(self):
        self.is_transcribing = False
        self.canvas.itemconfig(self.status_text, text="🎙️ Ready (Press F8 or Click)", fill="#a1a1aa")
        for bar, _, _ in self.bars:
            self.canvas.itemconfig(bar, fill="#3f3f46")
        self.reset_bars()

    def reset_bars(self):
        for bar, bx, bw in self.bars:
            self.canvas.coords(bar, bx, 58, bx + bw, 62)

    def animate_wave(self):
        if self.is_recording:
            vol = min(1.0, self.current_volume * 4.0)
            center = 60
            for i, (bar, bx, bw) in enumerate(self.bars):
                # Harmonic wave pattern scaled by volume
                mult = (1.0 - abs(i - 3) * 0.2)
                h = max(3, int(vol * 24 * mult))
                self.canvas.coords(bar, bx, center - h, bx + bw, center + h)
        else:
            self.reset_bars()
        self.root.after(40, self.animate_wave)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    WhisperFlowApp().run()
