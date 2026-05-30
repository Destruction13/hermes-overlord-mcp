param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsForBridge
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSCommandPath
$Bridge = Join-Path $Root "bridge.ps1"
if (-not (Test-Path -LiteralPath $Bridge)) {
    throw "Canonical Hermes bridge was not found at $Bridge"
}

& $Bridge @ArgsForBridge
exit $LASTEXITCODE
