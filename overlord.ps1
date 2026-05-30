param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$OverlordArgs
)

$ErrorActionPreference = "Stop"

$HermesRoot = Join-Path $env:LOCALAPPDATA "hermes"
$Python = Join-Path $HermesRoot "hermes-agent\venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Hermes Python runtime was not found at $Python"
}

$env:HERMES_HOME = $HermesRoot
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

if (-not $OverlordArgs -or $OverlordArgs.Count -eq 0) {
    $OverlordArgs = @("chat")
}

$Command = if ($OverlordArgs.Count -gt 0) { $OverlordArgs[0] } else { "chat" }
if ($Command -in @("chat", "gateway", "kanban")) {
    $EnsureObsidian = Join-Path $PSScriptRoot "ensure-obsidian.ps1"
    if (Test-Path -LiteralPath $EnsureObsidian) {
        & $EnsureObsidian | Out-Null
    }
}

& $Python -m hermes_cli.main -p overlord @OverlordArgs
exit $LASTEXITCODE
