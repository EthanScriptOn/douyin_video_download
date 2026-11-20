#!/usr/bin/env python3
"""macOS menu-bar helper for Douyin media intercept.

@author Codex
@date 2026-11-20
@comment Menu-bar only (no Dock Python rocket); serves localhost ingest/open APIs.
"""

from __future__ import annotations

import subprocess
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _prepare_menu_bar_only() -> None:
    """Hide Dock icon.

    Even when launched via our .app, ``exec python`` makes the process
    identity become Python.app (rocket icon). Force accessory policy ASAP.
    """
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

from helper.server import OUT, HelperServer  # noqa: E402

try:
    import rumps
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "缺少 rumps。请先运行 macos/start.command 或: pip install rumps"
    ) from exc


def _menubar_icon() -> Path:
    bundled = (
        ROOT
        / "macos"
        / "DouyinMediaHelper.app"
        / "Contents"
        / "Resources"
        / "menubar.png"
    )
    assets = ROOT / "helper" / "assets" / "menubar.png"
    return bundled if bundled.exists() else assets


class DouyinHelperApp(rumps.App):
    def __init__(self) -> None:
        icon = _menubar_icon()
        super().__init__(
            name="抖音媒体助手",
            title="",
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
        OUT.mkdir(parents=True, exist_ok=True)
        subprocess.run(["open", str(OUT)], check=False)

    def open_health(self, _sender=None) -> None:
        webbrowser.open(f"{self.server.base_url}/health")

    def show_help(self, _sender=None) -> None:
        rumps.alert(
            title="抖音媒体助手",
            message=(
                "1. Chrome 打开 chrome://extensions\n"
                "2. 加载已解压扩展: extension/\n"
                "3. 播放抖音视频后在插件里推送\n"
                f"4. 成品目录: {OUT}"
            ),
        )

    def quit_app(self, _sender=None) -> None:
        self.server.stop()
        rumps.quit_application()

    def run_app(self) -> None:
        _prepare_menu_bar_only()
        self.server.start()
        self.status_item.title = f"状态: 在线 · {self.server.base_url}"
        self.run()


def main() -> None:
    DouyinHelperApp().run_app()


if __name__ == "__main__":
    main()
