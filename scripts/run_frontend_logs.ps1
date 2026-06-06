param(
    [int]$Port = 3000
)

$Host.UI.RawUI.WindowTitle = "MedGemMA Frontend Logs"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Frontend = Join-Path $Root "frontend"
$LogDir = Join-Path $Root "logs"
$LogFile = Join-Path $LogDir "frontend.log"

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

Set-Location -LiteralPath $Frontend
Write-Host "Frontend: http://127.0.0.1:$Port"
Write-Host "Log file: $LogFile"

cmd /c "npm.cmd run dev -- --host 0.0.0.0 --port $Port 2>&1" |
    Tee-Object -FilePath $LogFile -Append
