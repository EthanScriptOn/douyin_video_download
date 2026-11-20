# douyin_video_download

Chrome 插件拦截抖音 Web 音视频轨 + 本机助手下载拼接（macOS / Windows）。

## 给用户发什么（推荐）

### macOS（自包含，无需 Python / brew / ffmpeg）

构建：

```bash
./scripts/build_macos_app.sh
```

产物：

```text
dist/release/DouyinMediaHelper-macOS-<arch>.zip
```

内含 `DouyinMediaHelper.app` + `extension/` + `使用说明.txt`。用户解压后：

1. 打开 `.app`（首次可能要右键 → 打开）
2. Chrome 加载同目录 `extension/`

成品目录：`~/Library/Application Support/DouyinMediaHelper/downloads`

> 当前构建出的包与构建机芯片一致（arm64 / x86_64）。Apple Silicon 与 Intel 不要混用。

### Windows（自包含 exe，无需 Python / ffmpeg）

在 Windows 上构建：

```bat
scripts\build_windows.bat
```

或由 GitHub Actions（`Build Windows package`）产出 artifact。

产物：

```text
dist/release/DouyinMediaHelper-Windows-x64.zip
```

内含 `DouyinMediaHelper.exe` + `extension/` + `使用说明.txt`。用户解压后双击 exe，**保持黑窗口不要关**。

开发调试仍可用：`windows\start.bat`（需要本机 Python）。

---

## 开发者模式（本仓库）

```
extension/                 # Chrome 扩展
helper/                    # localhost HTTP + 各平台入口
macos/start.command        # 开发启动（需本机 Python）
windows/start.bat
scripts/build_macos_app.sh # 打 macOS 用户包
```

```bash
# macOS 开发
./macos/start.command

# 依赖
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

接口（两边相同）：

- `GET  http://127.0.0.1:18767/health`
- `POST http://127.0.0.1:18767/ingest`
- `POST http://127.0.0.1:18767/open`

## 安装插件

1. Chrome → `chrome://extensions`
2. 开发者模式 → 加载已解压的扩展程序 → `extension/`

## 使用

1. 先开本机助手  
2. 登录抖音并播放视频  
3. 插件点「推送到本地」
