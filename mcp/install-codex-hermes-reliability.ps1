param(
    [switch]$StartNow
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$UserId = "{0}\{1}" -f $env:USERDOMAIN, $env:USERNAME

function Register-HermesTask {
    param(
        [string]$TaskName,
        [string]$ScriptPath,
        [string]$Description
    )

    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument (
        '-NoLogo -NoProfile -ExecutionPolicy Bypass -File "{0}" -Quiet' -f $ScriptPath
    )
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $UserId
    $settings = New-ScheduledTaskSettingsSet `
        -MultipleInstances IgnoreNew `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 1) `
        -StartWhenAvailable `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit ([TimeSpan]::Zero)

    try {
        $principal = New-ScheduledTaskPrincipal -UserId $UserId -LogonType Interactive -RunLevel Highest
        Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $Description -Force -ErrorAction Stop | Out-Null
        return "scheduled-task"
    } catch {
        try {
            $principal = New-ScheduledTaskPrincipal -UserId $UserId -LogonType Interactive -RunLevel Limited
            Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description $Description -Force -ErrorAction Stop | Out-Null
            return "scheduled-task"
        } catch {
            $startupDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
            New-Item -ItemType Directory -Force -Path $startupDir | Out-Null
            $cmdPath = Join-Path $startupDir ("{0}.cmd" -f $TaskName)
            $content = "@echo off`r`nstart `"`" /min powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`" -Quiet`r`n"
            Set-Content -LiteralPath $cmdPath -Value $content -Encoding ASCII
            return "startup-folder"
        }
    }
}

$serviceScript = Join-Path $Root "mcp\run-hermes-overlord-mcp-http.ps1"
$watchdogScript = Join-Path $Root "mcp\codex-hermes-watchdog.ps1"

$serviceMode = Register-HermesTask `
    -TaskName "Hermes_Codex_MCP_Service" `
    -ScriptPath $serviceScript `
    -Description "Persistent local HTTP MCP service for Codex -> Hermes Overlord."

$watchdogMode = Register-HermesTask `
    -TaskName "Hermes_Codex_MCP_Watchdog" `
    -ScriptPath $watchdogScript `
    -Description "Healthchecks and restarts the Codex -> Hermes MCP bridge and Overlord gateway."

if ($StartNow) {
    if ($serviceMode -eq "scheduled-task") {
        Start-ScheduledTask -TaskName "Hermes_Codex_MCP_Service" -ErrorAction SilentlyContinue
    } else {
        Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $serviceScript) -WindowStyle Hidden | Out-Null
    }
    Start-Sleep -Seconds 3
    if ($watchdogMode -eq "scheduled-task") {
        Start-ScheduledTask -TaskName "Hermes_Codex_MCP_Watchdog" -ErrorAction SilentlyContinue
    } else {
        Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $watchdogScript, "-Quiet") -WindowStyle Hidden | Out-Null
    }
}

[pscustomobject]@{ Component = "Hermes_Codex_MCP_Service"; InstallMode = $serviceMode }
[pscustomobject]@{ Component = "Hermes_Codex_MCP_Watchdog"; InstallMode = $watchdogMode }
