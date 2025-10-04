@echo off

REM 支持中文
chcp 65001 >nul

REM AI邮件简报系统 - 简单启动脚本 (不使用Celery)
REM 适合快速启动和日常维护

echo ========================================
echo   AI邮件简报系统 - 简单模式
echo ========================================
echo.
echo 说明: 此模式不使用Celery，使用线程处理
echo      启动快速，维护简单，适合日常使用
echo.

REM 切换到项目目录
cd /d "%~dp0"

REM 检查虚拟环境
if exist "venv\Scripts\activate.bat" (
    echo [信息] 激活虚拟环境...
    call venv\Scripts\activate.bat
) else (
    echo [信息] 未找到虚拟环境，使用系统Python
)

echo.
echo ========================================
echo   正在启动 Flask 应用...
echo ========================================
echo.

REM 设置环境变量（可选）
set FLASK_ENV=development
set FLASK_DEBUG=0

REM 启动Flask应用
python app.py

echo.
echo [信息] 应用已停止
pause

