$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $scriptDirectory 'invoke-native-command.ps1')
$lark = & (Join-Path $scriptDirectory 'install-lark-cli.ps1') |
    Select-Object -Last 1

foreach ($name in @(
    'LARKSUITE_CLI_USER_ACCESS_TOKEN',
    'LARKSUITE_CLI_BRAND',
    'LARKSUITE_CLI_APP_ID'
)) {
    Remove-Item "Env:$name" -ErrorAction SilentlyContinue
}
$env:LARKSUITE_CLI_NO_UPDATE_NOTIFIER = '1'
$env:LARKSUITE_CLI_NO_SKILLS_NOTIFIER = '1'

function Test-LarkUserAuth {
    $statusExitCode = -1
    $status = Invoke-NativeCommand `
        -Command { & $lark auth status --json 2>$null } `
        -ExitCode ([ref]$statusExitCode) | Out-String
    return $statusExitCode -eq 0 -and
        $status -match '"identity"\s*:\s*"user"'
}

$configExitCode = -1
Invoke-NativeCommand `
    -Command { & $lark config show } `
    -ExitCode ([ref]$configExitCode) `
    -DiscardOutput
if ($configExitCode -ne 0) {
    Write-Host 'Lark CLI is not configured. Complete the Feishu QR setup shown below.'
    Invoke-NativeCommand `
        -Command { & $lark config init --new --brand feishu --lang zh } `
        -ExitCode ([ref]$configExitCode)
    if ($configExitCode -ne 0) {
        throw 'Lark CLI configuration was not completed.'
    }
}

if (-not (Test-LarkUserAuth)) {
    Write-Host 'Lark CLI has no local user authorization. Complete the browser authorization below.'
    $loginExitCode = -1
    Invoke-NativeCommand `
        -Command { & $lark auth login --recommend } `
        -ExitCode ([ref]$loginExitCode)
    if ($loginExitCode -ne 0) {
        throw 'Lark user authorization failed.'
    }
}

if (-not (Test-LarkUserAuth)) {
    throw 'Lark authorization did not produce a usable local user identity.'
}
Write-Host 'Lark CLI is installed, configured and locally authorized.'
