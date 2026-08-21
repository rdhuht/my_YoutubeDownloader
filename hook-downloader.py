"""PyInstaller hook for our downloader module so PyInstaller includes it
in the PYZ archive (the static analysis in some PyInstaller versions fails
to follow `import _downloader` triggered after conditional sys.path setup).
"""
hiddenimports = ['_downloader']
