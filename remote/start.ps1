[CmdletBinding()]
param([switch]$LocalOnly,[switch]$NoOpen,[switch]$UseDockerBridge)
$ErrorActionPreference = 'Stop'
$projectDir = Split-Path $PSScriptRoot -Parent
$runtimeDir = Join-Path $projectDir '.runtime'
New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
Set-Location -LiteralPath $projectDir
$nodeExe = Join-Path $projectDir 'runtime\node.exe'
if (-not (Test-Path -LiteralPath $nodeExe)) { $nodeExe = (Get-Command node -ErrorAction SilentlyContinue).Source }
if (-not $nodeExe) { throw 'Download the Windows portable release ZIP, or install Node.js 22.12+ before running the source checkout.' }
if (-not (Test-Path -LiteralPath (Join-Path $projectDir 'node_modules\puppeteer-core\package.json'))) {
    & npm ci
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
}
$browserExe = @('C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe','C:\Program Files\Microsoft\Edge\Application\msedge.exe','C:\Program Files\Google\Chrome\Application\chrome.exe') | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $browserExe) { throw 'Microsoft Edge or Google Chrome must be installed on the render computer.' }
$gpuKey = 'HKCU:\Software\Microsoft\DirectX\UserGpuPreferences'
New-Item -Path $gpuKey -Force | Out-Null
$oldPreference = (Get-ItemProperty -LiteralPath $gpuKey -Name $browserExe -ErrorAction SilentlyContinue).$browserExe
$backupPath = Join-Path $runtimeDir 'gpu-preference-before.json'
if (-not (Test-Path -LiteralPath $backupPath)) { @{browser=$browserExe;previous=$oldPreference} | ConvertTo-Json | Set-Content -LiteralPath $backupPath -Encoding UTF8 }
$newPreference = 'GpuPreference=2;' + ([string]$oldPreference -replace 'GpuPreference=\d+;','')
New-ItemProperty -LiteralPath $gpuKey -Name $browserExe -Value $newPreference -PropertyType String -Force | Out-Null
$env:DAYLIGHT_BROWSER = $browserExe
$env:DAYLIGHT_BIND = if ($UseDockerBridge) { '0.0.0.0' } else { '127.0.0.1' }
Write-Host 'Dedicated GPU preference selected. Starting the daylight renderer...'
$running = $false
try { $health = Invoke-RestMethod 'http://127.0.0.1:5182/health' -TimeoutSec 2; $running = $health.service -eq 'cleveland-daylight-host' } catch {}
if ($running) {
    $existingStatePath = Join-Path $runtimeDir 'host.json'
    if (-not (Test-Path -LiteralPath $existingStatePath)) { throw 'Another copy is already running on port 5182. Stop that copy before starting this one.' }
    $existingState = Get-Content -LiteralPath $existingStatePath -Raw | ConvertFrom-Json
    if ($health.pid -and $existingState.pid -ne $health.pid) { throw 'Another copy owns port 5182. Stop that copy first.' }
}
if (-not $running) {
    $serverPath = Join-Path $PSScriptRoot 'server.mjs'
    $hostProcess = Start-Process -FilePath $nodeExe -ArgumentList @(('"' + $serverPath + '"')) -WorkingDirectory $projectDir -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDir 'host.log') -RedirectStandardError (Join-Path $runtimeDir 'host-error.log') -PassThru
    $limit = (Get-Date).AddSeconds(25)
    do {
        Start-Sleep -Milliseconds 500
        if ($hostProcess.HasExited) { throw (Get-Content (Join-Path $runtimeDir 'host-error.log') -Raw) }
        try { $health = Invoke-RestMethod 'http://127.0.0.1:5182/health' -TimeoutSec 2; $running = $health.service -eq 'cleveland-daylight-host' } catch {}
    } until ($running -or (Get-Date) -gt $limit)
    if (-not $running) { throw 'The daylight host did not start. See .runtime\host-error.log.' }
    $awakePath = Join-Path $PSScriptRoot 'keep-awake.ps1'
    Start-Process powershell.exe -ArgumentList @('-NoProfile','-File',('"'+$awakePath+'"'),'-HostProcessId',$hostProcess.Id) -WindowStyle Hidden | Out-Null
}
$hostState = Get-Content (Join-Path $runtimeDir 'host.json') -Raw | ConvertFrom-Json
$localUrl = 'http://127.0.0.1:5182/#' + $hostState.token
if (-not $LocalOnly -and -not $UseDockerBridge) {
    $tailscaleExe = (Get-Command tailscale -ErrorAction SilentlyContinue).Source
    if (-not $tailscaleExe -and (Test-Path 'C:\Program Files\Tailscale\tailscale.exe')) { $tailscaleExe = 'C:\Program Files\Tailscale\tailscale.exe' }
    if (-not $tailscaleExe) { throw 'Install Tailscale on this computer and phone once, sign in, then rerun START-DAYLIGHT.cmd. Download: https://tailscale.com/download/windows' }
    $tailnetState = (& $tailscaleExe status --json | Out-String) | ConvertFrom-Json
    if ($tailnetState.BackendState -ne 'Running') {
        Write-Host 'Sign into the Tailscale Windows app, then rerun START-DAYLIGHT.cmd.'
        if (-not $NoOpen) { Start-Process 'C:\Program Files\Tailscale\tailscale-ipn.exe' }
        exit 2
    }
    $serveState = (& $tailscaleExe serve status --json | Out-String) | ConvertFrom-Json
    $phonePort = 0
    foreach ($candidate in 5182..5192) {
        $tcp = if ($serveState.TCP) { $serveState.TCP.PSObject.Properties[[string]$candidate] } else { $null }
        $mappingKey = $tailnetState.Self.DNSName.TrimEnd('.') + ':' + $candidate
        $mapping = if ($serveState.Web) { $serveState.Web.PSObject.Properties[$mappingKey] } else { $null }
        $handler = if ($mapping) { $mapping.Value.Handlers.PSObject.Properties['/'].Value } else { $null }
        if (-not $tcp -or ($handler -and $handler.Proxy -eq 'http://127.0.0.1:5182')) { $phonePort = $candidate; break }
    }
    if ($phonePort -eq 0) { throw 'No unused private phone port is available in 5182-5192.' }
    & $tailscaleExe serve --bg --yes --https=$phonePort http://127.0.0.1:5182
    if ($LASTEXITCODE -ne 0) { throw 'Tailscale Serve needs attention. Complete any Tailscale HTTPS authorization shown above, then rerun the launcher.' }
    $phoneBase = 'https://' + $tailnetState.Self.DNSName.TrimEnd('.') + ':' + $phonePort + '/'
    @{phone_url=$phoneBase} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtimeDir 'connection.json') -Encoding UTF8
    Write-Host 'PRIVATE PHONE LINK (keep private):'
    Write-Host ($phoneBase + '#' + $hostState.token)
    Write-Host 'Enable Tailscale on the phone. The render computer must stay running.'
}
if (-not $LocalOnly -and $UseDockerBridge) {
    $dockerExe = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $dockerExe) { throw 'Install and start Docker Desktop once for the private phone bridge, then run START-DAYLIGHT.cmd again. The local renderer is running.' }
    & docker version --format '{{.Server.Version}}' 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        $desktopExe = 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
        if (Test-Path -LiteralPath $desktopExe) { Start-Process -FilePath $desktopExe -WindowStyle Hidden | Out-Null }
        Write-Host 'Waiting for Docker Desktop...'
        $limit = (Get-Date).AddSeconds(120)
        do { Start-Sleep -Seconds 3; & docker version --format '{{.Server.Version}}' 2>$null | Out-Null } until ($LASTEXITCODE -eq 0 -or (Get-Date) -gt $limit)
        if ($LASTEXITCODE -ne 0) { throw 'Start Docker Desktop and finish its first-time setup, then run this launcher again.' }
    }
    $bridgeScript = Join-Path $PSScriptRoot 'tailscale-mobile-preview.ps1'
    $bridgeName = 'daylight-' + ($env:COMPUTERNAME.ToLower() -replace '[^a-z0-9-]','-')
    $raw = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $bridgeScript -Action expose -LocalPort 5182 -BridgeHostname $bridgeName
    $resultCode = $LASTEXITCODE
    if ($raw) { $connection = ($raw -join "`n") | ConvertFrom-Json }
    if ($connection.status -eq 'needs_login') {
        Write-Host 'One-time Tailscale sign-in is required. Authorize this computer in the browser, then rerun START-DAYLIGHT.cmd.'
        Write-Host $connection.auth_url
        if (-not $NoOpen) { Start-Process $connection.auth_url }
        exit 2
    }
    if ($resultCode -ne 0 -or $connection.status -ne 'exposed') { throw 'Private phone access did not start. Check Docker Desktop and the bridge output.' }
    @{phone_url=$connection.phone_url} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtimeDir 'connection.json') -Encoding UTF8
    $phoneUrl = $connection.phone_url + '#' + $hostState.token
    Write-Host ''
    Write-Host 'PRIVATE PHONE LINK (keep private):'
    Write-Host $phoneUrl
    Write-Host 'Enable Tailscale on the phone. The computer and Docker Desktop must stay running.'
}
Write-Host ''
Write-Host 'Open the local dashboard and choose Connect phone for its QR code.'
Write-Host $localUrl
Write-Host 'Use STOP-DAYLIGHT.cmd to stop the renderer. Windows sleep is prevented while it runs.'
if (-not $NoOpen) { Start-Process $localUrl }
