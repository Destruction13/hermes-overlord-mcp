param(
    [switch]$Kill
)
$ErrorActionPreference = 'Stop'
$patterns = @(
    'trainer-premium-landing',
    't_f969f134',
    't_b3641807',
    'playwright_chromiumdev_profile',
    'chrome-devtools-mcp',
    'playwright-mcp',
    'ms-playwright',
    'remote-debugging-port',
    'site-check',
    'site checking',
    'premium-landing',
    'work kanban task',
    'kanban task',
    'npm run dev',
    'pnpm dev',
    'yarn dev',
    'vite',
    'playwright',
    'chromium'
)
$regex = ($patterns | ForEach-Object { [regex]::Escape($_) }) -join '|'
$selfPid = $PID
$rows = Get-CimInstance Win32_Process |
    Where-Object {
        $_.ProcessId -ne $selfPid -and
        $_.CommandLine -and
        ($_.CommandLine -match $regex)
    } |
    Sort-Object ProcessId |
    Select-Object ProcessId, ParentProcessId, Name, CommandLine

if (-not $rows) {
    Write-Output 'NO_MATCHES'
    exit 0
}

Write-Output 'MATCHES:'
foreach ($p in $rows) {
    $cmd = $p.CommandLine
    $cmd = [regex]::Replace($cmd, '(?i)(api[_-]?key|token|password|secret|authorization)(=|\s+)[^\s]+', '$1$2[REDACTED]')
    Write-Output ("PID={0} PPID={1} NAME={2} CMD={3}" -f $p.ProcessId, $p.ParentProcessId, $p.Name, $cmd)
}

if ($Kill) {
    Write-Output 'KILLING:'
    foreach ($p in $rows) {
        try {
            Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop
            Write-Output ("KILLED PID={0} NAME={1}" -f $p.ProcessId, $p.Name)
        } catch {
            Write-Output ("FAILED PID={0} NAME={1} ERROR={2}" -f $p.ProcessId, $p.Name, $_.Exception.Message)
        }
    }
}
