"""Main YouTubeDownloader UI class."""
import os
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import tkinter.font as tkFont
import threading
import webbrowser
import yt_dlp

from config import (
    get_proxy, set_proxy, get_cookiefile, set_cookiefile,
    get_max_concurrent, set_max_concurrent,
    FFMPEG_AVAILABLE, JS_RUNTIME, VERSION,
)
from utils import get_url_from_clipboard
from _downloader import load_video_msg, download_single, download_multi


class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title(f"YouTube 下载器 v{VERSION}")
        self.root.minsize(width=900, height=550)
        try:
            self.root.iconbitmap('imgs/logo.ico')
        except:
            pass
        self.cancel_event = threading.Event()
        self._active_ydl = None
        self.download_start_time = None
        self._last_log_path = None
        self.current_url = None
        self.is_playlist = False
        self.playlist_entries = []
        self.formats = []
        self.quality_options = []
        self.last_auto_paste_url = None
        self.tree_iid_map = {}
        self.current_download_index = None
        self._status_text = "就绪"
        self.download_path = os.path.join(os.path.expanduser('~'), 'Desktop')

        try:
            self.default_font = ("Microsoft YaHei", 10)
        except:
            self.default_font = ("Arial", 10)
        small_font = tkFont.Font(family=self.default_font[0], size=16)

        style = ttk.Style()
        style.configure('TButton', font=self.default_font, foreground='#ffffff')
        style.configure('TLabel', font=self.default_font)
        style.configure('TEntry', font=self.default_font)
        style.configure('Success.TLabel', foreground='green')
        style.configure('Failed.TLabel', foreground='red')
        style.configure('Converting.TLabel', foreground='orange')

        self.IntVar = tk.IntVar

        self._setup_ui(small_font)
        self.create_menu_bar()
        self.center_window(self.root)

        clipboard_url = get_url_from_clipboard(root)
        if clipboard_url:
            self.entry_url.insert(0, clipboard_url)
            self.update_status("已从剪贴板获取URL")

        # Non-blocking warning if no JS runtime is on PATH.
        if not JS_RUNTIME:
            self.root.after(
                800,
                lambda: messagebox.showwarning(
                    "需要 JavaScript 运行时",
                    "未检测到 Node.js 或 Deno。\n\n"
                    "当前 YouTube 启用了 SABR 流实验,没有 JS 运行时会导致 "
                    "\"The page needs to be reloaded\" 错误,并把可用画质限制在 360p。\n\n"
                    "请安装 Node.js 后重启本程序:\n"
                    "  https://nodejs.org/\n"
                    "或运行: winget install OpenJS.NodeJS"
                ),
            )

    def _setup_ui(self, small_font):
        self.top_frame = ttk.Frame(self.root)
        self.top_frame.pack(fill='x', padx=10, pady=5)

        self.entry_url = ttk.Entry(self.top_frame)
        self.entry_url.pack(fill='x', expand=True, padx=10, pady=10, side=tk.LEFT)
        self.entry_url.bind('<FocusIn>', self.on_entry_focus)
        self.entry_url.bind('<Button-1>', self.on_entry_click)

        self.button_load = ttk.Button(self.top_frame, text="加载视频信息", command=self.start_parse_video_thread, bootstyle='success')
        self.button_load.pack(side=tk.RIGHT)

        self.video_title_label = ttk.Label(self.root, text="请输入URL并点击加载", foreground='gray')
        self.video_title_label.pack(padx=10, pady=(5, 5))

        self.tree_frame = ttk.Frame(self.root)
        self.tree_frame.pack(fill='both', expand=True, padx=10, pady=5)

        self.tree_scroll_y = ttk.Scrollbar(self.tree_frame, orient='vertical')
        self.tree_scroll_x = ttk.Scrollbar(self.tree_frame, orient='horizontal')

        self.playlist_tree = ttk.Treeview(
            self.tree_frame,
            yscrollcommand=self.tree_scroll_y.set,
            xscrollcommand=self.tree_scroll_x.set,
            show='headings', selectmode='none', height=12
        )
        self.tree_scroll_y.config(command=self.playlist_tree.yview)
        self.tree_scroll_x.config(command=self.playlist_tree.xview)

        self.playlist_tree['columns'] = (
            'select', 'index', 'title', 'duration', 'size',
            'progress', 'speed', 'eta', 'convert',
        )
        self.playlist_tree.column('select', width=60, anchor='center')
        self.playlist_tree.column('index', width=60, anchor='center')
        self.playlist_tree.column('title', width=280)
        self.playlist_tree.column('duration', width=80, anchor='center')
        self.playlist_tree.column('size', width=80, anchor='center')
        self.playlist_tree.column('progress', width=110, anchor='center')
        self.playlist_tree.column('speed', width=90, anchor='center')
        self.playlist_tree.column('eta', width=80, anchor='center')
        self.playlist_tree.column('convert', width=80, anchor='center')

        self.playlist_tree.heading('select', text='✓')
        self.playlist_tree.heading('index', text='序号')
        self.playlist_tree.heading('title', text='标题')
        self.playlist_tree.heading('duration', text='时长')
        self.playlist_tree.heading('size', text='大小')
        self.playlist_tree.heading('progress', text='下载进度')
        self.playlist_tree.heading('speed', text='速度')
        self.playlist_tree.heading('eta', text='剩余')
        self.playlist_tree.heading('convert', text='转换状态')

        self.playlist_tree.tag_configure('success', foreground='green')
        self.playlist_tree.tag_configure('failed', foreground='red')
        self.playlist_tree.tag_configure('converting', foreground='orange')
        self.playlist_tree.tag_configure('downloading', foreground='cyan')

        self.playlist_tree.bind('<Button-1>', self.on_tree_click)

        self.playlist_tree.pack(side='left', fill='both', expand=True)
        self.tree_scroll_y.pack(side='right', fill='y')
        self.tree_scroll_x.pack(side='bottom', fill='x')

        self.check_vars = {}

        self.btn_frame = ttk.Frame(self.root)
        self.btn_frame.pack(pady=5)

        self.btn_select_all = ttk.Button(self.btn_frame, text="全选", command=self.select_all_videos, bootstyle='info', width=10)
        self.btn_select_all.pack(side=tk.LEFT, padx=5)

        self.btn_deselect_all = ttk.Button(self.btn_frame, text="取消全选", command=self.deselect_all_videos, bootstyle='info', width=10)
        self.btn_deselect_all.pack(side=tk.LEFT, padx=5)

        self.options_frame = ttk.Frame(self.root)
        self.options_frame.pack(pady=5)

        self.quality_label = ttk.Label(self.options_frame, text="下载质量:", font=small_font)
        self.quality_label.pack(side=tk.LEFT, padx=(10, 2))
        self.quality_combobox = ttk.Combobox(self.options_frame, state="readonly", width=15)
        self.quality_combobox.pack(side=tk.LEFT, padx=5)
        self.quality_combobox.bind('<<ComboboxSelected>>', self.on_quality_changed)

        self.caption_label = ttk.Label(self.options_frame, text="字幕:", font=small_font)
        self.caption_label.pack(side=tk.LEFT, padx=(10, 2))
        self.caption_combobox = ttk.Combobox(self.options_frame, state="readonly", width=15)
        self.caption_combobox.pack(side=tk.LEFT, padx=5)

        self.format_label = ttk.Label(self.options_frame, text="输出格式:", font=small_font)
        self.format_label.pack(side=tk.LEFT, padx=(10, 2))
        self.format_combobox = ttk.Combobox(self.options_frame, state="readonly", width=10)
        self.format_combobox['values'] = ['mp4', 'mkv', 'webm', 'avi', '不转换']
        self.format_combobox.current(0)
        self.format_combobox.pack(side=tk.LEFT, padx=5)

        self.download_btn_frame = ttk.Frame(self.root)
        self.download_btn_frame.pack(pady=5)

        self.button_browse = ttk.Button(self.download_btn_frame, text="下载路径", command=self.browse_path, bootstyle='info')
        self.button_browse.pack(side=tk.LEFT, padx=(10, 5))
        self.button_download = ttk.Button(self.download_btn_frame, text="开始下载", command=self.start_download_thread, bootstyle='danger', width=15)
        self.button_download.pack(side=tk.LEFT, padx=(5, 10))
        self.button_cancel = ttk.Button(self.download_btn_frame, text="取消下载", command=self.cancel_download, bootstyle='warning')
        self.button_cancel.pack(side=tk.LEFT, padx=(5, 10))
        self.button_cancel.config(state='disabled')

        self.status_bar = ttk.Label(self.root, text="就绪", relief='sunken', anchor='w')
        self.status_bar.pack(fill='x', padx=10, pady=(0, 5))

    def update_status(self, text):
        def _do():
            self._status_text = text
            self.status_bar['text'] = text
        try:
            self.root.after(0, _do)
        except RuntimeError:
            # Root destroyed (e.g. during shutdown) — silently drop the update.
            pass

    def on_entry_focus(self, event):
        clipboard_url = get_url_from_clipboard(self.root)
        if clipboard_url and clipboard_url != self.last_auto_paste_url and clipboard_url != self.entry_url.get().strip():
            self.entry_url.delete(0, tk.END)
            self.entry_url.insert(0, clipboard_url)
            self.last_auto_paste_url = clipboard_url
            self.update_status("已从剪贴板获取URL")

    def on_entry_click(self, event):
        self.on_entry_focus(event)

    def create_menu_bar(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="设置", menu=settings_menu)
        settings_menu.add_command(label="代理设置", command=self.show_proxy_dialog)
        settings_menu.add_command(label="Cookies 文件", command=self.show_cookies_dialog)
        settings_menu.add_command(label="并发下载数", command=self.show_concurrent_dialog)
        settings_menu.add_separator()
        settings_menu.add_command(label="关于", command=self.show_about)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用说明", command=self.show_help)
        help_menu.add_command(label="打开下载日志", command=self.open_download_log)
        help_menu.add_command(label="GitHub 仓库", command=self.open_github)

    def show_proxy_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("代理设置")
        dialog.geometry("450x130")
        dialog.transient(self.root)
        dialog.update_idletasks()
        dialog.minsize(450, 130)
        dialog.grab_set()
        dialog.geometry(f"+{self.root.winfo_x() + 100}+{self.root.winfo_y() + 100}")

        ttk.Label(dialog, text="代理地址 (例如: http://127.0.0.1:7897):").pack(pady=(15, 5), padx=10)
        proxy_entry = ttk.Entry(dialog, width=50)
        proxy_entry.pack(pady=5, padx=10)
        proxy_entry.insert(0, get_proxy() if get_proxy() else "")

        def save_proxy():
            proxy_value = proxy_entry.get().strip()
            set_proxy(proxy_value if proxy_value else None)
            dialog.destroy()
            if get_proxy():
                messagebox.showinfo("代理设置", f"代理已设置为: {get_proxy()}")
            else:
                messagebox.showinfo("代理设置", "代理已清除")

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="保存", command=save_proxy, bg="#0078d4", fg="white", relief="flat", font=self.default_font).pack(side=tk.LEFT, padx=5, pady=5, ipadx=10)
        tk.Button(btn_frame, text="取消", command=dialog.destroy, bg="#5c5c5c", fg="white", relief="flat", font=self.default_font).pack(side=tk.LEFT, padx=5, pady=5, ipadx=10)

    def show_about(self):
        messagebox.showinfo(
            "关于",
            f"YouTube 下载器 v{VERSION}\n\n"
            f"yt-dlp: {yt_dlp.version.__version__}\n"
            f"FFmpeg: {'可用' if FFMPEG_AVAILABLE else '未检测到'}\n"
            f"JS runtime: {JS_RUNTIME or '未检测到（请安装 Node.js）'}\n"
            f"代理: {get_proxy() or '无'}\n"
            f"Cookies: {get_cookiefile() or '无'}\n\n"
            "支持单视频和播放列表下载"
        )

    def show_download_error(self, short_msg, log_text, log_path=None):
        """Show the user the actual yt-dlp failure (and the captured log)
        instead of just \"下载失败\" in the status bar. The worker thread
        already wrote the full log to disk; this dialog just displays it.
        """
        if log_path is None:
            # Fall back to computing the path if the worker didn't pass one.
            from _downloader import _resolve_log_path
            log_path = _resolve_log_path(self)
        self._last_log_path = log_path

        # Prepend bgutil plugin diagnostic if it exists, so the user
        # can immediately see whether the POT provider is loaded.
        try:
            startup_log = os.path.join(os.path.expanduser('~'),
                                       'Desktop', 'yt_downloader_startup.log')
            if os.path.isfile(startup_log):
                mtime = os.path.getmtime(startup_log)
                # Only include the most recent session
                import time
                if time.time() - mtime < 600:
                    with open(startup_log, 'r', encoding='utf-8') as fh:
                        tail = fh.read()[-1500:]
                    log_text = '=== Most recent startup diagnostic ===\n' + tail + '\n\n' + log_text
        except Exception:
            pass

        # Brief popup first so the user notices.
        try:
            messagebox.showerror(
                "下载失败",
                f"{short_msg}\n\n详细日志已写入:\n{log_path}",
            )
        except Exception:
            pass

        # Then a full dialog with the scrollable log.
        dialog = tk.Toplevel(self.root)
        dialog.title("下载失败 — 详细日志")
        dialog.geometry("820x500")
        dialog.transient(self.root)
        dialog.update_idletasks()
        dialog.minsize(620, 320)
        dialog.grab_set()
        dialog.geometry(f"+{self.root.winfo_x() + 60}+{self.root.winfo_y() + 60}")

        ttk.Label(dialog, text=f"详细日志已同时写入: {log_path}",
                  font=self.default_font).pack(anchor='w', padx=10, pady=(12, 2))

        ttk.Label(dialog, text="错误信息：", font=self.default_font).pack(anchor='w', padx=10, pady=(8, 2))
        msg_box = tk.Text(dialog, height=4, wrap='word', font=self.default_font)
        msg_box.pack(fill='x', padx=10)
        msg_box.insert('1.0', short_msg or '(无)')
        msg_box.config(state='disabled')

        ttk.Label(dialog, text="yt-dlp 日志（可滚动）：", font=self.default_font).pack(anchor='w', padx=10, pady=(8, 2))
        log_box = tk.Text(dialog, wrap='none', font=("Consolas", 9))
        log_box.pack(fill='both', expand=True, padx=10, pady=(0, 8))
        log_box.insert('1.0', log_text or '(空)')
        log_box.config(state='disabled')

        scroll_y = ttk.Scrollbar(log_box, orient='vertical', command=log_box.yview)
        scroll_y.pack(side='right', fill='y')
        log_box['yscrollcommand'] = scroll_y.set

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=(0, 10))
        def open_log():
            if log_path and os.path.isfile(log_path):
                if os.name == 'nt':
                    subprocess.Popen(['notepad', log_path])
                elif os.name == 'posix':
                    subprocess.Popen(['open', log_path])
        tk.Button(btn_frame, text="打开日志文件", command=open_log, bg="#0078d4", fg="white",
                  relief="flat", font=self.default_font).pack(side=tk.LEFT, padx=5, ipadx=10)
        tk.Button(btn_frame, text="关闭", command=dialog.destroy, bg="#5c5c5c", fg="white",
                  relief="flat", font=self.default_font).pack(side=tk.LEFT, padx=5, ipadx=10)

    def show_concurrent_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("并发下载数")
        dialog.geometry("420x150")
        dialog.transient(self.root)
        dialog.update_idletasks()
        dialog.minsize(420, 150)
        dialog.grab_set()
        dialog.geometry(f"+{self.root.winfo_x() + 80}+{self.root.winfo_y() + 80}")

        ttk.Label(
            dialog,
            text="同时下载的视频数量 (1-8):\n"
                 "数值越大下载越快，但会被 YouTube 限速。",
            font=self.default_font,
        ).pack(anchor='w', padx=10, pady=(15, 5))

        n_var = tk.IntVar(value=get_max_concurrent())
        spin = ttk.Spinbox(dialog, from_=1, to=8, textvariable=n_var, width=5)
        spin.pack(pady=5, padx=10)

        def save():
            set_max_concurrent(n_var.get())
            dialog.destroy()
            messagebox.showinfo("并发下载数", f"已设置为 {get_max_concurrent()}")

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="保存", command=save, bg="#0078d4", fg="white",
                  relief="flat", font=self.default_font).pack(side=tk.LEFT, padx=5, ipadx=10)
        tk.Button(btn_frame, text="取消", command=dialog.destroy, bg="#5c5c5c", fg="white",
                  relief="flat", font=self.default_font).pack(side=tk.LEFT, padx=5, ipadx=10)

    def show_cookies_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Cookies 文件")
        dialog.geometry("620x180")
        dialog.transient(self.root)
        dialog.update_idletasks()
        dialog.minsize(620, 180)
        dialog.grab_set()
        dialog.geometry(f"+{self.root.winfo_x() + 80}+{self.root.winfo_y() + 80}")

        ttk.Label(
            dialog,
            text="选择从浏览器导出的 YouTube cookies 文件（Netscape 格式）。\n"
                 "登录 YouTube 后用浏览器扩展 \"Get cookies.txt LOCALLY\" 等工具导出。\n"
                 "留空则不使用 cookies（YouTube SABR 实验下最高仅可下载 360p）。",
        ).pack(pady=(15, 5), padx=10, anchor='w')

        path_var = tk.StringVar(value=get_cookiefile() or "")
        path_entry = ttk.Entry(dialog, textvariable=path_var, width=70)
        path_entry.pack(pady=5, padx=10)

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)

        def browse():
            initial = os.path.dirname(path_var.get()) if path_var.get() else os.path.expanduser('~')
            chosen = filedialog.askopenfilename(
                initialdir=initial,
                title="选择 cookies.txt",
                filetypes=[("Netscape cookies", "*.txt"), ("All files", "*.*")],
            )
            if chosen:
                path_var.set(chosen)

        def save():
            value = path_var.get().strip()
            set_cookiefile(value if value else None)
            dialog.destroy()
            if get_cookiefile():
                messagebox.showinfo("Cookies 文件", f"已设置: {get_cookiefile()}")
            else:
                messagebox.showinfo("Cookies 文件", "已清除 cookies")

        tk.Button(btn_frame, text="浏览...", command=browse, bg="#0078d4", fg="white",
                  relief="flat", font=self.default_font).pack(side=tk.LEFT, padx=5, pady=5, ipadx=10)
        tk.Button(btn_frame, text="保存", command=save, bg="#0078d4", fg="white",
                  relief="flat", font=self.default_font).pack(side=tk.LEFT, padx=5, pady=5, ipadx=10)
        tk.Button(btn_frame, text="取消", command=dialog.destroy, bg="#5c5c5c", fg="white",
                  relief="flat", font=self.default_font).pack(side=tk.LEFT, padx=5, pady=5, ipadx=10)

    def show_help(self):
        help_text = """YouTube 下载器 使用说明

【功能特点】
• 支持单视频和播放列表下载
• 支持多种视频质量选择
• 支持下载字幕
• 支持多种输出格式（mp4、mkv、webm、avi）
• 支持代理设置
• 支持登录 cookies（用于突破 YouTube SABR 实验的限制）

【使用方法】
1. 在顶部输入框粘贴YouTube视频URL
2. 点击"加载视频信息"按钮
3. 选择要下载的视频（可多选）
4. 选择下载质量、字幕和输出格式
5. 点击"开始下载"

【常见问题】
• 下载失败 / "page needs to be reloaded": 安装 Node.js (https://nodejs.org/)，重启本程序。
• 画质只有 360p: 这是 YouTube SABR 实验的匿名下载上限。要拿 1080p+，登录 YouTube → 用浏览器扩展导出 cookies.txt → 设置 → Cookies 文件 选择。
• 字幕无法下载: 该视频可能没有字幕或不支持该语言
• 格式转换失败: 请确保已安装 FFmpeg
• 网络问题: 设置 → 代理设置

【系统要求】
• Node.js（必需）：https://nodejs.org/
• FFmpeg（用于合并/转换）：https://ffmpeg.org/

GitHub仓库：https://github.com/rdhuht/my_YoutubeDownloader"""
        dialog = tk.Toplevel(self.root)
        dialog.title("使用说明")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()

        text_widget = tk.Text(dialog, wrap='word', font=self.default_font)
        text_widget.pack(fill='both', expand=True, padx=10, pady=10)
        text_widget.insert('1.0', help_text)
        text_widget.config(state='disabled')

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="关闭", command=dialog.destroy, bg="#5c5c5c", fg="white", relief="flat", font=self.default_font).pack()

    def open_github(self):
        webbrowser.open("https://github.com/rdhuht/my_YoutubeDownloader")

    def open_download_log(self):
        """Open the most recent download-failure log, or its containing folder
        if the file does not exist. From the menu the user can always find
        the log even if they closed the failure dialog too fast.
        """
        path = self._last_log_path
        if not path:
            # Fall back to the default location the logger writes to.
            base = getattr(self, 'download_path', None) or os.path.expanduser('~')
            path = os.path.join(base, 'last_download_log.txt')
        folder = os.path.dirname(path) or '.'
        if os.path.isfile(path):
            if os.name == 'nt':
                subprocess.Popen(['notepad', path])
            else:
                subprocess.Popen(['open', path])
        elif os.path.isdir(folder):
            if os.name == 'nt':
                subprocess.Popen(['explorer', folder.replace('/', '\\')])
            else:
                subprocess.Popen(['open', folder])
        else:
            messagebox.showinfo("日志", f"暂无下载日志。\n默认位置:\n{path}")

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
        self.update_status(f"下载路径: {self.download_path}")

    def update_video_progress_text(self, entry_index, text, tag='downloading'):
        def _do():
            for iid, idx in self.tree_iid_map.items():
                if idx == entry_index:
                    values = list(self.playlist_tree.item(iid, 'values'))
                    values[5] = text
                    self.playlist_tree.item(iid, values=values, tags=(tag,))
                    break
        try:
            self.root.after(0, _do)
        except RuntimeError:
            pass

    def update_video_speed_text(self, entry_index, text):
        def _do():
            for iid, idx in self.tree_iid_map.items():
                if idx == entry_index:
                    values = list(self.playlist_tree.item(iid, 'values'))
                    values[6] = text
                    self.playlist_tree.item(iid, values=values)
                    break
        try:
            self.root.after(0, _do)
        except RuntimeError:
            pass

    def update_video_eta_text(self, entry_index, text):
        def _do():
            for iid, idx in self.tree_iid_map.items():
                if idx == entry_index:
                    values = list(self.playlist_tree.item(iid, 'values'))
                    values[7] = text
                    self.playlist_tree.item(iid, values=values)
                    break
        try:
            self.root.after(0, _do)
        except RuntimeError:
            pass

    def update_video_convert_status(self, entry_index, status):
        def _do():
            for iid, idx in self.tree_iid_map.items():
                if idx == entry_index:
                    values = list(self.playlist_tree.item(iid, 'values'))
                    values[8] = status
                    self.playlist_tree.item(iid, values=values)
                    break
        try:
            self.root.after(0, _do)
        except RuntimeError:
            pass

    def set_video_result(self, entry_index, success):
        def _do():
            for iid, idx in self.tree_iid_map.items():
                if idx == entry_index:
                    values = list(self.playlist_tree.item(iid, 'values'))
                    if success:
                        values[5] = "100%"
                        self.playlist_tree.item(iid, values=values, tags=('success',))
                    else:
                        values[5] = "失败"
                        self.playlist_tree.item(iid, values=values, tags=('failed',))
                    break
        try:
            self.root.after(0, _do)
        except RuntimeError:
            pass

    def start_parse_video_thread(self):
        self.disable_buttons()
        self.update_status("正在解析视频信息...")
        threading.Thread(target=lambda: load_video_msg(self), daemon=True).start()

    def start_download_thread(self):
        selected = self.get_selected_videos()
        if not selected:
            messagebox.showwarning("警告", "请至少选择一个视频")
            self.enable_buttons()
            return
        self.disable_buttons()
        if len(selected) == 1:
            self.update_status("开始下载")
            threading.Thread(target=lambda: download_single(self, selected[0]), daemon=True).start()
        else:
            self.update_status(f"开始下载 {len(selected)} 个视频")
            threading.Thread(target=lambda: download_multi(self, selected), daemon=True).start()

    def disable_buttons(self):
        self.button_download.config(state='disabled')
        self.button_browse.config(state='disabled')
        self.button_load.config(state="disabled")
        self.btn_select_all.config(state='disabled')
        self.btn_deselect_all.config(state='disabled')

    def enable_buttons(self):
        self.button_download.config(state='normal')
        self.button_browse.config(state='normal')
        self.button_load.config(state='normal')
        self.btn_select_all.config(state='normal')
        self.btn_deselect_all.config(state='normal')

    def open_download_folder(self):
        if self.download_path:
            if os.name == 'nt':
                subprocess.Popen(['explorer', self.download_path.replace('/', '\\')])
            elif os.name == 'posix':
                subprocess.Popen(['open', self.download_path])

    def cancel_download(self):
        # Signal the worker thread, then close the live YoutubeDL instance so
        # yt-dlp aborts the in-flight HTTP read promptly. The worker surfaces
        # the cancellation in its own messagebox, so we don't pop one here.
        self.cancel_event.set()
        ydl = self._active_ydl
        if ydl is not None:
            try:
                ydl.close()
            except Exception:
                pass
        self.button_cancel.config(state='disabled')
        self.update_status("下载已取消")

    def select_all_videos(self):
        for var in self.check_vars.values():
            var.set(1)
        self.update_tree_selections()

    def deselect_all_videos(self):
        for var in self.check_vars.values():
            var.set(0)
        self.update_tree_selections()

    def update_tree_selections(self):
        for iid, var in self.check_vars.items():
            values = list(self.playlist_tree.item(iid, 'values'))
            values[0] = "√" if var.get() else ""
            self.playlist_tree.item(iid, values=values)

    def on_quality_changed(self, event=None):
        from utils import estimate_size
        quality_text = self.quality_combobox.get()
        if not quality_text or not self.playlist_entries:
            return

        selected_height = int(quality_text.replace('p', ''))

        for iid in self.check_vars.keys():
            index = int(self.playlist_tree.item(iid, 'values')[1]) - 1
            if index < len(self.playlist_entries):
                entry = self.playlist_entries[index]
                duration = entry.get('duration') or 300
                size_str = estimate_size(selected_height, duration)
                values = list(self.playlist_tree.item(iid, 'values'))
                values[4] = size_str
                self.playlist_tree.item(iid, values=values)

    def on_tree_click(self, event):
        region = self.playlist_tree.identify_region(event.x, event.y)
        if region == 'cell':
            item = self.playlist_tree.identify_row(event.y)
            if item and item in self.check_vars:
                var = self.check_vars[item]
                var.set(1 - var.get())
                self.update_tree_selections()
                return "break"

    def get_selected_videos(self):
        selected = []
        for iid, var in self.check_vars.items():
            if var.get():
                index = int(self.playlist_tree.item(iid, 'values')[1]) - 1
                if index < len(self.playlist_entries):
                    selected.append(self.playlist_entries[index])
        return selected