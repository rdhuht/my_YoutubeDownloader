from pytube import YouTube
import tkinter as tk
from tkinter import ttk

class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader")
        self.create_widgets()

    def create_widgets(self):
        self.link_label = ttk.Label(self.root, text="YouTube link:")
        self.link_label.pack()
        self.link_entry = ttk.Entry(self.root, width=60)
        self.link_entry.pack()
        self.load_button = ttk.Button(self.root, text="Load Video", command=self.load_video)
        self.load_button.pack()
        self.quality_label = ttk.Label(self.root, text="Select Quality:")
        self.quality_label.pack()
        self.quality_combobox = ttk.Combobox(self.root, state="readonly")
        self.quality_combobox.pack()
        self.download_button = ttk.Button(self.root, text="Download", command=self.download_video)
        self.download_button.pack()

    def load_video(self):
        url = self.link_entry.get()
        yt = YouTube(url)
        streams = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution')
        qualities = [stream.resolution for stream in streams]
        self.quality_combobox['values'] = qualities

    def download_video(self):
        selected_quality = self.quality_combobox.get()
        url = self.link_entry.get()
        yt = YouTube(url)
        stream = yt.streams.filter(resolution=selected_quality, file_extension='mp4').first()
        stream.download()  # You can specify a download path here

root = tk.Tk()
app = YouTubeDownloader(root)
root.mainloop()
from pytube import YouTube
import tkinter as tk
from tkinter import ttk

class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader")
        self.create_widgets()

    def create_widgets(self):
        self.link_label = ttk.Label(self.root, text="YouTube link:")
        self.link_label.pack()
        self.link_entry = ttk.Entry(self.root, width=60)
        self.link_entry.pack()
        self.load_button = ttk.Button(self.root, text="Load Video", command=self.load_video)
        self.load_button.pack()
        self.quality_label = ttk.Label(self.root, text="Select Quality:")
        self.quality_label.pack()
        self.quality_combobox = ttk.Combobox(self.root, state="readonly")
        self.quality_combobox.pack()
        self.download_button = ttk.Button(self.root, text="Download", command=self.download_video)
        self.download_button.pack()

    def load_video(self):
        url = self.link_entry.get()
        yt = YouTube(url)
        streams = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution')
        qualities = [stream.resolution for stream in streams]
        self.quality_combobox['values'] = qualities

    def download_video(self):
        selected_quality = self.quality_combobox.get()
        url = self.link_entry.get()
        yt = YouTube(url)
        stream = yt.streams.filter(resolution=selected_quality, file_extension='mp4').first()
        stream.download()  # You can specify a download path here

root = tk.Tk()
app = YouTubeDownloader(root)
root.mainloop()
