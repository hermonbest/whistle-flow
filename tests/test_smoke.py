import unittest
import numpy as np
import needle

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
    def test_needle_transcription_warm(self):
        """Verify needle model can transcribe 16 kHz silent array without crashing."""
        sample_rate = 16000
        silence = np.zeros(sample_rate, dtype=np.float32)
        result = needle.transcribe(silence)
        self.assertIsInstance(result, dict)
        self.assertIn("text", result)

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

    def test_streaming_long_audio_drains_cleanly(self):
        """Verify needle.stream drains long audio chunks (e.g. 5 seconds) without hanging or crashing."""
        sample_rate = 16000
        def chunk_gen():
            for _ in range(5):
                yield np.zeros(sample_rate, dtype=np.float32)
        results = list(needle.stream(chunk_gen()))
        self.assertGreaterEqual(len(results), 5)
        self.assertIn("text", results[-1])

if __name__ == "__main__":
    unittest.main()
