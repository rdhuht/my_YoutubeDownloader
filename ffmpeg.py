"""FFmpeg integration and progress logging."""
import re


class FFmpegProgressLogger:
    """Parses ffmpeg stderr `Duration:` and `time=` lines emitted by yt-dlp's
    FFmpeg-based postprocessors and surfaces a 0-99% progress string per
    playlist entry. Designed to be safe to call from any thread because
    `app.update_video_progress_text` is self-wrapping via `root.after(0, ...)`.
    """

    def __init__(self, app_instance, is_playlist=False, entry_index=None,
                 video_duration=None):
        self.app = app_instance
        self.is_playlist = is_playlist
        self.entry_index = entry_index
        # Prefer the duration we already have from the playlist entry so the
        # very first `time=` line yields a correct percentage, before ffmpeg
        # emits its own "Duration:" header.
        self._duration = video_duration or 0
        self._progress_pattern = re.compile(r'time=(\d+):(\d{2}):(\d{2}\.\d+)')
        self._duration_pattern = re.compile(r'Duration:\s*(\d+):(\d{2}):(\d{2})')

    def debug(self, info):
        # Only learn duration from a real "Duration:" header line. The regex
        # is anchored on the literal "Duration:" prefix so we don't pick up
        # arbitrary HH:MM:SS substrings elsewhere in ffmpeg's output.
        if self._duration == 0:
            match = self._duration_pattern.search(info)
            if match:
                h, m, s = int(match.group(1)), int(match.group(2)), int(match.group(3))
                self._duration = h * 3600 + m * 60 + s
        if 'time=' in info and self._duration > 0:
            match = self._progress_pattern.search(info)
            if match:
                h, m, s = int(match.group(1)), int(match.group(2)), float(match.group(3))
                current_time = h * 3600 + m * 60 + s
                percentage = min(current_time / self._duration * 100, 99)
                self.app.update_video_progress_text(
                    self.entry_index, f"转换中 {percentage:.0f}%", 'converting')

    def warning(self, info):
        pass

    def error(self, info):
        pass