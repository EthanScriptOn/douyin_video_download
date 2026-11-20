@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0.."

set "PORT=18767"
set "ROOT=%CD%"

where py >nul 2>&1
if errorlevel 1 (
  where python >nul 2>&1
  if errorlevel 1 (
    echo [错误] 未找到 Python。请安装 Python 3 并勾选 Add to PATH。
    pause
    exit /b 1
  )
  set "PY=python"
) else (
  set "PY=py -3"
)

if not exist ".venv\Scripts\python.exe" (
  echo 正在创建虚拟环境...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo [错误] 创建 .venv 失败。
    pause
    exit /b 1
  )
)

call ".venv\Scripts\activate.bat"
python -m pip install -q -r requirements-windows.txt
if errorlevel 1 (
  echo [错误] 安装依赖失败。
  pause
  exit /b 1
)

echo 启动 Windows 本机助手...
echo HTTP: http://127.0.0.1:%PORT%
echo 下载目录: %ROOT%\downloads
echo.
python -m helper.windows_app
pause
