import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock

from PIL import Image
from agent_app.executors.screen_video import ScreenVideo


class ScreenVideoTest(unittest.TestCase):
    def test_sampled_screenshots_produce_a_valid_mp4(self):
        with tempfile.TemporaryDirectory() as directory:
            session = Mock()
            session.screenshot.return_value = Image.new("RGB", (32, 48), (40, 120, 220))
            path = Path(directory) / "video.mp4"
            recorder = ScreenVideo(session, path, fps=4)
            recorder.start()
            deadline = time.monotonic() + 8
            while recorder.frames < 2 and not recorder.error and time.monotonic() < deadline:
                time.sleep(.05)
            evidence = recorder.stop()
            self.assertFalse(evidence.get("video_error"), evidence)
            self.assertEqual(path.read_bytes()[4:8], b"ftyp")
            import imageio.v2 as imageio

            with imageio.get_reader(path) as reader:
                frame = reader.get_data(0)
                self.assertEqual(frame.shape[:2], (48, 32))
                self.assertGreater(float(frame.std()), 10)


if __name__ == "__main__":
    unittest.main()
