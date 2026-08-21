"""FFmpeg integration and progress logging."""
import re


class CollectingLogger:
    """A yt-dlp logger that captures every line so the GUI can show them in a
    'details' dialog when a download fails.

    The FFmpegProgressLogger class below parses the ffmpeg stderr `time=`
    lines; this class is for capturing yt-dlp's own logging output.
    """

    def __init__(self, log_path=None):
        self.lines = []
        # Optional path that the worker thread will write the full log to
        # on failure. Kept here so download_single / download_multi can call
        # `collector.flush_to_disk(short_msg)` without needing access to
        # the app instance.
        self._log_path = log_path

    def debug(self, msg):
        if not isinstance(msg, str):
            return
        # Keep only meaningful debug lines; filter out the per-second
        # download percentage polling that floods the buffer.
        if '[download]' in msg and '%' in msg:
            return
        if 'Downloading webpage' in msg:
            return
        self.lines.append(msg)

    def info(self, msg):
        self._append(msg)

    def warning(self, msg):
        self._append('WARNING: ' + msg)

    def error(self, msg):
        self._append('ERROR: ' + msg)

    def _append(self, msg):
        if isinstance(msg, str):
            self.lines.append(msg)

    def text(self):
        return '\n'.join(self.lines[-200:])  # cap to last 200 lines

    def flush_to_disk(self, short_msg, log_path=None):
        """Write the captured log + short error message to disk synchronously.
        Returns the actual path written, or None on failure. Safe to call
        from any thread; does not touch Tk.
        """
        path = log_path or self._log_path
        if not path:
            return None
        try:
            from datetime import datetime
            import yt_dlp as _yt
            from config import (
                FFMPEG_AVAILABLE as _FFMPEG,
                JS_RUNTIME as _JS,
                get_proxy as _proxy,
                get_cookiefile as _cookies,
            )
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write('YouTube 下载器 — 下载失败日志\n')
                fh.write(f'Time: {datetime.now().isoformat()}\n')
                fh.write(f'yt-dlp: {_yt.version.__version__}\n')
                fh.write(f'FFmpeg: {"yes" if _FFMPEG else "no"}\n')
                fh.write(f'JS runtime: {_JS or "none"}\n')
                fh.write(f'Proxy: {_proxy() or "none"}\n')
                fh.write(f'Cookies: {_cookies() or "none"}\n\n')
                fh.write(f'=== Error ===\n{short_msg}\n\n')
                fh.write(f'=== yt-dlp log ===\n{self.text() or "(empty)"}\n')
            return path
        except Exception as exc:
            try:
                # Last-ditch effort: write the error to a sibling file
                # alongside the requested path so the user can still find it.
                import os
                fallback = os.path.join(os.path.dirname(path) or '.', 'last_log_error.txt')
                with open(fallback, 'w', encoding='utf-8') as fh:
                    fh.write(f'Could not write {path}: {exc}\n')
                return fallback
            except Exception:
                return None


class FFmpegProgressLogger:
    """Parses ffmpeg stderr `Duration:` and `time=` lines emitted by yt-dlp's
    FFmpeg-based postprocessors and surfaces a 0-99% progress string per
    playlist entry. Designed to be safe to call from any thread because
    `app.update_video_progress_text` is self-wrapping via `root.after(0, ...)`.
    """

    def __init__(self, app_instance, is_playlist=False, entry_index=None,
                 video_duration=None, collector=None):
        self.app = app_instance
        self.is_playlist = is_playlist
        self.entry_index = entry_index
        # Prefer the duration we already have from the playlist entry so the
        # very first `time=` line yields a correct percentage, before ffmpeg
        # emits its own "Duration:" header.
        self._duration = video_duration or 0
        self._progress_pattern = re.compile(r'time=(\d+):(\d{2}):(\d{2}\.\d+)')
        self._duration_pattern = re.compile(r'Duration:\s*(\d+):(\d{2}):(\d{2})')
        self._collector = collector  # optional CollectingLogger

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

    def info(self, info):
        if self._collector is not None:
            self._collector.info(info)

    def warning(self, info):
        if self._collector is not None:
            self._collector.warning(info)

    def error(self, info):
        if self._collector is not None:
            self._collector.error(info)