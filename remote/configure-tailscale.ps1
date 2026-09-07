[CmdletBinding()]
param([ValidateSet('enable','disable')][string]$Action='enable')
$ErrorActionPreference='Stop'
trap { Write-Output $_.Exception.Message; exit 1 }
$projectDir=Split-Path $PSScriptRoot -Parent
$runtimeDir=Join-Path $projectDir '.runtime'
$configPath=Join-Path $runtimeDir 'connection.json'
$tailscaleExe=(Get-Command tailscale -ErrorAction SilentlyContinue).Source
if (-not $tailscaleExe -and (Test-Path 'C:\Program Files\Tailscale\tailscale.exe')) { $tailscaleExe='C:\Program Files\Tailscale\tailscale.exe' }
if (-not $tailscaleExe) { throw 'Install Tailscale only if you want browser access from another device. Moonlight and local use need no Tailscale.' }
if ($Action -eq 'disable') {
    if (Test-Path -LiteralPath $configPath) {
        $config=Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
        if ($config.phone_url) {
            $url=[Uri]$config.phone_url
            $serveState=(& $tailscaleExe serve status --json | Out-String) | ConvertFrom-Json
            $mapping=if ($serveState.Web) { $serveState.Web.PSObject.Properties[$url.Authority] } else { $null }
            $handler=if ($mapping) { $mapping.Value.Handlers.PSObject.Properties['/'].Value } else { $null }
            if ($handler -and $handler.Proxy -eq 'http://127.0.0.1:5182') {
                & $tailscaleExe serve --https=$($url.Port) off | Out-Null
                if ($LASTEXITCODE -ne 0) { throw 'Could not disable this app Tailscale mapping.' }
            }
        }
    }
    @{phone_url=$null;enabled=$false} | ConvertTo-Json | Set-Content -LiteralPath $configPath -Encoding UTF8
    Write-Host 'Browser access disabled. Moonlight and the local dashboard keep working.'
    exit 0
}
    $tailnetState = (& $tailscaleExe status --json | Out-String) | ConvertFrom-Json
    if ($tailnetState.BackendState -ne 'Running') {
        throw 'Sign into the Tailscale Windows app first, then enable browser access again.'
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
    @{phone_url=$phoneBase;enabled=$true} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtimeDir 'connection.json') -Encoding UTF8
Write-Host 'Private browser access enabled.'
