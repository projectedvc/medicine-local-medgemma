param(
    [string]$BaseUrl = "https://shiny-net-slimy.ngrok-free.dev"
)

$ErrorActionPreference = "Stop"
$base = $BaseUrl.TrimEnd("/")
$headers = @{ "ngrok-skip-browser-warning" = "true" }

Write-Host "Checking $base"

$health = Invoke-RestMethod -Uri "$base/health" -Headers $headers
Write-Host "Health:" ($health | ConvertTo-Json -Compress)

if (-not $health.service) {
    Write-Warning "This looks like the small AI service, not the medicine backend. Expected a 'service' field."
}

$body = @{ login = "radiologist"; password = "radio123" } | ConvertTo-Json
try {
    $login = Invoke-RestMethod -Uri "$base/api/auth/login" -Method Post -ContentType "application/json" -Body $body -Headers $headers
    Write-Host "Login OK:" ($login.user.login)
} catch {
    $status = $_.Exception.Response.StatusCode.value__
    Write-Error "Login failed with HTTP $status. The public domain is not serving medicine backend /api routes."
}
