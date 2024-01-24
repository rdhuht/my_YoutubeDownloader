import os
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


class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader")
        self.root.minsize(width=600, height=350)  # 减少窗口的最小高度以使布局更紧凑

        # 定义字体
        large_font = tkFont.Font(family="Helvetica", size=26, weight="bold")
        middle_font = tkFont.Font(family="Helvetica", size=20, weight="bold")
        small_font = tkFont.Font(family="Helvetica", size=10)

        # 视频链接输入框
        self.label_url = ttk.Label(root, text="YouTube视频链接:", font=large_font)
        self.label_url.pack(pady=(10))
        self.entry_url = ttk.Entry(root)
        self.entry_url.pack(fill='x', expand=True, padx=20, pady=(2, 10))

        # 加载视频信息按钮
        self.button_load = ttk.Button(root, text="加载视频信息", command=self.load_video, bootstyle='success')
        self.button_load.pack(pady=(0, 5))

        # 显示视频标题
        self.video_title_label = ttk.Label(root, text="", font=small_font)
        self.video_title_label.pack(pady=(5, 5))

        # 视频清晰度和字幕选择框架
        self.quality_frame = ttk.Frame(root)
        self.quality_frame.pack(pady=(0, 5))
        self.quality_label = ttk.Label(self.quality_frame, text="清晰度:", font=middle_font)
        self.quality_label.pack(side=tk.LEFT, padx=(10, 2))
        self.quality_combobox = ttk.Combobox(self.quality_frame, state="readonly", width=15)
        self.quality_combobox.pack(side=tk.LEFT, padx=(2, 10))
        self.caption_label = ttk.Label(self.quality_frame, text="字幕:", font=middle_font)
        self.caption_label.pack(side=tk.LEFT, padx=(10, 2))
        self.caption_combobox = ttk.Combobox(self.quality_frame, state="readonly", width=25)
        self.caption_combobox.pack(side=tk.LEFT, padx=(2, 10))

        # 下载路径选择和开始下载按钮
        self.button_frame = ttk.Frame(root)
        self.button_frame.pack(pady=(0, 5))
        self.button_browse = ttk.Button(self.button_frame, text="选择下载路径", command=self.browse_path, bootstyle='info')
        self.button_browse.pack(side=tk.LEFT, padx=(10, 5))
        self.button_download = ttk.Button(self.button_frame, text="下载视频", command=self.start_download_thread, bootstyle='danger')
        self.button_download.pack(side=tk.LEFT, padx=(5, 10))

        # 进度条和进度百分比
        self.progress_label = ttk.Label(root, text="0%", font=middle_font)
        self.progress_label.pack(pady=(5, 2))
        self.progress = ttk.Progressbar(root, bootstyle="success-striped", orient='horizontal', mode='determinate')
        self.progress.pack(fill='x', expand=True, padx=20, pady=(2, 10))

        self.download_path = ""  # 用于存储下载路径

        self.center_window(self.root)
        self.root.bind("<<CloseParsingDialog>>", lambda e: self.close_parsing_dialog())


    def center_window(self, window):
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
        x = (window.winfo_screenwidth() // 2) - (width // 2)
        y = (window.winfo_screenheight() // 2) - (height // 2)
        window.geometry(f'+{x}+{y}')


    def browse_path(self):
        """ 弹出一个对话框，让用户选择下载路径 """
        self.download_path = filedialog.askdirectory()
        if self.download_path:
            messagebox.showinfo("路径选择", f"下载路径已选择：{self.download_path}")

    def show_progress(self, stream, chunk, bytes_remaining):
        """ 更新下载进度 """
        total_size = stream.filesize
        bytes_downloaded = total_size - bytes_remaining
        percentage_of_completion = bytes_downloaded / total_size * 100
        self.progress['value'] = percentage_of_completion
        self.progress_label['text'] = f"{percentage_of_completion:.2f}%"  # 更新百分比标签
        self.root.update_idletasks()


    def load_video(self):
        """加载视频信息并显示视频标题及可用字幕列表"""
        url = self.entry_url.get()
        try:
            yt = YouTube(url)
            self.video_title_label['text'] = yt.title  # 显示视频标题

            # 更新清晰度选项
            streams = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution')
            qualities = [stream.resolution for stream in streams]
            self.quality_combobox['values'] = qualities

            # 获取并展示可用字幕列表
            captions = yt.captions
            # 创建一个映射字典，用于存储语言名称到代码的映射
            self.caption_lang_map = {caption.name: caption.code for caption in captions.all()}
            # 更新下拉菜单，显示语言名称
            self.caption_combobox['values'] = list(self.caption_lang_map.keys())
        except Exception as e:
            messagebox.showerror("错误", f"加载视频时出错：{e}")




    def xml2srt(self, text):
        soup = BeautifulSoup(text, 'html.parser')  # 确保使用 'html.parser' 作为解析器
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


    def download_video(self):
        """根据用户选择的清晰度下载视频，并下载字幕（如果可用）"""
        url = self.entry_url.get()
        path = self.download_path
        selected_quality = self.quality_combobox.get()

        try:
            yt = YouTube(url, on_progress_callback=self.show_progress)
            stream = yt.streams.filter(res=selected_quality, file_extension='mp4').first()
            if stream:
                stream.download(output_path=path, filename=yt.title + ".mp4")

                # 获取用户选择的字幕名称
                selected_caption_name = self.caption_combobox.get()
                if selected_caption_name:
                    # 从映射中获取语言代码
                    selected_caption_language_code = self.caption_lang_map[selected_caption_name]
                    caption = yt.captions.get_by_language_code(selected_caption_language_code)
                    if caption:
                        xml_captions = caption.xml_captions
                        srt_captions = self.xml2srt(xml_captions)
                        caption_filename = f"{yt.title} - {selected_caption_language_code}.srt"
                        caption_path = os.path.join(path, caption_filename)
                        with open(caption_path, "w", encoding='utf-8') as file:
                            file.write(srt_captions)
                        messagebox.showinfo("字幕下载", "字幕下载成功。")
                    else:
                        messagebox.showinfo("字幕下载", "所选字幕不可用。")
            else:
                messagebox.showerror("错误", "未找到选定的视频清晰度")
        except Exception as e:
            messagebox.showerror("错误", f"下载过程中出错：{str(e)}")

        finally:
            self.root.event_generate("<<CloseParsingDialog>>", when="tail")
            # 下载完成后打开下载文件夹
            self.open_download_folder()
            # 重置下载功能
            self.progress['value'] = 0
            self.progress_label['text'] = "0%"
            self.enable_buttons()  # 重新启用按钮
            self.root.event_generate("<<CloseParsingDialog>>", when="tail")
            self.open_download_folder()
            # 可选：清空视频标题和清晰度选择
            self.video_title_label['text'] = ""
            self.quality_combobox['values'] = []


    def start_download_thread(self):
        """ 在新线程中开始下载视频，并重置进度条 """
        self.progress['value'] = 0
        self.disable_buttons()  # 禁用按钮
        self.parsing_dialog = self.show_parsing_dialog()  # 显示解析提示
        threading.Thread(target=self.download_video).start()


    def show_parsing_dialog(self):
        """ 显示一个持续的解析提示 """
        dialog = tk.Toplevel(self.root)
        dialog.title("提示")
        tk.Label(dialog, text="正在解析中，开始下载后可关闭此弹窗。").pack(pady=10)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.update_idletasks()  # 更新窗口任务，以便获取尺寸信息
        self.center_window(dialog)  # 将窗口居中
        return dialog
    
    def close_parsing_dialog(self):
        """ 关闭解析提示窗口 """
        if self.parsing_dialog:
            self.parsing_dialog.destroy()
            self.parsing_dialog = None


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
            # 根据操作系统的不同选择不同的命令
            if os.name == 'nt':  # 对于Windows
                subprocess.Popen(['explorer', self.download_path])
            elif os.name == 'posix':  # 对于macOS, Linux
                subprocess.Popen(['open', self.download_path])


if __name__ == "__main__":
    style = Style(theme='journal')  # 选择一个主题
    root = style.master  # 获取主窗口
    app = YouTubeDownloader(root)
    root.mainloop()


