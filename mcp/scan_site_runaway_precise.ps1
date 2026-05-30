$ErrorActionPreference = 'Stop'
$regex = 'work kanban task|trainer-premium-landing|vite preview --host 127\.0\.0\.1 --port 4173|chrome-devtools-mcp|playwright-mcp|playwright_chromiumdev_profile|@roxybrowser\\playwright-mcp|@roxybrowser/playwright-mcp'
$selfPid = $PID
$rows = Get-CimInstance Win32_Process | Where-Object {
    $_.ProcessId -ne $selfPid -and $_.CommandLine -and ($_.CommandLine -match $regex)
} | Sort-Object ProcessId | Select-Object ProcessId, ParentProcessId, Name, CommandLine
if (-not $rows) {
    Write-Output 'NO_MATCHES'
    exit 0
}
foreach ($p in $rows) {
    $cmd = [regex]::Replace($p.CommandLine, '(?i)(api[_-]?key|token|password|secret|authorization)(=|\s+)[^\s]+', '$1$2[REDACTED]')
    Write-Output ("PID={0} PPID={1} NAME={2} CMD={3}" -f $p.ProcessId, $p.ParentProcessId, $p.Name, $cmd)
}
exit 1
