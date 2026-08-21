"""Download logic and video loading functionality."""
import os
import time
import tkinter as tk
from tkinter import messagebox
import yt_dlp as youtube_dl

from config import get_proxy, get_cookiefile, FFMPEG_AVAILABLE, JS_RUNTIME
from utils import estimate_size, get_language_display, get_language_code, subtitle_sort_key
from ffmpeg import FFmpegProgressLogger, CollectingLogger


# yt-dlp 2025/2026 YouTube extractor notes:
# - YouTube has been running a SABR-only streaming experiment on anonymous
#   clients since 2026 (#12482); all HTTPS progressive streams are dropped
#   on `web`/`ios`/`web_safari`/`mweb`/`tv_simply` and `tv` may be DRM-only
#   (#12563). Anonymous downloads are typically capped at 360p.
# - `player_skip` was removed from the public extractor_args API in nightly
#   builds; the YouTube extractor picks its own precondition checks now.
# - The `mediaconnect` / `*_creator` / `*_music` clients still return the
#   legacy HTTPS formats during the SABR experiment, so we list them as
#   fallbacks. To get above 360p the user must provide login cookies (see
#   the cookies selection in the Settings menu).
# - For non-SABR sessions the first three clients (`tv`, `web`, `ios`) are
#   sufficient and avoid `web_safari`'s broken-by-default HLS path.
YOUTUBE_EXTRACTOR_ARGS = {
    'youtube': {
        # mweb is the only client that consistently returns real progressive
        # HTTPS formats after the 2026.08.17 SABR/HTTPS 403 change. web and
        # tv now hit the "page needs to be reloaded" gate; android returns
        # only the broken itag=18 stub. The 7897 proxy + bgutil POT provider
        # is what makes mweb formats actually downloadable.
        'player_client': ['mweb', 'web_safari', 'web', 'tv', 'ios'],
    },
    'youtubepot-bgutilhttp': {
        # List values are required by the plugin's _configuration_arg
        # helper. The default 127.0.0.1:4416 matches `bgutil-ytdlp-pot-provider`'s
        # server default. Override in the GUI Settings menu if the server runs
        # on another host/port.
        'base_url': ['http://127.0.0.1:4416'],
    },
}


def _resolve_log_path(app):
    """Return the absolute path where the failure log should be written for
    this app instance. Prefers the user's configured download folder.
    """
    import os
    base = getattr(app, 'download_path', None)
    if not base or not os.path.isdir(str(base)):
        base = os.path.join(os.path.expanduser('~'), 'Downloads')
        if not os.path.isdir(base):
            base = os.path.expanduser('~')
    return os.path.join(base, 'last_download_log.txt')

# Stable, well-supported format sort: prefer lower resolution (we already cap
# by height), prefer mp4/m4a wrappers, then smaller filesize, then bitrate.
FORMAT_SORT = ['res', 'ext:mp4:m4a', 'size', 'br']

# Output formats that can be reached by stream-copy remux (no transcode).
REMUX_FRIENDLY = {'mp4', 'mkv', 'webm'}


def _build_ydl_opts(app, *, for_download, output_format, height,
                    selected_subtitle, progress_hook_fn=None, logger=None):
    """Build the ydl_opts dict shared by parse, single, and batch downloads."""
    # Always install a collecting logger so we can show the user the actual
    # yt-dlp output when a download fails.
    collector = CollectingLogger()

    opts = {
        'quiet': True,
        'noprogress': True,
        'extractor_args': dict(YOUTUBE_EXTRACTOR_ARGS),
        'format_sort': list(FORMAT_SORT),
        # Use the GVS (split-stream) path so the bgutil PO Token actually
        # matters: itag=18 is a progressive URL that YouTube serves (or
        # doesn't) directly. For split streams, yt-dlp's GVS path calls
        # the POT provider, which is the only way the SABR-gated 1080p
        # streams currently work. mweb's HLS/dash formats survive the
        # SABR experiment when accompanied by a valid GVS token. We
        # fall back to the progressive `best[height<=N]` only as a
        # last resort, which yields 360p at most.
        'format': (
            f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/'
            f'bestvideo[height<={height}]+bestaudio/'
            f'best[height<={height}][ext=mp4]/'
            f'best[height<={height}]'
        ),
        'format_sort': ['res', 'ext:mp4:m4a', 'proto:https', 'size', 'br'],
        # Give the extractor a couple of tries — YouTube occasionally serves
        # a transient "page needs to be reloaded" response that a retry
        # resolves. The 60s socket_timeout tolerates slow proxy links
        # (e.g. 127.0.0.1:7897 during heavy traffic).
        'extractor_retries': 5,
        'retries': 5,
        'socket_timeout': 60,
        # YouTube's `n` challenge requires a JS runtime. yt-dlp only enables
        # deno by default; on Windows deno is rarely installed, so explicitly
        # try node first (the most common runtime on Windows). Without a
        # working JS runtime the SABR-experiment fallback formats may all be
        # filtered out, surfacing as "The page needs to be reloaded".
    }
    if JS_RUNTIME:
        opts['js_runtimes'] = {JS_RUNTIME: {}}

    proxy = get_proxy()
    if proxy:
        opts['proxy'] = proxy

    cookiefile = get_cookiefile()
    if cookiefile:
        opts['cookiefile'] = cookiefile

    if not for_download:
        opts['skip_download'] = True
        opts['logger'] = collector
        return opts, collector

    opts['outtmpl'] = os.path.join(app.download_path, '%(title)s.%(ext)s')

    if progress_hook_fn:
        opts['progress_hooks'] = [progress_hook_fn]

    # The FFmpegProgressLogger (when supplied) is given the collector so it
    # can forward its own non-debug messages into the same log buffer.
    if logger is not None:
        try:
            logger._collector = collector
        except AttributeError:
            pass
        opts['logger'] = logger
    else:
        opts['logger'] = collector

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

    return opts, collector


def load_video_msg(app):
    url = app.entry_url.get().strip()
    if not url:
        app.root.after(0, lambda: messagebox.showerror("错误", "请输入有效的视频URL。"))
        app.root.after(0, app.enable_buttons)
        app.root.after(0, lambda: app.update_status("就绪"))
        return
    collector = None
    try:
        app.current_url = url
        # Parse-only; default quality is a placeholder — we don't actually
        # restrict formats here, only at download time.
        ydl_opts, collector = _build_ydl_opts(
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
        log_path = _resolve_log_path(app)
        written = collector.flush_to_disk(str(e), log_path) if collector is not None else None
        if written:
            app._last_log_path = written
        log_text = collector.text() if collector is not None else ''
        app.root.after(0, lambda msg=str(e), log=log_text, p=written:
                       app.show_download_error(msg, log, p))
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

        iid = app.playlist_tree.insert('', 'end', values=(
            "√", i + 1, title, duration_str, size_str, "", "", "", "",
        ))
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
        speed = d.get('speed')
        eta = d.get('eta')
        if speed:
            app.update_video_speed_text(
                app.current_download_index, f"{speed/1024/1024:.1f}MB/s")
        if eta is not None:
            app.update_video_eta_text(
                app.current_download_index,
                time.strftime("%H:%M:%S", time.gmtime(max(0, int(eta)))))
        if app.download_start_time:
            elapsed_time = time.time() - app.download_start_time
            elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
            speed_str = f" {speed/1024/1024:.1f}MB/s" if speed else ""
            eta_str = ""
            if eta is not None:
                eta_str = f" 剩余 {time.strftime('%H:%M:%S', time.gmtime(max(0, int(eta))))}"
            app.update_status(f"下载中... 已用 {elapsed_str}{speed_str}{eta_str}")
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
        speed = d.get('speed')
        eta = d.get('eta')
        if speed:
            app.update_video_speed_text(
                app.current_download_index, f"{speed/1024/1024:.1f}MB/s")
        if eta is not None:
            app.update_video_eta_text(
                app.current_download_index,
                time.strftime("%H:%M:%S", time.gmtime(max(0, int(eta)))))
        if app.download_start_time:
            elapsed_time = time.time() - app.download_start_time
            elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
            speed_str = f" {speed/1024/1024:.1f}MB/s" if speed else ""
            eta_str = ""
            if eta is not None:
                eta_str = f" 剩余 {time.strftime('%H:%M:%S', time.gmtime(max(0, int(eta))))}"
            app.update_status(
                f"下载中... 已用 {elapsed_str}{speed_str}{eta_str}"
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

    ok, reason, collector = _download_one(
        app, entry, height=height, output_format=output_format,
        selected_subtitle=selected_subtitle, is_playlist=False,
        position_label="",
    )
    if ok:
        elapsed_time = time.time() - app.download_start_time
        elapsed_time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
        app.update_status(f"下载完成! 耗时: {elapsed_time_str}")
        app.root.after(0, lambda: messagebox.showinfo("下载完成", "视频已成功下载。"))
        app.root.after(0, app.open_download_folder)
    elif reason == 'cancelled':
        app.update_status("下载已取消")
        app.root.after(0, lambda: messagebox.showinfo("已取消", "下载已取消。"))
    else:
        log_text = collector.text() if collector is not None else ''
        log_path = _resolve_log_path(app)
        written = collector.flush_to_disk(reason, log_path) if collector is not None else None
        if written:
            app._last_log_path = written
        app.root.after(0, lambda msg=reason, log=log_text, p=written:
                       app.show_download_error(msg, log, p))
        app.update_status("下载失败")

    app.download_start_time = None
    app.current_download_index = None
    app.root.after(0, lambda: app.button_cancel.config(state='disabled'))
    app.root.after(0, app.enable_buttons)


def _download_one(app, entry, *, height, output_format, selected_subtitle,
                  is_playlist, position_label):
    """Single video download; safe to call from a worker thread."""
    import threading as _threading
    _tname = _threading.current_thread().name
    try:
        with open(os.path.join(os.path.expanduser("~"), "Desktop",
                               "yt_downloader_startup.log"),
                  "a", encoding="utf-8") as _df:
            _df.write(f"[download] thread={_tname} pos={position_label} "
                      f"title={entry.get('title', '?')!r} START\n")
    except Exception:
        pass
    video_url = entry.get('url') or entry.get('webpage_url')
    if not video_url:
        return False, 'no_url', None

    entry_index = (app.playlist_entries.index(entry)
                   if entry in app.playlist_entries else 0)
    app.current_download_index = entry_index
    app.root.after(0, lambda: app.update_status(
        f"下载第 {position_label} 个视频..."))

    ydl_opts, collector = _build_ydl_opts(
        app, for_download=True, output_format=output_format, height=height,
        selected_subtitle=selected_subtitle,
        progress_hook_fn=lambda d: (
            show_playlist_progress(app, d) if is_playlist
            else show_progress(app, d)),
        logger=FFmpegProgressLogger(
            app, is_playlist=is_playlist, entry_index=entry_index,
            video_duration=entry.get('duration'),
        ),
    )

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            app._active_ydl = ydl
            try:
                if app.cancel_event.is_set():
                    return False, 'cancelled', collector
                ydl.download([video_url])
            finally:
                app._active_ydl = None
        app.set_video_result(entry_index, True)
        app.update_video_convert_status(
            entry_index, "完成" if output_format != '不转换' else "")
        return True, None, collector
    except Exception as e:
        app.set_video_result(entry_index, False)
        app.update_video_convert_status(entry_index, "")
        # Persist log synchronously so the file exists regardless of GUI.
        log_path = _resolve_log_path(app)
        written = collector.flush_to_disk(str(e), log_path)
        if written:
            app._last_log_path = written
        return False, str(e), collector


def download_multi(app, selected_entries):
    quality_text = app.quality_combobox.get()
    if not quality_text:
        app.root.after(0, lambda: messagebox.showerror("错误", "请选择视频质量。"))
        app.root.after(0, app.enable_buttons)
        return

    height = int(quality_text.replace('p', ''))
    output_format = app.format_combobox.get()
    selected_subtitle = app.caption_combobox.get()
    from config import get_max_concurrent
    max_workers = max(1, get_max_concurrent())

    app.cancel_event.clear()
    app.download_start_time = time.time()
    app.root.after(0, lambda: app.button_cancel.config(state='normal'))

    app.total_playlist_videos = len(selected_entries)
    app.current_playlist_index = 0
    success_count = 0
    fail_count = 0
    fail_log_path = None

    from concurrent.futures import ThreadPoolExecutor, as_completed
    try:
        with open(os.path.join(os.path.expanduser("~"), "Desktop",
                               "yt_downloader_startup.log"),
                  "a", encoding="utf-8") as _df:
            _df.write(f"[download_multi] total={app.total_playlist_videos} "
                      f"max_workers={max_workers}\n")
    except Exception:
        pass
    # Note: the cancel check is the only synchronization between the
    # workers. yt-dlp's per-thread YoutubeDL instance handles its own
    # state; we don't share a single YoutubeDL across threads.
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {}
        for i, entry in enumerate(selected_entries):
            if app.cancel_event.is_set():
                break
            position_label = f"{i+1}/{app.total_playlist_videos}"
            fut = pool.submit(
                _download_one, app, entry,
                height=height, output_format=output_format,
                selected_subtitle=selected_subtitle, is_playlist=True,
                position_label=position_label,
            )
            futures[fut] = (i, entry)

        for fut in as_completed(futures):
            i, entry = futures[fut]
            ok, reason, collector = fut.result()
            if ok:
                success_count += 1
            elif reason == 'cancelled':
                pass  # don't count as failure
            elif reason == 'no_url':
                fail_count += 1
            else:
                fail_count += 1
                if collector is not None and fail_log_path is None:
                    # Capture the first failure's log path so the user
                    # can find it via 帮助 → 打开下载日志.
                    pass
            app.current_playlist_index = i + 1
            if app.cancel_event.is_set():
                break

    elapsed_time = time.time() - app.download_start_time
    elapsed_time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
    cancelled = app.cancel_event.is_set()
    app.update_status(
        "已取消" if cancelled
        else f"批量下载完成! 成功: {success_count}, 失败: {fail_count}, 用时 {elapsed_time_str}"
    )
    app.root.after(0, lambda: messagebox.showinfo(
        "已取消" if cancelled else "下载完成",
        f"下载已取消" if cancelled
        else f"成功: {success_count} 个, 失败: {fail_count} 个\n用时: {elapsed_time_str}",
    ))
    if not cancelled:
        app.root.after(0, app.open_download_folder)

    app.download_start_time = None
    app.current_download_index = None
    app.root.after(0, app.enable_buttons)
    app.root.after(0, lambda: app.button_cancel.config(state='disabled'))