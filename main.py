import os
import subprocess
import sys
import time
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap import Style
import threading
import tkinter.font as tkFont
import yt_dlp as youtube_dl

# 定义带有占位符文本的输入框类
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

# 定义主应用程序类
class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube 下载器")
        self.root.minsize(width=600, height=200)
        self.is_downloading = False
        self.download_start_time = None

        # 设置字体
        large_font = tkFont.Font(family="Arial", size=20)
        middle_font = tkFont.Font(family="Arial", size=18)
        small_font = tkFont.Font(family="Arial", size=16)

        # 顶部框架
        self.top_frame = ttk.Frame(root)
        self.top_frame.pack(fill='x', padx=10, pady=5)

        # 输入视频URL的文本框
        self.entry_url = PlaceholderEntry(self.top_frame, "在此输入视频URL")
        self.entry_url.pack(fill='x', expand=True, padx=10, pady=10, side=tk.LEFT)

        # 加载视频信息的按钮
        self.button_load = ttk.Button(self.top_frame, text="加载视频信息", command=self.start_parse_video_thread, bootstyle='success')
        self.button_load.pack(side=tk.RIGHT)

        # 显示视频标题的标签
        self.video_title_label = ttk.Label(root, text="视频标题", foreground='gray')
        self.video_title_label.pack(padx=10, pady=(0, 5))

        # 质量选择框架
        self.quality_frame = ttk.Frame(root)
        self.quality_frame.pack(padx=5, pady=10)
        self.quality_label = ttk.Label(self.quality_frame, text="质量:", font=small_font)
        self.quality_label.pack(side=tk.LEFT, padx=10)
        self.quality_combobox = ttk.Combobox(self.quality_frame, state="readonly", width=15)
        self.quality_combobox.pack(side=tk.LEFT, padx=5)

        # 字幕选择框架
        self.caption_label = ttk.Label(self.quality_frame, text="字幕:", font=small_font)
        self.caption_label.pack(side=tk.LEFT, padx=5)
        self.caption_combobox = ttk.Combobox(self.quality_frame, state="readonly", width=25)
        self.caption_combobox.pack(side=tk.LEFT, padx=5)

        # 按钮框架
        self.button_frame = ttk.Frame(root)
        self.button_frame.pack(pady=5)
        self.button_browse = ttk.Button(self.button_frame, text="下载路径", command=self.browse_path, bootstyle='info')
        self.button_browse.pack(side=tk.LEFT, padx=(10, 5))
        self.button_download = ttk.Button(self.button_frame, text="开始下载", command=self.start_download_thread, bootstyle='danger')
        self.button_download.pack(side=tk.LEFT, padx=(5, 10))
        self.button_cancel = ttk.Button(self.button_frame, text="取消下载", command=self.cancel_download, bootstyle='warning')
        self.button_cancel.pack(side=tk.LEFT, padx=(5, 10))
        self.button_cancel.config(state='disabled')

        # 底部框架
        self.bottom_frame = ttk.Frame(root)
        self.bottom_frame.pack(fill='x', padx=20, pady=5)

        # 进度条
        self.progress = ttk.Progressbar(self.bottom_frame, bootstyle="success-striped", orient='horizontal', mode='determinate')
        self.progress.pack(fill='x', expand=True, side=tk.LEFT)
        self.progress_label = ttk.Label(self.bottom_frame, text="0%", font=small_font)
        self.progress_label.pack(padx=8, pady=5)

        self.download_path = ""

        self.center_window(self.root)

    # 将窗口居中显示
    def center_window(self, window):
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
        x = (window.winfo_screenwidth() // 2) - (width // 2)
        y = (window.winfo_screenheight() // 2) - (height // 2)
        window.geometry(f'+{x}+{y}')

    # 浏览下载路径
    def browse_path(self):
        initial_path = os.path.join(os.path.expanduser('~'), 'Desktop')
        self.download_path = filedialog.askdirectory(initialdir=initial_path)
        if not self.download_path:
            self.download_path = initial_path
        self.root.title(f"YouTube 下载器 - 下载路径: {self.download_path}")

    # 显示下载进度
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
                self.root.title(f"YouTube 下载器 - 已用时间: {elapsed_time_str}")

    # 开始解析视频线程
    def start_parse_video_thread(self):
        self.progress['value'] = 0
        self.disable_buttons()
        self.root.title(f"YouTube 下载器 - 解析视频信息中...")
        threading.Thread(target=self.load_video_msg).start()

    # 开始下载视频线程
    def start_download_thread(self):
        self.progress['value'] = 0
        self.disable_buttons()
        self.root.title(f"YouTube 下载器 - 开始下载")
        threading.Thread(target=self.download_video).start()

    # 禁用按钮
    def disable_buttons(self):
        self.button_download.config(state='disabled')
        self.button_browse.config(state='disabled')
        self.button_load.config(state="disabled")

    # 启用按钮
    def enable_buttons(self):
        self.button_download.config(state='normal')
        self.button_browse.config(state='normal')
        self.button_load.config(state='normal')

    # 打开下载文件夹
    def open_download_folder(self):
        if self.download_path:
            if os.name == 'nt':
                subprocess.Popen(['explorer', self.download_path.replace('/', '\\')])
            elif os.name == 'posix':
                subprocess.Popen(['open', self.download_path])

    # 取消下载
    def cancel_download(self):
        self.is_downloading = False
        messagebox.showinfo("取消下载", "下载已取消。")
        self.button_cancel.config(state='disabled')
        self.root.title("YouTube 下载器")

    # 加载视频信息
    def load_video_msg(self):
        url = self.entry_url.get().strip()
        if not url or url == "在此输入视频URL":
            messagebox.showerror("错误", "请输入有效的视频URL。")
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

                title = info_dict.get('title', '视频')
                self.formats = info_dict.get('formats', [])  # 存储 formats
                self.video_title_label['text'] = f"视频标题: {title}"

                qualities = []
                for fmt in self.formats:
                    if fmt.get('ext') == 'mp4' and fmt.get('filesize'):
                        quality_text = f"{fmt['height']}p - {fmt['filesize'] / 1024 / 1024:.2f} MB"
                        qualities.append(quality_text)

                self.quality_combobox['values'] = qualities
                if qualities:
                    self.quality_combobox.current(0)

                subtitles = info_dict.get('subtitles', {})
                self.caption_combobox['values'] = list(subtitles.keys())
                if subtitles:
                    self.caption_combobox.current(0)

                self.root.title(f"YouTube 下载器 - 视频已加载: {title}")
        except Exception as e:
            messagebox.showerror("加载视频错误", f"错误: {e}")
            self.root.title("YouTube 下载器")
        finally:
            self.enable_buttons()

    # 下载视频
    def download_video(self):
        url = self.entry_url.get().strip()
        if not url or url == "在此输入视频URL":
            messagebox.showerror("错误", "请输入有效的视频URL。")
            self.enable_buttons()
            return

        quality_text = self.quality_combobox.get()
        if not quality_text:
            messagebox.showerror("错误", "请选择视频质量。")
            self.enable_buttons()
            return

        selected_format = None
        for fmt in self.formats:  # 使用存储的formats
            if fmt.get('ext') == 'mp4' and fmt.get('filesize'):
                quality_opt = f"{fmt['height']}p - {fmt['filesize'] / 1024 / 1024:.2f} MB"
                if quality_text == quality_opt:
                    selected_format = fmt['format_id']
                    break

        if not selected_format:
            messagebox.showerror("错误", "未能找到匹配的格式。")
            self.enable_buttons()
            return

        selected_subtitle = self.caption_combobox.get()

        self.is_downloading = True
        self.download_start_time = time.time()

        ydl_opts = {
            'format': selected_format,  # 使用选择的格式 ID
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
            self.root.title(f"YouTube 下载器 - 下载完成 (已用时间: {elapsed_time_str})")
            messagebox.showinfo("下载完成", "视频已成功下载。")
            self.open_download_folder()
        except Exception as e:
            messagebox.showerror("下载错误", f"错误: {e}")
            self.root.title("YouTube 下载器")
        finally:
            self.is_downloading = False
            self.enable_buttons()
            self.download_start_time = None


# 主程序入口
if __name__ == "__main__":
    root = tk.Tk()
    style = Style(theme="superhero")
    app = YouTubeDownloader(root)
    root.mainloop()
