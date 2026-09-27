param(
    [string]$OffTime = "21:00",
    [string]$OnTime  = "23:00",
    [string]$OffCommand = "foot off",
    [string]$OnCommand  = "foot on",
    [switch]$Remove
)

# 注册/删除两个 Windows 计划任务：
#   每天 $OffTime 执行 python jomoo_toilet.py foot off（关闭脚感）
#   每天 $OnTime  执行 python jomoo_toilet.py foot on （打开脚感）
#
# 用法：
#   powershell -ExecutionPolicy Bypass -File .\setup_schedule.ps1
#   powershell -ExecutionPolicy Bypass -File .\setup_schedule.ps1 -OffTime 22:00 -OnTime 07:00
#   powershell -ExecutionPolicy Bypass -File .\setup_schedule.ps1 -OffCommand 'multi "foot off" "set autocover off"' -OnCommand 'multi "foot on" "set autocover on"'
#   powershell -ExecutionPolicy Bypass -File .\setup_schedule.ps1 -Remove
#
# 说明：
#   - 任务以当前用户身份运行，仅在用户登录时执行（BLE 需要用户会话）
#   - 通过 pythonw + run_silent.pyw 静默运行，不弹出黑色控制台窗口
#   - 运行日志追加写入 logs 目录
#   - 电脑睡眠时会唤醒执行；错过的时间点开机后自动补跑

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$tool = Join-Path $root "jomoo_toilet.py"
$logDir = Join-Path $root "logs"

$tasks = @(
    [pscustomobject]@{ Name = "JOMOO_Foot_Off"; At = $OffTime; Arg = $OffCommand; Log = "foot_off.log"; Desc = "每天 $OffTime 执行: $OffCommand" },
    [pscustomobject]@{ Name = "JOMOO_Foot_On";  At = $OnTime;  Arg = $OnCommand;  Log = "foot_on.log";  Desc = "每天 $OnTime 执行: $OnCommand" }
)

if ($Remove) {
    foreach ($t in $tasks) {
        if (Get-ScheduledTask -TaskName $t.Name -ErrorAction SilentlyContinue) {
            Unregister-ScheduledTask -TaskName $t.Name -Confirm:$false
            Write-Host "已删除计划任务: $($t.Name)"
        } else {
            Write-Host "计划任务不存在: $($t.Name)"
        }
    }
    exit 0
}

$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { throw "找不到 python，请先安装 Python 并加入 PATH" }
$pyw = Join-Path (Split-Path -Parent $py) "pythonw.exe"
if (-not (Test-Path -LiteralPath $pyw)) { throw "找不到 pythonw.exe（应与 python.exe 同目录）" }
$launcher = Join-Path $root "run_silent.pyw"
if (-not (Test-Path -LiteralPath $launcher)) { throw "找不到静默启动器: $launcher" }
if (-not (Test-Path -LiteralPath $tool)) { throw "找不到脚本: $tool" }

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

foreach ($t in $tasks) {
    $log = Join-Path $logDir $t.Log
    # pythonw 是 GUI 子系统程序，本身不创建控制台；run_silent.pyw 负责把输出写入日志
    $action = New-ScheduledTaskAction -Execute $pyw `
        -Argument "`"$launcher`" `"$log`" $($t.Arg)" `
        -WorkingDirectory $root
    $trigger = New-ScheduledTaskTrigger -Daily -At $t.At
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -StartWhenAvailable -WakeToRun -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
        -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName $t.Name -Action $action -Trigger $trigger `
        -Settings $settings -Description $t.Desc -Force | Out-Null
    Write-Host "已创建计划任务: $($t.Name)  每天 $($t.At)  ->  python jomoo_toilet.py $($t.Arg)（pythonw 静默运行）"
}

Write-Host ""
Write-Host "完成。查看: Get-ScheduledTask -TaskName JOMOO_Foot_*"
Write-Host "日志目录: $logDir"
Write-Host "删除任务: powershell -ExecutionPolicy Bypass -File .\setup_schedule.ps1 -Remove"
