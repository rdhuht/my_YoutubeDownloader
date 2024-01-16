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



class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader")
        self.root.minsize(width=400, height=200)  # 设置最小尺寸
        self.root.maxsize(width=800, height=200)  # 设置最大尺寸

        # 定义较大的字体
        large_font = tkFont.Font(family="Helvetica", size=12, weight="bold")

        # 设置标签的字体大小
        self.label_url = ttk.Label(root, text="YouTube视频链接:", font=large_font)
        self.label_url.pack(pady=(10, 0))

        self.entry_url = ttk.Entry(root)
        self.entry_url.pack(fill='x', expand=True, padx=20)

        # 创建一个框架来容纳按钮
        self.button_frame = ttk.Frame(root)
        self.button_frame.pack(pady=10)  # 在按钮框架周围添加垂直间距

        # 在框架内添加按钮
        self.button_browse = ttk.Button(self.button_frame, text="选择下载路径", command=self.browse_path)
        self.button_browse.pack(side=tk.LEFT, padx=10)  # 在按钮之间添加水平间距

        self.button_download = ttk.Button(self.button_frame, text="下载视频", command=self.start_download_thread)
        self.button_download.pack(side=tk.LEFT)  # 按钮放置在右侧

        # 设置进度百分比显示的字体大小
        self.progress_label = ttk.Label(root, text="0%", font=large_font)
        self.progress_label.pack()
        
        # 进度条
        self.progress = ttk.Progressbar(root, bootstyle="success-striped", orient='horizontal', mode='determinate')
        self.progress.pack(fill='x', expand=True, padx=20, pady=10)

        self.download_path = ""  # 用于存储下载路径

        self.center_window(self.root)

        # 绑定自定义事件到close_parsing_dialog方法
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


    def download_video(self):
        """ 视频下载方法，包括进度回调和下载完成的处理 """
        url = self.entry_url.get()
        path = self.download_path
        try:
            yt = YouTube(url, on_progress_callback=self.show_progress)
            # video = yt.streams.first()
            video = yt.streams.filter(file_extension='mp4').get_by_itag(22) #22表示720p,137为1080p
            video.download(path)
        except Exception as e:
            messagebox.showerror("错误", f"下载过程中出错：{e}")
        finally:
            # 使用事件来通知主线程关闭解析提示窗口
            self.root.event_generate("<<CloseParsingDialog>>", when="tail")


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

    def enable_buttons(self):
        """ 启用按钮 """
        self.button_download.config(state='normal')
        self.button_browse.config(state='normal')



if __name__ == "__main__":
    style = Style(theme='journal')  # 选择一个主题
    root = style.master  # 获取主窗口
    app = YouTubeDownloader(root)
    root.mainloop()


