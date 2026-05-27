"""Configuration constants and application settings."""
import re
import subprocess

_proxy = "http://127.0.0.1:7897"

def get_proxy():
    return _proxy

def set_proxy(value):
    global _proxy
    _proxy = value if value else None

YOUTUBE_URL_PATTERN = re.compile(r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$')

def check_ffmpeg():
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except:
        return False

FFMPEG_AVAILABLE = check_ffmpeg()
print(f"FFmpeg available: {FFMPEG_AVAILABLE}")