param(
    [string]$NgrokPath = "ngrok",
    [int]$Port = 3000
)

$Host.UI.RawUI.WindowTitle = "MedGemMA ngrok Public URL"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$LogDir = Join-Path $Root "logs"
$LogFile = Join-Path $LogDir "ngrok.log"

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

Write-Host "Public tunnel for http://127.0.0.1:$Port"
Write-Host "Copy the Forwarding URL from this window."
Write-Host "Log file: $LogFile"

if ($env:NGROK_AUTHTOKEN) {
    & $NgrokPath config add-authtoken $env:NGROK_AUTHTOKEN | Out-Null
}

$quotedNgrok = '"' + $NgrokPath + '"'
cmd /c "$quotedNgrok http $Port 2>&1" |
    Tee-Object -FilePath $LogFile -Append
