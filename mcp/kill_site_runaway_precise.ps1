$ErrorActionPreference = 'Stop'

# Precise kill set for the runaway site work only. Avoid broad browser matches
# such as regular Edge/WebView crashpad processes.
$explicitRegex = 'work kanban task|trainer-premium-landing|chrome-devtools-mcp|playwright-mcp|playwright_chromiumdev_profile|@roxybrowser\\playwright-mcp|@roxybrowser/playwright-mcp'
$parentRegex = 'vite preview --host 127\.0\.0\.1 --port 4173|npx\.cmd .*chrome-devtools-mcp|npx-cli\.js.*chrome-devtools-mcp|playwright-mcp\.cmd|cmd\.exe .*chrome-devtools-mcp|npx\.cmd .*playwright-mcp|npx-cli\.js.*playwright-mcp|cmd\.exe .*playwright-mcp'

$all = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine } |
    Select-Object ProcessId, ParentProcessId, Name, CommandLine
$byPid = @{}
foreach ($p in $all) { $byPid[[int]$p.ProcessId] = $p }

$kill = @{}
foreach ($p in $all) {
    if ($p.CommandLine -match $explicitRegex) {
        $kill[[int]$p.ProcessId] = $true
    }
}

# Include descendants of explicit matches.
$changed = $true
while ($changed) {
    $changed = $false
    foreach ($p in $all) {
        $procId = [int]$p.ProcessId
        $parentId = [int]$p.ParentProcessId
        if (-not $kill.ContainsKey($procId) -and $kill.ContainsKey($parentId)) {
            $kill[$procId] = $true
            $changed = $true
        }
    }
}

# Include only narrow wrapper parents for matched children (cmd/npx/vite wrappers).
$changed = $true
while ($changed) {
    $changed = $false
    foreach ($procIdObj in @($kill.Keys)) {
        $procId = [int]$procIdObj
        if (-not $byPid.ContainsKey($procId)) { continue }
        $parentId = [int]$byPid[$procId].ParentProcessId
        if ($parentId -le 0 -or $kill.ContainsKey($parentId) -or -not $byPid.ContainsKey($parentId)) { continue }
        $parent = $byPid[$parentId]
        if ($parent.CommandLine -match $parentRegex) {
            $kill[$parentId] = $true
            $changed = $true
        }
    }
}

$targets = @()
foreach ($procIdObj in $kill.Keys) {
    $procId = [int]$procIdObj
    if ($byPid.ContainsKey($procId)) { $targets += $byPid[$procId] }
}
$targets = $targets | Sort-Object ProcessId -Descending

if (-not $targets) {
    Write-Output 'NO_TARGETS'
    exit 0
}

Write-Output 'TARGETS:'
foreach ($p in ($targets | Sort-Object ProcessId)) {
    $cmd = [regex]::Replace($p.CommandLine, '(?i)(api[_-]?key|token|password|secret|authorization)(=|\s+)[^\s]+', '$1$2[REDACTED]')
    Write-Output ("PID={0} PPID={1} NAME={2} CMD={3}" -f $p.ProcessId, $p.ParentProcessId, $p.Name, $cmd)
}

Write-Output 'KILLING:'
foreach ($p in $targets) {
    try {
        Stop-Process -Id ([int]$p.ProcessId) -Force -ErrorAction Stop
        Write-Output ("KILLED PID={0} NAME={1}" -f $p.ProcessId, $p.Name)
    } catch {
        Write-Output ("FAILED PID={0} NAME={1} ERROR={2}" -f $p.ProcessId, $p.Name, $_.Exception.Message)
    }
}

Start-Sleep -Milliseconds 800

$remaining = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and ($_.CommandLine -match $explicitRegex -or $_.CommandLine -match 'trainer-premium-landing')
} | Select-Object ProcessId, ParentProcessId, Name, CommandLine
if ($remaining) {
    Write-Output 'REMAINING:'
    foreach ($p in ($remaining | Sort-Object ProcessId)) {
        $cmd = [regex]::Replace($p.CommandLine, '(?i)(api[_-]?key|token|password|secret|authorization)(=|\s+)[^\s]+', '$1$2[REDACTED]')
        Write-Output ("PID={0} PPID={1} NAME={2} CMD={3}" -f $p.ProcessId, $p.ParentProcessId, $p.Name, $cmd)
    }
    exit 1
}
Write-Output 'REMAINING: NONE'
