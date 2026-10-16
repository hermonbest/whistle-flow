import os
import sys
import math
import time
import queue
import json
import argparse
import logging
import threading
import subprocess
import ctypes
import urllib.request
from ctypes import wintypes
from pathlib import Path
from websockets.sync.client import connect as ws_sync_connect

LOG_FILE = Path(__file__).resolve().parent / "whisper_flow.log"
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("whistle_flow")
logger.info("Whistle Flow engine initialized.")

import numpy as np
import sounddevice as sd
import tkinter as tk
import keyboard
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from faster_whisper import WhisperModel

# ---------------------------------------------------------------------------
# Windows plumbing (DPI awareness + per-pixel-alpha layered window)
# ---------------------------------------------------------------------------
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # crisp on high-DPI screens
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

user32.GetDC.argtypes = [ctypes.c_void_p]
user32.GetDC.restype = ctypes.c_void_p
user32.GetParent.argtypes = [ctypes.c_void_p]
user32.GetParent.restype = ctypes.c_void_p
user32.GetForegroundWindow.restype = ctypes.c_void_p
user32.IsWindow.argtypes = [ctypes.c_void_p]
user32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
user32.GetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int]
user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.SetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t]
user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, ctypes.c_uint]
gdi32.CreateCompatibleDC.argtypes = [ctypes.c_void_p]
gdi32.CreateCompatibleDC.restype = ctypes.c_void_p
gdi32.SelectObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
gdi32.SelectObject.restype = ctypes.c_void_p


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD),
                ("biCompression", wintypes.DWORD), ("biSizeImage", wintypes.DWORD),
                ("biXPelsPerMeter", wintypes.LONG), ("biYPelsPerMeter", wintypes.LONG),
                ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [("BlendOp", ctypes.c_ubyte), ("BlendFlags", ctypes.c_ubyte),
                ("SourceConstantAlpha", ctypes.c_ubyte), ("AlphaFormat", ctypes.c_ubyte)]


gdi32.CreateDIBSection.argtypes = [ctypes.c_void_p, ctypes.POINTER(BITMAPINFO), ctypes.c_uint,
                                   ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p, wintypes.DWORD]
gdi32.CreateDIBSection.restype = ctypes.c_void_p
user32.UpdateLayeredWindow.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(wintypes.POINT),
                                       ctypes.POINTER(wintypes.SIZE), ctypes.c_void_p,
                                       ctypes.POINTER(wintypes.POINT), wintypes.DWORD,
                                       ctypes.POINTER(BLENDFUNCTION), wintypes.DWORD]
user32.UpdateLayeredWindow.restype = wintypes.BOOL

GWL_EXSTYLE = -20
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
HWND_TOPMOST = -1
SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = 0x0001, 0x0002, 0x0010


class LayeredSurface:
    """Pushes RGBA PIL images to a window with true per-pixel alpha (smooth edges, soft shadow)."""

    def __init__(self, hwnd, w, h):
        self.hwnd, self.w, self.h = hwnd, w, h
        self.hdc_screen = user32.GetDC(None)
        self.hdc_mem = gdi32.CreateCompatibleDC(self.hdc_screen)
        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = w
        bmi.bmiHeader.biHeight = -h  # top-down
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = 0
        self.bits = ctypes.c_void_p()
        self.hbmp = gdi32.CreateDIBSection(self.hdc_screen, ctypes.byref(bmi), 0,
                                           ctypes.byref(self.bits), None, 0)
        gdi32.SelectObject(self.hdc_mem, self.hbmp)
        self.blend = BLENDFUNCTION(0, 0, 255, 1)  # AC_SRC_OVER + AC_SRC_ALPHA
        self.size = wintypes.SIZE(w, h)
        self.src = wintypes.POINT(0, 0)

    def update(self, img, x, y):
        arr = np.asarray(img, dtype=np.uint8)
        a = arr[..., 3:4].astype(np.uint16)
        rgb = (arr[..., :3].astype(np.uint16) * a + 127) // 255  # premultiply
        out = np.empty((self.h, self.w, 4), dtype=np.uint8)
        out[..., 0] = rgb[..., 2]
        out[..., 1] = rgb[..., 1]
        out[..., 2] = rgb[..., 0]
        out[..., 3] = arr[..., 3]
        ctypes.memmove(self.bits, out.ctypes.data, out.nbytes)
        pt = wintypes.POINT(int(x), int(y))
        user32.UpdateLayeredWindow(self.hwnd, self.hdc_screen, ctypes.byref(pt), ctypes.byref(self.size),
                                   self.hdc_mem, ctypes.byref(self.src), 0, ctypes.byref(self.blend), 2)


# ---------------------------------------------------------------------------
# VAD & Audio Utilities
# ---------------------------------------------------------------------------
SAMPLE_RATE = 16000

class AudioMuter:
    """Mutes background application audio sessions while recording and restores them on finish."""

    def __init__(self):
        self.muted_controls = []
        self._lock = threading.Lock()

    def mute_others(self):
        with self._lock:
            # If already muted, avoid double muting or losing tracking
            if self.muted_controls:
                return
            try:
                import comtypes
                from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
                comtypes.CoInitialize()
                my_pid = os.getpid()
                sessions = AudioUtilities.GetAllSessions()
                for session in sessions:
                    try:
                        proc = session.Process
                        if proc and proc.pid == my_pid:
                            continue
                        vol = session._ctl.QueryInterface(ISimpleAudioVolume)
                        if vol.GetMute() == 0:
                            vol.SetMute(1, None)
                            self.muted_controls.append(vol)
                    except Exception:
                        pass
                logger.info(f"Muted {len(self.muted_controls)} background audio session(s).")
            except Exception as e:
                logger.warning(f"AudioMuter mute error: {e}")

    def unmute_all(self):
        with self._lock:
            if not self.muted_controls:
                return
            count = 0
            for vol in self.muted_controls:
                try:
                    vol.SetMute(0, None)
                    count += 1
                except Exception:
                    pass
            self.muted_controls.clear()
            logger.info(f"Restored/unmuted {count} background audio session(s).")


def play_click(kind: str = "start"):
    """Plays a soft, pleasant tactile click via sounddevice instead of harsh winsound motherboard beeps."""
    def _run():
        try:
            if kind == "start":
                freq, duration, volume = 1350, 0.016, 0.08
            elif kind == "stop":
                freq, duration, volume = 850, 0.018, 0.07
            else:  # cancel / error
                freq, duration, volume = 480, 0.022, 0.06

            t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
            decay = np.exp(-t * 220)
            wave = (np.sin(2 * np.pi * freq * t) * decay * volume).astype(np.float32)
            sd.play(wave, samplerate=SAMPLE_RATE)
            sd.wait()
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True).start()


def trim_silence(audio: np.ndarray, sample_rate: int = 16000, threshold_db: float = -46.0) -> np.ndarray:
    """Trims leading and trailing silence using RMS energy gating."""
    if len(audio) == 0:
        return audio
    frame_len = int(sample_rate * 0.02)  # 20ms frames
    num_frames = len(audio) // frame_len
    if num_frames == 0:
        return audio
    frames = audio[:num_frames * frame_len].reshape(num_frames, frame_len)
    rms = np.sqrt(np.mean(frames ** 2, axis=1) + 1e-9)
    db = 20.0 * np.log10(rms)
    voiced = np.where(db > threshold_db)[0]
    if len(voiced) == 0:
        return audio
    pad = int(sample_rate * 0.08)  # 80ms padding
    start_idx = max(0, voiced[0] * frame_len - pad)
    end_idx = min(len(audio), (voiced[-1] + 1) * frame_len + pad)
    return audio[start_idx:end_idx]


# ---------------------------------------------------------------------------
# Push-to-Talk State Controller
# ---------------------------------------------------------------------------
class PttController:
    """Manages Push-To-Talk (hold > 300ms) vs Tap-To-Lock (short tap < 300ms)."""
    HOLD_THRESHOLD = 0.30

    def __init__(self, on_start, on_stop):
        self.on_start = on_start
        self.on_stop = on_stop
        self.is_recording = False
        self.is_locked = False
        self.press_time = 0.0
        self.lock = threading.Lock()

    def on_press(self):
        with self.lock:
            self.press_time = time.perf_counter()
            if not self.is_recording:
                self.is_recording = True
                self.is_locked = False
                self.on_start()

    def on_release(self):
        with self.lock:
            if not self.is_recording:
                return
            duration = time.perf_counter() - self.press_time
            if duration >= self.HOLD_THRESHOLD:
                # Held: Push-To-Talk -> finish and paste
                self.is_recording = False
                self.is_locked = False
                self.on_stop()
            else:
                # Tap: Toggle lock
                if self.is_locked:
                    self.is_recording = False
                    self.is_locked = False
                    self.on_stop()
                else:
                    self.is_locked = True

    def toggle(self):
        with self.lock:
            if not self.is_recording:
                self.is_recording = True
                self.is_locked = True
                self.on_start()
            else:
                self.is_recording = False
                self.is_locked = False
                self.on_stop()

    def cancel(self):
        with self.lock:
            self.is_recording = False
            self.is_locked = False


# ---------------------------------------------------------------------------
# Configuration & Phonon Engine Plumbing
# ---------------------------------------------------------------------------
CONFIG_FILE = Path(__file__).resolve().parent / "config.json"


def load_config() -> dict:
    cfg = {
        "engine": "whisper",
        "phonon_port": 8000,
        "phonon_model": "phonon-2",
    }
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception as e:
            logger.warning(f"Error reading config: {e}")
    return cfg


def save_config(cfg: dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        logger.warning(f"Error saving config: {e}")


class PhononServerManager:
    """Manages the background 'fermion serve phonon-2' daemon on localhost."""

    def __init__(self, port: int = 8000, model: str = "phonon-2"):
        self.port = port
        self.model = model
        self.process = None
        self._lock = threading.Lock()

    def is_running(self) -> bool:
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{self.port}/health")
            with urllib.request.urlopen(req, timeout=1.0) as res:
                if res.status == 200:
                    data = json.loads(res.read().decode())
                    return data.get("status") == "ok"
        except Exception:
            return False
        return False

    def ensure_server(self, timeout: float = 12.0) -> bool:
        with self._lock:
            if self.is_running():
                return True
            logger.info(f"Phonon server not detected on port {self.port}. Starting background daemon...")
            try:
                CREATE_NO_WINDOW = 0x08000000
                cmd = [
                    sys.executable,
                    "-c",
                    "import sys, fermion.cli; sys.exit(fermion.cli.main())",
                    "serve",
                    self.model,
                    "--port",
                    str(self.port),
                ]
                self.process = subprocess.Popen(
                    cmd,
                    creationflags=CREATE_NO_WINDOW,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                t0 = time.perf_counter()
                while time.perf_counter() - t0 < timeout:
                    time.sleep(0.3)
                    if self.is_running():
                        logger.info(f"Phonon daemon online in {(time.perf_counter() - t0):.1f}s.")
                        return True
                    if self.process.poll() is not None:
                        logger.error(f"Phonon daemon exited early: {self.process.returncode}")
                        return False
            except Exception as e:
                logger.error(f"Failed to start Phonon daemon: {e}")
                return False
            return False

    def stop(self):
        with self._lock:
            if self.process and self.process.poll() is None:
                try:
                    self.process.terminate()
                    self.process.wait(timeout=2.0)
                    logger.info("Phonon server process stopped.")
                except Exception:
                    pass
                self.process = None


class PhononStreamClient:
    """Streams live 16kHz float32 audio over WebSocket to Phonon-2 (/v1/audio/stream)."""

    def __init__(self, port: int = 8000):
        self.port = port
        self.ws = None
        self.is_active = False
        self.done_event = threading.Event()
        self.final_text = ""
        self.on_partial_cb = None
        self.on_done_cb = None
        self._thread = None
        self._send_queue = queue.Queue()

    def start_stream(self, on_partial=None, on_done=None):
        self.abort()
        self.is_active = True
        self.done_event.clear()
        self.final_text = ""
        self.on_partial_cb = on_partial
        self.on_done_cb = on_done
        while not self._send_queue.empty():
            try:
                self._send_queue.get_nowait()
            except Exception:
                break

        ready_event = threading.Event()

        def _worker():
            uri = f"ws://127.0.0.1:{self.port}/v1/audio/stream"
            try:
                with ws_sync_connect(uri, ping_interval=20, ping_timeout=20) as ws:
                    self.ws = ws
                    # Send stream configuration handshake
                    ws.send(json.dumps({"sample_rate": 16000, "format": "pcm_f32le"}))
                    ready_event.set()

                    # Start dedicated receiver thread
                    def _receiver():
                        try:
                            for msg in ws:
                                data = json.loads(msg)
                                mtype = data.get("type")
                                if mtype == "partial":
                                    txt = data.get("text", "")
                                    if self.on_partial_cb:
                                        self.on_partial_cb(txt)
                                elif mtype == "done":
                                    self.final_text = data.get("text", "").strip()
                                    if self.on_done_cb:
                                        self.on_done_cb(self.final_text)
                                    self.done_event.set()
                                    break
                                elif mtype == "error":
                                    logger.warning(f"Phonon server error: {data.get('message')}")
                                    self.done_event.set()
                                    break
                        except Exception:
                            pass
                        finally:
                            self.done_event.set()

                    rec_thread = threading.Thread(target=_receiver, daemon=True)
                    rec_thread.start()

                    # Main sender loop
                    while self.is_active:
                        try:
                            item = self._send_queue.get(timeout=0.2)
                        except queue.Empty:
                            continue
                        if item is None:  # Stop signal
                            try:
                                ws.send(json.dumps({"type": "end"}))
                            except Exception:
                                pass
                            break
                        try:
                            ws.send(item)
                        except Exception as e:
                            logger.warning(f"Error sending audio frame: {e}")
                            break

                    self.done_event.wait(timeout=2.0)
            except Exception as e:
                logger.warning(f"Phonon WebSocket connect notice: {e}")
            finally:
                self.is_active = False
                self.done_event.set()
                ready_event.set()
                self.ws = None

        self._thread = threading.Thread(target=_worker, daemon=True)
        self._thread.start()
        ready_event.wait(timeout=1.5)

    def send_audio_chunk(self, chunk: np.ndarray):
        if not self.is_active:
            return
        audio_bytes = chunk.astype(np.float32).tobytes()
        self._send_queue.put(audio_bytes)

    def stop_and_wait(self, timeout: float = 2.0) -> str:
        if self.is_active:
            self._send_queue.put(None)
            self.done_event.wait(timeout=timeout)
        self.abort()
        return self.final_text

    def abort(self):
        self.is_active = False
        self.done_event.set()
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
            self.ws = None


# ---------------------------------------------------------------------------
# Look & feel
# ---------------------------------------------------------------------------
SS = 3                       # supersampling factor for anti-aliasing

PAD = 30                     # room around the pill for shadow / glow / spring overshoot
IDLE_W, IDLE_H = 70, 26
ACT_W, ACT_H = 190, 46
MAX_ACT_W = 340              # expanded width for live text streaming
WIN_W, WIN_H = MAX_ACT_W + PAD * 2, ACT_H + PAD * 2

NUM_BARS = 21
BAR_SPACING = 7.5
BAR_W = 3.4
MAX_BAR_H = ACT_H - 14

BG = (24, 24, 27)
IDLE_COL = (150, 156, 168)
WHITE = (255, 255, 255)
CYAN = (56, 189, 248)
VIOLET = (167, 139, 250)
PINK = (244, 114, 182)
GREEN = (74, 222, 128)
AURORA = [CYAN, VIOLET, PINK]

SPRING_K, SPRING_C = 260.0, 21.0   # slightly under-damped = a little bounce

try:
    FONT_LIVE = ImageFont.truetype("segoeui.ttf", 13 * SS)
    FONT_TOAST = ImageFont.truetype("segoeuib.ttf", 11 * SS)
except Exception:
    try:
        FONT_LIVE = ImageFont.truetype("arial.ttf", 13 * SS)
        FONT_TOAST = ImageFont.truetype("arialbd.ttf", 11 * SS)
    except Exception:
        FONT_LIVE = ImageFont.load_default()
        FONT_TOAST = ImageFont.load_default()


def lerp(a, b, t):
    return a + (b - a) * t


def clamp(x, lo=0.0, hi=1.0):
    return lo if x < lo else hi if x > hi else x


def lerp_color(c1, c2, t):
    return tuple(lerp(a, b, t) for a, b in zip(c1, c2))


def aurora(p):
    p %= 1.0
    x = p * 3
    i = int(x)
    f = x - i
    f = f * f * (3 - 2 * f)
    return lerp_color(AURORA[i % 3], AURORA[(i + 1) % 3], f)


def rgb(c):
    return tuple(int(clamp(v, 0, 255)) for v in c)


class WisprPillApp:
    def __init__(self, engine_override=None, phonon_port=None):
        self.root = tk.Tk()
        self.root.title("Whistle Flow")

        self.config = load_config()
        self.engine = engine_override or self.config.get("engine", "whisper")
        self.phonon_port = phonon_port or self.config.get("phonon_port", 8000)
        self.phonon_model = self.config.get("phonon_model", "phonon-2")

        self.phonon_server = PhononServerManager(port=self.phonon_port, model=self.phonon_model)
        self.phonon_client = PhononStreamClient(port=self.phonon_port)

        self.live_text = ""
        self.toast_msg = ""
        self.toast_col = WHITE
        self.toast_t = 0.0

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.x = (sw - WIN_W) // 2
        self.y = sh - WIN_H - 70

        self.root.geometry(f"{WIN_W}x{WIN_H}+{self.x}+{self.y}")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.update()

        # Turn the Tk window into a click-through-where-transparent, never-steals-focus layered window
        self.hwnd = user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
        ex = user32.GetWindowLongPtrW(self.hwnd, GWL_EXSTYLE)
        ex |= WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_TOPMOST
        user32.SetWindowLongPtrW(self.hwnd, GWL_EXSTYLE, ex)
        self.surface = LayeredSurface(self.hwnd, WIN_W, WIN_H)

        # Audio / app state
        self.is_transcribing = False
        self.audio_queue = queue.Queue()
        self.stream = None
        self.last_target_hwnd = 0
        self.level_raw = 0.0
        self.done_t = None  # perf_counter timestamp of last successful paste
        self.model = None
        self.audio_muter = AudioMuter()

        # PTT Controller (<kbd>Ctrl + Space</kbd>)
        self.ptt = PttController(on_start=self.start_recording, on_stop=self.stop_and_paste)

        # Animation state
        self.expand, self.vel = 0.0, 0.0
        self.hover = 0.0
        self.level = 0.0
        self.bar_h = [BAR_W] * NUM_BARS
        self.col = IDLE_COL
        self.glow = 0.0
        self.glow_col = WHITE
        self.last_t = time.perf_counter()
        self.last_sig = None

        # Mouse state
        self.drag_off = (0, 0)
        self.press_xy = (0, 0)
        self.dragging = False
        self.dragged = False

        self.setup_controls()

        # Warm up faster-whisper in background thread
        threading.Thread(target=self.warmup, daemon=True).start()

        # If starting in phonon mode, warm up phonon daemon in background thread
        if self.engine == "phonon":
            threading.Thread(target=self.phonon_server.ensure_server, daemon=True).start()

        self.track_focus()
        self.tick()

    # ------------------------------------------------------------------ input
    def setup_controls(self):
        self.root.bind("<Button-1>", self.on_press)
        self.root.bind("<B1-Motion>", self.on_drag)
        self.root.bind("<ButtonRelease-1>", self.on_release)
        self.root.bind("<Double-Button-1>", lambda e: self.toggle_engine())
        self.root.bind("<Button-3>", lambda e: self.on_close())

        # Primary Push-To-Talk: Ctrl + Space
        self.space_down = False

        def on_key_event(e):
            if e.name == "space":
                if e.event_type == "down":
                    if keyboard.is_pressed("ctrl") and not self.space_down:
                        if keyboard.is_pressed("shift"):
                            # Ctrl + Shift + Space: Toggle between Whisper and Phonon
                            self.toggle_engine()
                            return
                        self.space_down = True
                        self.ptt.on_press()
                elif e.event_type == "up":
                    if self.space_down:
                        self.space_down = False
                        self.ptt.on_release()
            elif e.name == "f9" and e.event_type == "down":
                self.toggle_engine()
            elif self.space_down and e.event_type == "up" and ("ctrl" in e.name or "control" in e.name):
                # Also trigger release if Ctrl is released before Space during PTT
                self.space_down = False
                self.ptt.on_release()

        keyboard.hook(on_key_event)

        # Fallback hotkeys
        keyboard.add_hotkey("f8", self.ptt.toggle, suppress=False)
        keyboard.add_hotkey("ctrl+shift+e", self.toggle_engine, suppress=False)
        keyboard.add_hotkey("esc", self.cancel, suppress=False)

    def toggle_engine(self):
        if self.engine == "whisper":
            self.engine = "phonon"
            self.toast_msg = "PHONON 2 (STREAM)"
            self.toast_col = VIOLET
            threading.Thread(target=self.phonon_server.ensure_server, daemon=True).start()
        else:
            self.engine = "whisper"
            self.toast_msg = "WHISPER (INT8)"
            self.toast_col = CYAN
        self.config["engine"] = self.engine
        save_config(self.config)
        self.toast_t = time.perf_counter()
        play_click("start")
        logger.info(f"Active engine switched to: {self.engine.upper()}")

    def on_close(self):
        try:
            self.phonon_server.stop()
        except Exception:
            pass
        self.root.destroy()
        sys.exit(0)

    def on_phonon_partial(self, text: str):
        if self.ptt.is_recording:
            self.live_text = text.strip()

    def on_press(self, e):
        self.press_xy = (e.x_root, e.y_root)
        self.drag_off = (e.x_root - self.x, e.y_root - self.y)
        self.dragging = True
        self.dragged = False

    def on_drag(self, e):
        if abs(e.x_root - self.press_xy[0]) + abs(e.y_root - self.press_xy[1]) > 4:
            self.dragged = True
        if self.dragged:
            self.x = e.x_root - self.drag_off[0]
            self.y = e.y_root - self.drag_off[1]

    def on_release(self, e):
        self.dragging = False
        if not self.dragged:
            self.ptt.toggle()

    # ------------------------------------------------------------------ STT / audio
    def warmup(self):
        try:
            t0 = time.perf_counter()
            self.model = WhisperModel("tiny.en", device="cpu", compute_type="int8", local_files_only=True)
            segments, _ = self.model.transcribe(np.zeros(SAMPLE_RATE, dtype=np.float32), language="en", beam_size=1)
            list(segments)
            logger.info(f"Faster-Whisper INT8 model loaded and warmed up in {(time.perf_counter() - t0)*1000:.1f}ms.")
        except Exception as e:
            logger.warning(f"Faster-Whisper local load notice: {e}. Trying default loader...")
            try:
                self.model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
                segments, _ = self.model.transcribe(np.zeros(SAMPLE_RATE, dtype=np.float32), language="en", beam_size=1)
                list(segments)
                logger.info("Faster-Whisper INT8 model loaded successfully.")
            except Exception as e2:
                logger.error(f"Faster-Whisper load error: {e2}")

    def track_focus(self):
        fg = user32.GetForegroundWindow()
        if fg and fg != self.hwnd and fg != self.root.winfo_id():
            self.last_target_hwnd = fg
        # Keep above everything without grabbing focus
        user32.SetWindowPos(self.hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
        self.root.after(500, self.track_focus)

    def play_sound(self, kind: str = "start"):
        play_click(kind)

    def start_recording(self):
        if self.is_transcribing:
            return
        self.done_t = None
        self.live_text = ""
        self.audio_muter.mute_others()
        self.play_sound("start")
        logger.info(f"Recording started. Active engine: {self.engine.upper()}")

        # Clear audio queue
        while not self.audio_queue.empty():
            self.audio_queue.get_nowait()

        if self.engine == "phonon":
            if not self.phonon_server.is_running():
                threading.Thread(target=self.phonon_server.ensure_server, daemon=True).start()
            self.phonon_client.start_stream(on_partial=self.on_phonon_partial)

        # Audio capture callback
        def audio_cb(indata, frames, time_info, status):
            if self.ptt.is_recording:
                flat = indata.flatten().copy()
                self.audio_queue.put(flat)
                if self.engine == "phonon":
                    self.phonon_client.send_audio_chunk(flat)

                # Measure volume for live waveform
                rms = float(np.sqrt(np.mean(indata ** 2)))
                db = 20.0 * math.log10(rms + 1e-9)
                self.level_raw = clamp((db + 52.0) / 38.0)

        self.stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=audio_cb)
        self.stream.start()

    def _close_stream(self):
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None

    def cancel(self):
        if self.ptt.is_recording:
            self.ptt.cancel()
            self.level_raw = 0.0
            self._close_stream()
            if self.engine == "phonon":
                self.phonon_client.abort()
            self.live_text = ""
            self.audio_muter.unmute_all()
            while not self.audio_queue.empty():
                self.audio_queue.get_nowait()
            self.play_sound("cancel")
            logger.info("Recording cancelled by user.")

    def stop_and_paste(self):
        t_release = time.perf_counter()
        self.is_transcribing = True
        self.level_raw = 0.0
        self._close_stream()
        self.audio_muter.unmute_all()
        self.play_sound("stop")

        target = self.last_target_hwnd
        engine = self.engine

        def _worker():
            pasted = False
            text = ""

            if engine == "phonon":
                t0 = time.perf_counter()
                final = self.phonon_client.stop_and_wait(timeout=2.0)
                if final:
                    text = final
                    logger.info(f"Phonon streaming finalized in {(time.perf_counter() - t0)*1000:.1f}ms: '{text}'")
                else:
                    logger.warning("Phonon streaming returned empty or unavailable. Falling back to Whisper...")

            # If Whisper engine OR if Phonon returned empty / server unavailable:
            if not text:
                chunks = []
                while not self.audio_queue.empty():
                    chunks.append(self.audio_queue.get_nowait())

                if chunks:
                    audio = np.concatenate(chunks).flatten()
                    rec_duration = len(audio) / SAMPLE_RATE
                    trimmed = trim_silence(audio)
                    trim_duration = len(trimmed) / SAMPLE_RATE
                    logger.info(f"Key released. Audio: {rec_duration:.2f}s (trimmed: {trim_duration:.2f}s). Decoding with Whisper...")

                    if len(trimmed) >= int(SAMPLE_RATE * 0.25):
                        t_decode_start = time.perf_counter()
                        try:
                            if self.model is not None:
                                segments, _ = self.model.transcribe(trimmed, language="en", beam_size=1)
                                text = " ".join(s.text.strip() for s in segments if s.text).strip()
                            decode_ms = (time.perf_counter() - t_decode_start) * 1000
                            logger.info(f"Whisper decoded in {decode_ms:.1f}ms: '{text}'")
                        except Exception as err:
                            logger.error(f"Whisper transcribe error: {err}", exc_info=True)

            if text:
                t_paste_start = time.perf_counter()
                subprocess.run(["clip"], input=text.encode("utf-16le"), check=True)
                if target and user32.IsWindow(target):
                    try:
                        user32.SetForegroundWindow(target)
                    except Exception:
                        pass
                time.sleep(0.04)
                # Inject Ctrl + V
                user32.keybd_event(0x11, 0, 0, 0)
                user32.keybd_event(0x56, 0, 0, 0)
                user32.keybd_event(0x56, 0, 0x0002, 0)
                user32.keybd_event(0x11, 0, 0x0002, 0)
                pasted = True
                total_latency_ms = (time.perf_counter() - t_release) * 1000
                logger.info(f"Pasted in {(time.perf_counter() - t_paste_start)*1000:.1f}ms. Total latency: {total_latency_ms:.1f}ms")

            time.sleep(0.08)
            if pasted:
                self.done_t = time.perf_counter()
            self.live_text = ""
            self.is_transcribing = False

        threading.Thread(target=_worker, daemon=True).start()

    # ------------------------------------------------------------------ animation
    def tick(self):
        now = time.perf_counter()
        dt = min(0.05, max(0.001, now - self.last_t))
        self.last_t = now

        in_done = self.done_t is not None and (now - self.done_t) < 0.9
        in_toast = bool(self.toast_msg and (now - self.toast_t < 1.2))
        active = self.ptt.is_recording or self.is_transcribing or in_done or in_toast

        # Spring for the expand/collapse (gives that little bounce)
        target = 1.0 if active else 0.0
        acc = SPRING_K * (target - self.expand) - SPRING_C * self.vel
        self.vel += acc * dt
        self.expand = clamp(self.expand + self.vel * dt, -0.2, 1.3)
        if abs(self.vel) < 1e-3 and abs(target - self.expand) < 1e-3:
            self.expand, self.vel = target, 0.0

        # Hover (pointer inside the idle pill)
        px, py = self.root.winfo_pointerxy()
        cxs, cys = self.x + WIN_W / 2, self.y + WIN_H / 2
        inside = abs(px - cxs) < (IDLE_W / 2 + 10) and abs(py - cys) < (IDLE_H / 2 + 8) and not active
        self.hover += ((1.0 if inside else 0.0) - self.hover) * (1 - math.exp(-14 * dt))
        if abs(self.hover) < 1e-3:
            self.hover = 0.0

        # Mic level (fast attack, slow release)
        lt = self.level_raw if self.ptt.is_recording else 0.0
        self.level += (lt - self.level) * (1 - math.exp(-(28 if lt > self.level else 7) * dt))

        # Colour + glow targets
        if in_toast:
            col_t = self.toast_col
            glow_t, glow_col_t = 0.7, self.toast_col
        elif in_done:
            col_t = GREEN
            fade = math.exp(-(now - self.done_t) * 3.0)
            glow_t, glow_col_t = 0.8 * fade, GREEN
        elif self.is_transcribing:
            col_t = CYAN
            glow_t, glow_col_t = 0.55, aurora(now * 0.35)
        elif self.ptt.is_recording:
            if self.engine == "phonon":
                col_t = VIOLET if self.live_text else WHITE
                glow_t, glow_col_t = 0.2 + 0.4 * self.level, VIOLET if self.live_text else (210, 200, 255)
            else:
                col_t = WHITE
                glow_t, glow_col_t = 0.15 + 0.45 * self.level, (210, 200, 255)
        else:
            col_t = lerp_color(IDLE_COL, WHITE, self.hover * 0.8)
            glow_t, glow_col_t = 0.0, self.glow_col
        k = 1 - math.exp(-14 * dt)
        self.col = lerp_color(self.col, col_t, k)
        self.glow_col = lerp_color(self.glow_col, glow_col_t, 1 - math.exp(-12 * dt))
        self.glow += (glow_t - self.glow) * (1 - math.exp(-10 * dt))

        self.update_bars(now, dt, in_done)

        # Redraw when state changed
        sig = (round(self.expand, 3), round(self.hover, 3), round(self.glow, 3), self.x, self.y,
               tuple(int(v) for v in self.col), tuple(int(v) for v in self.glow_col),
               tuple(round(h, 1) for h in self.bar_h), self.live_text,
               self.toast_msg if in_toast else "")
        if sig != self.last_sig:
            self.last_sig = sig
            self.surface.update(self.compose(now), self.x, self.y)
            delay = 15
        else:
            delay = 33
        self.root.after(delay, self.tick)

    def update_bars(self, now, dt, in_done):
        n = NUM_BARS
        for i in range(n):
            c = (i - (n - 1) / 2) / ((n - 1) / 2)  # -1 .. 1
            env = math.exp(-(c * 1.5) ** 2)
            if self.ptt.is_recording:
                wob = 0.6 + 0.4 * math.sin(now * 11 + i * 1.3) * math.sin(now * 5.3 + i * 0.7)
                breathe = 1.6 * env * (0.5 + 0.5 * math.sin(now * 3 + i * 0.4))
                tgt = BAR_W + breathe + (MAX_BAR_H - BAR_W) * self.level * env * wob
            elif self.is_transcribing:
                wave = 0.5 + 0.5 * math.sin(now * 7 - i * 0.55)
                tgt = BAR_W + 13 * wave * (0.35 + 0.65 * env)
            elif in_done:
                r = now - self.done_t
                ring = max(0.0, 1.0 - abs(abs(c) - r * 2.2) * 3.0) * math.exp(-r * 3.5)
                tgt = BAR_W + 18 * ring
            else:
                tgt = BAR_W
            rate = 45 if tgt > self.bar_h[i] else 12
            self.bar_h[i] += (tgt - self.bar_h[i]) * (1 - math.exp(-rate * dt))

    # ------------------------------------------------------------------ rendering
    def compose(self, now):
        W, H, S = WIN_W, WIN_H, SS
        e = self.expand
        e_c = clamp(e)
        hv = self.hover

        in_toast = bool(self.toast_msg and (now - self.toast_t < 1.2))
        has_live_text = bool(self.engine == "phonon" and self.ptt.is_recording and self.live_text)

        if in_toast:
            target_act_w = 230.0
        elif has_live_text:
            # Smooth expansion based on text length
            est_w = 120.0 + len(self.live_text) * 7.5
            target_act_w = min(MAX_ACT_W, max(ACT_W, est_w))
        else:
            target_act_w = ACT_W

        pw = max(24.0, lerp(IDLE_W, target_act_w, e) + 14 * hv * (1 - e_c))
        ph = max(18.0, lerp(IDLE_H, ACT_H, e) + 3 * hv * (1 - e_c))
        ph *= 1 - min(0.08, abs(self.vel) * 0.02)  # tiny squash & stretch while moving
        cx, cy = W / 2, H / 2
        x0, y0, x1, y1 = cx - pw / 2, cy - ph / 2, cx + pw / 2, cy + ph / 2
        r = ph / 2

        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))

        # Soft drop shadow
        sh = Image.new("L", (W, H), 0)
        ImageDraw.Draw(sh).rounded_rectangle((x0, y0 + 4, x1, y1 + 4), radius=r, fill=120)
        sh = sh.filter(ImageFilter.GaussianBlur(7))
        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        shadow.putalpha(sh)
        canvas = Image.alpha_composite(canvas, shadow)

        # Coloured glow
        if self.glow > 0.01:
            gm = Image.new("L", (W, H), 0)
            ImageDraw.Draw(gm).rounded_rectangle((x0 - 2, y0 - 2, x1 + 2, y1 + 2), radius=r + 2,
                                                 fill=int(clamp(self.glow) * 210))
            gm = gm.filter(ImageFilter.GaussianBlur(10))
            glow = Image.new("RGBA", (W, H), rgb(self.glow_col) + (0,))
            glow.putalpha(gm)
            canvas = Image.alpha_composite(canvas, glow)

        # Pill body + border
        big = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
        d = ImageDraw.Draw(big)
        border_a = int(lerp(120, 235, e_c) + 25 * hv)
        d.rounded_rectangle((x0 * S, y0 * S, x1 * S, y1 * S), radius=r * S, fill=BG + (248,),
                            outline=(255, 255, 255, border_a), width=int(1.6 * S))

        if in_toast:
            # Draw toast engine message
            tw = d.textlength(self.toast_msg, font=FONT_TOAST)
            tx = cx * S - tw / 2
            ty = cy * S - 7 * S
            d.text((tx, ty), self.toast_msg, font=FONT_TOAST, fill=rgb(self.toast_col) + (245,))
        elif has_live_text and e_c > 0.4:
            # Phonon Live Streaming: 7 voice bars on left + streaming text preview on right
            mini_bars = 7
            mini_spacing = 6.0
            start_bx = (x0 + 20) * S
            max_h = (ph - 12) * S
            for i in range(mini_bars):
                bx = start_bx + i * (mini_spacing * S)
                bh = max(BAR_W * S, min(self.bar_h[i] * S, max_h))
                d.rounded_rectangle((bx - (BAR_W * S) / 2, cy * S - bh / 2, bx + (BAR_W * S) / 2, cy * S + bh / 2),
                                    radius=(BAR_W * S) / 2, fill=VIOLET + (230,))

            # Format live text with ellipsis if it overflows available space
            text_x = start_bx + mini_bars * (mini_spacing * S) + 10 * S
            max_text_w = (x1 - 18) * S - text_x

            display_text = self.live_text
            while display_text and d.textlength("... " + display_text, font=FONT_LIVE) > max_text_w:
                parts = display_text.split(" ", 1)
                if len(parts) > 1:
                    display_text = parts[1]
                else:
                    display_text = display_text[3:]
            if display_text != self.live_text and display_text:
                display_text = "... " + display_text

            # Render live text
            d.text((text_x, cy * S - 9 * S), display_text, font=FONT_LIVE, fill=(255, 255, 255, 240))

            # Pulsing cursor dot
            cursor_x = text_x + d.textlength(display_text, font=FONT_LIVE) + 5 * S
            cursor_alpha = int(128 + 127 * math.sin(now * 8))
            d.ellipse((cursor_x, cy * S - 3 * S, cursor_x + 5 * S, cy * S + 2 * S),
                      fill=VIOLET + (cursor_alpha,))
        else:
            # Standard 21 bars (Whisper mode or idle / initial recording state)
            avail = pw / 2 - 15
            max_h = ph - 10
            for i in range(NUM_BARS):
                off = (i - (NUM_BARS - 1) / 2) * BAR_SPACING
                vis = clamp((avail - abs(off)) / BAR_SPACING + 0.5)
                if vis <= 0.01:
                    continue
                h = min(max(self.bar_h[i], BAR_W), max_h)
                bx = cx + off
                if self.is_transcribing:
                    col = aurora(now * 0.5 - i * 0.045)
                else:
                    col = self.col
                alpha = int(255 * vis * lerp(0.8, 1.0, e_c))
                d.rounded_rectangle(((bx - BAR_W / 2) * S, (cy - h / 2) * S, (bx + BAR_W / 2) * S, (cy + h / 2) * S),
                                    radius=BAR_W / 2 * S, fill=rgb(col) + (alpha,))

        big = big.resize((W, H), Image.LANCZOS)
        return Image.alpha_composite(canvas, big)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    kernel32 = ctypes.windll.kernel32
    mutex = kernel32.CreateMutexW(None, False, "WhistleFlowSingleInstanceMutex")
    ERROR_ALREADY_EXISTS = 183
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        # Another instance is already running
        sys.exit(0)

    parser = argparse.ArgumentParser(description="Whistle Flow Dictation Pill")
    parser.add_argument("--engine", choices=["whisper", "phonon"], help="Speech recognition engine (whisper or phonon)")
    parser.add_argument("--port", type=int, default=None, help="Phonon server port")
    args, _ = parser.parse_known_args()

    WisprPillApp(engine_override=args.engine, phonon_port=args.port).run()

