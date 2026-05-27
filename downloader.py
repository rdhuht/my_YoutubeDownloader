"""Download logic and video loading functionality."""
import os
import time
from tkinter import messagebox
import yt_dlp as youtube_dl

from config import get_proxy, FFMPEG_AVAILABLE
from utils import estimate_size, get_language_display, get_language_code, subtitle_sort_key
from ffmpeg import FFmpegProgressLogger


def load_video_msg(app):
    url = app.entry_url.get().strip()
    if not url:
        app.root.after(0, lambda: messagebox.showerror("错误", "请输入有效的视频URL。"))
        app.root.after(0, app.enable_buttons)
        app.root.after(0, lambda: app.update_status("就绪"))
        return
    try:
        app.current_url = url
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
        }
        proxy = get_proxy()
        if proxy:
            ydl_opts['proxy'] = proxy

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            entries = info_dict.get('entries', [])
            if entries:
                app.is_playlist = True
                app.root.after(0, lambda d=info_dict: load_playlist_ui(app, d))
            else:
                app.is_playlist = False
                app.root.after(0, lambda d=info_dict: load_single_ui(app, d))

    except Exception as e:
        app.root.after(0, lambda: messagebox.showerror("加载视频错误", f"错误: {e}"))
        app.root.after(0, lambda: app.update_status("加载失败"))
    finally:
        app.root.after(0, app.enable_buttons)


def load_single_ui(app, info_dict):
    title = info_dict.get('title', '视频')
    app.formats = info_dict.get('formats', [])
    app.video_title_label['text'] = f"视频: {title}"

    heights = set()
    for fmt in app.formats:
        if fmt.get('ext') == 'mp4' and fmt.get('height'):
            heights.add(fmt.get('height'))

    app.quality_options = sorted(list(heights), reverse=True)
    app.quality_combobox['values'] = [f"{h}p" for h in app.quality_options]
    if app.quality_options:
        app.quality_combobox.current(0)

    subtitles = info_dict.get('subtitles', {})
    subtitle_list = sorted([get_language_display(k) for k in subtitles.keys()], key=subtitle_sort_key) if subtitles else ['无']
    app.caption_combobox['values'] = subtitle_list
    app.caption_combobox.current(0)

    app.playlist_entries = [info_dict]
    load_treeview(app)

    app.update_status(f"已加载: {title}")


def load_playlist_ui(app, info_dict):
    playlist_title = info_dict.get('title', '播放列表')
    entries = info_dict.get('entries', [])

    app.playlist_entries = [e for e in entries if e is not None]
    app.video_title_label['text'] = f"播放列表: {playlist_title} (共 {len(app.playlist_entries)} 个视频)"

    heights = set()
    for entry in app.playlist_entries:
        if entry and entry.get('formats'):
            for fmt in entry.get('formats', []):
                if fmt.get('ext') == 'mp4' and fmt.get('height'):
                    heights.add(fmt.get('height'))

    app.quality_options = sorted(list(heights), reverse=True) if heights else [1080, 720, 480, 360]
    app.quality_combobox['values'] = [f"{h}p" for h in app.quality_options]
    if app.quality_options:
        app.quality_combobox.current(0)

    subtitles = set()
    for entry in app.playlist_entries:
        if entry and entry.get('subtitles'):
            subtitles.update(entry.get('subtitles', {}).keys())
    subtitle_list = sorted([get_language_display(k) for k in subtitles], key=subtitle_sort_key) if subtitles else ['无']
    app.caption_combobox['values'] = subtitle_list
    app.caption_combobox.current(0)

    load_treeview(app)
    app.update_status(f"已加载播放列表: {playlist_title} ({len(app.playlist_entries)} 个视频)")


def load_treeview(app):
    for item in app.playlist_tree.get_children():
        app.playlist_tree.delete(item)
    app.check_vars.clear()
    app.tree_iid_map.clear()

    quality_text = app.quality_combobox.get()
    selected_height = int(quality_text.replace('p', '')) if quality_text else 1080

    for i, entry in enumerate(app.playlist_entries):
        if entry is None:
            continue

        title = entry.get('title', '未知标题')
        duration = entry.get('duration')
        duration_str = time.strftime("%H:%M:%S", time.gmtime(duration)) if duration else "--:--"

        height = entry.get('height') or selected_height
        duration_val = entry.get('duration') or 300
        size_str = estimate_size(height, duration_val)

        iid = app.playlist_tree.insert('', 'end', values=("√", i + 1, title, duration_str, size_str, "", ""))
        var = app.IntVar(value=1)
        app.check_vars[iid] = var
        app.tree_iid_map[iid] = i

    app.root.after(100, app.on_quality_changed)


def show_progress(app, d):
    if d['status'] == 'downloading':
        downloaded = d.get('downloaded_bytes', 0) or 0
        total = d.get('total_bytes') or d.get('totalbyte') or 0
        if total and total > 0:
            percentage = min(downloaded / total * 100, 100)
            app.update_video_progress_text(app.current_download_index, f"{percentage:.0f}%", 'downloading')
        app.root.update_idletasks()
        if app.download_start_time:
            elapsed_time = time.time() - app.download_start_time
            elapsed_time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
            app.update_status(f"下载中... {elapsed_time_str}")
    elif d['status'] == 'finished' and d.get('postprocessor'):
        app.download_phase = 'converting'
        app.update_video_convert_status(app.current_download_index, "转换中")


def show_playlist_progress(app, d):
    if d['status'] == 'downloading':
        downloaded = d.get('downloaded_bytes', 0) or 0
        total = d.get('total_bytes') or d.get('totalbyte') or 0
        if total and total > 0:
            percentage = min(downloaded / total * 100, 100)
            app.update_video_progress_text(app.current_download_index, f"{percentage:.0f}%", 'downloading')
        app.root.update_idletasks()
        if app.download_start_time:
            elapsed_time = time.time() - app.download_start_time
            elapsed_time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
            app.update_status(f"视频 {app.current_playlist_index}/{app.total_playlist_videos} 下载中... {elapsed_time_str}")
    elif d['status'] == 'finished' and d.get('postprocessor'):
        app.download_phase = 'converting'
        app.update_video_convert_status(app.current_download_index, "转换中")


def download_single(app, entry):
    quality_text = app.quality_combobox.get()
    if not quality_text:
        app.root.after(0, lambda: messagebox.showerror("错误", "请选择视频质量。"))
        app.root.after(0, app.enable_buttons)
        return

    height = int(quality_text.replace('p', ''))
    format_str = f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={height}]+bestaudio/best'

    app.is_downloading = True
    app.download_start_time = time.time()
    app.download_phase = 'downloading'
    app.root.after(0, lambda: app.button_cancel.config(state='normal'))

    video_url = entry.get('url') or entry.get('webpage_url')
    if not video_url:
        app.root.after(0, lambda: messagebox.showerror("错误", "无法获取视频URL。"))
        app.root.after(0, app.enable_buttons)
        return

    entry_index = app.playlist_entries.index(entry)
    app.current_download_index = entry_index

    output_format = app.format_combobox.get()
    use_converter = output_format != '不转换' and FFMPEG_AVAILABLE

    ydl_opts = {
        'format': format_str,
        'outtmpl': os.path.join(app.download_path, '%(title)s.%(ext)s'),
        'progress_hooks': [lambda d: show_progress(app, d)],
    }

    proxy = get_proxy()
    if proxy:
        ydl_opts['proxy'] = proxy

    if use_converter:
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': output_format,
        }]
        ydl_opts['logger'] = FFmpegProgressLogger(app, is_playlist=False, entry_index=entry_index)

    selected_subtitle = app.caption_combobox.get()
    if selected_subtitle and selected_subtitle != '无':
        lang_code = get_language_code(selected_subtitle)
        if lang_code == 'zh':
            lang_code = 'zh-Hans'
        if lang_code in ['zh-Hans', 'zh-CN', 'zh']:
            ydl_opts['subtitleslangs'] = ['zh-Hans', 'zh-CN', 'zh']
        else:
            ydl_opts['subtitleslangs'] = [lang_code]
        ydl_opts['writesubtitles'] = True
        ydl_opts['subtitlesformat'] = 'srt'

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        elapsed_time = time.time() - app.download_start_time
        elapsed_time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
        app.set_video_result(entry_index, True)
        app.update_video_convert_status(entry_index, "完成" if use_converter else "")
        app.update_status(f"下载完成! 耗时: {elapsed_time_str}")
        app.root.after(0, lambda: messagebox.showinfo("下载完成", "视频已成功下载。"))
        app.root.after(0, app.open_download_folder)
    except Exception as e:
        app.set_video_result(entry_index, False)
        app.update_video_convert_status(entry_index, "")
        app.root.after(0, lambda: messagebox.showerror("下载错误", f"错误: {e}"))
        app.update_status("下载失败")
    finally:
        app.is_downloading = False
        app.root.after(0, app.enable_buttons)
        app.download_start_time = None
        app.current_download_index = None
        app.root.after(0, lambda: app.button_cancel.config(state='disabled'))


def download_multi(app, selected_entries):
    quality_text = app.quality_combobox.get()
    if not quality_text:
        app.root.after(0, lambda: messagebox.showerror("错误", "请选择视频质量。"))
        app.root.after(0, app.enable_buttons)
        return

    height = int(quality_text.replace('p', ''))
    format_str = f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<={height}]+bestaudio/best'

    app.is_downloading = True
    app.download_start_time = time.time()
    app.root.after(0, lambda: app.button_cancel.config(state='normal'))

    app.total_playlist_videos = len(selected_entries)
    app.current_playlist_index = 0
    success_count = 0
    fail_count = 0

    selected_subtitle = app.caption_combobox.get()
    output_format = app.format_combobox.get()
    use_converter = output_format != '不转换' and FFMPEG_AVAILABLE

    proxy = get_proxy()

    for i, entry in enumerate(selected_entries):
        if not app.is_downloading:
            break

        app.current_playlist_index = i + 1
        video_url = entry.get('url') or entry.get('webpage_url')
        if not video_url:
            fail_count += 1
            continue

        entry_index = app.playlist_entries.index(entry) if entry in app.playlist_entries else i
        app.current_download_index = entry_index

        app.update_status(f"下载第 {i+1}/{app.total_playlist_videos} 个视频...")

        ydl_opts = {
            'format': format_str,
            'outtmpl': os.path.join(app.download_path, '%(title)s.%(ext)s'),
            'progress_hooks': [lambda d: show_playlist_progress(app, d)],
        }

        if proxy:
            ydl_opts['proxy'] = proxy

        if use_converter:
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }]
            ydl_opts['logger'] = FFmpegProgressLogger(app, is_playlist=True, entry_index=entry_index)

        if selected_subtitle and selected_subtitle != '无':
            lang_code = get_language_code(selected_subtitle)
            if lang_code == 'zh':
                lang_code = 'zh-Hans'
            if lang_code in ['zh-Hans', 'zh-CN', 'zh']:
                ydl_opts['subtitleslangs'] = ['zh-Hans', 'zh-CN', 'zh']
            else:
                ydl_opts['subtitleslangs'] = [lang_code]
            ydl_opts['writesubtitles'] = True
            ydl_opts['subtitlesformat'] = 'srt'

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            success_count += 1
            app.set_video_result(entry_index, True)
            app.update_video_convert_status(entry_index, "完成" if use_converter else "")
        except Exception as e:
            fail_count += 1
            app.set_video_result(entry_index, False)
            app.update_video_convert_status(entry_index, "")
            print(f"下载失败: {entry.get('title', '未知')} - {e}")

    elapsed_time = time.time() - app.download_start_time
    elapsed_time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
    app.update_status(f"批量下载完成! 成功: {success_count}, 失败: {fail_count}")
    app.root.after(0, lambda: messagebox.showinfo("下载完成", f"成功: {success_count} 个, 失败: {fail_count} 个"))
    app.root.after(0, app.open_download_folder)

    app.is_downloading = False
    app.root.after(0, app.enable_buttons)
    app.download_start_time = None
    app.current_download_index = None
    app.root.after(0, lambda: app.button_cancel.config(state='disabled'))