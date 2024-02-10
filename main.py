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
from pytube import YouTube
import threading
import tkinter.simpledialog as sd
import tkinter.messagebox as mb
import tkinter.font as tkFont
import subprocess
from bs4 import BeautifulSoup
from pytube.exceptions import PytubeError

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
        self.root.minsize(width=600, height=200)  # 减少窗口的最小高度以使布局更紧凑
        self.streams_map = {}  # 新增属性来存储清晰度和文件大小的映射
        self.is_downloading = False  # 新增属性来标记是否正在下载
        self.download_start_time = None

        # 定义字体
        large_font = tkFont.Font(family="阿里巴巴普惠体 3.0 75 SemiBold", size=20)
        middle_font = tkFont.Font(family="阿里巴巴普惠体 3.0 75 SemiBold", size=18)
        small_font = tkFont.Font(family="阿里巴巴普惠体 3.0 75 SemiBold", size=16)

        # 创建一个新的 Frame 用于容纳视频链接 Label 和加载按钮
        self.top_frame = ttk.Frame(root)
        self.top_frame.pack(fill='x', padx=10, pady=5)

        # 链接输入框
        self.entry_url = PlaceholderEntry(self.top_frame, "在这里输入视频链接")
        self.entry_url.pack(fill='x', expand=True, padx=10, pady=10, side=tk.LEFT)

        # 加载视频信息按钮
        self.button_load = ttk.Button(self.top_frame, text="解析链接", command=self.start_parse_video_thread, bootstyle='success')
        self.button_load.pack(side=tk.RIGHT)

        # 显示视频标题
        self.video_title_label = ttk.Label(root, text="视频标题", foreground='gray')
        self.video_title_label.pack(padx=10, pady=(0, 5))  # 紧接着 top_frame 下方放置

        # 视频清晰度和字幕选择框架
        self.quality_frame = ttk.Frame(root)
        self.quality_frame.pack(padx=5, pady=10)
        self.quality_label = ttk.Label(self.quality_frame, text="清晰度:", font=small_font)
        self.quality_label.pack(side=tk.LEFT, padx=10)
        self.quality_combobox = ttk.Combobox(self.quality_frame, state="readonly", width=15)
        self.quality_combobox.pack(side=tk.LEFT, padx=5)
        self.caption_label = ttk.Label(self.quality_frame, text="字幕:", font=small_font)
        self.caption_label.pack(side=tk.LEFT, padx=5)
        self.caption_combobox = ttk.Combobox(self.quality_frame, state="readonly", width=25)
        self.caption_combobox.pack(side=tk.LEFT, padx=5)

        # 下载路径选择和开始下载按钮
        self.button_frame = ttk.Frame(root)
        self.button_frame.pack(pady=5)
        self.button_browse = ttk.Button(self.button_frame, text="下载路径", command=self.browse_path, bootstyle='info')
        self.button_browse.pack(side=tk.LEFT, padx=(10, 5))
        self.button_download = ttk.Button(self.button_frame, text="开始下载", command=self.start_download_thread, bootstyle='danger')
        self.button_download.pack(side=tk.LEFT, padx=(5, 10))
        self.button_cancel = ttk.Button(self.button_frame, text="取消下载", command=self.cancel_download, bootstyle='warning')
        self.button_cancel.pack(side=tk.LEFT, padx=(5, 10))
        self.button_cancel.config(state='disabled')  # 初始状态为禁用

        # 创建一个新的 Frame 用于容纳视频链接 Label 和加载按钮
        self.bottom_frame = ttk.Frame(root)
        self.bottom_frame.pack(fill='x', padx=20, pady=5)

        # 进度条和进度百分比
        self.progress = ttk.Progressbar(self.bottom_frame, bootstyle="success-striped", orient='horizontal', mode='determinate')
        self.progress.pack(fill='both', expand=True, side=tk.LEFT)
        self.progress_label = ttk.Label(self.bottom_frame, text="0%", font=small_font)
        self.progress_label.pack(padx=8, pady=5)

        self.download_path = ""  # 用于存储下载路径

        self.center_window(self.root)


    def center_window(self, window):
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
        x = (window.winfo_screenwidth() // 2) - (width // 2)
        y = (window.winfo_screenheight() // 2) - (height // 2)
        window.geometry(f'+{x}+{y}')


    def browse_path(self):
        """ Let the user choose a download path, default to the Desktop if not chosen """
        initial_path = os.path.join(os.path.expanduser('~'), 'Desktop')
        self.download_path = filedialog.askdirectory(initialdir=initial_path)
        if not self.download_path:  # If the user cancels the selection
            self.download_path = initial_path  # Default to Desktop
        # messagebox.showinfo("路径选择", f"下载路径已选择：{self.download_path}")
        self.root.title(f"YouTube Downloader - 下载路径已选择：{self.download_path}")


    def show_progress(self, stream, chunk, bytes_remaining):
        """ 更新下载进度 """
        if not self.is_downloading:
            return  # 如果下载被取消，则不更新进度
        total_size = stream.filesize
        bytes_downloaded = total_size - bytes_remaining
        percentage_of_completion = bytes_downloaded / total_size * 100
        self.progress['value'] = percentage_of_completion
        self.progress_label['text'] = f"{percentage_of_completion:.2f}%"  # 更新百分比标签
        self.root.update_idletasks()
        if self.download_start_time:
            elapsed_time = time.time() - self.download_start_time
            elapsed_time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
            self.root.title(f"YouTube Downloader - 用时: {elapsed_time_str}")


    def get_ffmpeg_path(self):
        """
        解压并返回 ffmpeg 的路径。根据操作系统的不同，适配不同的执行逻辑。
        如果是打包的应用程序，则从临时目录运行。支持Windows和macOS。
        """
        # 检测操作系统
        if platform.system() == 'Windows':
            ffmpeg_exe = 'ffmpeg.exe'
        else:
            ffmpeg_exe = 'ffmpeg'

        if getattr(sys, 'frozen', False):
            # 如果应用程序是打包的，则从 _MEIPASS 目录解压 ffmpeg
            temp_dir = tempfile.mkdtemp()
            ffmpeg_temp_path = os.path.join(temp_dir, ffmpeg_exe)
            shutil.copyfile(os.path.join(sys._MEIPASS, ffmpeg_exe), ffmpeg_temp_path)
            os.chmod(ffmpeg_temp_path, 0o755)  # 确保文件是可执行的
            return ffmpeg_temp_path
        else:
            # 如果是在开发环境，则直接返回项目目录中的 ffmpeg 路径
            return os.path.join(os.path.dirname(__file__), 'ffmpeg', ffmpeg_exe)


    def xml2srt(self, text):
        # Ensure using 'lxml' as the parser for XML documents
        soup = BeautifulSoup(text, 'lxml')
        ps = soup.findAll('p')
        output = ''
        num = 0
        for i, p in enumerate(ps):
            try:
                num += 1
                text = p.text
                start_time = int(p['t'])
                duration = int(p['d'])
                end_time = start_time + duration

                # 转换时间格式
                start_hours, start_remainder = divmod(start_time, 3600000)
                start_minutes, start_seconds = divmod(start_remainder, 60000)
                start_seconds, start_milliseconds = divmod(start_seconds, 1000)

                end_hours, end_remainder = divmod(end_time, 3600000)
                end_minutes, end_seconds = divmod(end_remainder, 60000)
                end_seconds, end_milliseconds = divmod(end_seconds, 1000)

                # 格式化时间字符串
                start_time_str = f"{start_hours:02}:{start_minutes:02}:{start_seconds:02},{start_milliseconds:03}"
                end_time_str = f"{end_hours:02}:{end_minutes:02}:{end_seconds:02},{end_milliseconds:03}"

                output += f"{num}\n{start_time_str} --> {end_time_str}\n{text}\n\n"
            except KeyError:
                pass  # 忽略没有时间属性的标签
        return output


    def clean_filename(self, filename):
        # 替换不合法字符
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')  # 使用下划线替代不合法字符
        return filename


    def extract_resolution_and_size(self, quality):
        resolution, size = quality.split(' - ')
        size = float(size.replace('MB', ''))
        resolution = int(resolution.replace('p', ''))
        return resolution, size
    

    def start_parse_video_thread(self):
        """ 在新线程中开始分析视频信息，并重置进度条 """
        self.progress['value'] = 0
        self.disable_buttons()  # 禁用按钮
        self.root.title(f"YouTube Downloader - 解析视频信息中……")
        threading.Thread(target=self.load_video_msg).start()


    def start_download_thread(self):
        """ 在新线程中开始下载视频，并重置进度条 """
        self.progress['value'] = 0
        self.disable_buttons()  # 禁用按钮
        self.root.title(f"YouTube Downloader - 开始下载")
        threading.Thread(target=self.download_video).start()


    def disable_buttons(self):
        """ 禁用按钮 """
        self.button_download.config(state='disabled')
        self.button_browse.config(state='disabled')
        self.button_load.config(state="disabled")


    def enable_buttons(self):
        """ 启用按钮 """
        self.button_download.config(state='normal')
        self.button_browse.config(state='normal')
        self.button_load.config(state='normal')


    def open_download_folder(self):
        """ 打开下载文件夹 """
        if self.download_path:
            if os.name == 'nt':  # 对于Windows
                subprocess.Popen(['explorer', self.download_path.replace('/', '\\')])
            elif os.name == 'posix':  # 对于macOS, Linux
                subprocess.Popen(['open', self.download_path])


    def cancel_download(self):
        """取消当前下载任务"""
        self.is_downloading = False
        messagebox.showinfo("取消下载", "用户取消下载。")
        self.button_cancel.config(state='disabled')  # 取消下载后禁用取消按钮
        self.root.title("YouTube Downloader")


    def load_video_msg(self):
        """加载视频信息并显示视频标题及可用字幕列表"""
        url = self.entry_url.get()
        try:
            yt = YouTube(url)
            self.video_title_label.config(foreground='black')
            self.video_title_label['text'] = yt.title  # 显示视频标题

            streams = yt.streams.filter(progressive=False, file_extension='mp4').order_by('resolution')
            self.streams_map.clear()  # 清空之前的映射
            qualities = []
            for stream in streams:
                display_text = "{} - {:.2f}MB".format(stream.resolution, stream.filesize / (1024 * 1024))
                self.streams_map[display_text] = stream.resolution  # 储存映射
                qualities.append(display_text)
            qualities_sorted_correctly = sorted(qualities, key=self.extract_resolution_and_size, reverse=True)
            self.quality_combobox['values'] = qualities_sorted_correctly
            if qualities:
                self.quality_combobox.current(0)

            # 获取并展示可用字幕列表
            captions = yt.captions
            if len(captions) == 0:
                self.root.title("YouTube Downloader - 无字幕文件，请选择分辨率和下载路径")
            else:
                self.root.title("YouTube Downloader - 请选择分辨率、字幕和下载路径")
            # 创建一个映射字典，用于存储语言名称到代码的映射
            self.caption_lang_map = {caption.name: caption.code for caption in captions}
            # 更新下拉菜单，显示语言名称
            self.caption_combobox['values'] = list(self.caption_lang_map.keys())

            # 设置默认字幕选择逻辑，根据实际可用选项调整
            caption_preferences = ['Chinese (China)', 'Chinese', 'Chinese (Traditional)', 'English']
            selected_caption = None
            for pref in caption_preferences:
                if pref in self.caption_lang_map:  # 确保使用的是实际存在的键
                    selected_caption = pref
                    break
            if selected_caption:
                # 设置Combobox为首选字幕语言
                self.caption_combobox.set(selected_caption)

        except PytubeError as e:
            messagebox.showerror("Pytube 错误", f"加载视频时出错: {e}")
        except Exception as e:
            messagebox.showerror("错误", f"加载视频时出错：{e}")
        finally:
            # 重置下载功能
            self.progress['value'] = 0
            self.progress_label['text'] = "0%"
            self.enable_buttons()  # 重新启用按钮
            self.root.event_generate("<<CloseParsingDialog>>", when="tail")


    def update_elapsed_time(self):
        if self.download_start_time and self.is_downloading:
            elapsed_time = time.time() - self.download_start_time
            elapsed_time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
            self.root.title(f"YouTube Downloader - 用时: {elapsed_time_str}")
            # Call this method again after 1 second
            self.root.after(1000, self.update_elapsed_time)


    def download_video(self):
        """根据用户选择的清晰度下载视频，并下载字幕（如果可用）"""
        self.root.title("YouTube Downloader")
        self.is_downloading = True
        self.download_start_time = time.time()  # Record start time
        self.update_elapsed_time()  # Start the elapsed time update timer

        self.button_cancel.config(state='normal')  # 启用取消按钮
        url = self.entry_url.get()
        if not self.download_path:
            # Default to desktop if no path is set
            self.download_path = os.path.join(os.path.expanduser('~'), 'Desktop')
        selected_quality_with_size = self.quality_combobox.get()
        selected_quality = self.streams_map.get(selected_quality_with_size)  # 从映射中获取实际清晰度值
                
        try:
            yt = YouTube(url, on_progress_callback=self.show_progress)
            if selected_quality in ["144p", "240p", "360p", "480p", "720p"]:
                stream = yt.streams.filter(res=selected_quality, file_extension='mp4').first()
                if stream and self.is_downloading:
                    self.root.title("YouTube Downloader - 开始下载普通视频")
                    stream.download(output_path=self.download_path, filename=self.clean_filename(yt.title) + ".mp4")
            elif selected_quality in ["1080p"]:
                # Get the resolution video-only stream
                video_stream = yt.streams.filter(res=selected_quality, mime_type='video/mp4').first()
                # Get the best audio stream
                audio_stream = yt.streams.filter(only_audio=True, mime_type='audio/mp4').first()
                if video_stream and audio_stream and self.is_downloading:
                    self.root.title("YouTube Downloader - 开始下载高清视频")
                    video_filename = video_stream.download(output_path=self.download_path, filename_prefix="video_")
                    audio_filename = audio_stream.download(output_path=self.download_path, filename_prefix="audio_")
                # 合并音视频文件
                output_filename = self.clean_filename(yt.title) + ".mp4"
                output_path = os.path.join(self.download_path, output_filename)
                self.merge_video_and_audio(video_filename, audio_filename, output_path)
                if not self.is_downloading:
                    return
            else:
                print("无此分辨率")
            self.download_caption(yt)
        except PytubeError as e:
            messagebox.showerror("Pytube 错误", f"下载过程中出错: {e}")
        except Exception as e:
            messagebox.showerror("错误", f"下载过程中出错：{str(e)}")

        finally:
            self.is_downloading = False
            self.button_cancel.config(state='disabled')
            # self.root.title("YouTube Downloader")
            self.open_download_folder()
            # 重置下载功能
            self.progress['value'] = 0
            self.progress_label['text'] = "0%"
            self.enable_buttons()  # 重新启用按钮
            self.root.event_generate("<<CloseParsingDialog>>", when="tail")
            # 可选：清空视频标题和清晰度选择
            # self.video_title_label['text'] = ""
            # self.quality_combobox['values'] = []


    def download_caption(self, yt):
        # 获取用户选择的字幕名称
        selected_caption_name = self.caption_combobox.get()
        if selected_caption_name:
            # 从映射中获取语言代码
            selected_caption_language_code = self.caption_lang_map[selected_caption_name]
            caption = yt.captions[selected_caption_language_code]

            if caption:
                xml_captions = caption.xml_captions
                srt_captions = self.xml2srt(xml_captions)
                caption_filename = f"{yt.title} - {selected_caption_language_code}.srt"
                caption_path = os.path.join(self.download_path, self.clean_filename(caption_filename))
                with open(caption_path, "w", encoding='utf-8') as file:
                    file.write(srt_captions)
                messagebox.showinfo("下载", "下载成功。")
            else:
                messagebox.showinfo("下载", "所选字幕不可用。")


    def merge_video_and_audio(self, video_path, audio_path, output_path):
        """
        使用 ffmpeg 合并视频和音频到一个 MP4 文件。
        """
        ffmpeg_path = self.get_ffmpeg_path()  # 获取 ffmpeg 的路径
        cmd = [
            ffmpeg_path,  # 使用获取的 ffmpeg 路径
            '-i', video_path,
            '-i', audio_path,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-strict', 'experimental',
            output_path,
            '-y'
        ]
        try:
            self.root.title(f"YouTube Downloader - 合并视频和音频中……")
            subprocess.run(cmd, check=True)
            os.remove(video_path)  # 删除原始视频文件
            os.remove(audio_path)  # 删除原始音频文件
        except subprocess.CalledProcessError as e:
            messagebox.showerror("合并错误", f"合并视频和音频时出错: {e}")


if __name__ == "__main__":
    style = Style(theme='journal')  # 选择一个主题
    root = style.master  # 获取主窗口
    app = YouTubeDownloader(root)
    root.mainloop()


