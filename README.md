# YouTube Downloader

## 概述 Overview

这是一个用于下载YouTube视频的桌面应用程序，允许用户选择视频质量和字幕（如果可用）。它提供了一个基于`tkinter`和`ttkbootstrap`构建的图形用户界面（GUI），使非技术专业人士也能轻松使用。

This application is a desktop utility for downloading YouTube videos, allowing users to select video quality and subtitles (if available). It provides a graphical user interface (GUI) built with `tkinter` and `ttkbootstrap`, making it user-friendly and accessible to individuals without technical expertise.

### 特点 Features

- **视频链接输入 Video Link Input**: 用户可以粘贴YouTube视频链接进行下载。
- **加载视频信息 Video Information Loading**: 获取并显示视频标题、可用质量和字幕。
- **下载路径选择 Download Path Selection**: 允许用户选择视频和字幕将被保存的目录。
- **进度指示 Progress Indication**: 通过进度条和百分比显示下载进度。
- **字幕下载 Subtitles Download**: 支持下载SRT格式的字幕，从原始XML转换而来，使用BeautifulSoup进行解析。

### 系统要求 Requirements

确保您的系统已安装Python（推荐使用Python 3.6或更新版本）。以下包在`requirements.txt`中列出并需要安装：

Ensure you have Python installed on your system (Python 3.6 or newer is recommended). The following packages are required and listed in `requirements.txt`:

- `altgraph==0.17.4`
- `beautifulsoup4==4.12.3`
- `bs4==0.0.2`
- `lxml==5.1.0`
- `macholib==1.16.3`
- `packaging==23.2`
- `pillow==10.2.0`
- `pyinstaller-hooks-contrib==2024.0`
- `pytube==15.0.0`
- `setuptools==69.0.3`
- `soupsieve==2.5`
- `ttkbootstrap==1.10.1`

### 安装 Installation

1. 克隆此仓库或下载源代码。
2. 导航到包含应用程序的目录。
3. 使用pip安装所需的包：

   ```
   pip install -r requirements.txt
   ```

### 运行应用程序 Running the Application

要运行应用程序，请导航到包含`YouTubeDownloader.py`的目录，并在终端中执行以下命令：

```
python YouTubeDownloader.py
```

应用程序窗口将打开，您可以开始通过输入YouTube链接、选择所需的视频质量和字幕（如需要），并指定下载位置来下载视频。

### 使用指南 Usage Guide

1. **输入YouTube视频链接 Enter YouTube Video Link**: 在提供的字段中粘贴链接。
2. **加载视频信息 Load Video Information**: 点击“加载视频信息”以获取视频详细信息。
3. **选择质量和字幕 Select Quality and Subtitles**: 从下拉菜单中选择所需的视频质量和字幕。
4. **选择下载路径 Choose Download Path**: 点击“选择下载路径”并选择一个文件夹。
5. **下载视频 Download Video**: 点击“下载视频”开始下载过程。

### 注意 Note

此应用程序旨在供个人使用和教育目的，请在使用此工具时尊重版权法和YouTube的服务条款。
