"""Download logic and video loading functionality."""
import os
import time
import tkinter as tk
from tkinter import messagebox
import yt_dlp as youtube_dl

from config import get_proxy, FFMPEG_AVAILABLE
from utils import estimate_size, get_language_display, get_language_code, subtitle_sort_key
from ffmpeg import FFmpegProgressLogger


# yt-dlp 2025/2026 no longer reliably downloads 1080p+ YouTube videos via the
# default `web`/`ios`/`android` clients because they now require a PO Token.
# Pin to the TV / Web Safari / Mobile-Web clients which still serve anonymous
# streams, and skip the (now broken) player config fetch.
YOUTUBE_EXTRACTOR_ARGS = {
    'youtube': {
        'player_client': ['tv', 'web_safari', 'mweb'],
        'player_skip': ['configs', 'translated_subs'],
    }
}

# Stable, well-supported format sort: prefer lower resolution (we already cap
# by height), prefer mp4/m4a wrappers, then smaller filesize, then bitrate.
FORMAT_SORT = ['res', 'ext:mp4:m4a', 'size', 'br']

# Output formats that can be reached by stream-copy remux (no transcode).
REMUX_FRIENDLY = {'mp4', 'mkv', 'webm'}


def _build_ydl_opts(app, *, for_download, output_format, height,
                    selected_subtitle, progress_hook_fn=None, logger=None):
    """Build the ydl_opts dict shared by parse, single, and batch downloads."""
    opts = {
        'quiet': True,
        'noprogress': True,
        'extractor_args': dict(YOUTUBE_EXTRACTOR_ARGS),
        'format_sort': list(FORMAT_SORT),
        # Height-bounded bestvideo+bestaudio with a combined "best" fallback.
        # Drop the strict `ext=mp4`/`ext=m4a` filter — YouTube frequently only
        # offers webm/opus at the chosen resolution.
        'format': f'bestvideo[height<={height}]+bestaudio/best[height<={height}]',
    }

    proxy = get_proxy()
    if proxy:
        opts['proxy'] = proxy

    if not for_download:
        opts['skip_download'] = True
        return opts

    opts['outtmpl'] = os.path.join(app.download_path, '%(title)s.%(ext)s')

    if progress_hook_fn:
        opts['progress_hooks'] = [progress_hook_fn]

    # Output container selection. `merge_output_format` is the canonical key
    # as of yt-dlp 2025.06.09 — the old `preferedformat` typo on
    # FFmpegVideoConvertor is deprecated.
    if output_format and output_format != '不转换' and FFMPEG_AVAILABLE:
        opts['merge_output_format'] = output_format
        if output_format in REMUX_FRIENDLY:
            # Stream-copy remux — fast, lossless.
            opts['postprocessors'] = [{
                'key': 'FFmpegVideoRemuxer',
                'preferedformat': output_format,
            }]
        else:
            # avi (and any non-remux target) requires a real transcode.
            opts['postprocessors'] = [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': output_format,
            }]
        if logger is not None:
            opts['logger'] = logger

    if selected_subtitle and selected_subtitle != '无':
        lang_code = get_language_code(selected_subtitle)
        if lang_code == 'zh':
            lang_code = 'zh-Hans'
        if lang_code in ('zh-Hans', 'zh-CN', 'zh'):
            opts['subtitleslangs'] = ['zh-Hans', 'zh-CN', 'zh']
        else:
            opts['subtitleslangs'] = [lang_code]
        opts['writesubtitles'] = True
        opts['subtitlesformat'] = 'srt'

    return opts


def load_video_msg(app):
    url = app.entry_url.get().strip()
    if not url:
        app.root.after(0, lambda: messagebox.showerror("错误", "请输入有效的视频URL。"))
        app.root.after(0, app.enable_buttons)
        app.root.after(0, lambda: app.update_status("就绪"))
        return
    try:
        app.current_url = url
        # Parse-only; default quality is a placeholder — we don't actually
        # restrict formats here, only at download time.
        ydl_opts = _build_ydl_opts(
            app, for_download=False, output_format=None, height=1080,
            selected_subtitle=None,
        )

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
        var = tk.IntVar(value=1)
        app.check_vars[iid] = var
        app.tree_iid_map[iid] = i

    app.root.after(100, app.on_quality_changed)


def show_progress(app, d):
    # Belt-and-braces: if the user pressed cancel, abort from inside the hook.
    if app.cancel_event.is_set():
        raise Exception("Download cancelled")
    if d['status'] == 'downloading':
        downloaded = d.get('downloaded_bytes', 0) or 0
        total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
        if total and total > 0:
            percentage = min(downloaded / total * 100, 100)
            app.update_video_progress_text(app.current_download_index, f"{percentage:.0f}%", 'downloading')
        if app.download_start_time:
            elapsed_time = time.time() - app.download_start_time
            elapsed_time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
            speed = d.get('speed')
            eta = d.get('eta')
            speed_str = f" {speed/1024/1024:.1f}MB/s" if speed else ""
            eta_str = f" ETA {int(eta)}s" if eta is not None else ""
            app.update_status(f"下载中... {elapsed_time_str}{speed_str}{eta_str}")
    elif d['status'] == 'finished' and d.get('postprocessor'):
        app.download_phase = 'converting'
        app.update_video_convert_status(app.current_download_index, "转换中")


def show_playlist_progress(app, d):
    if app.cancel_event.is_set():
        raise Exception("Download cancelled")
    if d['status'] == 'downloading':
        downloaded = d.get('downloaded_bytes', 0) or 0
        total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
        if total and total > 0:
            percentage = min(downloaded / total * 100, 100)
            app.update_video_progress_text(app.current_download_index, f"{percentage:.0f}%", 'downloading')
        if app.download_start_time:
            elapsed_time = time.time() - app.download_start_time
            elapsed_time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
            speed = d.get('speed')
            eta = d.get('eta')
            speed_str = f" {speed/1024/1024:.1f}MB/s" if speed else ""
            eta_str = f" ETA {int(eta)}s" if eta is not None else ""
            app.update_status(
                f"视频 {app.current_playlist_index}/{app.total_playlist_videos} 下载中... "
                f"{elapsed_time_str}{speed_str}{eta_str}"
            )
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
    output_format = app.format_combobox.get()
    selected_subtitle = app.caption_combobox.get()

    app.cancel_event.clear()
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

    ydl_opts = _build_ydl_opts(
        app, for_download=True, output_format=output_format, height=height,
        selected_subtitle=selected_subtitle,
        progress_hook_fn=lambda d: show_progress(app, d),
        logger=FFmpegProgressLogger(
            app, is_playlist=False, entry_index=entry_index,
            video_duration=entry.get('duration'),
        ),
    )

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            app._active_ydl = ydl
            try:
                if app.cancel_event.is_set():
                    return
                ydl.download([video_url])
            finally:
                app._active_ydl = None
        elapsed_time = time.time() - app.download_start_time
        elapsed_time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
        app.set_video_result(entry_index, True)
        app.update_video_convert_status(entry_index, "完成" if output_format != '不转换' else "")
        app.update_status(f"下载完成! 耗时: {elapsed_time_str}")
        app.root.after(0, lambda: messagebox.showinfo("下载完成", "视频已成功下载。"))
        app.root.after(0, app.open_download_folder)
    except Exception as e:
        app.set_video_result(entry_index, False)
        app.update_video_convert_status(entry_index, "")
        if app.cancel_event.is_set():
            app.update_status("下载已取消")
            app.root.after(0, lambda: messagebox.showinfo("已取消", "下载已取消。"))
        else:
            app.root.after(0, lambda: messagebox.showerror("下载错误", f"错误: {e}"))
            app.update_status("下载失败")
    finally:
        app.download_start_time = None
        app.current_download_index = None
        app.root.after(0, lambda: app.button_cancel.config(state='disabled'))
        app.root.after(0, app.enable_buttons)


def download_multi(app, selected_entries):
    quality_text = app.quality_combobox.get()
    if not quality_text:
        app.root.after(0, lambda: messagebox.showerror("错误", "请选择视频质量。"))
        app.root.after(0, app.enable_buttons)
        return

    height = int(quality_text.replace('p', ''))
    output_format = app.format_combobox.get()
    selected_subtitle = app.caption_combobox.get()

    app.cancel_event.clear()
    app.download_start_time = time.time()
    app.root.after(0, lambda: app.button_cancel.config(state='normal'))

    app.total_playlist_videos = len(selected_entries)
    app.current_playlist_index = 0
    success_count = 0
    fail_count = 0

    for i, entry in enumerate(selected_entries):
        if app.cancel_event.is_set():
            break

        app.current_playlist_index = i + 1
        video_url = entry.get('url') or entry.get('webpage_url')
        if not video_url:
            fail_count += 1
            continue

        entry_index = app.playlist_entries.index(entry) if entry in app.playlist_entries else i
        app.current_download_index = entry_index
        app.update_status(f"下载第 {i+1}/{app.total_playlist_videos} 个视频...")

        ydl_opts = _build_ydl_opts(
            app, for_download=True, output_format=output_format, height=height,
            selected_subtitle=selected_subtitle,
            progress_hook_fn=lambda d: show_playlist_progress(app, d),
            logger=FFmpegProgressLogger(
                app, is_playlist=True, entry_index=entry_index,
                video_duration=entry.get('duration'),
            ),
        )

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                app._active_ydl = ydl
                try:
                    if app.cancel_event.is_set():
                        break
                    ydl.download([video_url])
                finally:
                    app._active_ydl = None
            success_count += 1
            app.set_video_result(entry_index, True)
            app.update_video_convert_status(entry_index, "完成" if output_format != '不转换' else "")
        except Exception as e:
            fail_count += 1
            app.set_video_result(entry_index, False)
            app.update_video_convert_status(entry_index, "")
            print(f"下载失败: {entry.get('title', '未知')} - {e}")

    elapsed_time = time.time() - app.download_start_time
    elapsed_time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
    cancelled = app.cancel_event.is_set()
    app.update_status(
        "已取消" if cancelled
        else f"批量下载完成! 成功: {success_count}, 失败: {fail_count}"
    )
    app.root.after(0, lambda: messagebox.showinfo(
        "已取消" if cancelled else "下载完成",
        "下载已取消" if cancelled else f"成功: {success_count} 个, 失败: {fail_count} 个",
    ))
    if not cancelled:
        app.root.after(0, app.open_download_folder)

    app.download_start_time = None
    app.current_download_index = None
    app.root.after(0, app.enable_buttons)
    app.root.after(0, lambda: app.button_cancel.config(state='disabled'))