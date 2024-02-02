
# YouTube Downloader

## 简介 / Introduction
这是一个使用Python编写的YouTube视频下载器GUI应用程序。它允许用户输入YouTube视频链接，选择视频质量和字幕（如果可用），并下载视频到指定的位置。 / This is a GUI application for downloading YouTube videos written in Python. It allows users to input a YouTube video link, select video quality and captions (if available), and download the video to a specified location.

## 功能 / Features
- 视频信息加载：根据输入的YouTube视频链接加载视频信息。 / Video information loading: Load video information based on the input YouTube video link.
- 视频质量选择：用户可以选择不同的视频质量进行下载。 / Video quality selection: Users can select different video qualities for download.
- 字幕下载：如果视频有字幕，用户可以选择下载字幕。 / Captions download: If the video has captions, users can choose to download the captions.
- 下载路径选择：用户可以指定视频下载的路径。 / Download path selection: Users can specify the path where the video will be downloaded.
- GUI界面：提供图形用户界面，方便用户操作。 / GUI interface: Provides a graphical user interface for easy user operation.

## 依赖 / Dependencies
- Python 3.6+
- tkinter
- ttkbootstrap
- pytube
- BeautifulSoup4

## 安装 / Installation
首先，确保安装了Python 3.6或更高版本。然后，使用pip安装所需的依赖： / First, ensure Python 3.6 or higher is installed. Then, install the required dependencies using pip:
```
pip install pytube ttkbootstrap beautifulsoup4
```

## 使用 / Usage
1. 运行脚本： / Run the script:
```
python youtube_downloader.py
```
2. 输入YouTube视频链接并点击“加载视频信息”按钮。 / Enter the YouTube video link and click the "Load Video Info" button.
3. 选择视频质量和字幕（如果需要）。 / Select video quality and captions (if needed).
4. 选择下载路径（默认为桌面）。 / Choose the download path (default is Desktop).
5. 点击“下载视频”开始下载。 / Click "Download Video" to start downloading.

## 许可 / License
MIT

## 警告 / Disclaimer
本工具仅供学习和研究目的，请勿用于任何非法目的。使用本工具下载视频可能违反YouTube的服务条款，请自行承担相应的法律责任。 / This tool is for educational and research purposes only, do not use it for any illegal purposes. Downloading videos using this tool may violate YouTube's Terms of Service, use it at your own risk.
