import unittest
import numpy as np
import needle

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

if __name__ == "__main__":
    unittest.main()
