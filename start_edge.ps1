# Start Microsoft Edge with CDP remote debugging for fara-agent
# Usage: .\start_edge.ps1 [-Port 9222] [-Profile ""] [-UserDataDir ""] [-EdgeExe ""]
# All parameters auto-detected if omitted.

param(
    [int]$Port = 9222,
    [string]$Profile = "",
    [string]$UserDataDir = "",
    [string]$EdgeExe = ""
)

# Auto-detect Edge executable
if (-not $EdgeExe) {
    $candidates = @(
        "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    )
    $EdgeExe = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $EdgeExe) { Write-Error "Edge not found. Set -EdgeExe explicitly."; exit 1 }
}

# Auto-detect user data dir
if (-not $UserDataDir) {
    $UserDataDir = "$env:LOCALAPPDATA\Microsoft\Edge\User Data"
}

# Auto-detect most recently used profile if not specified
if (-not $Profile) {
    $Profile = Get-ChildItem "$UserDataDir" -Directory |
        Where-Object { $_.Name -match "^(Default|Profile \d+)$" } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1 -ExpandProperty Name
    if (-not $Profile) { $Profile = "Default" }
    Write-Host "Auto-detected profile: $Profile"
}

# Kill anything already holding the port
$line = netstat -ano | Select-String "\s+0\.0\.0\.0:$Port\s+" | Select-Object -First 1
if (-not $line) {
    $line = netstat -ano | Select-String "\s+127\.0\.0\.1:$Port\s+" | Select-Object -First 1
}
if ($line) {
    $existingPid = ($line.ToString().Trim() -split '\s+')[-1]
    Write-Host "Killing process $existingPid on port $Port..."
    Stop-Process -Id $existingPid -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

# Close any existing Edge instances (required — debug flag only applies to new processes)
$edgeProcs = Get-Process msedge -ErrorAction SilentlyContinue
if ($edgeProcs) {
    Write-Host "Closing existing Edge processes..."
    $edgeProcs | Stop-Process -Force
    Start-Sleep -Seconds 2
}

# Launch Edge with CDP
Write-Host "Starting Edge (profile: '$Profile', CDP port: $Port)..."
Start-Process -FilePath $EdgeExe -ArgumentList `
    "--remote-debugging-port=$Port", `
    "--user-data-dir=$UserDataDir", `
    "--profile-directory=$Profile", `
    "--no-first-run", `
    "--no-default-browser-check", `
    "--start-maximized"

# Wait for CDP to be ready (up to 30 seconds)
$deadline = (Get-Date).AddSeconds(30)
while ((Get-Date) -lt $deadline) {
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:$Port/json/version" -UseBasicParsing -TimeoutSec 2
        $browser = ($r.Content | ConvertFrom-Json).Browser
        Write-Host "Edge ready: $browser (CDP on port $Port)"
        exit 0
    } catch {
        Start-Sleep -Seconds 1
    }
}

Write-Host "ERROR: Edge did not expose CDP on port $Port within 30 seconds." -ForegroundColor Red
exit 1
