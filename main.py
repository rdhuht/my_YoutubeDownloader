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

class FFmpegProgressLogger:
    def __init__(self, app_instance, is_playlist=False, entry_index=None):
        self.app = app_instance
        self.is_playlist = is_playlist
        self.entry_index = entry_index
        self._progress_pattern = re.compile(r'time=(\d+):(\d{2}):(\d{2}\.\d+)')
        self._duration = 0

    def debug(self, info):
        if 'Duration:' in info:
            try:
                match = re.search(r'(\d+):(\d{2}):(\d{2})', info)
                if match:
                    h, m, s = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    self._duration = h * 3600 + m * 60 + s
            except:
                pass
        if 'time=' in info:
            match = self._progress_pattern.search(info)
            if match and self._duration > 0:
                h, m, s = int(match.group(1)), int(match.group(2)), float(match.group(3))
                current_time = h * 3600 + m * 60 + s
                percentage = min(current_time / self._duration * 100, 99)
                self.app.update_video_progress_text(self.entry_index, f"转换中 {percentage:.0f}%")

    def warning(self, info):
        pass

    def error(self, info):
        pass

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

# 语言代码映射
LANGUAGE_MAP = {
    'en': '英文',
    'zh': '简体中文',
    'zh-Hans': '简体中文',
    'zh-Hant': '繁体中文',
    'zh-TW': '繁体中文',
    'zh-CN': '简体中文',
    'zh-Hans-CN': '简体中文',
    'zh-Hant-TW': '繁体中文',
    'ja': '日语',
    'ko': '韩语',
    'es': '西班牙语',
    'fr': '法语',
    'de': '德语',
    'it': '意大利语',
    'ru': '俄语',
    'pt': '葡萄牙语',
    'pt-BR': '巴西葡萄牙语',
    'vi': '越南语',
    'id': '印尼语',
    'th': '泰语',
    'ar': '阿拉伯语',
    'hi': '印地语',
    'nl': '荷兰语',
    'pl': '波兰语',
    'tr': '土耳其语',
    'uk': '乌克兰语',
    'sv': '瑞典语',
    'no': '挪威语',
    'fi': '芬兰语',
    'da': '丹麦语',
    'cs': '捷克语',
    'el': '希腊语',
    'he': '希伯来语',
    'ro': '罗马尼亚语',
    'hu': '匈牙利语',
    'ms': '马来语',
    'gu': '古吉拉特语',
    'fa': '波斯语',
    'bn': '孟加拉语',
    'ur': '乌尔都语',
    'bg': '保加利亚语',
    'sk': '斯洛伐克语',
    'sw': '斯瓦希里语',
    'ka': '格鲁吉亚语',
    'ta': '泰米尔语',
    'fil': '菲律宾语',
    'ml': '马拉雅拉姆语',
    'te': '泰卢固语',
    'mr': '马拉蒂语',
    'kn': '卡纳达语',
    'pa': '旁遮普语',
    'my': '缅甸语',
    'km': '高棉语',
    'lo': '老挝语',
    'am': '阿姆哈拉语',
    'ne': '尼泊尔语',
    'si': '僧伽罗语',
    'jw': '爪哇语',
    'su': '巽他语',
    'ca': '加泰罗尼亚语',
    'hr': '克罗地亚语',
    'sr': '塞尔维亚语',
    'sl': '斯洛文尼亚语',
    'et': '爱沙尼亚语',
    'lv': '拉脱维亚语',
    'lt': '立陶宛语',
    'az': '阿塞拜疆语',
    'kk': '哈萨克语',
    'uz': '乌兹别克语',
    'be': '白俄罗斯语',
    'mk': '马其顿语',
    'sq': '阿尔巴尼亚语',
    'hy': '亚美尼亚语',
    'eu': '巴斯克语',
    'gl': '加利西亚语',
    'af': '南非荷兰语',
    'iw': '希伯来语',
}

def get_language_display(code):
    return LANGUAGE_MAP.get(code, code)

def subtitle_sort_key(display_name):
    priority = {'简体中文': 0, '繁体中文': 1, 'English': 2}
    return (priority.get(display_name, 3), display_name)

def get_language_code(display):
    for code, name in LANGUAGE_MAP.items():
        if name == display:
            return code
    return display

# 定义主应用程序类
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
        self.format_map = {}
        self.formats = []
        self.quality_options = []
        self.last_auto_paste_url = None
        self.tree_iid_map = {}
        self.current_download_index = None
        self._status_text = "就绪"

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

        # ===== 顶部框架 =====
        self.top_frame = ttk.Frame(root)
        self.top_frame.pack(fill='x', padx=10, pady=5)

        self.entry_url = ttk.Entry(self.top_frame)
        self.entry_url.pack(fill='x', expand=True, padx=10, pady=10, side=tk.LEFT)
        self.entry_url.bind('<FocusIn>', self.on_entry_focus)
        self.entry_url.bind('<Button-1>', self.on_entry_click)

        clipboard_url = get_url_from_clipboard(root)
        if clipboard_url:
            self.entry_url.insert(0, clipboard_url)
            self.update_status("已从剪贴板获取URL")

        self.button_load = ttk.Button(self.top_frame, text="加载视频信息", command=self.start_parse_video_thread, bootstyle='success')
        self.button_load.pack(side=tk.RIGHT)

        # ===== 内容区域 =====
        self.video_title_label = ttk.Label(root, text="请输入URL并点击加载", foreground='gray')
        self.video_title_label.pack(padx=10, pady=(5, 5))

        # Treeview 框架
        self.tree_frame = ttk.Frame(root)
        self.tree_frame.pack(fill='both', expand=True, padx=10, pady=5)

        self.tree_scroll_y = ttk.Scrollbar(self.tree_frame, orient='vertical')
        self.tree_scroll_x = ttk.Scrollbar(self.tree_frame, orient='horizontal')

        # Treeview - 列: 选择, 序号, 标题, 时长, 大小, 下载进度, 转换状态
        self.playlist_tree = ttk.Treeview(self.tree_frame, yscrollcommand=self.tree_scroll_y.set, xscrollcommand=self.tree_scroll_x.set, show='headings', selectmode='none', height=12)
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

        self.btn_frame = ttk.Frame(root)
        self.btn_frame.pack(pady=5)

        self.btn_select_all = ttk.Button(self.btn_frame, text="全选", command=self.select_all_videos, bootstyle='info', width=10)
        self.btn_select_all.pack(side=tk.LEFT, padx=5)

        self.btn_deselect_all = ttk.Button(self.btn_frame, text="取消全选", command=self.deselect_all_videos, bootstyle='info', width=10)
        self.btn_deselect_all.pack(side=tk.LEFT, padx=5)

        self.options_frame = ttk.Frame(root)
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

        self.download_btn_frame = ttk.Frame(root)
        self.download_btn_frame.pack(pady=5)

        self.button_browse = ttk.Button(self.download_btn_frame, text="下载路径", command=self.browse_path, bootstyle='info')
        self.button_browse.pack(side=tk.LEFT, padx=(10, 5))
        self.button_download = ttk.Button(self.download_btn_frame, text="开始下载", command=self.start_download_thread, bootstyle='danger', width=15)
        self.button_download.pack(side=tk.LEFT, padx=(5, 10))
        self.button_cancel = ttk.Button(self.download_btn_frame, text="取消下载", command=self.cancel_download, bootstyle='warning')
        self.button_cancel.pack(side=tk.LEFT, padx=(5, 10))
        self.button_cancel.config(state='disabled')

        self.status_bar = ttk.Label(root, text="就绪", relief='sunken', anchor='w')
        self.status_bar.pack(fill='x', padx=10, pady=(0, 5))

        self.download_path = os.path.join(os.path.expanduser('~'), 'Desktop')

        self.create_menu_bar()
        self.center_window(self.root)

    # 更新状态信息到窗口标题和底部状态栏
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

    def show_about(self):
        messagebox.showinfo("关于", "YouTube 下载器 v4.0\n\n支持单视频和播放列表下载")

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
        import webbrowser
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

    def show_progress(self, d):
        if d['status'] == 'downloading':
            downloaded = d.get('downloaded_bytes', 0) or 0
            total = d.get('total_bytes') or d.get('totalbyte') or 0
            if total and total > 0:
                percentage = min(downloaded / total * 100, 100)
                self.update_video_progress_text(self.current_download_index, f"{percentage:.0f}%", 'downloading')
            self.root.update_idletasks()
            if self.download_start_time:
                elapsed_time = time.time() - self.download_start_time
                elapsed_time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
                self.update_status(f"下载中... {elapsed_time_str}")
        elif d['status'] == 'finished' and d.get('postprocessor'):
            self.download_phase = 'converting'
            self.update_video_convert_status(self.current_download_index, "转换中")

    def show_playlist_progress(self, d):
        if d['status'] == 'downloading':
            downloaded = d.get('downloaded_bytes', 0) or 0
            total = d.get('total_bytes') or d.get('totalbyte') or 0
            if total and total > 0:
                percentage = min(downloaded / total * 100, 100)
                self.update_video_progress_text(self.current_download_index, f"{percentage:.0f}%", 'downloading')
            self.root.update_idletasks()
            if self.download_start_time:
                elapsed_time = time.time() - self.download_start_time
                elapsed_time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
                self.update_status(f"视频 {self.current_playlist_index}/{self.total_playlist_videos} 下载中... {elapsed_time_str}")
        elif d['status'] == 'finished' and d.get('postprocessor'):
            self.download_phase = 'converting'
            self.update_video_convert_status(self.current_download_index, "转换中")

    def start_parse_video_thread(self):
        self.disable_buttons()
        self.update_status("正在解析视频信息...")
        threading.Thread(target=self.load_video_msg).start()

    def start_download_thread(self):
        selected = self.get_selected_videos()
        if not selected:
            messagebox.showwarning("警告", "请至少选择一个视频")
            self.enable_buttons()
            return
        self.disable_buttons()
        if len(selected) == 1:
            self.update_status("开始下载")
            threading.Thread(target=self.download_single, args=(selected[0],)).start()
        else:
            self.update_status(f"开始下载 {len(selected)} 个视频")
            threading.Thread(target=self.download_multi, args=(selected,)).start()

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

    def load_video_msg(self):
        url = self.entry_url.get().strip()
        if not url:
            messagebox.showerror("错误", "请输入有效的视频URL。")
            self.enable_buttons()
            self.update_status("就绪")
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
                entries = info_dict.get('entries', [])
                if entries:
                    self.is_playlist = True
                    self.load_playlist_ui(info_dict)
                else:
                    self.is_playlist = False
                    self.load_single_ui(info_dict)

        except Exception as e:
            messagebox.showerror("加载视频错误", f"错误: {e}")
            self.update_status("加载失败")
        finally:
            self.enable_buttons()

    def load_single_ui(self, info_dict):
        title = info_dict.get('title', '视频')
        self.formats = info_dict.get('formats', [])
        self.video_title_label['text'] = f"视频: {title}"

        heights = set()
        for fmt in self.formats:
            if fmt.get('ext') == 'mp4' and fmt.get('height'):
                heights.add(fmt.get('height'))

        self.quality_options = sorted(list(heights), reverse=True)
        self.quality_combobox['values'] = [f"{h}p" for h in self.quality_options]
        if self.quality_options:
            self.quality_combobox.current(0)

        subtitles = info_dict.get('subtitles', {})
        subtitle_list = sorted([get_language_display(k) for k in subtitles.keys()], key=subtitle_sort_key) if subtitles else ['无']
        self.caption_combobox['values'] = subtitle_list
        self.caption_combobox.current(0)

        self.playlist_entries = [info_dict]
        self.load_treeview()

        self.update_status(f"已加载: {title}")

    def load_playlist_ui(self, info_dict):
        playlist_title = info_dict.get('title', '播放列表')
        entries = info_dict.get('entries', [])

        self.playlist_entries = [e for e in entries if e is not None]
        self.video_title_label['text'] = f"播放列表: {playlist_title} (共 {len(self.playlist_entries)} 个视频)"

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

        subtitles = set()
        for entry in self.playlist_entries:
            if entry and entry.get('subtitles'):
                subtitles.update(entry.get('subtitles', {}).keys())
        subtitle_list = sorted([get_language_display(k) for k in subtitles], key=subtitle_sort_key) if subtitles else ['无']
        self.caption_combobox['values'] = subtitle_list
        self.caption_combobox.current(0)

        self.load_treeview()
        self.update_status(f"已加载播放列表: {playlist_title} ({len(self.playlist_entries)} 个视频)")

    def load_treeview(self):
        for item in self.playlist_tree.get_children():
            self.playlist_tree.delete(item)
        self.check_vars.clear()
        self.tree_iid_map.clear()

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

            height = entry.get('height') or selected_height
            duration_val = entry.get('duration') or 300
            size_str = estimate_size(height, duration_val)

            iid = self.playlist_tree.insert('', 'end', values=("√", i + 1, title, duration_str, size_str, "", ""))
            var = tk.IntVar(value=1)
            self.check_vars[iid] = var
            self.tree_iid_map[iid] = i

        self.root.after(100, self.on_quality_changed)

    def download_single(self, entry):
        quality_text = self.quality_combobox.get()
        if not quality_text:
            messagebox.showerror("错误", "请选择视频质量。")
            self.enable_buttons()
            return

        height = int(quality_text.replace('p', ''))
        format_str = f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={height}]+bestaudio/best'

        self.is_downloading = True
        self.download_start_time = time.time()
        self.download_phase = 'downloading'
        self.button_cancel.config(state='normal')

        video_url = entry.get('url') or entry.get('webpage_url')
        if not video_url:
            messagebox.showerror("错误", "无法获取视频URL。")
            self.enable_buttons()
            return

        entry_index = self.playlist_entries.index(entry)
        self.current_download_index = entry_index

        output_format = self.format_combobox.get()
        use_converter = output_format != '不转换' and FFMPEG_AVAILABLE

        ydl_opts = {
            'format': format_str,
            'outtmpl': os.path.join(self.download_path, '%(title)s.%(ext)s'),
            'progress_hooks': [self.show_progress],
        }

        if USER_PROXY:
            ydl_opts['proxy'] = USER_PROXY

        if use_converter:
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': output_format,
            }]
            ydl_opts['logger'] = FFmpegProgressLogger(self, is_playlist=False, entry_index=entry_index)

        selected_subtitle = self.caption_combobox.get()
        if selected_subtitle and selected_subtitle != '无':
            lang_code = get_language_code(selected_subtitle)
            if lang_code == 'zh':
                lang_code = 'zh-Hans'
            if lang_code in ['zh-Hans', 'zh-CN', 'zh']:
                ydl_opts['subtitleslangs'] = ['zh-Hans', 'zh-CN', 'zh']
            else:
                ydl_opts['subtitleslangs'] = [lang_code]
            ydl_opts['writesubtitles'] = True
            ydl_opts['subtitlesformat'] = 'srt'

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            elapsed_time = time.time() - self.download_start_time
            elapsed_time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
            self.set_video_result(entry_index, True)
            self.update_video_convert_status(entry_index, "完成" if use_converter else "")
            self.update_status(f"下载完成! 耗时: {elapsed_time_str}")
            messagebox.showinfo("下载完成", "视频已成功下载。")
            self.open_download_folder()
        except Exception as e:
            self.set_video_result(entry_index, False)
            self.update_video_convert_status(entry_index, "")
            messagebox.showerror("下载错误", f"错误: {e}")
            self.update_status("下载失败")
        finally:
            self.is_downloading = False
            self.enable_buttons()
            self.download_start_time = None
            self.current_download_index = None
            self.button_cancel.config(state='disabled')

    def download_multi(self, selected_entries):
        quality_text = self.quality_combobox.get()
        if not quality_text:
            messagebox.showerror("错误", "请选择视频质量。")
            self.enable_buttons()
            return

        height = int(quality_text.replace('p', ''))
        format_str = f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={height}]+bestaudio/best'

        self.is_downloading = True
        self.download_start_time = time.time()
        self.button_cancel.config(state='normal')

        self.total_playlist_videos = len(selected_entries)
        self.current_playlist_index = 0
        success_count = 0
        fail_count = 0

        selected_subtitle = self.caption_combobox.get()
        output_format = self.format_combobox.get()
        use_converter = output_format != '不转换' and FFMPEG_AVAILABLE

        for i, entry in enumerate(selected_entries):
            if not self.is_downloading:
                break

            self.current_playlist_index = i + 1
            video_url = entry.get('url') or entry.get('webpage_url')
            if not video_url:
                fail_count += 1
                continue

            entry_index = self.playlist_entries.index(entry) if entry in self.playlist_entries else i
            self.current_download_index = entry_index

            self.update_status(f"下载第 {i+1}/{self.total_playlist_videos} 个视频...")

            ydl_opts = {
                'format': format_str,
                'outtmpl': os.path.join(self.download_path, '%(title)s.%(ext)s'),
                'progress_hooks': [self.show_playlist_progress],
            }

            if USER_PROXY:
                ydl_opts['proxy'] = USER_PROXY

            if use_converter:
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }]
                ydl_opts['logger'] = FFmpegProgressLogger(self, is_playlist=True, entry_index=entry_index)

            if selected_subtitle and selected_subtitle != '无':
                lang_code = get_language_code(selected_subtitle)
                if lang_code == 'zh':
                    lang_code = 'zh-Hans'
                if lang_code in ['zh-Hans', 'zh-CN', 'zh']:
                    ydl_opts['subtitleslangs'] = ['zh-Hans', 'zh-CN', 'zh']
                else:
                    ydl_opts['subtitleslangs'] = [lang_code]
                ydl_opts['writesubtitles'] = True
                ydl_opts['subtitlesformat'] = 'srt'

            try:
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video_url])
                success_count += 1
                self.set_video_result(entry_index, True)
                self.update_video_convert_status(entry_index, "完成" if use_converter else "")
            except Exception as e:
                fail_count += 1
                self.set_video_result(entry_index, False)
                self.update_video_convert_status(entry_index, "")
                print(f"下载失败: {entry.get('title', '未知')} - {e}")

        elapsed_time = time.time() - self.download_start_time
        elapsed_time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
        self.update_status(f"批量下载完成! 成功: {success_count}, 失败: {fail_count}")
        messagebox.showinfo("下载完成", f"成功: {success_count} 个, 失败: {fail_count} 个")
        self.open_download_folder()

        self.is_downloading = False
        self.enable_buttons()
        self.download_start_time = None
        self.current_download_index = None
        self.button_cancel.config(state='disabled')


# 主程序入口
if __name__ == "__main__":
    root = tk.Tk()
    style = Style(theme="superhero")
    app = YouTubeDownloader(root)
    root.mainloop()