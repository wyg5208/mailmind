@echo off
chcp 65001 >nul

echo.
echo ========================================
echo   AI邮件简报系统 - 统一启动
echo ========================================
echo.

cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" (
    echo [错误] 虚拟环境不存在!
    echo 当前目录: %CD%
    pause
    exit /b 1
)

echo [信息] 激活虚拟环境...
call venv\Scripts\activate.bat

echo [信息] 检查Redis连接...
redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo [警告] Redis未响应，使用简单模式
    echo.
    python app.py
    pause
    exit /b 0
)

echo [成功] Redis正常
echo.
echo 选择运行模式:
echo 1. 完整模式 (Flask + Celery)
echo 2. 简单模式 (仅Flask)
echo.
set /p mode="请选择 (1/2): "

if "%mode%"=="2" (
    echo.
    echo [信息] 简单模式启动中...
    python app.py
    pause
    exit /b 0
)

echo.
echo [信息] 完整模式启动中...
echo 正在启动 Celery Worker...
echo.

start "Celery Worker" cmd /k "cd /d %~dp0 && call venv\Scripts\activate.bat && celery -A services.celery_app worker --loglevel=info --pool=solo"

timeout /t 2 /nobreak >nul

echo Celery Worker 已启动
echo.
echo 正在启动 Flask 应用...
echo.

python app.py

pause

