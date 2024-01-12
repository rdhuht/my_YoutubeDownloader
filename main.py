import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pytube import YouTube
import threading

class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader")

        # 设置界面元素
        self.label_url = tk.Label(root, text="YouTube视频链接:")
        self.label_url.pack()

        self.entry_url = tk.Entry(root, width=40)
        self.entry_url.pack()

        self.button_browse = tk.Button(root, text="选择下载路径", command=self.browse_path)
        self.button_browse.pack()

        self.button_download = tk.Button(root, text="下载视频", command=self.start_download_thread)
        self.button_download.pack()

        # 添加进度条
        self.progress = ttk.Progressbar(root, orient='horizontal', length=400, mode='determinate')
        self.progress.pack()

        self.download_path = ""  # 用于存储下载路径

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
        self.root.update_idletasks()

    def download_video(self):
        """ 视频下载方法，包括进度回调和下载完成的处理 """
        url = self.entry_url.get()
        path = self.download_path  # 使用用户选择的下载路径
        try:
            yt = YouTube(url, on_progress_callback=self.show_progress)
            video = yt.streams.first()
            video.download(path)
            messagebox.showinfo("下载完成", "视频已成功下载！")
            # 打开下载目录
            os.startfile(path)
        except Exception as e:
            messagebox.showerror("错误", f"下载过程中出错：{e}")
    def start_download_thread(self):
        """ 在新线程中开始下载视频，并重置进度条 """
        self.progress['value'] = 0  # 重置进度条
        download_thread = threading.Thread(target=self.download_video)
        download_thread.start()


if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeDownloader(root)
    root.mainloop()
