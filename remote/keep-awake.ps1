param([int]$HostProcessId)
Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public static class DaylightPower { [DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint flags); }'
try {
    [DaylightPower]::SetThreadExecutionState([uint32]2147483649) | Out-Null
    while (Get-Process -Id $HostProcessId -ErrorAction SilentlyContinue) { Start-Sleep -Seconds 15 }
} finally { [DaylightPower]::SetThreadExecutionState([uint32]2147483648) | Out-Null }
