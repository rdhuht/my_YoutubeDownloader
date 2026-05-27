"""Entry point for YouTube Downloader application."""
import tkinter as tk
from ttkbootstrap import Style

from ui import YouTubeDownloader
from config import FFMPEG_AVAILABLE

if __name__ == "__main__":
    root = tk.Tk()
    style = Style(theme="superhero")
    app = YouTubeDownloader(root)
    root.mainloop()