param(
    [switch]$Help,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsForBridge
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSCommandPath
$HermesHome = Join-Path $env:LOCALAPPDATA "hermes"
$Python = Join-Path $HermesHome "hermes-agent\venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Hermes Python runtime was not found at $Python"
}

function Convert-BridgeArgs {
    param([string[]]$ArgsIn)
    $map = @{
        "-TaskId" = "--task-id"
        "-Board" = "--board"
        "-Root" = "--root"
        "-Workspace" = "--workspace"
        "-Assignee" = "--assignee"
        "-Mode" = "--mode"
        "-Priority" = "--priority"
        "-IdempotencyKey" = "--idempotency-key"
        "-MaxRuntime" = "--max-runtime"
        "-MaxChildren" = "--max-children"
        "-LogTailBytes" = "--log-tail-bytes"
        "-Dispatch" = "--dispatch"
        "-NoMicroReports" = "--no-micro-reports"
        "-DryRun" = "--dry-run"
        "-Deep" = "--deep"
        "-Human" = "--human"
        "-HeartbeatPrompt" = "heartbeat-prompt"
    }
    $out = @()
    foreach ($arg in $ArgsIn) {
        if ($map.ContainsKey($arg)) { $out += $map[$arg] } else { $out += $arg }
    }
    return $out
}

$env:HERMES_HOME = $HermesHome
$env:HERMES_BRIDGE_ROOT = $Root
$env:PYTHONPATH = if ($env:PYTHONPATH) { "$Root;$env:PYTHONPATH" } else { $Root }
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:HERMES_QUIET = "1"
$env:HERMES_REDACT_SECRETS = "true"

if ($Help) {
    & $Python -m bridge.cli --help
    exit $LASTEXITCODE
}

$NormalizedArgs = @(Convert-BridgeArgs -ArgsIn $ArgsForBridge)
& $Python -m bridge.cli @NormalizedArgs
exit $LASTEXITCODE
