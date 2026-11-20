#!/bin/zsh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PORT=18767
APP="$ROOT/macos/DouyinMediaHelper.app"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -q -r requirements.txt

chmod +x "$APP/Contents/MacOS/DouyinMediaHelper"

echo "启动菜单栏助手（开发模式 / 无 Dock 火箭图标）…"
echo "HTTP: http://127.0.0.1:$PORT"
echo "下载目录: $ROOT/downloads"
echo "提示: 用户分发请用 scripts/build_macos_app.sh 打出自包含 .app"
open "$APP"
