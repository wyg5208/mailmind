# AI邮件简报系统 - 日志轮转脚本
# 用于Windows任务计划器定时执行
# 建议每天凌晨2点执行(避开0点的业务高峰)

param(
    [string]$LogDir = "D:\python_projects\fecth_email_with_ai\logs",
    [string]$LogFile = "email_digest.log",
    [int]$KeepDays = 30
)

# 获取当前日期(YYYY_MM_DD格式)
$dateStr = Get-Date -Format "yyyy_MM_dd"
$yesterday = (Get-Date).AddDays(-1).ToString("yyyy_MM_dd")

# 日志文件路径
$currentLog = Join-Path $LogDir $LogFile
$archivedLog = Join-Path $LogDir "$([System.IO.Path]::GetFileNameWithoutExtension($LogFile))_$yesterday.log"

Write-Host "======================================"
Write-Host "  日志轮转脚本开始执行"
Write-Host "  时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host "======================================"
Write-Host ""

# 检查日志目录是否存在
if (-not (Test-Path $LogDir)) {
    Write-Host "[错误] 日志目录不存在: $LogDir" -ForegroundColor Red
    exit 1
}

# 检查当前日志文件是否存在
if (-not (Test-Path $currentLog)) {
    Write-Host "[警告] 当前日志文件不存在: $currentLog" -ForegroundColor Yellow
    exit 0
}

# 检查文件大小
$fileSize = (Get-Item $currentLog).Length
$fileSizeMB = [math]::Round($fileSize / 1MB, 2)
Write-Host "[信息] 当前日志文件大小: $fileSizeMB MB"

# 如果文件为空或很小,跳过轮转
if ($fileSize -lt 1KB) {
    Write-Host "[跳过] 日志文件太小,无需轮转"
    exit 0
}

try {
    # 方案1: 复制后清空(推荐,避免多进程访问冲突)
    Write-Host "[步骤1] 复制日志文件到归档: $archivedLog"
    Copy-Item -Path $currentLog -Destination $archivedLog -Force
    
    Write-Host "[步骤2] 清空原日志文件(保留文件句柄)"
    # 使用.NET方法清空文件,避免删除重建导致的多进程冲突
    [System.IO.File]::WriteAllText($currentLog, "", [System.Text.Encoding]::UTF8)
    
    Write-Host "[成功] 日志轮转完成" -ForegroundColor Green
    Write-Host "  - 归档文件: $archivedLog ($fileSizeMB MB)"
    Write-Host "  - 原文件已清空"
    
} catch {
    Write-Host "[错误] 日志轮转失败: $_" -ForegroundColor Red
    Write-Host "错误详情: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# 清理旧日志文件
Write-Host ""
Write-Host "[步骤3] 清理 $KeepDays 天前的旧日志..."

$cutoffDate = (Get-Date).AddDays(-$KeepDays)
$oldLogs = Get-ChildItem -Path $LogDir -Filter "*_*.log" | Where-Object {
    $_.LastWriteTime -lt $cutoffDate
}

if ($oldLogs.Count -eq 0) {
    Write-Host "[信息] 没有需要清理的旧日志文件"
} else {
    Write-Host "[信息] 找到 $($oldLogs.Count) 个旧日志文件需要删除:"
    foreach ($log in $oldLogs) {
        try {
            $logSizeMB = [math]::Round($log.Length / 1MB, 2)
            Write-Host "  - 删除: $($log.Name) ($logSizeMB MB, 最后修改: $($log.LastWriteTime.ToString('yyyy-MM-dd')))"
            Remove-Item -Path $log.FullName -Force
        } catch {
            Write-Host "  [警告] 删除失败: $($log.Name) - $_" -ForegroundColor Yellow
        }
    }
    Write-Host "[成功] 旧日志清理完成" -ForegroundColor Green
}

Write-Host ""
Write-Host "======================================"
Write-Host "  日志轮转脚本执行完成"
Write-Host "  时间: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host "======================================"

