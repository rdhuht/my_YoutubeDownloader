"""Configuration constants and application settings."""
import re
import subprocess

VERSION = "1.6.0"

_proxy = "http://127.0.0.1:7897"
_cookiefile = None
_max_concurrent = 3


def get_proxy():
    return _proxy


def set_proxy(value):
    global _proxy
    _proxy = value if value else None


def get_cookiefile():
    return _cookiefile


def set_cookiefile(value):
    global _cookiefile
    _cookiefile = value if value else None


def get_max_concurrent():
    return _max_concurrent


def set_max_concurrent(value):
    global _max_concurrent
    try:
        n = int(value)
    except (TypeError, ValueError):
        return
    if n < 1:
        n = 1
    if n > 8:
        n = 8
    _max_concurrent = n

YOUTUBE_URL_PATTERN = re.compile(r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$')

def check_ffmpeg():
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except:
        return False

FFMPEG_AVAILABLE = check_ffmpeg()
print(f"FFmpeg available: {FFMPEG_AVAILABLE}")


def check_js_runtime():
    """Return the name of the first available JS runtime (node/deno) or None.

    yt-dlp needs a JS runtime to solve YouTube's `n` challenge. Without one,
    current YouTube streams typically fail with "The page needs to be reloaded"
    under the SABR streaming experiment.
    """
    import shutil
    for name in ('node', 'deno'):
        if shutil.which(name):
            return name
    return None


JS_RUNTIME = check_js_runtime()
print(f"JS runtime available: {JS_RUNTIME or 'none'}")