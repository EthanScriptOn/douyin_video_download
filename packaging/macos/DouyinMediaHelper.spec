# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: self-contained macOS menu-bar helper."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files

# SPECPATH is packaging/macos → repo root is parent of packaging
ROOT = Path(SPECPATH).resolve().parents[1]
ASSETS = ROOT / "helper" / "assets"

rumps_datas, rumps_binaries, rumps_hidden = collect_all("rumps")
iio_datas, iio_binaries, iio_hidden = collect_all("imageio_ffmpeg")

datas = [
    (str(ASSETS / "menubar.png"), "helper/assets"),
    (str(ASSETS / "menubar@2x.png"), "helper/assets"),
]
datas += rumps_datas + iio_datas + collect_data_files("imageio_ffmpeg")

binaries = rumps_binaries + iio_binaries
hiddenimports = sorted(
    set(
        rumps_hidden
        + iio_hidden
        + [
            "rumps",
            "AppKit",
            "Foundation",
            "Cocoa",
            "objc",
            "imageio_ffmpeg",
            "helper",
            "helper.server",
            "helper.macos_app",
        ]
    )
)

icon_path = ASSETS / "app_icon_512.png"
# Prefer .icns if present in the thin .app Resources.
icns = ROOT / "macos" / "DouyinMediaHelper.app" / "Contents" / "Resources" / "AppIcon.icns"
icon = str(icns) if icns.exists() else (str(icon_path) if icon_path.exists() else None)

a = Analysis(
    [str(ROOT / "helper" / "macos_app.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name="DouyinMediaHelper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="DouyinMediaHelper",
)

app = BUNDLE(
    coll,
    name="DouyinMediaHelper.app",
    icon=icon,
    bundle_identifier="com.yuebuy.douyin-media-helper",
    info_plist={
        "CFBundleName": "抖音媒体助手",
        "CFBundleDisplayName": "抖音媒体助手",
        "CFBundleShortVersionString": "0.2.0",
        "CFBundleVersion": "2",
        "LSMinimumSystemVersion": "12.0",
        # Show Dock icon so double-click is obviously successful for end users.
        "LSUIElement": False,
        "NSHighResolutionCapable": True,
        "NSPrincipalClass": "NSApplication",
    },
)
