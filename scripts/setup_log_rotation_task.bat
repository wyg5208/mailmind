@echo off
chcp 65001 >nul
echo ====================================
echo   配置Windows任务计划器
echo   用于AI邮件简报系统日志轮转
echo ====================================
echo.

set TASK_NAME=AI邮件简报系统-日志轮转
set SCRIPT_PATH=%~dp0rotate_logs.ps1
set PROJECT_DIR=%~dp0..

echo [信息] 任务配置:
echo   - 任务名称: %TASK_NAME%
echo   - 脚本路径: %SCRIPT_PATH%
echo   - 执行时间: 每天凌晨02:00
echo   - 运行账户: SYSTEM
echo.

echo [信息] 检查是否已存在同名任务...
schtasks /Query /TN "%TASK_NAME%" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [警告] 发现已存在的任务,将删除后重新创建...
    schtasks /Delete /TN "%TASK_NAME%" /F
    echo [成功] 旧任务已删除
    echo.
)

echo [信息] 创建新的计划任务...
schtasks /Create /SC DAILY /TN "%TASK_NAME%" /TR "powershell.exe -ExecutionPolicy Bypass -NoProfile -File \"%SCRIPT_PATH%\"" /ST 02:00 /RU SYSTEM /RL HIGHEST /F

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ====================================
    echo   [成功] 计划任务创建成功!
    echo ====================================
    echo.
    echo 任务详情:
    echo   - 任务名称: %TASK_NAME%
    echo   - 执行时间: 每天凌晨02:00
    echo   - 脚本路径: %SCRIPT_PATH%
    echo   - 运行权限: SYSTEM账户(最高权限)
    echo.
    echo ====================================
    echo   测试命令
    echo ====================================
    echo.
    echo 1. 查看任务详情:
    echo    schtasks /Query /TN "%TASK_NAME%" /V /FO LIST
    echo.
    echo 2. 立即运行任务测试:
    echo    schtasks /Run /TN "%TASK_NAME%"
    echo.
    echo 3. 查看任务执行历史:
    echo    打开任务计划器(taskschd.msc),找到任务,查看"历史记录"选项卡
    echo.
    echo 4. 手动测试轮转脚本:
    echo    powershell.exe -ExecutionPolicy Bypass -File "%SCRIPT_PATH%"
    echo.
    echo ====================================
    echo.
    
    choice /C YN /M "是否立即运行任务进行测试?"
    if %ERRORLEVEL% EQU 1 (
        echo.
        echo [信息] 开始运行任务...
        schtasks /Run /TN "%TASK_NAME%"
        echo.
        echo [提示] 任务已触发,请检查logs目录查看结果
        echo        日志目录: %PROJECT_DIR%\logs
        echo.
    )
) else (
    echo.
    echo ====================================
    echo   [错误] 计划任务创建失败!
    echo ====================================
    echo.
    echo 可能的原因:
    echo   1. 没有管理员权限
    echo   2. 任务计划器服务未启动
    echo   3. 脚本路径包含特殊字符
    echo.
    echo 解决方法:
    echo   1. 右键此脚本,选择"以管理员身份运行"
    echo   2. 检查服务: services.msc 查找 Task Scheduler
    echo   3. 确保脚本路径不含中文或特殊字符
    echo.
)

echo.
pause

