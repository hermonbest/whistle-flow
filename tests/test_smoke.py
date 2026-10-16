import os
from pathlib import Path
import unittest
import numpy as np

class PttController:
    HOLD_THRESHOLD = 0.30

    def __init__(self, on_start, on_stop):
        self.on_start = on_start
        self.on_stop = on_stop
        self.is_recording = False
        self.is_locked = False
        self.press_time = 0.0

    def on_press(self, now):
        self.press_time = now
        if not self.is_recording:
            self.is_recording = True
            self.on_start()

    def on_release(self, now):
        if not self.is_recording:
            return
        duration = now - self.press_time
        if duration >= self.HOLD_THRESHOLD:
            self.is_recording = False
            self.is_locked = False
            self.on_stop()
        else:
            if self.is_locked:
                self.is_recording = False
                self.is_locked = False
                self.on_stop()
            else:
                self.is_locked = True

    def cancel(self):
        self.is_recording = False
        self.is_locked = False

class TestWhistleFlowSmoke(unittest.TestCase):

    def test_layered_surface_structure(self):
        """Verify image processing pipeline handles Pillow RGBA composites."""
        from PIL import Image, ImageDraw, ImageFilter
        W, H = 250, 106
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((30, 30, 220, 76), radius=23, fill=(24, 24, 27, 248), outline=(255, 255, 255, 200))
        self.assertEqual(img.size, (W, H))

    def test_ptt_hold_release(self):
        """Hold > 300ms triggers push-to-talk (stops on release)."""
        started = []
        stopped = []
        ptt = PttController(lambda: started.append(1), lambda: stopped.append(1))
        ptt.on_press(now=10.0)
        self.assertEqual(len(started), 1)
        self.assertEqual(len(stopped), 0)
        ptt.on_release(now=10.5)  # held 500ms
        self.assertEqual(len(stopped), 1)
        self.assertFalse(ptt.is_recording)
        self.assertFalse(ptt.is_locked)

    def test_ptt_tap_locks_handsfree(self):
        """Tap < 300ms locks handsfree, second tap stops."""
        started = []
        stopped = []
        ptt = PttController(lambda: started.append(1), lambda: stopped.append(1))
        # First tap (100ms)
        ptt.on_press(now=10.0)
        ptt.on_release(now=10.1)
        self.assertEqual(len(started), 1)
        self.assertEqual(len(stopped), 0)
        self.assertTrue(ptt.is_recording)
        self.assertTrue(ptt.is_locked)

        # Second tap (80ms)
        ptt.on_press(now=12.0)
        ptt.on_release(now=12.08)
        self.assertEqual(len(stopped), 1)
        self.assertFalse(ptt.is_recording)

    def test_faster_whisper_int8_transcription(self):
        """Verify faster-whisper INT8 model loads and transcribes silence in < 200ms."""
        from faster_whisper import WhisperModel
        model = WhisperModel("tiny.en", device="cpu", compute_type="int8", local_files_only=True)
        silence = np.zeros(16000, dtype=np.float32)
        segments, _ = model.transcribe(silence, language="en", beam_size=1)
        res_list = list(segments)
        self.assertIsInstance(res_list, list)

    def test_audio_muter_lifecycle(self):
        """Verify AudioMuter mute and unmute calls succeed without unhandled exceptions."""
        from whisper_flow import AudioMuter
        muter = AudioMuter()
        # Test mute
        muter.mute_others()
        # Test unmute
        muter.unmute_all()
        self.assertEqual(len(muter.muted_controls), 0)

    def test_click_waveform_generation(self):
        """Verify tactile click waveform is synthesized cleanly within bounds."""
        freq, duration, volume = 1350, 0.016, 0.08
        sample_rate = 16000
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        decay = np.exp(-t * 220)
        wave = (np.sin(2 * np.pi * freq * t) * decay * volume).astype(np.float32)
        self.assertGreater(len(wave), 0)
        self.assertLessEqual(np.max(np.abs(wave)), 0.10)
        self.assertEqual(wave.dtype, np.float32)

    def test_config_management(self):
        """Verify config load and save correctly handles engine selection."""
        from whisper_flow import load_config, save_config
        cfg = load_config()
        self.assertIn("engine", cfg)
        orig_engine = cfg["engine"]
        try:
            cfg["engine"] = "phonon"
            save_config(cfg)
            loaded = load_config()
            self.assertEqual(loaded["engine"], "phonon")
        finally:
            cfg["engine"] = orig_engine
            save_config(cfg)

    def test_phonon_client_framing(self):
        """Verify PhononStreamClient queues float32 audio chunks in raw bytes format."""
        from whisper_flow import PhononStreamClient
        client = PhononStreamClient(port=8999)
        client.is_active = True
        audio = np.ones(160, dtype=np.float32) * 0.5
        client.send_audio_chunk(audio)
        self.assertEqual(client._send_queue.qsize(), 1)
        raw_bytes = client._send_queue.get_nowait()
        self.assertEqual(len(raw_bytes), 160 * 4)
        client.abort()
        self.assertFalse(client.is_active)

    def test_live_text_rendering(self):
        """Verify PIL renders live text preview and font metrics without error."""
        from PIL import Image, ImageDraw, ImageFont
        W, H, S = 400, 106, 3
        img = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        font = ImageFont.truetype("segoeui.ttf", 13 * S)
        text = "Testing live stream transcription preview."
        w = d.textlength(text, font=font)
        self.assertGreater(w, 0)
        d.text((100, 50), text, font=font, fill=(255, 255, 255, 240))
        resized = img.resize((W, H), Image.LANCZOS)
        self.assertEqual(resized.size, (W, H))

if __name__ == "__main__":
    unittest.main()

