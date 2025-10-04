@echo off
REM 支持中文
chcp 65001 >nul


REM AI邮件简报系统 - Celery Worker 启动脚本
REM 在新终端窗口中运行此脚本

echo ========================================
echo   AI邮件简报系统 - Celery Worker
echo ========================================
echo.



REM 检查虚拟环境是否存在
if not exist "venv\Scripts\activate.bat" (
    echo [错误] 虚拟环境不存在!
    echo 请先运行: python -m venv venv
    pause
    exit /b 1
)

echo [信息] 激活虚拟环境...
call venv\Scripts\activate.bat

echo [信息] 检查Redis连接...
redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo [警告] Redis未运行或连接失败!
    echo 请先启动Redis服务器
    echo.
    echo 快速启动Redis:
    echo   docker run -d -p 6379:6379 redis
    echo 或
    echo   redis-server.exe
    echo.
    pause
    exit /b 1
)

echo [成功] Redis连接正常
echo.

echo [信息] 启动Celery Worker...
echo 日志级别: INFO
echo Worker模式: solo (Windows兼容)
echo 日志文件: logs\celery_YYYY_MM_DD.log
echo.
echo ========================================
echo   Celery Worker 正在运行中...
echo   按 Ctrl+C 停止
echo.
echo   控制台日志: 实时显示
echo   文件日志: logs\celery_%date:~0,4%_%date:~5,2%_%date:~8,2%.log
echo ========================================
echo.

REM 启动Celery Worker
celery -A services.celery_app worker --loglevel=info --pool=solo

REM 如果Worker意外退出
echo.
echo [警告] Celery Worker 已停止
pause

