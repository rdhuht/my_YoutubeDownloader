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
import re
import yt_dlp as youtube_dl

# 检查ffmpeg是否可用
def check_ffmpeg():
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except:
        return False

FFMPEG_AVAILABLE = check_ffmpeg()
print(f"FFmpeg available: {FFMPEG_AVAILABLE}")

# 用户代理配置 - 默认使用本地代理
USER_PROXY = "http://127.0.0.1:7897"

# YouTube URL 正则表达式
YOUTUBE_URL_PATTERN = re.compile(r'(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$')

# 从剪贴板获取URL
def get_url_from_clipboard(root):
    try:
        clipboard_text = root.clipboard_get()
        if clipboard_text and YOUTUBE_URL_PATTERN.match(clipboard_text.strip()):
            return clipboard_text.strip()
    except:
        pass
    return None

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
        self.entry_url = ttk.Entry(self.top_frame)
        self.entry_url.pack(fill='x', expand=True, padx=10, pady=10, side=tk.LEFT)

        # 检查剪贴板是否有URL
        clipboard_url = get_url_from_clipboard(root)
        if clipboard_url:
            self.entry_url.insert(0, clipboard_url)
            self.root.title(f"YouTube 下载器 - 已从剪贴板获取URL")

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

        # 字幕/配音选择框架
        self.caption_label = ttk.Label(self.quality_frame, text="字幕/配音:", font=small_font)
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

        self.download_path = os.path.join(os.path.expanduser('~'), 'Desktop')
        self.entry_url['foreground'] = 'grey'
        self.entry_url.insert(0, "在此输入视频URL")

        # 创建菜单栏
        self.create_menu_bar()

        self.center_window(self.root)

    # 创建菜单栏
    def create_menu_bar(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # 设置菜单
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="设置", menu=settings_menu)
        settings_menu.add_command(label="代理设置", command=self.show_proxy_dialog)
        settings_menu.add_separator()
        settings_menu.add_command(label="关于", command=self.show_about)

    # 代理设置对话框
    def show_proxy_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("代理设置")
        dialog.geometry("400x120")
        dialog.transient(self.root)
        dialog.grab_set()

        # 让对话框居中
        dialog.geometry(f"+{self.root.winfo_x() + 100}+{self.root.winfo_y() + 100}")

        ttk.Label(dialog, text="代理地址 (例如: http://127.0.0.1:7897):").pack(pady=(15, 5), padx=10)
        proxy_entry = ttk.Entry(dialog, width=50)
        proxy_entry.pack(pady=5, padx=10)
        proxy_entry.insert(0, USER_PROXY if USER_PROXY else "")

        def save_proxy():
            global USER_PROXY
            proxy_value = proxy_entry.get().strip()
            USER_PROXY = proxy_value if proxy_value else None
            dialog.destroy()
            if USER_PROXY:
                messagebox.showinfo("代理设置", f"代理已设置为: {USER_PROXY}")
            else:
                messagebox.showinfo("代理设置", "代理已清除")

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="保存", command=save_proxy).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    # 关于对话框
    def show_about(self):
        messagebox.showinfo("关于", "YouTube 下载器 v2.0\n\n支持代理设置和多音轨视频下载")

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
            downloaded = d.get('downloaded_bytes', 0) or 0
            total = d.get('total_bytes') or d.get('totalbyte') or 1
            if total and total > 0:
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
            if USER_PROXY:
                ydl_opts['proxy'] = USER_PROXY

            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=False)

                title = info_dict.get('title', '视频')
                self.formats = info_dict.get('formats', [])  # 存储 formats
                self.video_title_label['text'] = f"视频标题: {title}"

                qualities = []
                format_map = {}  # 存储 quality_text -> format_id 的映射
                for fmt in self.formats:
                    # 筛选mp4格式的视频（不严格要求filesize存在）
                    if fmt.get('ext') == 'mp4' and fmt.get('height'):
                        height = fmt.get('height')
                        filesize = fmt.get('filesize')
                        format_id = fmt.get('format_id')

                        # 计算预估文件大小
                        if filesize:
                            size_str = f"{filesize / 1024 / 1024:.2f} MB"
                        else:
                            # 预估大小基于分辨率（粗略估算）
                            est_size = height * height * 10 / 8  # 粗略估算
                            if est_size > 1024:
                                size_str = f"~{est_size / 1024:.1f} GB"
                            else:
                                size_str = f"~{est_size:.0f} MB"

                        quality_text = f"{height}p - {size_str}"
                        qualities.append(quality_text)
                        format_map[quality_text] = format_id

                # 去重并保持顺序
                seen = set()
                unique_qualities = []
                for q in qualities:
                    if q not in seen:
                        seen.add(q)
                        unique_qualities.append(q)

                self.quality_combobox['values'] = unique_qualities
                self.format_map = format_map  # 保存映射供下载时使用
                if unique_qualities:
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

        # 使用保存的format_map获取format_id
        selected_format = self.format_map.get(quality_text)
        if not selected_format:
            messagebox.showerror("错误", "未能找到匹配的格式。")
            self.enable_buttons()
            return

        selected_subtitle = self.caption_combobox.get()

        self.is_downloading = True
        self.download_start_time = time.time()
        self.button_cancel.config(state='normal')

        # 构建格式选择字符串
        if selected_format:
            format_str = f"{selected_format}+bestaudio/best"
        else:
            format_str = "bestvideo+bestaudio/best"

        ydl_opts = {
            'format': format_str,
            'outtmpl': os.path.join(self.download_path, '%(title)s.%(ext)s'),
            'progress_hooks': [self.show_progress],
        }

        # 添加代理设置
        if USER_PROXY:
            ydl_opts['proxy'] = USER_PROXY

        # 只有在ffmpeg可用时才添加后处理器
        if FFMPEG_AVAILABLE:
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }]
        else:
            # 如果没有ffmpeg，尝试直接下载mp4格式
            ydl_opts['format'] = f"{selected_format}/best"

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
            self.button_cancel.config(state='disabled')


# 主程序入口
if __name__ == "__main__":
    root = tk.Tk()
    style = Style(theme="superhero")
    app = YouTubeDownloader(root)
    root.mainloop()
