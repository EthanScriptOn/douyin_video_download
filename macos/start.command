#!/bin/zsh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PORT=18767
APP="$ROOT/macos/DouyinMediaHelper.app"

if ! command -v ffmpeg >/dev/null 2>&1; then
  osascript -e 'display alert "缺少 ffmpeg" message "请先安装: brew install ffmpeg"'
  exit 1
fi

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -q -r requirements.txt

chmod +x "$APP/Contents/MacOS/DouyinMediaHelper"

# Prefer the .app so Dock shows our icon (actually hidden via LSUIElement)
# instead of the Python rocket.
echo "启动菜单栏助手（无 Dock 火箭图标）…"
echo "HTTP: http://127.0.0.1:$PORT"
echo "下载目录: $ROOT/downloads"
open "$APP"
