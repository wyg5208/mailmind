@echo off

REM 支持中文
chcp 65001 >nul

echo.
echo ========================================
echo   AI邮件简报系统 - 调试启动
echo ========================================
echo.

echo [调试] 步骤1: 检查脚本位置
echo 脚本位置: %~dp0
echo.
pause

echo [调试] 步骤2: 切换到项目目录
cd /d "%~dp0"
echo 当前目录: %CD%
echo.
pause

echo [调试] 步骤3: 检查虚拟环境
if exist "venv\Scripts\activate.bat" (
    echo [OK] 虚拟环境存在
) else (
    echo [错误] 虚拟环境不存在！
    echo 完整路径: %CD%\venv\Scripts\activate.bat
    pause
    exit /b 1
)
echo.
pause

echo [调试] 步骤4: 激活虚拟环境
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [错误] 激活虚拟环境失败！
    pause
    exit /b 1
)
echo [OK] 虚拟环境已激活
echo.
pause

echo [调试] 步骤5: 检查Python
python --version
if errorlevel 1 (
    echo [错误] Python不可用！
    pause
    exit /b 1
)
echo.
pause

echo [调试] 步骤6: 检查Redis
redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo [警告] Redis不可用
    echo 将使用简单模式（不影响使用）
    set USE_SIMPLE_MODE=1
) else (
    echo [OK] Redis可用
    set USE_SIMPLE_MODE=0
)
echo.
pause

echo [调试] 步骤7: 检查app.py
if exist "app.py" (
    echo [OK] app.py存在
) else (
    echo [错误] app.py不存在！
    pause
    exit /b 1
)
echo.
pause

echo [调试] 全部检查通过！
echo.
echo 现在启动Flask应用...
echo.
pause

python app.py

pause

