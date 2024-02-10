import tkinter as tk
from tkinter import ttk, messagebox
from ttkbootstrap import Style
from pytube import YouTube, Playlist
import threading

# 初始化界面
style = Style(theme='litera')
root = style.master
root.title("YouTube Downloader")
root.geometry('800x600')

# 定义全局变量
videos = []
video_titles = []
selections = []

# 解析视频信息
def fetch_video_info(url):
    global videos, video_titles
    videos.clear()
    video_titles.clear()
    try:
        if "playlist" in url:
            p = Playlist(url)
            for url in p.video_urls:
                yt = YouTube(url)
                videos.append(yt)
                video_titles.append(yt.title)
        else:
            yt = YouTube(url)
            videos.append(yt)
            video_titles.append(yt.title)
        
        display_videos()
    except Exception as e:
        messagebox.showerror("Error", str(e))

# 显示视频列表
def display_videos():
    video_listbox.delete(0, tk.END)
    for title in video_titles:
        video_listbox.insert(tk.END, title)
    video_listbox.selection_set(0, tk.END)

# 开始下载
def start_download():
    selected_indices = video_listbox.curselection()
    selected_videos = [videos[i] for i in selected_indices]
    if not selected_videos:
        messagebox.showinfo("Info", "No video selected for download.")
        return
    
    threading.Thread(target=download_videos, args=(selected_videos,)).start()

# 下载视频
def download_videos(selected_videos):
    for i, video in enumerate(selected_videos):
        stream = video.streams.get_highest_resolution()
        stream.download()
        update_progress(i + 1, len(selected_videos))

# 更新进度条
def update_progress(current, total):
    progress['value'] = (current / total) * 100
    root.update_idletasks()

# 界面元素
url_entry = ttk.Entry(root, width=60)
url_entry.pack(pady=20)

fetch_button = ttk.Button(root, text="Fetch Video Info", command=lambda: fetch_video_info(url_entry.get()))
fetch_button.pack(pady=10)

video_listbox = tk.Listbox(root, selectmode='extended', width=50, height=15)
video_listbox.pack(pady=20)

download_button = ttk.Button(root, text="Download Selected", command=start_download)
download_button.pack(pady=10)

progress = ttk.Progressbar(root, length=300, mode='determinate')
progress.pack(pady=20)

root.mainloop()
