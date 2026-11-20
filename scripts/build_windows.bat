@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0.."

echo ==^> build Windows exe

where py >nul 2>&1
if errorlevel 1 (
  set "PY=python"
) else (
  set "PY=py -3"
)

if not exist ".venv\Scripts\python.exe" (
  %PY% -m venv .venv
)
call ".venv\Scripts\activate.bat"
python -m pip install -q -U pip
python -m pip install -q -r requirements-build-windows.txt
if errorlevel 1 (
  echo [错误] 安装构建依赖失败
  exit /b 1
)

rmdir /s /q build\pyinstaller-win 2>nul
rmdir /s /q dist\pyinstaller-win 2>nul
mkdir dist\release 2>nul

pyinstaller --noconfirm --clean --distpath dist\pyinstaller-win --workpath build\pyinstaller-win packaging\windows\DouyinMediaHelper.spec
if errorlevel 1 (
  echo [错误] PyInstaller 失败
  exit /b 1
)

set "EXE=dist\pyinstaller-win\DouyinMediaHelper.exe"
if not exist "%EXE%" (
  echo [错误] 未找到 %EXE%
  exit /b 1
)

set "STAGE=dist\release\DouyinMediaHelper-Windows-x64"
rmdir /s /q "%STAGE%" 2>nul
mkdir "%STAGE%"
copy /y "%EXE%" "%STAGE%\DouyinMediaHelper.exe" >nul
xcopy /e /i /y extension "%STAGE%\extension" >nul

powershell -NoProfile -Command ^
  @\"^
抖音媒体助手（Windows 自包含版）`r`n`r`n^
【需要】`r`n^
- Windows 10/11 x64`r`n^
- Google Chrome`r`n`r`n^
【不需要】`r`n^
- 不需要安装 Python / ffmpeg`r`n`r`n^
【第一次用】`r`n^
1. 解压这个 zip`r`n^
2. 双击 DouyinMediaHelper.exe`r`n^
   - 会弹出黑色命令行窗口，保持它不要关`r`n^
   - 若被 Windows 智能筛选拦截：更多信息 → 仍要运行`r`n^
3. 看到「接口: http://127.0.0.1:18767」即表示已启动`r`n`r`n^
【安装 Chrome 插件（只做一次）】`r`n^
1. Chrome 打开 chrome://extensions`r`n^
2. 打开右上角「开发者模式」`r`n^
3. 点「加载已解压的扩展程序」`r`n^
4. 选本目录里的 extension 文件夹`r`n`r`n^
【日常使用】`r`n^
1. 先双击打开助手窗口，再开 Chrome`r`n^
2. 登录抖音并播放视频`r`n^
3. 点插件里的「推送到本地」`r`n^
4. 成品目录一般在：`r`n^
   %%APPDATA%%\DouyinMediaHelper\downloads`r`n^
   （窗口里输入 o 然后回车可打开）`r`n`r`n^
【窗口内命令】`r`n^
o = 打开下载目录`r`n^
h = 打开健康检查`r`n^
q = 退出`r`n^
\"@ | Set-Content -Encoding UTF8 '%STAGE%\使用说明.txt'

del /f /q dist\release\DouyinMediaHelper-Windows-x64.zip 2>nul
powershell -NoProfile -Command "Compress-Archive -Path 'dist\release\DouyinMediaHelper-Windows-x64' -DestinationPath 'dist\release\DouyinMediaHelper-Windows-x64.zip' -Force"
echo ==^> zip: dist\release\DouyinMediaHelper-Windows-x64.zip
dir dist\release\DouyinMediaHelper-Windows-x64.zip
