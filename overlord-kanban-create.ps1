param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Title,

    [string]$Body = "",

    [string]$Workspace = "dir:C:\AI",

    [string]$Assignee = "overlord",

    [string]$Board = "overlord"
)

$ErrorActionPreference = "Stop"

$ArgsForHermes = @(
    "kanban",
    "--board",
    $Board,
    "create",
    $Title,
    "--assignee",
    $Assignee,
    "--workspace",
    $Workspace,
    "--created-by",
    "codex-overlord",
    "--json"
)

if ($Body) {
    $ArgsForHermes += @("--body", $Body)
}

& "$PSScriptRoot\overlord.ps1" @ArgsForHermes
exit $LASTEXITCODE
