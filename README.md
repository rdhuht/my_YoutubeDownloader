# YouTube Downloader (YouTube视频下载器)

## English

### Description
This YouTube Downloader is a Python-based GUI application that allows users to download YouTube videos in various resolutions and optionally with subtitles. It utilizes the `yt-dlp` library for downloading videos and `ffmpeg` for processing videos that require merging separate audio and video streams.

### Features
- Download videos in various resolutions with estimated file size display
- Support for downloading subtitles
- Progress tracking with elapsed time display
- Download cancellation support
- Proxy settings support
- Clipboard URL detection - paste URL on focus/click
- Cross-platform GUI created with `tkinter` and `ttkbootstrap`
- Automatic download folder opening after download completes

### Requirements
- Python 3.x
- ffmpeg (for merging audio and video streams)
- Required Python packages (see requirements.txt)

### Installation
1. Install Python on your system
2. Install ffmpeg:
   - Windows: Download from https://ffmpeg.org/ and add to PATH
   - macOS: `brew install ffmpeg`
   - Linux: `sudo apt install ffmpeg` or your distro's package manager
3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

### Usage
1. Start the application
2. Enter the YouTube video URL in the provided field (or paste from clipboard by clicking the input field)
3. Click "加载视频信息" (Load Video Info) to fetch video details
4. Select the desired video resolution and subtitle language (if needed)
5. Choose the download path by clicking "下载路径" (Download Path)
6. Click "开始下载" (Start Download) to begin downloading
7. Click "取消下载" (Cancel Download) to stop an ongoing download

### Menu
- **设置 (Settings)** > **代理设置 (Proxy Settings)**: Configure proxy server
- **设置 (Settings)** > **关于 (About)**: Application information

### Contributing
Contributions to improve the application or add new features are welcome. Please fork the repository, make your changes, and submit a pull request.

### License
This project is licensed under the MIT License.

### Disclaimer
This tool is for educational and research purposes only, do not use it for any illegal purposes. Downloading videos using this tool may violate YouTube's Terms of Service, use it at your own risk.

---

## 中文

### 描述
这个YouTube视频下载器是一个基于Python的GUI应用程序，允许用户下载各种分辨率的YouTube视频，并可选下载字幕。它使用了`yt-dlp`库来下载视频，以及`ffmpeg`来处理需要合并音频和视频流的视频。

### 功能特点
- 支持下载各种分辨率的视频，并显示预估文件大小
- 支持下载字幕
- 进度跟踪和已用时间显示
- 支持取消下载
- 代理设置功能
- 剪贴板URL检测 - 点击输入框时自动粘贴URL
- 使用`tkinter`和`ttkbootstrap`创建的跨平台GUI
- 下载完成后自动打开下载文件夹

### 系统要求
- Python 3.x
- ffmpeg (用于合并音频和视频流)
- Python依赖包 (见 requirements.txt)

### 安装
1. 在系统上安装Python
2. 安装ffmpeg:
   - Windows: 从 https://ffmpeg.org/ 下载并添加到PATH
   - macOS: `brew install ffmpeg`
   - Linux: `sudo apt install ffmpeg` 或对应发行版的包管理器
3. 安装Python依赖:
```bash
pip install -r requirements.txt
```

### 使用方法
1. 启动应用程序
2. 在输入框中输入YouTube视频URL (或点击输入框从剪贴板粘贴)
3. 点击"加载视频信息"获取视频详情
4. 选择所需的视频分辨率和字幕语言（如需要）
5. 点击"下载路径"选择下载保存位置
6. 点击"开始下载"开始下载视频
7. 点击"取消下载"可停止正在下载的任务

### 菜单
- **设置** > **代理设置**: 配置代理服务器
- **设置** > **关于**: 查看应用程序信息

### 贡献
欢迎贡献以改进应用程序或添加新功能。请fork仓库，进行更改，并提交拉取请求。

### 许可
该项目在MIT许可下授权。

### 警告
本工具仅供学习和研究目的，请勿用于任何非法目的。使用本工具下载视频可能违反YouTube的服务条款，请自行承担相应的法律责任。