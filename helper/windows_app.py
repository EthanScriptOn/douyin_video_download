#!/usr/bin/env python3
"""Windows console helper for Douyin media intercept.

@author Codex
@date 2026-11-20
@comment Visible console window; works both from source and frozen .exe.
"""

from __future__ import annotations

import sys
import threading
import webbrowser
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if not getattr(sys, "frozen", False) and str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from helper.server import (  # noqa: E402
    OUT,
    HelperServer,
    find_ffmpeg,
    free_port,
    is_frozen,
    open_downloads_dir,
)


def main() -> None:
    try:
        ffmpeg = find_ffmpeg()
    except RuntimeError as exc:
        print(f"[错误] {exc}", flush=True)
        input("按回车键退出…")
        raise SystemExit(1) from exc

    free_port()
    server = HelperServer()
    try:
        server.start()
    except SystemExit as exc:
        print(str(exc), flush=True)
        input("按回车键退出…")
        raise

    mode = "打包版" if is_frozen() else "开发版"
    print("=" * 48, flush=True)
    print(f"  抖音媒体助手 (Windows · {mode})", flush=True)
    print(f"  接口: {server.base_url}", flush=True)
    print(f"  成品: {OUT}", flush=True)
    print(f"  ffmpeg: {ffmpeg}", flush=True)
    print("=" * 48, flush=True)
    print("命令: o=打开下载目录  h=健康检查  q=退出", flush=True)
    print("请保持本窗口运行，再在 Chrome 插件里「推送到本地」。", flush=True)
    print("关掉本窗口 = 退出助手。", flush=True)

    stop = threading.Event()

    def _stdin_loop() -> None:
        while not stop.is_set():
            try:
                line = sys.stdin.readline()
            except Exception:
                break
            if not line:
                break
            cmd = line.strip().lower()
            if cmd in {"q", "quit", "exit"}:
                stop.set()
                break
            if cmd in {"o", "open"}:
                open_downloads_dir()
                print(f"已打开: {OUT}", flush=True)
            elif cmd in {"h", "health"}:
                webbrowser.open(f"{server.base_url}/health")
            elif cmd:
                print("未知命令。可用: o / h / q", flush=True)

    threading.Thread(target=_stdin_loop, daemon=True).start()
    try:
        while not stop.wait(0.5):
            pass
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
        print("已退出。", flush=True)


if __name__ == "__main__":
    main()
