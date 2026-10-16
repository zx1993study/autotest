import base64
import io
from pathlib import Path

from web_automation.mobile import screen_from_xml


def capture(session,bundle_id):
    current = session.app_current()
    if current.get('bundleId') != bundle_id:
        raise ValueError('前台应用已变化，请打开目标应用后重新开始')
    screen = screen_from_xml(session.source(),bundle_id,session.window_size())
    frame = None if screen['sensitive'] else session.screenshot()
    encoded = None
    if frame is not None:
        preview = frame.copy()
        preview.thumbnail((1200,1200))
        output = io.BytesIO()
        preview.save(output,format='PNG')
        if len(output.getvalue()) <= 4*1024*1024:
            encoded = base64.b64encode(output.getvalue()).decode('ascii')
    return screen,encoded,frame


class ObservationVideo:
    """Reuse observed frames, with no parallel unfiltered screenshot thread."""
    def __init__(self,path:Path,enabled=True):
        self.path,self.enabled = path,enabled
        self.writer = None
        self.size = None
        self.error = ''

    def append(self,frame):
        if not self.enabled or frame is None or self.error:
            return
        try:
            import imageio.v2 as imageio
            import numpy as np
            if self.writer is None:
                self.path.parent.mkdir(parents=True,exist_ok=True)
                self.writer = imageio.get_writer(str(self.path),fps=1,macro_block_size=2)
                self.size = frame.size
            self.writer.append_data(np.asarray(frame.convert('RGB').resize(self.size)))
            if self.path.exists() and self.path.stat().st_size > 200*1024*1024:
                raise ValueError('Recording exceeded 200 MiB')
        except Exception:
            self.error = '设备观察录屏编码失败'

    def close(self):
        if self.writer:
            try:
                self.writer.close()
            except Exception:
                self.error = '录屏文件未完整生成'
        if self.path.is_file() and not self.error:
            return {'video_local_path':str(self.path),'video_file':self.path.name,
                    'recording_mode':'wda_observation_sampling','recording_fps':1}
        return {'video_error':self.error} if self.error else {}
