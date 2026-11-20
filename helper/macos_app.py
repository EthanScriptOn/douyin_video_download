#!/usr/bin/env python3
"""macOS menu-bar helper for Douyin media intercept.

@author Codex
@date 2026-11-20
@comment Menu-bar helper; packaged .app also shows a Dock icon so launch is obvious.
"""

from __future__ import annotations

import sys
import webbrowser
from pathlib import Path

# Dev mode: repo root on sys.path. Frozen: PyInstaller already has packages.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if not getattr(sys, "frozen", False) and str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _prepare_menu_bar_only() -> None:
    """Dev launcher: hide the Python rocket Dock icon.

    Packaged .app keeps a normal Dock icon so double-click clearly "does something".
    """
    if getattr(sys, "frozen", False):
        return
    try:
        from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
        from Foundation import NSBundle

        info = NSBundle.mainBundle().infoDictionary()
        if info is not None:
            info["LSUIElement"] = "1"
        app = NSApplication.sharedApplication()
        app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    except Exception:
        pass


_prepare_menu_bar_only()

from helper.server import (  # noqa: E402
    OUT,
    HelperServer,
    bundle_dir,
    find_ffmpeg,
    free_port,
    is_frozen,
    open_downloads_dir,
)

try:
    import rumps
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "缺少 rumps。请先运行 macos/start.command 或: pip install rumps"
    ) from exc


def _menubar_icon() -> Path:
    exe = Path(sys.executable).resolve()
    if is_frozen():
        candidates = [
            bundle_dir() / "helper" / "assets" / "menubar.png",
            bundle_dir() / "menubar.png",
            exe.parent.parent / "Resources" / "helper" / "assets" / "menubar.png",
            exe.parent.parent / "Resources" / "menubar.png",
            exe.parent / "helper" / "assets" / "menubar.png",
        ]
    else:
        candidates = [
            _REPO_ROOT
            / "macos"
            / "DouyinMediaHelper.app"
            / "Contents"
            / "Resources"
            / "menubar.png",
            _REPO_ROOT / "helper" / "assets" / "menubar.png",
        ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[-1]


class DouyinHelperApp(rumps.App):
    def __init__(self) -> None:
        icon = _menubar_icon()
        # Keep a short title so the item is visible even if the icon is tiny / hidden
        # behind the macOS menu-bar overflow ("…").
        super().__init__(
            name="抖音媒体助手",
            title="抖音",
            icon=str(icon) if icon.exists() else None,
            template=True,
            quit_button=None,
        )
        self.server = HelperServer(on_event=self._on_event)
        self.status_item = rumps.MenuItem("状态: 启动中…")
        self.last_item = rumps.MenuItem("最近成品: 无")
        self.menu = [
            self.status_item,
            self.last_item,
            None,
            rumps.MenuItem("打开下载目录", callback=self.open_downloads),
            rumps.MenuItem("打开健康检查", callback=self.open_health),
            rumps.MenuItem("安装说明", callback=self.show_help),
            None,
            rumps.MenuItem("退出", callback=self.quit_app),
        ]
        self._last_output: str | None = None

    def _on_event(self, event: str, payload: dict) -> None:
        if event == "ingest_ok":
            path = str(payload.get("output") or "")
            self._last_output = path
            name = Path(path).name if path else "完成"
            self.last_item.title = f"最近成品: {name}"
            self.status_item.title = "状态: 在线 · 最近拼接成功"
            rumps.notification("抖音媒体助手", "拼接完成", name)
        elif event == "ingest_fail":
            self.status_item.title = "状态: 在线 · 最近拼接失败"
            rumps.notification(
                "抖音媒体助手",
                "拼接失败",
                str(payload.get("error") or "")[:120],
            )
        elif event == "ingest_start":
            self.status_item.title = "状态: 在线 · 正在下载拼接…"

    def open_downloads(self, _sender=None) -> None:
        open_downloads_dir()

    def open_health(self, _sender=None) -> None:
        webbrowser.open(f"{self.server.base_url}/health")

    def show_help(self, _sender=None) -> None:
        rumps.alert(
            title="抖音媒体助手",
            message=(
                "双击打开后不会弹出大窗口。\n"
                "请看：\n"
                "· Dock 上的「抖音媒体助手」\n"
                "· 屏幕右上角菜单栏文字「抖音」\n\n"
                "1. Chrome 打开 chrome://extensions\n"
                "2. 开发者模式 → 加载已解压扩展（同目录 extension/）\n"
                "3. 播放抖音视频后在插件里推送\n"
                f"4. 成品目录: {OUT}"
            ),
        )

    def quit_app(self, _sender=None) -> None:
        self.server.stop()
        rumps.quit_application()

    def run_app(self) -> None:
        _prepare_menu_bar_only()
        try:
            find_ffmpeg()
        except RuntimeError as exc:
            rumps.alert(title="抖音媒体助手", message=str(exc))
            raise SystemExit(1) from exc
        free_port()
        self.server.start()
        self.status_item.title = f"状态: 在线 · {self.server.base_url}"
        rumps.notification(
            "抖音媒体助手",
            "已启动",
            "看 Dock 图标，或屏幕右上角菜单栏「抖音」",
        )
        self.run()


def main() -> None:
    DouyinHelperApp().run_app()


if __name__ == "__main__":
    main()
