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

# 定义主应用程序类
class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube 下载器")
        self.root.minsize(width=700, height=450)
        self.is_downloading = False
        self.download_start_time = None
        self.current_url = None
        self.is_playlist = False
        self.playlist_entries = []
        self.format_map = {}
        self.formats = []

        # 设置字体（优先使用支持中文的字体）
        try:
            self.default_font = ("Microsoft YaHei", 10)
        except:
            self.default_font = ("Arial", 10)
        large_font = tkFont.Font(family=self.default_font[0], size=20)
        middle_font = tkFont.Font(family=self.default_font[0], size=18)
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

        # ===== Tab 控件 =====
        self.tab_control = ttk.Notebook(root)
        self.tab_control.pack(fill='both', expand=True, padx=10, pady=5)

        # 单视频 Tab
        self.single_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.single_tab, text="单视频")

        # 播放列表 Tab
        self.playlist_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.playlist_tab, text="播放列表")

        # ===== 单视频 Tab 内容 =====
        # 显示视频标题的标签
        self.video_title_label = ttk.Label(self.single_tab, text="视频标题", foreground='gray')
        self.video_title_label.pack(padx=10, pady=(5, 5))

        # 质量选择框架
        self.quality_frame = ttk.Frame(self.single_tab)
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

        # ===== 播放列表 Tab 内容 =====
        # 播放列表标题
        self.playlist_title_label = ttk.Label(self.playlist_tab, text="播放列表标题", foreground='gray')
        self.playlist_title_label.pack(padx=10, pady=(5, 5))

        # 播放列表视频数量
        self.playlist_count_label = ttk.Label(self.playlist_tab, text="共 0 个视频", foreground='gray')
        self.playlist_count_label.pack(padx=10, pady=(0, 5))

        # Treeview 框架
        self.tree_frame = ttk.Frame(self.playlist_tab)
        self.tree_frame.pack(fill='both', expand=True, padx=10, pady=5)

        # Treeview 滚动条
        self.tree_scroll_y = ttk.Scrollbar(self.tree_frame, orient='vertical')
        self.tree_scroll_x = ttk.Scrollbar(self.tree_frame, orient='horizontal')

        # Treeview
        self.playlist_tree = ttk.Treeview(self.tree_frame, yscrollcommand=self.tree_scroll_y.set, xscrollcommand=self.tree_scroll_x.set, show='headings', selectmode='none', height=10)
        self.tree_scroll_y.config(command=self.playlist_tree.yview)
        self.tree_scroll_x.config(command=self.playlist_tree.xview)

        # 定义列
        self.playlist_tree['columns'] = ('select', 'index', 'title', 'duration')
        self.playlist_tree.column('select', width=50, anchor='center')
        self.playlist_tree.column('index', width=50, anchor='center')
        self.playlist_tree.column('title', width=400)
        self.playlist_tree.column('duration', width=100, anchor='center')

        # 设置表头
        self.playlist_tree.heading('select', text='选择')
        self.playlist_tree.heading('index', text='序号')
        self.playlist_tree.heading('title', text='标题')
        self.playlist_tree.heading('duration', text='时长')

        self.playlist_tree.pack(side='left', fill='both', expand=True)
        self.tree_scroll_y.pack(side='right', fill='y')
        self.tree_scroll_x.pack(side='bottom', fill='x')

        # 复选框存储
        self.check_vars = {}

        # 全选/取消全选按钮框架
        self.playlist_btn_frame = ttk.Frame(self.playlist_tab)
        self.playlist_btn_frame.pack(pady=5)

        self.btn_select_all = ttk.Button(self.playlist_btn_frame, text="全选", command=self.select_all_videos, bootstyle='info', width=10)
        self.btn_select_all.pack(side=tk.LEFT, padx=5)

        self.btn_deselect_all = ttk.Button(self.playlist_btn_frame, text="取消全选", command=self.deselect_all_videos, bootstyle='info', width=10)
        self.btn_deselect_all.pack(side=tk.LEFT, padx=5)

        # 播放列表质量选择
        self.playlist_quality_frame = ttk.Frame(self.playlist_tab)
        self.playlist_quality_frame.pack(pady=5)
        self.playlist_quality_label = ttk.Label(self.playlist_quality_frame, text="下载质量:", font=small_font)
        self.playlist_quality_label.pack(side=tk.LEFT, padx=10)
        self.playlist_quality_combobox = ttk.Combobox(self.playlist_quality_frame, state="readonly", width=15)
        self.playlist_quality_combobox.pack(side=tk.LEFT, padx=5)

        # 播放列表字幕/配音选择
        self.playlist_caption_frame = ttk.Frame(self.playlist_tab)
        self.playlist_caption_frame.pack(pady=5)
        self.playlist_caption_label = ttk.Label(self.playlist_caption_frame, text="字幕/配音:", font=small_font)
        self.playlist_caption_label.pack(side=tk.LEFT, padx=10)
        self.playlist_caption_combobox = ttk.Combobox(self.playlist_caption_frame, state="readonly", width=15)
        self.playlist_caption_combobox.pack(side=tk.LEFT, padx=5)

        # 下载选中视频按钮
        self.btn_download_selected = ttk.Button(self.playlist_btn_frame, text="下载选中视频", command=self.start_download_selected_thread, bootstyle='danger', width=15)
        self.btn_download_selected.pack(side=tk.LEFT, padx=20)

        # ===== 底部按钮框架（单视频Tab）=====
        self.button_frame = ttk.Frame(root)
        self.button_frame.pack(pady=5)

        self.button_browse = ttk.Button(self.button_frame, text="下载路径", command=self.browse_path, bootstyle='info')
        self.button_browse.pack(side=tk.LEFT, padx=(10, 5))
        self.button_download = ttk.Button(self.button_frame, text="开始下载", command=self.start_download_thread, bootstyle='danger')
        self.button_download.pack(side=tk.LEFT, padx=(5, 10))
        self.button_cancel = ttk.Button(self.button_frame, text="取消下载", command=self.cancel_download, bootstyle='warning')
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
        messagebox.showinfo("关于", "YouTube 下载器 v3.0\n\n支持单视频和播放列表下载")

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

    # 开始下载选中视频线程
    def start_download_selected_thread(self):
        selected = self.get_selected_videos()
        if not selected:
            messagebox.showwarning("警告", "请至少选择一个视频")
            return
        self.progress['value'] = 0
        self.disable_buttons()
        self.root.title(f"YouTube 下载器 - 开始下载 {len(selected)} 个视频")
        threading.Thread(target=self.download_playlist, args=(selected,)).start()

    # 禁用按钮
    def disable_buttons(self):
        self.button_download.config(state='disabled')
        self.button_browse.config(state='disabled')
        self.button_load.config(state="disabled")
        self.btn_download_selected.config(state='disabled')
        self.btn_select_all.config(state='disabled')
        self.btn_deselect_all.config(state='disabled')

    # 启用按钮
    def enable_buttons(self):
        self.button_download.config(state='normal')
        self.button_browse.config(state='normal')
        self.button_load.config(state='normal')
        self.btn_download_selected.config(state='normal')
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
            self.playlist_tree.item(iid, values=(
                "√" if var.get() else "",
                self.playlist_tree.item(iid, 'values')[1],
                self.playlist_tree.item(iid, 'values')[2],
                self.playlist_tree.item(iid, 'values')[3]
            ))

    # 获取选中的视频
    def get_selected_videos(self):
        selected = []
        for iid, var in self.check_vars.items():
            if var.get():
                index = int(self.playlist_tree.item(iid, 'values')[1]) - 1
                if index < len(self.playlist_entries):
                    selected.append(self.playlist_entries[index])
        return selected

    # 复选框点击处理
    def on_check_click(self, iid):
        self.update_tree_selections()

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
                    # 播放列表
                    self.is_playlist = True
                    self.load_playlist_ui(info_dict)
                else:
                    # 单视频
                    self.is_playlist = False
                    self.load_single_video_ui(info_dict)

        except Exception as e:
            messagebox.showerror("加载视频错误", f"错误: {e}")
            self.root.title("YouTube 下载器")
        finally:
            self.enable_buttons()

    # 加载单视频UI
    def load_single_video_ui(self, info_dict):
        title = info_dict.get('title', '视频')
        self.formats = info_dict.get('formats', [])
        self.video_title_label['text'] = f"视频标题: {title}"

        qualities = []
        self.format_map = {}
        for fmt in self.formats:
            if fmt.get('ext') == 'mp4' and fmt.get('height'):
                height = fmt.get('height')
                filesize = fmt.get('filesize')
                format_id = fmt.get('format_id')

                if filesize:
                    size_str = f"{filesize / 1024 / 1024:.2f} MB"
                else:
                    est_size = height * height * 10 / 8
                    if est_size > 1024:
                        size_str = f"~{est_size / 1024:.1f} GB"
                    else:
                        size_str = f"~{est_size:.0f} MB"

                quality_text = f"{height}p - {size_str}"
                qualities.append(quality_text)
                self.format_map[quality_text] = format_id

        # 去重并保持顺序
        seen = set()
        unique_qualities = []
        for q in qualities:
            if q not in seen:
                seen.add(q)
                unique_qualities.append(q)

        self.quality_combobox['values'] = unique_qualities
        if unique_qualities:
            self.quality_combobox.current(0)

        subtitles = info_dict.get('subtitles', {})
        self.caption_combobox['values'] = list(subtitles.keys())
        if subtitles:
            self.caption_combobox.current(0)

        # 切换到单视频Tab
        self.tab_control.select(0)
        self.root.title(f"YouTube 下载器 - 视频已加载: {title}")

    # 加载播放列表UI
    def load_playlist_ui(self, info_dict):
        playlist_title = info_dict.get('title', '播放列表')
        entries = info_dict.get('entries', [])

        self.playlist_entries = [e for e in entries if e is not None]
        self.playlist_title_label['text'] = f"播放列表: {playlist_title}"
        self.playlist_count_label['text'] = f"共 {len(self.playlist_entries)} 个视频"

        # 清空Treeview
        for item in self.playlist_tree.get_children():
            self.playlist_tree.delete(item)
        self.check_vars.clear()

        # 获取所有视频的质量选项
        qualities = []
        format_map = {}
        sample_formats = None

        # 从第一个有效条目获取格式信息
        for entry in self.playlist_entries:
            if entry and entry.get('formats'):
                sample_formats = entry.get('formats', [])
                break

        if sample_formats:
            for fmt in sample_formats:
                if fmt.get('ext') == 'mp4' and fmt.get('height'):
                    height = fmt.get('height')
                    filesize = fmt.get('filesize')
                    format_id = fmt.get('format_id')

                    if filesize:
                        size_str = f"{filesize / 1024 / 1024:.2f} MB"
                    else:
                        est_size = height * height * 10 / 8
                        if est_size > 1024:
                            size_str = f"~{est_size / 1024:.1f} GB"
                        else:
                            size_str = f"~{est_size:.0f} MB"

                    quality_text = f"{height}p - {size_str}"
                    if quality_text not in qualities:
                        qualities.append(quality_text)
                        format_map[quality_text] = format_id

        self.playlist_quality_combobox['values'] = qualities
        if qualities:
            self.playlist_quality_combobox.current(0)

        # 获取字幕/配音选项
        subtitles = set()
        for entry in self.playlist_entries:
            if entry and entry.get('subtitles'):
                subtitles.update(entry.get('subtitles', {}).keys())
        subtitle_list = list(subtitles)
        self.playlist_caption_combobox['values'] = subtitle_list
        if subtitle_list:
            self.playlist_caption_combobox.current(0)

        # 填充Treeview
        for i, entry in enumerate(self.playlist_entries):
            if entry is None:
                continue
            title = entry.get('title', '未知标题')
            duration = entry.get('duration')
            if duration:
                duration_str = time.strftime("%H:%M:%S", time.gmtime(duration))
            else:
                duration_str = "--:--"

            var = tk.IntVar(value=1)  # 默认选中
            self.check_vars[f"I{i}"] = var

            iid = self.playlist_tree.insert('', 'end', values=("√", i + 1, title, duration_str))

        # 切换到播放列表Tab
        self.tab_control.select(1)
        self.root.title(f"YouTube 下载器 - 播放列表已加载: {playlist_title}")

    # 下载视频
    def download_video(self):
        url = self.current_url
        if not url:
            messagebox.showerror("错误", "请输入有效的视频URL。")
            self.enable_buttons()
            return

        quality_text = self.quality_combobox.get()
        if not quality_text:
            messagebox.showerror("错误", "请选择视频质量。")
            self.enable_buttons()
            return

        selected_format = self.format_map.get(quality_text)
        if not selected_format:
            messagebox.showerror("错误", "未能找到匹配的格式。")
            self.enable_buttons()
            return

        selected_subtitle = self.caption_combobox.get()

        self.is_downloading = True
        self.download_start_time = time.time()
        self.button_cancel.config(state='normal')

        if selected_format:
            format_str = f"{selected_format}+bestaudio/best"
        else:
            format_str = "bestvideo+bestaudio/best"

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
        else:
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

    # 下载播放列表
    def download_playlist(self, selected_entries):
        if not selected_entries:
            self.enable_buttons()
            return

        quality_text = self.playlist_quality_combobox.get()
        if not quality_text:
            messagebox.showerror("错误", "请选择视频质量。")
            self.enable_buttons()
            return

        # 获取format_id
        format_id = None
        for q, fid in self.format_map.items() if hasattr(self, 'format_map') else []:
            if q == quality_text:
                format_id = fid
                break

        if not format_id and self.playlist_quality_combobox['values']:
            format_id = self.playlist_quality_combobox['values'][0].split(' - ')[0] if self.playlist_quality_combobox['values'] else None

        self.is_downloading = True
        self.download_start_time = time.time()
        self.button_cancel.config(state='normal')

        total = len(selected_entries)
        success_count = 0
        fail_count = 0

        for i, entry in enumerate(selected_entries):
            if not self.is_downloading:
                break

            video_url = entry.get('url') or entry.get('webpage_url')
            if not video_url:
                fail_count += 1
                continue

            self.root.title(f"YouTube 下载器 - 下载第 {i+1}/{total} 个视频...")

            if format_id:
                format_str = f"{format_id}+bestaudio/best"
            else:
                format_str = "bestvideo+bestaudio/best"

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

            # 添加字幕设置
            selected_subtitle = self.playlist_caption_combobox.get()
            if selected_subtitle:
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
