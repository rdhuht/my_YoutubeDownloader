import os
import subprocess
import sys
import tempfile
import shutil
import platform
import time
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap import Style
import threading
import tkinter.simpledialog as sd
import tkinter.messagebox as mb
import tkinter.font as tkFont
from bs4 import BeautifulSoup
import yt_dlp as youtube_dl

class PlaceholderEntry(ttk.Entry):
    def __init__(self, container, placeholder, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.placeholder = placeholder
        self.placeholder_color = 'grey'
        self.default_fg_color = self['foreground']

        self.bind("<FocusIn>", self._focus_in)
        self.bind("<FocusOut>", self._focus_out)

        self._focus_out(None)

    def _focus_in(self, event):
        if self['foreground'] == self.placeholder_color:
            self.delete(0, "end")
            self['foreground'] = self.default_fg_color

    def _focus_out(self, event):
        if not self.get():
            self.insert(0, self.placeholder)
            self['foreground'] = self.placeholder_color

class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader")
        self.root.minsize(width=600, height=200)
        self.is_downloading = False
        self.download_start_time = None

        large_font = tkFont.Font(family="Arial", size=20)
        middle_font = tkFont.Font(family="Arial", size=18)
        small_font = tkFont.Font(family="Arial", size=16)

        self.top_frame = ttk.Frame(root)
        self.top_frame.pack(fill='x', padx=10, pady=5)

        self.entry_url = PlaceholderEntry(self.top_frame, "Enter video URL here")
        self.entry_url.pack(fill='x', expand=True, padx=10, pady=10, side=tk.LEFT)

        self.button_load = ttk.Button(self.top_frame, text="Load Video Info", command=self.start_parse_video_thread, bootstyle='success')
        self.button_load.pack(side=tk.RIGHT)

        self.video_title_label = ttk.Label(root, text="Video Title", foreground='gray')
        self.video_title_label.pack(padx=10, pady=(0, 5))

        self.quality_frame = ttk.Frame(root)
        self.quality_frame.pack(padx=5, pady=10)
        self.quality_label = ttk.Label(self.quality_frame, text="Quality:", font=small_font)
        self.quality_label.pack(side=tk.LEFT, padx=10)
        self.quality_combobox = ttk.Combobox(self.quality_frame, state="readonly", width=15)
        self.quality_combobox.pack(side=tk.LEFT, padx=5)

        self.caption_label = ttk.Label(self.quality_frame, text="Subtitles:", font=small_font)
        self.caption_label.pack(side=tk.LEFT, padx=5)
        self.caption_combobox = ttk.Combobox(self.quality_frame, state="readonly", width=25)
        self.caption_combobox.pack(side=tk.LEFT, padx=5)

        self.button_frame = ttk.Frame(root)
        self.button_frame.pack(pady=5)
        self.button_browse = ttk.Button(self.button_frame, text="Download Path", command=self.browse_path, bootstyle='info')
        self.button_browse.pack(side=tk.LEFT, padx=(10, 5))
        self.button_download = ttk.Button(self.button_frame, text="Start Download", command=self.start_download_thread, bootstyle='danger')
        self.button_download.pack(side=tk.LEFT, padx=(5, 10))
        self.button_cancel = ttk.Button(self.button_frame, text="Cancel Download", command=self.cancel_download, bootstyle='warning')
        self.button_cancel.pack(side=tk.LEFT, padx=(5, 10))
        self.button_cancel.config(state='disabled')

        self.bottom_frame = ttk.Frame(root)
        self.bottom_frame.pack(fill='x', padx=20, pady=5)

        self.progress = ttk.Progressbar(self.bottom_frame, bootstyle="success-striped", orient='horizontal', mode='determinate')
        self.progress.pack(fill='x', expand=True, side=tk.LEFT)
        self.progress_label = ttk.Label(self.bottom_frame, text="0%", font=small_font)
        self.progress_label.pack(padx=8, pady=5)

        self.download_path = ""

        self.center_window(self.root)

    def center_window(self, window):
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
        x = (window.winfo_screenwidth() // 2) - (width // 2)
        y = (window.winfo_screenheight() // 2) - (height // 2)
        window.geometry(f'+{x}+{y}')

    def browse_path(self):
        initial_path = os.path.join(os.path.expanduser('~'), 'Desktop')
        self.download_path = filedialog.askdirectory(initialdir=initial_path)
        if not self.download_path:
            self.download_path = initial_path
        self.root.title(f"YouTube Downloader - Download Path Selected: {self.download_path}")

    def show_progress(self, d):
        if d['status'] == 'downloading':
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes', 1)
            percentage = downloaded / total * 100
            self.progress['value'] = percentage
            self.progress_label['text'] = f"{percentage:.2f}%"
            self.root.update_idletasks()
            if self.download_start_time:
                elapsed_time = time.time() - self.download_start_time
                elapsed_time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
                self.root.title(f"YouTube Downloader - Elapsed Time: {elapsed_time_str}")

    def start_parse_video_thread(self):
        self.progress['value'] = 0
        self.disable_buttons()
        self.root.title(f"YouTube Downloader - Parsing Video Info...")
        threading.Thread(target=self.load_video_msg).start()

    def start_download_thread(self):
        self.progress['value'] = 0
        self.disable_buttons()
        self.root.title(f"YouTube Downloader - Starting Download")
        threading.Thread(target=self.download_video).start()

    def disable_buttons(self):
        self.button_download.config(state='disabled')
        self.button_browse.config(state='disabled')
        self.button_load.config(state="disabled")

    def enable_buttons(self):
        self.button_download.config(state='normal')
        self.button_browse.config(state='normal')
        self.button_load.config(state='normal')

    def open_download_folder(self):
        if self.download_path:
            if os.name == 'nt':
                subprocess.Popen(['explorer', self.download_path.replace('/', '\\')])
            elif os.name == 'posix':
                subprocess.Popen(['open', self.download_path])

    def cancel_download(self):
        self.is_downloading = False
        messagebox.showinfo("Cancel Download", "Download Cancelled by User.")
        self.button_cancel.config(state='disabled')
        self.root.title("YouTube Downloader")

    def load_video_msg(self):
        url = self.entry_url.get().strip()
        if not url or url == "Enter video URL here":
            messagebox.showerror("Error", "Please enter a valid video URL.")
            self.enable_buttons()
            return
        try:
            ydl_opts = {
                'quiet': True,
                'skip_download': True,
                'noplaylist': True,
            }
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=False)
                title = info_dict.get('title', 'Video')
                formats = info_dict.get('formats', [])
                self.video_title_label['text'] = f"Video Title: {title}"

                qualities = []
                for fmt in formats:
                    if fmt.get('height'):
                        qualities.append(f"{fmt['format_id']} - {fmt['height']}p")

                subtitles = info_dict.get('subtitles', {})

                self.quality_combobox['values'] = qualities
                if qualities:
                    self.quality_combobox.current(0)

                self.caption_combobox['values'] = list(subtitles.keys())
                if subtitles:
                    self.caption_combobox.current(0)

                self.root.title(f"YouTube Downloader - Video Loaded: {title}")
        except Exception as e:
            messagebox.showerror("Error Loading Video", f"Error: {e}")
            self.root.title("YouTube Downloader")
        finally:
            self.enable_buttons()

    def download_video(self):
        url = self.entry_url.get().strip()
        if not url or url == "Enter video URL here":
            messagebox.showerror("Error", "Please enter a valid video URL.")
            self.enable_buttons()
            return

        quality = self.quality_combobox.get()
        if not quality:
            messagebox.showerror("Error", "Please select a video quality.")
            self.enable_buttons()
            return

        selected_subtitle = self.caption_combobox.get()

        self.is_downloading = True
        self.download_start_time = time.time()

        ydl_opts = {
            'format': quality.split(" - ")[0],
            'outtmpl': os.path.join(self.download_path, '%(title)s.%(ext)s'),
            'progress_hooks': [self.show_progress],
        }

        if selected_subtitle:
            ydl_opts['subtitleslangs'] = [selected_subtitle]
            ydl_opts['writesubtitles'] = True
            ydl_opts['subtitlesformat'] = 'srt'

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            elapsed_time = time.time() - self.download_start_time
            elapsed_time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
            self.root.title(f"YouTube Downloader - Download Complete (Elapsed Time: {elapsed_time_str})")
            messagebox.showinfo("Download Complete", "The video has been downloaded successfully.")
            self.open_download_folder()
        except Exception as e:
            messagebox.showerror("Download Error", f"Error: {e}")
            self.root.title("YouTube Downloader")
        finally:
            self.is_downloading = False
            self.enable_buttons()
            self.download_start_time = None

if __name__ == "__main__":
    root = tk.Tk()
    style = Style(theme="superhero")
    app = YouTubeDownloader(root)
    root.mainloop()
