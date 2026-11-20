#!/bin/zsh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ARCH="$(uname -m)"
echo "==> build macOS app ($ARCH)"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -q -U pip
python -m pip install -q -r requirements-build.txt

rm -rf build/pyinstaller dist/pyinstaller
mkdir -p build/pyinstaller dist/pyinstaller dist/release

pyinstaller \
  --noconfirm \
  --clean \
  --distpath dist/pyinstaller \
  --workpath build/pyinstaller \
  packaging/macos/DouyinMediaHelper.spec

APP="dist/pyinstaller/DouyinMediaHelper.app"
if [ ! -d "$APP" ]; then
  echo "build failed: $APP missing" >&2
  exit 1
fi

# Drop Gatekeeper quarantine on the build machine artifact (users may still see it after download).
xattr -cr "$APP" 2>/dev/null || true

STAGE="dist/release/DouyinMediaHelper-macOS-${ARCH}"
rm -rf "$STAGE"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
cp -R extension "$STAGE/extension"
cat > "$STAGE/使用说明.txt" <<EOF
抖音媒体助手（macOS 自包含版）

【需要】
- macOS 12+（本包架构: ${ARCH}）
- Google Chrome

【不需要】
- 不需要安装 Python / Homebrew / ffmpeg
- 没有「下一步/完成」那种安装向导：.app 双击就是在运行程序

【第一次用】
1. 解压这个 zip
2. 双击「DouyinMediaHelper.app」
   - 不会弹出大窗口（这是正常的）
   - 成功标志：Dock 出现「抖音媒体助手」；屏幕右上角菜单栏出现「抖音」
   - 若弹窗说无法打开 / 无法验证开发者：
     先关掉弹窗 → 右键点这个 .app → 选「打开」→ 再点「打开」
3. 以后每次用：再双击一次即可（已在运行时再双击通常会保持原实例）

【安装 Chrome 插件（只做一次）】
1. Chrome 打开 chrome://extensions
2. 打开右上角「开发者模式」
3. 点「加载已解压的扩展程序」
4. 选本目录里的 extension 文件夹

【日常使用】
1. 先双击打开助手，再开 Chrome
2. 登录抖音并播放视频
3. 点插件里的「推送到本地」
4. 成品目录：
   ~/Library/Application Support/DouyinMediaHelper/downloads
   （也可在菜单栏图标里点「打开下载目录」）

【说明】
- 本包已内置 ffmpeg，无需 brew
- Apple Silicon 与 Intel 包不通用；请使用与本机芯片匹配的 zip
EOF

ZIP="dist/release/DouyinMediaHelper-macOS-${ARCH}.zip"
rm -f "$ZIP"
ditto -c -k --keepParent "$STAGE" "$ZIP"

echo "==> app: $APP"
echo "==> zip: $ZIP"
echo "==> folder: $STAGE"
ls -lh "$ZIP"
