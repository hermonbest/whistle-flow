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

os.environ["NEEDLE_TELEMETRY"] = "0"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

user32 = ctypes.windll.user32
SAMPLE_RATE = 16000

class WisprPillApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Wispr Flow")

        # Color palette matching the Wispr Flow screenshot
        self.TRANS_COLOR = "#000001"
        self.BORDER_COLOR = "#ffffff"
        self.BG_COLOR = "#1c1c1e"
        self.DOT_COLOR = "#d1d5db"
        self.ACTIVE_COLOR = "#ffffff"
        self.PASTE_COLOR = "#38bdf8"

        # Dimensions & positioning
        self.pill_w = 190
        self.pill_h = 52
        self.radius = self.pill_h // 2
        self.win_w = self.pill_w + 10
        self.win_h = self.pill_h + 10

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        sx = (sw - self.win_w) // 2
        sy = sh - self.win_h - 100

        self.root.geometry(f"{self.win_w}x{self.win_h}+{sx}+{sy}")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.config(bg=self.TRANS_COLOR)
        self.root.wm_attributes("-transparentcolor", self.TRANS_COLOR)

        # State
        self.is_recording = False
        self.is_transcribing = False
        self.audio_queue = queue.Queue()
        self.stream = None
        self.last_target_hwnd = 0
        self.current_volume = 0.0
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.dragged = False

        self.build_pill_ui()
        self.setup_controls()

        # Warm up STT in background thread
        threading.Thread(target=self.warmup, daemon=True).start()

        # Lifecycle loops
        self.track_focus()
        self.animate_waveform()

    def build_pill_ui(self):
        self.canvas = tk.Canvas(
            self.root,
            width=self.win_w,
            height=self.win_h,
            bg=self.TRANS_COLOR,
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)

        ox, oy = 5, 5
        pw, ph, r = self.pill_w, self.pill_h, self.radius

        # Pill background fill (capsule: 2 circles + central rectangle)
        self.bg_left = self.canvas.create_oval(ox, oy, ox + 2*r, oy + 2*r, fill=self.BG_COLOR, outline=self.BG_COLOR)
        self.bg_right = self.canvas.create_oval(ox + pw - 2*r, oy, ox + pw, oy + 2*r, fill=self.BG_COLOR, outline=self.BG_COLOR)
        self.bg_rect = self.canvas.create_rectangle(ox + r, oy, ox + pw - r, oy + 2*r, fill=self.BG_COLOR, outline=self.BG_COLOR)

        # Crisp border (arcs + top/bottom lines)
        self.border_left = self.canvas.create_arc(ox, oy, ox + 2*r, oy + 2*r, start=90, extent=180, style="arc", outline=self.BORDER_COLOR, width=3)
        self.border_right = self.canvas.create_arc(ox + pw - 2*r, oy, ox + pw, oy + 2*r, start=270, extent=180, style="arc", outline=self.BORDER_COLOR, width=3)
        self.border_top = self.canvas.create_line(ox + r, oy + 1.5, ox + pw - r, oy + 1.5, fill=self.BORDER_COLOR, width=3)
        self.border_bot = self.canvas.create_line(ox + r, oy + 2*r - 1.5, ox + pw - r, oy + 2*r - 1.5, fill=self.BORDER_COLOR, width=3)

        # Centered waveform dots (9 dots matching user image)
        self.dots = []
        num_dots = 9
        dot_spacing = 13
        start_x = ox + (pw - (num_dots - 1) * dot_spacing) // 2
        cy = oy + r

        for i in range(num_dots):
            dx = start_x + i * dot_spacing
            # Small rounded bar/dot
            bar = self.canvas.create_line(dx, cy - 2, dx, cy + 2, fill=self.DOT_COLOR, width=4, capstyle="round")
            self.dots.append((bar, dx, cy))

    def setup_controls(self):
        # Click and drag support
        self.canvas.bind("<Button-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        # Right click to quit
        self.canvas.bind("<Button-3>", lambda e: (self.root.destroy(), sys.exit(0)))

        # Global hotkeys
        try:
            keyboard.add_hotkey("f8", self.toggle, suppress=False)
            keyboard.add_hotkey("ctrl+shift+space", self.toggle, suppress=False)
        except Exception:
            pass

    def on_press(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.dragged = False

    def on_drag(self, event):
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        if abs(dx) + abs(dy) > 4:
            self.dragged = True
            nx = self.root.winfo_x() + dx
            ny = self.root.winfo_y() + dy
            self.root.geometry(f"+{nx}+{ny}")

    def on_release(self, event):
        if not self.dragged:
            self.toggle()

    def warmup(self):
        try:
            needle.transcribe(np.zeros(SAMPLE_RATE, dtype=np.float32))
        except Exception:
            pass

    def track_focus(self):
        fg = user32.GetForegroundWindow()
        my_h = self.root.winfo_id()
        if fg and fg != my_h:
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
        self.play_sound(1300, 80)

        # Visual indicator: glowing dots
        for bar, _, _ in self.dots:
            self.canvas.itemconfig(bar, fill=self.ACTIVE_COLOR)

        while not self.audio_queue.empty():
            self.audio_queue.get_nowait()

        def audio_cb(indata, frames, time_info, status):
            if self.is_recording:
                self.audio_queue.put(indata.copy())
                self.current_volume = float(np.max(np.abs(indata)))

        self.stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=audio_cb)
        self.stream.start()

    def stop_and_paste(self):
        self.is_recording = False
        self.is_transcribing = True
        self.current_volume = 0.0
        self.play_sound(750, 80)

        # Visual indicator: cyan processing ripple
        for bar, _, _ in self.dots:
            self.canvas.itemconfig(bar, fill=self.PASTE_COLOR)

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
                            subprocess.run(["clip"], input=text.encode("utf-16le"), check=True)
                            if target and user32.IsWindow(target):
                                try:
                                    user32.SetForegroundWindow(target)
                                except Exception:
                                    pass
                            time.sleep(0.08)
                            user32.keybd_event(0x11, 0, 0, 0)
                            user32.keybd_event(0x56, 0, 0, 0)
                            user32.keybd_event(0x56, 0, 0x0002, 0)
                            user32.keybd_event(0x11, 0, 0x0002, 0)
                    except Exception as err:
                        print(f"[!] STT error: {err}")

            self.root.after(150, self.reset_ui)

        threading.Thread(target=_worker, daemon=True).start()

    def reset_ui(self):
        self.is_transcribing = False
        for bar, dx, cy in self.dots:
            self.canvas.itemconfig(bar, fill=self.DOT_COLOR)
            self.canvas.coords(bar, dx, cy - 2, dx, cy + 2)

    def animate_waveform(self):
        if self.is_recording:
            vol = min(1.0, self.current_volume * 4.5)
            for i, (bar, dx, cy) in enumerate(self.dots):
                # Harmonic wave tapering from center
                distance_from_center = abs(i - 4)
                mult = max(0.2, 1.0 - distance_from_center * 0.18)
                h = max(2, int(vol * 16 * mult))
                self.canvas.coords(bar, dx, cy - h, dx, cy + h)
        elif self.is_transcribing:
            # Subtle wave ripple while transcribing
            t = time.time() * 10
            for i, (bar, dx, cy) in enumerate(self.dots):
                h = int(3 + np.sin(t + i * 0.6) * 3)
                self.canvas.coords(bar, dx, cy - h, dx, cy + h)
        else:
            for bar, dx, cy in self.dots:
                self.canvas.coords(bar, dx, cy - 2, dx, cy + 2)

        self.root.after(35, self.animate_waveform)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    WisprPillApp().run()
