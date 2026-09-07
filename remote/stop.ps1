$ErrorActionPreference='Stop'
$projectDir=Split-Path $PSScriptRoot -Parent
$statePath=Join-Path $projectDir '.runtime\host.json'
if (-not (Test-Path -LiteralPath $statePath)) { Write-Host 'This copy is not running.'; exit }
$state=Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
$ownedProcess=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$state.pid)
$expected=Join-Path $PSScriptRoot 'server.mjs'
if ($ownedProcess -and $ownedProcess.CommandLine.Contains($expected)) {
    & taskkill.exe /PID $state.pid /T /F
    Write-Host 'Daylight renderer stopped. Normal sleep behavior resumes shortly.'
} else { Write-Host 'The recorded process is no longer this daylight host.' }
