param(
    [int]$Port = 8000
)

$Host.UI.RawUI.WindowTitle = "MedGemMA Backend Logs"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Backend = Join-Path $Root "backend"
$LogDir = Join-Path $Root "logs"
$LogFile = Join-Path $LogDir "backend.log"

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$env:PYTHONIOENCODING = "utf-8"

Set-Location -LiteralPath $Backend
Write-Host "Backend: http://127.0.0.1:$Port"
Write-Host "Log file: $LogFile"

cmd /c ".\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port $Port 2>&1" |
    Tee-Object -FilePath $LogFile -Append
