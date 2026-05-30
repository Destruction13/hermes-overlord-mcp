param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$BotToken,

    [string]$AllowedUsers = "",

    [string]$HomeChannel = "",

    [string]$HomeChannelName = "Hermes Overlord",


    [switch]$RestartGateway
)

$ErrorActionPreference = "Stop"

$HermesRoot = Join-Path $env:LOCALAPPDATA "hermes"
$ProfileRoot = Join-Path $HermesRoot "profiles\overlord"
$EnvPath = Join-Path $ProfileRoot ".env"
$Python = Join-Path $HermesRoot "hermes-agent\venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $ProfileRoot)) {
    throw "Overlord profile was not found at $ProfileRoot"
}

if (-not (Test-Path -LiteralPath $EnvPath)) {
    New-Item -ItemType File -Path $EnvPath -Force | Out-Null
}

function Set-DotEnvValue {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Value
    )

    $lines = @(Get-Content -LiteralPath $Path -ErrorAction SilentlyContinue)
    $escaped = $Value.Replace('`', '``').Replace('"', '\"')
    $line = "$Name=`"$escaped`""
    $found = $false

    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match "^\s*$([regex]::Escape($Name))=") {
            $lines[$i] = $line
            $found = $true
        }
    }

    if (-not $found) {
        $lines += $line
    }

    Set-Content -LiteralPath $Path -Value $lines -Encoding UTF8
}

Set-DotEnvValue -Path $EnvPath -Name "TELEGRAM_BOT_TOKEN" -Value $BotToken
Set-DotEnvValue -Path $EnvPath -Name "TELEGRAM_REPLY_TO_MODE" -Value "all"

if ($AllowedUsers) {
    Set-DotEnvValue -Path $EnvPath -Name "TELEGRAM_ALLOWED_USERS" -Value $AllowedUsers
}

if ($HomeChannel) {
    Set-DotEnvValue -Path $EnvPath -Name "TELEGRAM_HOME_CHANNEL" -Value $HomeChannel
    Set-DotEnvValue -Path $EnvPath -Name "TELEGRAM_HOME_CHANNEL_NAME" -Value $HomeChannelName
}

if (Test-Path -LiteralPath $Python) {
    & $Python -c "from tools.lazy_deps import ensure; ensure('platform.telegram', prompt=False)" | Out-Null
}

if ($RestartGateway) {
    & (Join-Path $PSScriptRoot "overlord.ps1") gateway restart | Out-Null
}

Write-Host "Telegram gateway config updated for Overlord. Token value was not printed."
if (-not $RestartGateway) {
    Write-Host "Run: .\overlord.ps1 gateway restart"
}
