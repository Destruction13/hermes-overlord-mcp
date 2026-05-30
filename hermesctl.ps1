param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsForHermesCtl
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSCommandPath
$Python = $env:HERMES_PYTHON
if (-not $Python) {
    $HermesHome = if ($env:HERMES_HOME) { $env:HERMES_HOME } else { Join-Path $env:LOCALAPPDATA "hermes" }
    $Candidate = Join-Path $HermesHome "hermes-agent\venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $Candidate) {
        $Python = $Candidate
    } else {
        $Python = "python"
    }
}

& $Python (Join-Path $Root "hermesctl.py") @ArgsForHermesCtl
exit $LASTEXITCODE
