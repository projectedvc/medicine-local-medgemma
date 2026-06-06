param(
    [Parameter(Mandatory = $true)]
    [int]$Port,
    [string]$Label = "Service"
)

$ErrorActionPreference = "Stop"

$listeners = netstat.exe -ano |
    Select-String -Pattern "^\s*TCP\s+\S+:$Port\s+\S+\s+LISTENING\s+(\d+)\s*$"

$processIds = @()
foreach ($listener in $listeners) {
    $match = [regex]::Match($listener.Line, "LISTENING\s+(\d+)\s*$")
    if ($match.Success) {
        $processIds += [int]$match.Groups[1].Value
    }
}

$processIds = $processIds | Sort-Object -Unique | Where-Object { $_ -gt 0 -and $_ -ne $PID }

if (-not $processIds) {
    Write-Host "$Label port $Port is free."
    exit 0
}

foreach ($processId in $processIds) {
    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if ($process) {
        Write-Host "Stopping $Label port ${Port}: PID $processId ($($process.ProcessName))"
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    } else {
        Write-Host "Stopping $Label port ${Port}: PID $processId"
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    }
}
