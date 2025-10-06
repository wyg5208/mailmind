@echo off
chcp 65001 > nul
echo ========================================
echo   重载 Nginx 配置
echo ========================================
echo.

echo [信息] 测试 Nginx 配置...
d:\nginx\nginx.exe -t

if %errorlevel% neq 0 (
    echo.
    echo [错误] Nginx 配置测试失败！
    echo [建议] 请检查配置文件语法
    pause
    exit /b 1
)

echo.
echo [成功] 配置测试通过
echo.
echo [信息] 重载 Nginx...

d:\nginx\nginx.exe -s reload

if %errorlevel% equ 0 (
    echo.
    echo [成功] Nginx 配置已重载
    echo.
    echo [提示] 新的超时配置已生效：
    echo   - AI助手API: 180秒（3分钟）
    echo   - 其他API: 120秒（2分钟）
) else (
    echo.
    echo [错误] Nginx 重载失败
    echo [建议] 请检查 Nginx 是否正在运行
)

echo.
pause

