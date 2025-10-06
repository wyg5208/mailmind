# AI邮件简报系统 - 快速重启脚本
# 用于重新加载新添加的路由

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AI邮件简报系统 - 快速重启" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 停止所有Python进程
Write-Host "[1/3] 停止现有Python进程..." -ForegroundColor Yellow
$pythonProcesses = Get-Process python* -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    $pythonProcesses | Stop-Process -Force
    Write-Host "  ✓ 已停止 $($pythonProcesses.Count) 个Python进程" -ForegroundColor Green
    Start-Sleep -Seconds 2
} else {
    Write-Host "  ✓ 没有运行中的Python进程" -ForegroundColor Green
}

# 切换到项目目录
Write-Host ""
Write-Host "[2/3] 切换到项目目录..." -ForegroundColor Yellow
Set-Location -Path "D:\python_projects\fecth_email_with_ai"
Write-Host "  ✓ 当前目录: $(Get-Location)" -ForegroundColor Green

# 启动应用
Write-Host ""
Write-Host "[3/3] 启动应用..." -ForegroundColor Yellow
Write-Host "  使用: start_simple.bat" -ForegroundColor Cyan
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  按任意键启动应用..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# 启动应用
.\start_simple.bat


