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

from config import get_proxy, set_proxy, FFMPEG_AVAILABLE
from utils import get_url_from_clipboard
from downloader import load_video_msg, download_single, download_multi


class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube 下载器")
        self.root.minsize(width=900, height=550)
        try:
            self.root.iconbitmap('imgs/logo.ico')
        except:
            pass
        self.is_downloading = False
        self.download_start_time = None
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

        self.playlist_tree['columns'] = ('select', 'index', 'title', 'duration', 'size', 'progress', 'convert')
        self.playlist_tree.column('select', width=60, anchor='center')
        self.playlist_tree.column('index', width=60, anchor='center')
        self.playlist_tree.column('title', width=280)
        self.playlist_tree.column('duration', width=80, anchor='center')
        self.playlist_tree.column('size', width=80, anchor='center')
        self.playlist_tree.column('progress', width=120, anchor='center')
        self.playlist_tree.column('convert', width=80, anchor='center')

        self.playlist_tree.heading('select', text='✓')
        self.playlist_tree.heading('index', text='序号')
        self.playlist_tree.heading('title', text='标题')
        self.playlist_tree.heading('duration', text='时长')
        self.playlist_tree.heading('size', text='大小')
        self.playlist_tree.heading('progress', text='下载进度')
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
        self._status_text = text
        self.root.title("YouTube 下载器")
        self.status_bar['text'] = text

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
        settings_menu.add_separator()
        settings_menu.add_command(label="关于", command=self.show_about)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="使用说明", command=self.show_help)
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
        messagebox.showinfo("关于", "YouTube 下载器 v1.4.0\n\n支持单视频和播放列表下载")

    def show_help(self):
        help_text = """YouTube 下载器 使用说明

【功能特点】
• 支持单视频和播放列表下载
• 支持多种视频质量选择
• 支持下载字幕
• 支持多种输出格式（mp4、mkv、webm、avi）
• 支持代理设置

【使用方法】
1. 在顶部输入框粘贴YouTube视频URL
2. 点击"加载视频信息"按钮
3. 选择要下载的视频（可多选）
4. 选择下载质量、字幕和输出格式
5. 点击"开始下载"

【常见问题】
• 下载失败：请检查网络连接或尝试设置代理
• 字幕无法下载：该视频可能没有字幕或不支持该语言
• 格式转换失败：请确保已安装FFmpeg

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
        for iid, idx in self.tree_iid_map.items():
            if idx == entry_index:
                values = list(self.playlist_tree.item(iid, 'values'))
                values[5] = text
                self.playlist_tree.item(iid, values=values, tags=(tag,))
                break

    def update_video_convert_status(self, entry_index, status):
        for iid, idx in self.tree_iid_map.items():
            if idx == entry_index:
                values = list(self.playlist_tree.item(iid, 'values'))
                values[6] = status
                self.playlist_tree.item(iid, values=values)
                break

    def set_video_result(self, entry_index, success):
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

    def start_parse_video_thread(self):
        self.disable_buttons()
        self.update_status("正在解析视频信息...")
        threading.Thread(target=lambda: load_video_msg(self)).start()

    def start_download_thread(self):
        selected = self.get_selected_videos()
        if not selected:
            messagebox.showwarning("警告", "请至少选择一个视频")
            self.enable_buttons()
            return
        self.disable_buttons()
        if len(selected) == 1:
            self.update_status("开始下载")
            threading.Thread(target=lambda: download_single(self, selected[0])).start()
        else:
            self.update_status(f"开始下载 {len(selected)} 个视频")
            threading.Thread(target=lambda: download_multi(self, selected)).start()

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
        self.is_downloading = False
        messagebox.showinfo("取消下载", "下载已取消。")
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