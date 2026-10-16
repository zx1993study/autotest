from __future__ import annotations

import threading
import time
from pathlib import Path


class ScreenVideo:
    """Record sampled WDA screenshots; this is not native device screen capture."""

    def __init__(self, session, path: Path, fps: int = 2) -> None:
        self.session = session
        self.path = path
        self.fps = fps
        self.error = ""
        self.stop_event = threading.Event()
        self.thread = None
        self.frames = 0

    def start(self):
        self.thread = threading.Thread(target=self._record, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=40)
        if self.thread and self.thread.is_alive():
            return {"video_error": "Recording did not finish in time"}
        if self.frames and self.path.exists():
            return {"video_file": self.path.name, "video_local_path": str(self.path), "recording_mode": "wda_screenshot_sampling", "recording_fps": self.fps, "video_error": self.error or None}
        return {"video_error": self.error or "No recording frames were captured"}

    def _record(self):
        writer = None
        try:
            import imageio.v2 as imageio
            import numpy as np

            self.path.parent.mkdir(parents=True, exist_ok=True)
            writer = imageio.get_writer(str(self.path), fps=self.fps, macro_block_size=2)
            dimensions = None
            while not self.stop_event.is_set():
                started = time.monotonic()
                frame = self.session.screenshot().convert("RGB")
                dimensions = dimensions or frame.size
                writer.append_data(np.asarray(frame.resize(dimensions)))
                self.frames += 1
                if self.path.exists() and self.path.stat().st_size > 200 * 1024 * 1024:
                    raise RuntimeError("Recording exceeded the 200 MiB limit")
                self.stop_event.wait(max(0, 1 / self.fps - (time.monotonic() - started)))
        except Exception as exc:  # noqa: BLE001 - encoder thread failures become video evidence.
            self.error = str(exc)
        finally:
            if writer is not None:
                try:
                    writer.close()
                except Exception as exc:  # noqa: BLE001 - capture encoder finalization failures.
                    self.error = str(exc)
