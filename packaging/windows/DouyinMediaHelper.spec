# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: self-contained Windows console helper."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files

ROOT = Path(SPECPATH).resolve().parents[1]

iio_datas, iio_binaries, iio_hidden = collect_all("imageio_ffmpeg")

datas = iio_datas + collect_data_files("imageio_ffmpeg")
binaries = iio_binaries
hiddenimports = sorted(
    set(
        iio_hidden
        + [
            "imageio_ffmpeg",
            "helper",
            "helper.server",
            "helper.windows_app",
        ]
    )
)

a = Analysis(
    [str(ROOT / "helper" / "windows_app.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["rumps", "AppKit", "Foundation"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="DouyinMediaHelper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
