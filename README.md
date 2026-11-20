# douyin_video_download

最小化交付：Chrome 插件拦截抖音 Web 音视频轨 + macOS 菜单栏本机助手下载拼接。

```
douyin-media-helper/
  extension/                 # Chrome 扩展（Load unpacked）
  helper/                    # localhost HTTP + macOS 菜单栏
  macos/start.command        # 双击启动（会打开 .app）
  macos/DouyinMediaHelper.app
  downloads/                 # 成品目录（不入库）
```

## 依赖

- macOS
- Google Chrome
- Python 3
- `ffmpeg`：`brew install ffmpeg`

## 启动本机助手

双击：

```text
macos/start.command
```

或打开：

```text
macos/DouyinMediaHelper.app
```

菜单栏出现下载箭头图标（无 Dock 小火箭）。助手监听：

- `GET  http://127.0.0.1:18767/health`
- `POST http://127.0.0.1:18767/ingest`
- `POST http://127.0.0.1:18767/open`

## 安装插件

1. Chrome 打开 `chrome://extensions`
2. 开发者模式 → 加载已解压的扩展程序
3. 选择本仓库 `extension/` 目录（当前版本见弹窗标题）

## 使用

1. 先开菜单栏助手  
2. 登录抖音并播放视频（带 `modal_id` 更稳）  
3. 插件按视频显示双轨是否齐全  
4. 点「推送到本地」；成功后可「打开 / 复制路径」

## 说明

- 不依赖 AI 平台；本机 HTTP 即可  
- Windows 托盘版后续再加，协议保持同一套 localhost API
