import os
import subprocess
import sys
import time
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap import Style
from ttkbootstrap.constants import *
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
        url = clipboard_text.strip()
        if url and YOUTUBE_URL_PATTERN.match(url):
            return url
    except:
        pass
    return None

# 计算预估文件大小
def estimate_size(height, duration=None):
    est_size = height * height * 10 / 8  # 粗略估算 bytes per pixel
    if duration and duration > 0:
        est_size = est_size * duration / 60  # 根据时长调整
    if est_size > 1024 * 1024 * 1024:
        return f"{est_size / 1024 / 1024 / 1024:.2f} GB"
    elif est_size > 1024 * 1024:
        return f"{est_size / 1024 / 1024:.1f} MB"
    else:
        return f"{est_size / 1024:.0f} KB"

# 定义主应用程序类
class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube 下载器")
        self.root.minsize(width=800, height=500)
        self.is_downloading = False
        self.download_start_time = None
        self.current_url = None
        self.is_playlist = False
        self.playlist_entries = []
        self.format_map = {}
        self.formats = []
        self.quality_options = []  # 简化的质量选项列表

        # 设置字体（优先使用支持中文的字体）
        try:
            self.default_font = ("Microsoft YaHei", 10)
        except:
            self.default_font = ("Arial", 10)
        small_font = tkFont.Font(family=self.default_font[0], size=16)

        # 设置 ttk 样式，使用支持中文的字体
        style = ttk.Style()
        style.configure('TButton', font=self.default_font, foreground='#ffffff')
        style.configure('TLabel', font=self.default_font)
        style.configure('TEntry', font=self.default_font)

        # ===== 顶部框架 =====
        self.top_frame = ttk.Frame(root)
        self.top_frame.pack(fill='x', padx=10, pady=5)

        # 输入视频URL的文本框
        self.entry_url = ttk.Entry(self.top_frame)
        self.entry_url.pack(fill='x', expand=True, padx=10, pady=10, side=tk.LEFT)
        # 点击输入框时检查剪贴板
        self.entry_url.bind('<FocusIn>', self.on_entry_focus)
        self.entry_url.bind('<Button-1>', self.on_entry_click)

        # 检查剪贴板是否有URL（启动时）
        clipboard_url = get_url_from_clipboard(root)
        if clipboard_url:
            self.entry_url.insert(0, clipboard_url)
            self.root.title(f"YouTube 下载器 - 已从剪贴板获取URL")

        # 加载视频信息的按钮
        self.button_load = ttk.Button(self.top_frame, text="加载视频信息", command=self.start_parse_video_thread, bootstyle='success')
        self.button_load.pack(side=tk.RIGHT)

        # ===== 内容区域 =====
        # 视频信息标题
        self.video_title_label = ttk.Label(root, text="请输入URL并点击加载", foreground='gray')
        self.video_title_label.pack(padx=10, pady=(5, 5))

        # Treeview 框架
        self.tree_frame = ttk.Frame(root)
        self.tree_frame.pack(fill='both', expand=True, padx=10, pady=5)

        # Treeview 滚动条
        self.tree_scroll_y = ttk.Scrollbar(self.tree_frame, orient='vertical')
        self.tree_scroll_x = ttk.Scrollbar(self.tree_frame, orient='horizontal')

        # Treeview - 列: 选择, 序号, 标题, 时长, 大小
        self.playlist_tree = ttk.Treeview(self.tree_frame, yscrollcommand=self.tree_scroll_y.set, xscrollcommand=self.tree_scroll_x.set, show='headings', selectmode='none', height=12)
        self.tree_scroll_y.config(command=self.playlist_tree.yview)
        self.tree_scroll_x.config(command=self.playlist_tree.xview)

        # 定义列
        self.playlist_tree['columns'] = ('select', 'index', 'title', 'duration', 'size')
        self.playlist_tree.column('select', width=50, anchor='center')
        self.playlist_tree.column('index', width=50, anchor='center')
        self.playlist_tree.column('title', width=400)
        self.playlist_tree.column('duration', width=100, anchor='center')
        self.playlist_tree.column('size', width=100, anchor='center')

        # 设置表头
        self.playlist_tree.heading('select', text='选择')
        self.playlist_tree.heading('index', text='序号')
        self.playlist_tree.heading('title', text='标题')
        self.playlist_tree.heading('duration', text='时长')
        self.playlist_tree.heading('size', text='大小')

        # 绑定点击事件到选择列
        self.playlist_tree.bind('<Button-1>', self.on_tree_click)

        self.playlist_tree.pack(side='left', fill='both', expand=True)
        self.tree_scroll_y.pack(side='right', fill='y')
        self.tree_scroll_x.pack(side='bottom', fill='x')

        # 复选框存储
        self.check_vars = {}

        # 全选/取消全选按钮框架
        self.btn_frame = ttk.Frame(root)
        self.btn_frame.pack(pady=5)

        self.btn_select_all = ttk.Button(self.btn_frame, text="全选", command=self.select_all_videos, bootstyle='info', width=10)
        self.btn_select_all.pack(side=tk.LEFT, padx=5)

        self.btn_deselect_all = ttk.Button(self.btn_frame, text="取消全选", command=self.deselect_all_videos, bootstyle='info', width=10)
        self.btn_deselect_all.pack(side=tk.LEFT, padx=5)

        # 下载质量选择
        self.quality_frame = ttk.Frame(root)
        self.quality_frame.pack(pady=5)
        self.quality_label = ttk.Label(self.quality_frame, text="下载质量:", font=small_font)
        self.quality_label.pack(side=tk.LEFT, padx=10)
        self.quality_combobox = ttk.Combobox(self.quality_frame, state="readonly", width=15)
        self.quality_combobox.pack(side=tk.LEFT, padx=5)

        # 字幕/配音选择
        self.caption_frame = ttk.Frame(root)
        self.caption_frame.pack(pady=5)
        self.caption_label = ttk.Label(self.caption_frame, text="字幕/配音:", font=small_font)
        self.caption_label.pack(side=tk.LEFT, padx=10)
        self.caption_combobox = ttk.Combobox(self.caption_frame, state="readonly", width=15)
        self.caption_combobox.pack(side=tk.LEFT, padx=5)

        # 下载按钮框架
        self.download_btn_frame = ttk.Frame(root)
        self.download_btn_frame.pack(pady=5)

        self.button_browse = ttk.Button(self.download_btn_frame, text="下载路径", command=self.browse_path, bootstyle='info')
        self.button_browse.pack(side=tk.LEFT, padx=(10, 5))
        self.button_download = ttk.Button(self.download_btn_frame, text="下载选中视频", command=self.start_download_thread, bootstyle='danger', width=15)
        self.button_download.pack(side=tk.LEFT, padx=(5, 10))
        self.button_cancel = ttk.Button(self.download_btn_frame, text="取消下载", command=self.cancel_download, bootstyle='warning')
        self.button_cancel.pack(side=tk.LEFT, padx=(5, 10))
        self.button_cancel.config(state='disabled')

        # ===== 底部框架 =====
        self.bottom_frame = ttk.Frame(root)
        self.bottom_frame.pack(fill='x', padx=20, pady=5)

        # 进度条
        self.progress = ttk.Progressbar(self.bottom_frame, bootstyle="success-striped", orient='horizontal', mode='determinate')
        self.progress.pack(fill='x', expand=True, side=tk.LEFT)
        self.progress_label = ttk.Label(self.bottom_frame, text="0%", font=small_font)
        self.progress_label.pack(padx=8, pady=5)

        self.download_path = os.path.join(os.path.expanduser('~'), 'Desktop')

        # 创建菜单栏
        self.create_menu_bar()

        self.center_window(self.root)

    # 输入框获得焦点或点击时检查剪贴板
    def on_entry_focus(self, event):
        clipboard_url = get_url_from_clipboard(self.root)
        if clipboard_url and not self.entry_url.get().strip():
            self.entry_url.delete(0, tk.END)
            self.entry_url.insert(0, clipboard_url)
            self.root.title(f"YouTube 下载器 - 已从剪贴板获取URL")

    def on_entry_click(self, event):
        self.on_entry_focus(event)

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
        dialog.geometry("450x130")
        dialog.transient(self.root)
        dialog.update_idletasks()
        dialog.minsize(450, 130)
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
        tk.Button(btn_frame, text="保存", command=save_proxy, bg="#0078d4", fg="white", relief="flat", font=self.default_font).pack(side=tk.LEFT, padx=5, pady=5, ipadx=10)
        tk.Button(btn_frame, text="取消", command=dialog.destroy, bg="#5c5c5c", fg="white", relief="flat", font=self.default_font).pack(side=tk.LEFT, padx=5, pady=5, ipadx=10)

    # 关于对话框
    def show_about(self):
        messagebox.showinfo("关于", "YouTube 下载器 v4.0\n\n支持单视频和播放列表下载")

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
            total = d.get('total_bytes') or d.get('totalbyte') or 0
            if total and total > 0:
                percentage = min(downloaded / total * 100, 100)
                self.progress['value'] = percentage
                self.progress_label['text'] = f"{percentage:.2f}%"
            self.root.update_idletasks()
            if self.download_start_time:
                elapsed_time = time.time() - self.download_start_time
                elapsed_time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
                self.root.title(f"YouTube 下载器 - 已用时间: {elapsed_time_str}")

    # 显示播放列表下载进度
    def show_playlist_progress(self, d):
        if d['status'] == 'downloading':
            downloaded = d.get('downloaded_bytes', 0) or 0
            total = d.get('total_bytes') or d.get('totalbyte') or 0
            if total and total > 0:
                percentage = min(downloaded / total * 100, 100)
                self.progress_label['text'] = f"视频 {self.current_playlist_index}/{self.total_playlist_videos} - {percentage:.2f}%"
                self.progress['value'] = percentage
            self.root.update_idletasks()
            if self.download_start_time:
                elapsed_time = time.time() - self.download_start_time
                elapsed_time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
                self.root.title(f"YouTube 下载器 - 视频 {self.current_playlist_index}/{self.total_playlist_videos} - 已用时间: {elapsed_time_str}")

    # 开始解析视频线程
    def start_parse_video_thread(self):
        self.progress['value'] = 0
        self.disable_buttons()
        self.root.title(f"YouTube 下载器 - 解析视频信息中...")
        threading.Thread(target=self.load_video_msg).start()

    # 开始下载视频线程
    def start_download_thread(self):
        selected = self.get_selected_videos()
        if not selected:
            messagebox.showwarning("警告", "请至少选择一个视频")
            self.enable_buttons()
            return
        self.progress['value'] = 0
        self.disable_buttons()
        if len(selected) == 1:
            self.root.title(f"YouTube 下载器 - 开始下载")
            threading.Thread(target=self.download_single, args=(selected[0],)).start()
        else:
            self.root.title(f"YouTube 下载器 - 开始下载 {len(selected)} 个视频")
            threading.Thread(target=self.download_multi, args=(selected,)).start()

    # 禁用按钮
    def disable_buttons(self):
        self.button_download.config(state='disabled')
        self.button_browse.config(state='disabled')
        self.button_load.config(state="disabled")
        self.btn_select_all.config(state='disabled')
        self.btn_deselect_all.config(state='disabled')

    # 启用按钮
    def enable_buttons(self):
        self.button_download.config(state='normal')
        self.button_browse.config(state='normal')
        self.button_load.config(state='normal')
        self.btn_select_all.config(state='normal')
        self.btn_deselect_all.config(state='normal')

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

    # 全选视频
    def select_all_videos(self):
        for var in self.check_vars.values():
            var.set(1)
        self.update_tree_selections()

    # 取消全选
    def deselect_all_videos(self):
        for var in self.check_vars.values():
            var.set(0)
        self.update_tree_selections()

    # 更新Treeview选择状态
    def update_tree_selections(self):
        for iid, var in self.check_vars.items():
            values = list(self.playlist_tree.item(iid, 'values'))
            values[0] = "√" if var.get() else ""
            self.playlist_tree.item(iid, values=values)

    # Treeview点击事件
    def on_tree_click(self, event):
        region = self.playlist_tree.identify_region(event.x, event.y)
        if region == 'cell':
            column = self.playlist_tree.identify_column(event.x)
            if column == '#1':  # 选择列
                item = self.playlist_tree.identify_row(event.y)
                if item and item in self.check_vars:
                    var = self.check_vars[item]
                    var.set(1 - var.get())
                    self.update_tree_selections()
                    return "break"

    # 获取选中的视频
    def get_selected_videos(self):
        selected = []
        for iid, var in self.check_vars.items():
            if var.get():
                index = int(self.playlist_tree.item(iid, 'values')[1]) - 1
                if index < len(self.playlist_entries):
                    selected.append(self.playlist_entries[index])
        return selected

    # 加载视频信息
    def load_video_msg(self):
        url = self.entry_url.get().strip()
        if not url:
            messagebox.showerror("错误", "请输入有效的视频URL。")
            self.enable_buttons()
            return
        try:
            self.current_url = url
            ydl_opts = {
                'quiet': True,
                'skip_download': True,
            }
            if USER_PROXY:
                ydl_opts['proxy'] = USER_PROXY

            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(url, download=False)

                # 判断是否为播放列表
                entries = info_dict.get('entries', [])
                if entries:
                    self.is_playlist = True
                    self.load_playlist_ui(info_dict)
                else:
                    self.is_playlist = False
                    self.load_single_ui(info_dict)

        except Exception as e:
            messagebox.showerror("加载视频错误", f"错误: {e}")
            self.root.title("YouTube 下载器")
        finally:
            self.enable_buttons()

    # 加载单视频UI
    def load_single_ui(self, info_dict):
        title = info_dict.get('title', '视频')
        self.formats = info_dict.get('formats', [])
        self.video_title_label['text'] = f"视频: {title}"

        # 收集质量选项（只显示分辨率）
        heights = set()
        for fmt in self.formats:
            if fmt.get('ext') == 'mp4' and fmt.get('height'):
                heights.add(fmt.get('height'))

        self.quality_options = sorted(list(heights), reverse=True)
        self.quality_combobox['values'] = [f"{h}p" for h in self.quality_options]
        if self.quality_options:
            self.quality_combobox.current(0)

        # 字幕选项
        subtitles = info_dict.get('subtitles', {})
        self.caption_combobox['values'] = list(subtitles.keys()) if subtitles else ['无']
        self.caption_combobox.current(0)

        # 清空并添加单个视频到列表
        self.playlist_entries = [info_dict]
        self.load_treeview()

        self.root.title(f"YouTube 下载器 - 已加载: {title}")

    # 加载播放列表UI
    def load_playlist_ui(self, info_dict):
        playlist_title = info_dict.get('title', '播放列表')
        entries = info_dict.get('entries', [])

        self.playlist_entries = [e for e in entries if e is not None]
        self.video_title_label['text'] = f"播放列表: {playlist_title} (共 {len(self.playlist_entries)} 个视频)"

        # 收集质量选项
        heights = set()
        for entry in self.playlist_entries:
            if entry and entry.get('formats'):
                for fmt in entry.get('formats', []):
                    if fmt.get('ext') == 'mp4' and fmt.get('height'):
                        heights.add(fmt.get('height'))

        self.quality_options = sorted(list(heights), reverse=True) if heights else [1080, 720, 480, 360]
        self.quality_combobox['values'] = [f"{h}p" for h in self.quality_options]
        if self.quality_options:
            self.quality_combobox.current(0)

        # 字幕选项
        subtitles = set()
        for entry in self.playlist_entries:
            if entry and entry.get('subtitles'):
                subtitles.update(entry.get('subtitles', {}).keys())
        subtitle_list = list(subtitles) if subtitles else ['无']
        self.caption_combobox['values'] = subtitle_list
        self.caption_combobox.current(0)

        self.load_treeview()
        self.root.title(f"YouTube 下载器 - 已加载: {playlist_title}")

    # 加载Treeview
    def load_treeview(self):
        for item in self.playlist_tree.get_children():
            self.playlist_tree.delete(item)
        self.check_vars.clear()

        quality_text = self.quality_combobox.get()
        if quality_text:
            selected_height = int(quality_text.replace('p', ''))
        else:
            selected_height = 1080

        for i, entry in enumerate(self.playlist_entries):
            if entry is None:
                continue

            title = entry.get('title', '未知标题')
            duration = entry.get('duration')
            if duration:
                duration_str = time.strftime("%H:%M:%S", time.gmtime(duration))
            else:
                duration_str = "--:--"

            # 计算预估大小
            height = entry.get('height') or selected_height
            duration_val = entry.get('duration') or 300  # 默认5分钟
            size_str = estimate_size(height, duration_val)

            iid = self.playlist_tree.insert('', 'end', values=("√", i + 1, title, duration_str, size_str))
            var = tk.IntVar(value=1)
            self.check_vars[iid] = var

    # 下载单个视频
    def download_single(self, entry):
        quality_text = self.quality_combobox.get()
        if not quality_text:
            messagebox.showerror("错误", "请选择视频质量。")
            self.enable_buttons()
            return

        height = int(quality_text.replace('p', ''))
        format_str = f"bestvideo[height<={height}]+bestaudio/best"

        self.is_downloading = True
        self.download_start_time = time.time()
        self.button_cancel.config(state='normal')

        video_url = entry.get('url') or entry.get('webpage_url')
        if not video_url:
            messagebox.showerror("错误", "无法获取视频URL。")
            self.enable_buttons()
            return

        ydl_opts = {
            'format': format_str,
            'outtmpl': os.path.join(self.download_path, '%(title)s.%(ext)s'),
            'progress_hooks': [self.show_progress],
        }

        if USER_PROXY:
            ydl_opts['proxy'] = USER_PROXY

        if FFMPEG_AVAILABLE:
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }]

        selected_subtitle = self.caption_combobox.get()
        if selected_subtitle and selected_subtitle != '无':
            ydl_opts['subtitleslangs'] = [selected_subtitle]
            ydl_opts['writesubtitles'] = True
            ydl_opts['subtitlesformat'] = 'srt'

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
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

    # 下载多个视频
    def download_multi(self, selected_entries):
        quality_text = self.quality_combobox.get()
        if not quality_text:
            messagebox.showerror("错误", "请选择视频质量。")
            self.enable_buttons()
            return

        height = int(quality_text.replace('p', ''))
        format_str = f"bestvideo[height<={height}]+bestaudio/best"

        self.is_downloading = True
        self.download_start_time = time.time()
        self.button_cancel.config(state='normal')

        self.total_playlist_videos = len(selected_entries)
        self.current_playlist_index = 0
        success_count = 0
        fail_count = 0

        selected_subtitle = self.caption_combobox.get()

        for i, entry in enumerate(selected_entries):
            if not self.is_downloading:
                break

            self.current_playlist_index = i + 1
            video_url = entry.get('url') or entry.get('webpage_url')
            if not video_url:
                fail_count += 1
                continue

            self.root.title(f"YouTube 下载器 - 下载第 {i+1}/{self.total_playlist_videos} 个视频...")

            ydl_opts = {
                'format': format_str,
                'outtmpl': os.path.join(self.download_path, '%(title)s.%(ext)s'),
                'progress_hooks': [self.show_playlist_progress],
            }

            if USER_PROXY:
                ydl_opts['proxy'] = USER_PROXY

            if FFMPEG_AVAILABLE:
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }]

            if selected_subtitle and selected_subtitle != '无':
                ydl_opts['subtitleslangs'] = [selected_subtitle]
                ydl_opts['writesubtitles'] = True
                ydl_opts['subtitlesformat'] = 'srt'

            try:
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video_url])
                success_count += 1
            except Exception as e:
                fail_count += 1
                print(f"下载失败: {entry.get('title', '未知')} - {e}")

        elapsed_time = time.time() - self.download_start_time
        elapsed_time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
        self.root.title(f"YouTube 下载器 - 下载完成 (已用时间: {elapsed_time_str})")
        messagebox.showinfo("下载完成", f"成功: {success_count} 个, 失败: {fail_count} 个")
        self.open_download_folder()

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