[CmdletBinding()]
param(
    [ValidateSet("status", "expose", "disable", "list")]
    [string]$Action = "status",
    [ValidateRange(1, 65535)]
    [int]$LocalPort = 1,
    [ValidateRange(0, 65535)]
    [int]$PublicPort = 0,
    [string]$BridgeContainer = "codex-tailscale-bridge",
    [string]$BridgeHostname = "sammy-dev-bridge",
    [string]$StateVolume = "codex-tailscale-state",
    [switch]$SkipBackendCheck
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$socket = "/tmp/tailscaled.sock"

function Invoke-Docker {
    param([Parameter(Mandatory)][string[]]$Arguments, [switch]$AllowFailure)
    $output = & docker @Arguments 2>&1
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0 -and -not $AllowFailure) {
        throw "docker $($Arguments -join ' ') failed: $($output -join [Environment]::NewLine)"
    }
    return [pscustomobject]@{ Output = @($output); ExitCode = $exitCode }
}

function Get-BridgeStatus {
    $result = Invoke-Docker -Arguments @("exec", $BridgeContainer, "tailscale", "--socket=$socket", "status", "--json")
    return (($result.Output -join "`n") | ConvertFrom-Json)
}

function Ensure-Bridge {
    $dockerVersion = Invoke-Docker -Arguments @("version", "--format", "{{.Server.Version}}") -AllowFailure
    if ($dockerVersion.ExitCode -ne 0) {
        throw "Docker Desktop is not available. Start Docker Desktop before exposing a site."
    }

    $inspect = Invoke-Docker -Arguments @("inspect", $BridgeContainer, "--format", "{{.State.Status}}") -AllowFailure
    if ($inspect.ExitCode -ne 0) {
        [void](Invoke-Docker -Arguments @("volume", "create", $StateVolume))
        [void](Invoke-Docker -Arguments @(
            "run", "-d", "--name", $BridgeContainer, "--restart", "unless-stopped",
            "--entrypoint", "tailscaled", "-v", "${StateVolume}:/var/lib/tailscale",
            "tailscale/tailscale:stable", "--state=/var/lib/tailscale/tailscaled.state",
            "--socket=$socket", "--tun=userspace-networking", "--socks5-server=localhost:1055"
        ))
        Start-Sleep -Seconds 2
        [void](Invoke-Docker -Arguments @(
            "exec", "-d", $BridgeContainer, "tailscale", "--socket=$socket", "up",
            "--hostname=$BridgeHostname", "--accept-dns=false"
        ))
        Start-Sleep -Seconds 3
    } elseif (($inspect.Output -join "").Trim() -ne "running") {
        [void](Invoke-Docker -Arguments @("start", $BridgeContainer))
        Start-Sleep -Seconds 2
    }

    return Get-BridgeStatus
}

function Write-JsonResult {
    param([Parameter(Mandatory)]$Value)
    $Value | ConvertTo-Json -Depth 8
}

function Get-PhoneHost {
    param([Parameter(Mandatory)]$Status)
    $dnsName = [string]$Status.Self.DNSName
    if (-not [string]::IsNullOrWhiteSpace($dnsName)) { return $dnsName.TrimEnd(".") }
    if ($Status.TailscaleIPs.Count -gt 0) { return [string]$Status.TailscaleIPs[0] }
    throw "The bridge has no tailnet hostname or IP."
}

function Test-Backend {
    param([Parameter(Mandatory)][int]$Port)
    $probe = Invoke-Docker -Arguments @(
        "exec", $BridgeContainer, "wget", "-S", "-O", "/dev/null", "--timeout=5",
        "http://host.docker.internal:$Port/"
    ) -AllowFailure
    $text = $probe.Output -join "`n"
    if ($probe.ExitCode -eq 0 -or $text -match "HTTP/[0-9.]+ [1-5][0-9][0-9]") {
        return [pscustomobject]@{ Reachable = $true; Detail = ($text -split "`n" | Select-Object -First 1) }
    }
    return [pscustomobject]@{ Reachable = $false; Detail = $text }
}

$status = Ensure-Bridge
if ([string]$status.BackendState -ne "Running") {
    Write-JsonResult ([ordered]@{
        status = "needs_login"
        backend_state = [string]$status.BackendState
        auth_url = [string]$status.AuthURL
        bridge = $BridgeContainer
        next_step = "Open auth_url on a signed-in tailnet device, authorize the bridge, then rerun this command."
    })
    exit 2
}

$phoneHost = Get-PhoneHost -Status $status

switch ($Action) {
    "status" {
        Write-JsonResult ([ordered]@{
            status = "running"
            bridge = $BridgeContainer
            hostname = $phoneHost
            tailnet = [string]$status.CurrentTailnet.Name
            tailscale_ips = @($status.TailscaleIPs)
        })
    }
    "list" {
        $serveStatus = Invoke-Docker -Arguments @("exec", $BridgeContainer, "tailscale", "--socket=$socket", "serve", "status", "--json")
        $serveStatus.Output -join "`n"
    }
    "expose" {
        if ($LocalPort -eq 1) { throw "-LocalPort is required for Action expose." }
        if ($PublicPort -eq 0) { $PublicPort = $LocalPort }
        $backend = if ($SkipBackendCheck) {
            [pscustomobject]@{ Reachable = $true; Detail = "Backend check skipped by caller." }
        } else {
            Test-Backend -Port $LocalPort
        }
        if (-not $backend.Reachable) {
            Write-JsonResult ([ordered]@{
                status = "backend_unreachable"
                local_port = $LocalPort
                detail = $backend.Detail
                next_step = "Start the site and ensure it is reachable from Docker at host.docker.internal:$LocalPort."
            })
            exit 3
        }
        [void](Invoke-Docker -Arguments @(
            "exec", $BridgeContainer, "tailscale", "--socket=$socket", "serve", "--yes", "--bg",
            "--http=$PublicPort", "http://host.docker.internal:$LocalPort"
        ))
        $portSuffix = if ($PublicPort -eq 80) { "" } else { ":$PublicPort" }
        Write-JsonResult ([ordered]@{
            status = "exposed"
            private = $true
            public_funnel = $false
            local_port = $LocalPort
            tailnet_port = $PublicPort
            phone_url = "http://${phoneHost}${portSuffix}/"
            backend_check = $backend.Detail
            requirements = @("Tailscale enabled on the phone", "Docker Desktop running", "Project server running")
        })
    }
    "disable" {
        if ($PublicPort -eq 0) { throw "-PublicPort is required for Action disable." }
        [void](Invoke-Docker -Arguments @(
            "exec", $BridgeContainer, "tailscale", "--socket=$socket", "serve", "--http=$PublicPort", "off"
        ))
        Write-JsonResult ([ordered]@{
            status = "disabled"
            tailnet_port = $PublicPort
            bridge = $BridgeContainer
        })
    }
}
