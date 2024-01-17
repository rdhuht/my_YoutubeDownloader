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
        # [原有代码省略...]
        self.entry_url.pack(fill='x', expand=True, padx=20)

        # 新增视频清晰度选择下拉菜单
        self.quality_label = ttk.Label(root, text="选择视频清晰度:")
        self.quality_label.pack()
        self.quality_combobox = ttk.Combobox(root, state="readonly")
        self.quality_combobox.pack()
        self.button_load = ttk.Button(root, text="加载视频信息", command=self.load_video)
        self.button_load.pack()

        # [原有代码省略...]

    # 新增加载视频信息的方法
    def load_video(self):
        url = self.entry_url.get()
        yt = YouTube(url)
        streams = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution')
        qualities = [stream.resolution for stream in streams]
        self.quality_combobox['values'] = qualities

    def download_video(self):
        """ 根据用户选择的清晰度下载视频 """
        url = self.entry_url.get()
        path = self.download_path
        selected_quality = self.quality_combobox.get()
        try:
            yt = YouTube(url, on_progress_callback=self.show_progress)
            stream = yt.streams.filter(res=selected_quality, file_extension='mp4').first()
            if stream:
                stream.download(path)
            else:
                messagebox.showerror("错误", "未找到选定的视频清晰度")
        except Exception as e:
            messagebox.showerror("错误", f"下载过程中出错：{e}")
        finally:
            self.root.event_generate("<<CloseParsingDialog>>", when="tail")

    # [其余代码与原先相同...]

if __name__ == "__main__":
    style = Style(theme='journal')
    root = style.master
    app = YouTubeDownloader(root)
    root.mainloop()
