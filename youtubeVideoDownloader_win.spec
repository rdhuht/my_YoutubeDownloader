# -*- mode: python ; coding: utf-8 -*-

import os
import sys

block_cipher = None

# Locate ttkbootstrap's resource folders so they end up next to the
# executable. ttkbootstrap reads theme JSON, icon fonts and other assets via
# `importlib.resources` at runtime — bundling them under the same package
# layout is required.
_ttk_root = os.path.dirname(__import__('ttkbootstrap').__file__)
ttk_themes_dir = os.path.join(_ttk_root, 'themes')
ttk_assets_dir = os.path.join(_ttk_root, 'assets')

# Locate yt-dlp embedded JS solver (ejs) so YouTube's `n` challenge solver
# scripts are available inside the frozen executable.
_ejs_root = os.path.dirname(__import__('yt_dlp_ejs').__file__)
ejs_yt_dir = os.path.join(_ejs_root, 'yt')

# Bundle the bgutil-ytdlp-pot-provider plugin (a yt_dlp_plugins/extractor
# directory) from the project-local _plugins/ tree. main.py adds this
# directory to sys.path and explicitly imports the plugin modules, which
# is the only way to make the plugin discoverable inside a PyInstaller
# bundle (the `datas` mapping alone doesn't put modules on sys.path for
# a namespace package like yt_dlp_plugins).
_project_root = os.path.abspath(os.path.dirname(SPECPATH))
_local_plugins = os.path.join(_project_root, '_plugins')
if not os.path.isdir(_local_plugins):
    raise RuntimeError(
        'Project-local _plugins/ not found at ' + _local_plugins
        + ' — run the build script that copies bgutil plugin files there,'
        ' or `pip install bgutil-ytdlp-pot-provider` first.')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('imgs/logo.ico', 'imgs'),
        (ttk_themes_dir, 'ttkbootstrap/themes'),
        (ttk_assets_dir, 'ttkbootstrap/assets'),
        (ejs_yt_dir, 'yt_dlp_ejs/yt'),
        (_local_plugins, '_plugins'),
        # Ship _downloader.py as a data file so the frozen exe can exec
        # it at startup. This bypasses the PYZ caching issue where
        # PyInstaller 6.21 ships a stale _downloader module in the PYZ.
        ('_downloader.py', '.'),
    ],
    hiddenimports=[
        'yt_dlp_ejs',
        'yt_dlp_ejs.yt',
        'yt_dlp_ejs.yt.solver',
        'yt_dlp_plugins.extractor.getpot_bgutil',
        'yt_dlp_plugins.extractor.getpot_bgutil_http',
        'yt_dlp_plugins.extractor.getpot_bgutil_script',
    ],
    hookspath=['.'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='youtubeVideoDownloader_v3',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['imgs/logo.ico'],
)