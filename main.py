"""Entry point for YouTube Downloader application."""
import os
import sys
import tkinter as tk
from ttkbootstrap import Style

# Ensure the bgutil-ytdlp-pot-provider plugin is registered with yt-dlp
# even when the bundled exe is run on a machine that doesn't have it
# installed. PyInstaller only packages the .py files as data; yt-dlp's
# plugin discovery scans every directory on sys.path for a `yt_dlp_plugins`
# sub-folder, so we need to put the *parent* of `yt_dlp_plugins` on
# sys.path (not `yt_dlp_plugins/extractor` itself).
import importlib

def _add_bgutil_plugin_path():
    """Compute the directory that should sit on sys.path so that
    `<dir>/yt_dlp_plugins/extractor/getpot_bgutil_http.py` is importable
    by yt-dlp's plugin discovery, both in dev and in a frozen exe.
    """
    # 1. Frozen exe: PyInstaller unpacks to sys._MEIPASS.
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        candidate = os.path.join(meipass, '_plugins')
        if os.path.isdir(candidate):
            return candidate
    # 2. Dev run: project root's _plugins/ folder.
    here = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.join(here, '_plugins')
    if os.path.isdir(candidate):
        return candidate
    # 3. Already-installed: site-packages itself (the package puts
    #    yt_dlp_plugins/extractor/ directly under site-packages). The
    #    'site' module's __file__ is not reliable inside a frozen
    #    exe, so use a defensive try/except.
    try:
        import site as _site
        site_file = getattr(_site, '__file__', None)
        if site_file:
            sp = os.path.dirname(os.path.dirname(site_file))
            if os.path.isdir(os.path.join(sp, 'yt_dlp_plugins', 'extractor')):
                return sp
        # Fallback: sys.path entries that look like site-packages
        for p in sys.path:
            cand = os.path.join(p, 'yt_dlp_plugins', 'extractor')
            if os.path.isdir(cand):
                return p
    except Exception:
        pass
    return None

_plugin_root = _add_bgutil_plugin_path()
if _plugin_root and _plugin_root not in sys.path:
    sys.path.insert(0, _plugin_root)
# Pre-import the plugin so its @register_provider runs before yt-dlp
# builds its provider registry. Wrapped in try/except because a frozen
# exe can fail to import for many reasons we want to see in the log.
try:
    importlib.import_module('yt_dlp_plugins.extractor.getpot_bgutil_http')
    _bgutil_status = 'imported'
except Exception as _bgerr:
    import traceback
    _bgutil_status = f'FAILED: {_bgerr!r}'
    traceback.print_exc()

# Write a one-line diagnostic to a known location so the user can verify
# whether the bundled exe actually loaded the plugin.
try:
    import platform, datetime
    diag = (
        f'=== YouTube Downloader v1.6.0 startup diagnostic ===\n'
        f'Time: {datetime.datetime.now().isoformat()}\n'
        f'frozen: {getattr(sys, "frozen", False)}\n'
        f'_MEIPASS: {getattr(sys, "_MEIPASS", None)}\n'
        f'_plugin_root: {_plugin_root}\n'
        f'bgutil_http import: {_bgutil_status}\n'
        f'Plugin root contents: '
        f'{os.listdir(os.path.join(_plugin_root, "yt_dlp_plugins", "extractor")) if _plugin_root and os.path.isdir(os.path.join(_plugin_root, "yt_dlp_plugins", "extractor")) else "MISSING"}\n'
    )
    with open(os.path.join(os.path.expanduser("~"), "Desktop",
                           "yt_downloader_startup.log"),
              "a", encoding="utf-8") as _df:
        _df.write(diag + "\n")
except Exception:
    pass

from ui import YouTubeDownloader
from config import FFMPEG_AVAILABLE
# Workaround for PyInstaller 6.21 PYZ caching: when frozen, the PYZ's
# _downloader module can be stale (PyInstaller 6.21 ships an old
# .pyc). Re-exec the bundled source file at startup to guarantee the
# running exe always sees the latest _downloader code.
if getattr(sys, 'frozen', False):
    import importlib.util as _ilu
    _dl_candidates = [
        os.path.join(getattr(sys, '_MEIPASS', os.path.dirname(__file__)),
                     '_downloader.py'),
        os.path.join(os.path.dirname(sys.executable), '_downloader.py'),
    ]
    for _p in _dl_candidates:
        if os.path.exists(_p):
            try:
                with open(_p, 'r', encoding='utf-8') as _f:
                    _src = _f.read()
                import types as _types
                _mod = _types.ModuleType('_downloader')
                exec(compile(_src, _p, 'exec'), _mod.__dict__)
                sys.modules['_downloader'] = _mod
                import _downloader as downloader  # noqa: F401
                break
            except Exception as _e:
                print(f'[main] failed to exec _downloader.py: {_e}')

import _downloader as downloader  # noqa: F401  (imported for side effect: registers the module)

if __name__ == "__main__":
    root = tk.Tk()
    style = Style(theme="superhero")
    app = YouTubeDownloader(root)
    # If the bgutil plugin import failed inside a frozen build, surface it
    # visibly to the user — otherwise the symptom is silent ("The page
    # needs to be reloaded") which is what was happening before.
    if getattr(sys, 'frozen', False) and not _bgutil_status.startswith('imported'):
        from tkinter import messagebox
        root.after(
            600,
            lambda: messagebox.showerror(
                "bgutil 插件未加载",
                "无法在 exe 中加载 bgutil POT 插件 (用于生成 YouTube PO Token)。\n\n"
                f"原因: {_bgutil_status}\n\n"
                "没有这个插件,当前 YouTube 的 SABR 实验会让所有视频下载失败。\n"
                "请把 Desktop 下的 yt_downloader_startup.log 发给开发者。"
            ),
        )
    root.mainloop()