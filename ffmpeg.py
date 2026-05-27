"""FFmpeg integration and progress logging."""
import re

class FFmpegProgressLogger:
    def __init__(self, app_instance, is_playlist=False, entry_index=None):
        self.app = app_instance
        self.is_playlist = is_playlist
        self.entry_index = entry_index
        self._progress_pattern = re.compile(r'time=(\d+):(\d{2}):(\d{2}\.\d+)')
        self._duration = 0

    def debug(self, info):
        if 'Duration:' in info:
            try:
                match = re.search(r'(\d+):(\d{2}):(\d{2})', info)
                if match:
                    h, m, s = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    self._duration = h * 3600 + m * 60 + s
            except:
                pass
        if 'time=' in info:
            match = self._progress_pattern.search(info)
            if match and self._duration > 0:
                h, m, s = int(match.group(1)), int(match.group(2)), float(match.group(3))
                current_time = h * 3600 + m * 60 + s
                percentage = min(current_time / self._duration * 100, 99)
                self.app.update_video_progress_text(self.entry_index, f"转换中 {percentage:.0f}%")

    def warning(self, info):
        pass

    def error(self, info):
        pass