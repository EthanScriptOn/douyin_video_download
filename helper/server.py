#!/usr/bin/env python3
"""Local HTTP helper: ingest Douyin media URLs, stitch, open files.

@author Codex
@date 2026-11-20
@comment localhost-only download/ffmpeg service for the Chrome extension.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

HOST = "127.0.0.1"
DEFAULT_PORT = 18767

_SSL_CTX = ssl._create_unverified_context()
_FFMPEG_BIN: Optional[str] = None


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def bundle_dir() -> Path:
    """Directory with bundled resources (PyInstaller _MEIPASS or package root)."""
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def data_dir() -> Path:
    """Writable data root for downloads / config."""
    if is_frozen():
        if sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support" / "DouyinMediaHelper"
        elif sys.platform == "win32":
            base = Path(os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming")) / "DouyinMediaHelper"
        else:
            base = Path.home() / ".local" / "share" / "DouyinMediaHelper"
        base.mkdir(parents=True, exist_ok=True)
        return base
    return Path(__file__).resolve().parents[1]


ROOT = data_dir()
OUT = ROOT / "downloads"
OUT.mkdir(parents=True, exist_ok=True)


def find_ffmpeg() -> str:
    """Resolve ffmpeg.

    Frozen (.app/.exe): prefer bundled / imageio-ffmpeg so users need no PATH setup.
    Dev mode: prefer env → PATH → imageio-ffmpeg.
    """
    global _FFMPEG_BIN
    if _FFMPEG_BIN:
        return _FFMPEG_BIN

    env = os.environ.get("FFMPEG_BINARY") or os.environ.get("FFMPEG_PATH")
    if env and Path(env).is_file():
        _FFMPEG_BIN = env
        return _FFMPEG_BIN

    def _from_imageio() -> Optional[str]:
        try:
            import imageio_ffmpeg

            path = imageio_ffmpeg.get_ffmpeg_exe()
            return path if path and Path(path).is_file() else None
        except Exception:
            return None

    bundled = bundle_dir() / "ffmpeg"
    if is_frozen():
        if bundled.is_file():
            _FFMPEG_BIN = str(bundled)
            return _FFMPEG_BIN
        bundled_iio = _from_imageio()
        if bundled_iio:
            _FFMPEG_BIN = bundled_iio
            return _FFMPEG_BIN

    which = shutil.which("ffmpeg")
    if which:
        _FFMPEG_BIN = which
        return _FFMPEG_BIN

    if bundled.is_file():
        _FFMPEG_BIN = str(bundled)
        return _FFMPEG_BIN

    bundled_iio = _from_imageio()
    if bundled_iio:
        _FFMPEG_BIN = bundled_iio
        return _FFMPEG_BIN

    raise RuntimeError(
        "未找到 ffmpeg。请安装 ffmpeg 并加入 PATH，或使用官方打包版助手。"
    )


def download(url: str, dest: Path) -> int:
    req = Request(
        url,
        headers={
            "Referer": "https://www.douyin.com/",
            "Origin": "https://www.douyin.com",
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/157.0.0.0 Safari/537.36"
            ),
        },
        method="GET",
    )
    try:
        with urlopen(req, timeout=180, context=_SSL_CTX) as resp:
            data = resp.read()
    except HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} downloading CDN object") from exc
    except URLError as exc:
        raise RuntimeError(f"CDN download failed: {exc.reason!r}") from exc
    if len(data) < 2048:
        raise RuntimeError(f"CDN object too small ({len(data)} bytes); URL may have expired")
    dest.write_bytes(data)
    return len(data)


def stitch(video: Path, audio: Path, out: Path) -> None:
    cmd = [
        find_ffmpeg(),
        "-y",
        "-i",
        str(video),
        "-i",
        str(audio),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0?",
        "-c",
        "copy",
        "-shortest",
        str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-1500:] if proc.stderr else "ffmpeg failed")


def open_local_file(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    out_root = OUT.resolve()
    if out_root not in resolved.parents and resolved != out_root:
        raise PermissionError("path outside download folder")
    if not resolved.is_file():
        raise FileNotFoundError(f"file not found: {resolved}")
    if sys.platform == "darwin":
        subprocess.run(["open", "-R", str(resolved)], check=False)
        subprocess.run(["open", str(resolved)], check=False)
    elif sys.platform == "win32":
        # Reveal in Explorer, then open with the default player.
        subprocess.run(["explorer", f"/select,{resolved}"], check=False)
        os.startfile(str(resolved))  # type: ignore[attr-defined]
    else:
        subprocess.run(["xdg-open", str(resolved)], check=False)
    return resolved


def open_downloads_dir() -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    resolved = OUT.resolve()
    if sys.platform == "darwin":
        subprocess.run(["open", str(resolved)], check=False)
    elif sys.platform == "win32":
        os.startfile(str(resolved))  # type: ignore[attr-defined]
    else:
        subprocess.run(["xdg-open", str(resolved)], check=False)
    return resolved


def free_port(port: int = DEFAULT_PORT) -> None:
    """Best-effort: kill whatever is already listening on the helper port."""
    try:
        _free_port_impl(port)
    except Exception as exc:  # pragma: no cover
        print(f"[warn] free_port skipped: {exc}", flush=True)


def _free_port_impl(port: int) -> None:
    if sys.platform == "darwin" or sys.platform.startswith("linux"):
        try:
            out = subprocess.check_output(
                ["lsof", f"-tiTCP:{port}", "-sTCP:LISTEN"],
                text=True,
                stderr=subprocess.DEVNULL,
                encoding="utf-8",
                errors="replace",
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            return
        for pid in {p.strip() for p in out.splitlines() if p.strip()}:
            subprocess.run(["kill", pid], check=False)
            time.sleep(0.2)
            subprocess.run(["kill", "-9", pid], check=False)
        return

    if sys.platform == "win32":
        # Chinese Windows netstat is often GBK/CP936 — never assume UTF-8.
        try:
            raw = subprocess.check_output(["netstat", "-ano"], stderr=subprocess.DEVNULL)
        except (subprocess.CalledProcessError, FileNotFoundError):
            return
        out = raw.decode("utf-8", errors="replace")
        if "LISTENING" not in out.upper():
            # Retry with system OEM code page guess.
            out = raw.decode("gbk", errors="replace")
        pat = re.compile(rf"[:\]]{port}\s")
        pids: set[str] = set()
        for line in out.splitlines():
            if "LISTENING" not in line.upper() or not pat.search(line + " "):
                continue
            parts = line.split()
            if parts:
                pids.add(parts[-1])
        for pid in pids:
            if pid.isdigit() and pid != "0":
                subprocess.run(["taskkill", "/F", "/PID", pid], check=False, capture_output=True)
        return


class HelperHandler(BaseHTTPRequestHandler):
    event_hook: Optional[Callable[[str, dict[str, Any]], None]] = None

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS, GET")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8"))

    def _json(self, code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _emit(self, event: str, payload: dict[str, Any]) -> None:
        hook = self.event_hook
        if hook:
            try:
                hook(event, payload)
            except Exception:
                pass

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if self.path.rstrip("/") == "/health":
            try:
                ffmpeg = find_ffmpeg()
            except Exception as exc:
                self._json(500, {"ok": False, "error": str(exc)})
                return
            self._json(
                200,
                {
                    "ok": True,
                    "out_dir": str(OUT),
                    "host": HOST,
                    "frozen": is_frozen(),
                    "ffmpeg": ffmpeg,
                },
            )
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.rstrip("/")
        try:
            payload = self._read_json()
        except Exception:
            self._json(400, {"ok": False, "error": "bad json"})
            return

        if path == "/open":
            try:
                opened = open_local_file(Path(str(payload.get("path") or "")))
                self._emit("open", {"path": str(opened)})
                self._json(200, {"ok": True, "path": str(opened)})
            except Exception as exc:
                self._json(500, {"ok": False, "error": str(exc)})
            return

        if path != "/ingest":
            self.send_response(404)
            self.end_headers()
            return

        video_url = payload.get("video_url") or ""
        audio_url = payload.get("audio_url") or ""
        if not video_url or not audio_url:
            self._json(400, {"ok": False, "error": "need video_url and audio_url"})
            return

        stamp = time.strftime("%Y%m%d_%H%M%S")
        video_path = OUT / f"video_{stamp}.mp4"
        audio_path = OUT / f"audio_{stamp}.mp4"
        out_path = OUT / f"stitched_{stamp}.mp4"
        self._emit("ingest_start", {"key": payload.get("key"), "page_url": payload.get("page_url")})
        try:
            vb = download(video_url, video_path)
            ab = download(audio_url, audio_path)
            stitch(video_path, audio_path, out_path)
            result = {
                "ok": True,
                "video_bytes": vb,
                "audio_bytes": ab,
                "output": str(out_path),
                "output_bytes": out_path.stat().st_size,
            }
            print(f"[ingest] ok -> {out_path} ({result['output_bytes']} bytes)", flush=True)
            self._emit("ingest_ok", result)
            self._json(200, result)
        except Exception as exc:
            print(f"[ingest] fail: {exc}", flush=True)
            self._emit("ingest_fail", {"error": str(exc)})
            self._json(500, {"ok": False, "error": str(exc)})

    def log_message(self, fmt: str, *args: Any) -> None:
        print("%s - %s" % (self.address_string(), fmt % args), flush=True)


class HelperServer:
    def __init__(self, port: int = DEFAULT_PORT, on_event: Optional[Callable[[str, dict[str, Any]], None]] = None):
        self.port = port
        self.on_event = on_event
        self._httpd: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def base_url(self) -> str:
        return f"http://{HOST}:{self.port}"

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        Handler = type(
            "BoundHelperHandler",
            (HelperHandler,),
            {"event_hook": staticmethod(self.on_event) if self.on_event else None},
        )
        try:
            self._httpd = ThreadingHTTPServer((HOST, self.port), Handler)
        except OSError as exc:
            hint = (
                "再双击一次 windows\\start.bat"
                if sys.platform == "win32"
                else "再双击一次 macos/start.command"
            )
            raise SystemExit(
                f"无法监听 {HOST}:{self.port}（{exc}）。通常是旧助手还在运行：{hint}"
            ) from exc
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        print(f"listening {self.base_url}  out={OUT}", flush=True)

    def stop(self) -> None:
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None


def serve_forever(port: int = DEFAULT_PORT) -> None:
    server = HelperServer(port=port)
    server.start()
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    serve_forever()
