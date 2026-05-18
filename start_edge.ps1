# Start Microsoft Edge with CDP remote debugging for fara-agent
# Usage: .\start_edge.ps1 [-Port 9222] [-Profile ""] [-UserDataDir ""] [-EdgeExe ""]
# All parameters auto-detected if omitted.

param(
    [int]$Port = 9222,
    [string]$Profile = "Default",
    [string]$UserDataDir = "",   # leave empty to use agent-local profile
    [string]$EdgeExe = "",
    [int]$TimeoutSeconds = 120
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

# Use a dedicated agent-local profile to avoid session restore / data: tab issues
if (-not $UserDataDir) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $UserDataDir = "$scriptDir\.edge-profile"
    Write-Host "Using agent-local profile: $UserDataDir"
} else {
    Write-Host "Using custom profile dir: $UserDataDir\$Profile"
}

# Kill anything already holding the port
$connections = netstat -ano | Select-String "[:.]$Port\s+\S+\s+LISTEN"
foreach ($conn in $connections) {
    $parts = $conn.ToString().Trim() -split '\s+'
    $existingPid = [int]($parts[-1])
    if ($existingPid -gt 0) {
        Write-Host "Killing process $existingPid on port $Port..."
        Stop-Process -Id $existingPid -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
    }
}

# Close any existing Edge instances (required — debug flag only applies to new processes)
$edgeProcs = Get-Process msedge -ErrorAction SilentlyContinue
if ($edgeProcs) {
    Write-Host "Closing $($edgeProcs.Count) existing Edge process(es)..."
    $edgeProcs | Stop-Process -Force
    Start-Sleep -Seconds 3
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
    # Do NOT pass a startup URL — it creates an extra tab alongside the data: init tab.
    # Navigation is handled by the agent after CDP connects.

# Wait for CDP to be ready
Write-Host "Waiting for Edge CDP (up to $TimeoutSeconds seconds)..."
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
while ((Get-Date) -lt $deadline) {
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:$Port/json/version" -UseBasicParsing -TimeoutSec 2
        $browser = ($r.Content | ConvertFrom-Json).Browser
        Write-Host "Edge ready: $browser (CDP on port $Port)"
        exit 0
    } catch {
        Start-Sleep -Seconds 2
    }
}

Write-Host "ERROR: Edge did not expose CDP on port $Port within $TimeoutSeconds seconds." -ForegroundColor Red
exit 1
