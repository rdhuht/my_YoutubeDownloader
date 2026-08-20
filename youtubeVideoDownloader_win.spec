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

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('imgs/logo.ico', 'imgs'),
        (ttk_themes_dir, 'ttkbootstrap/themes'),
        (ttk_assets_dir, 'ttkbootstrap/assets'),
    ],
    hiddenimports=[],
    hookspath=[],
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
    name='youtubeVideoDownloader',
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