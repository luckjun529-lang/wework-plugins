$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $scriptDirectory 'invoke-native-command.ps1')
$wecom = & (Join-Path $scriptDirectory 'install-wecom-cli.ps1') -PrintPath |
    Select-Object -Last 1

foreach ($name in @('WECOM_ACCESS_TOKEN', 'WECOM_BOT_ID', 'WECOM_SECRET')) {
    Remove-Item "Env:$name" -ErrorAction SilentlyContinue
}

$probeExitCode = -1
Invoke-NativeCommand `
    -Command { & $wecom contact --help } `
    -ExitCode ([ref]$probeExitCode) `
    -DiscardOutput
if ($probeExitCode -ne 0) {
    Write-Host 'WeCom CLI has no usable local robot configuration. Opening QR authorization...'
    $initExitCode = -1
    Invoke-NativeCommand `
        -Command { & $wecom init --noninteractive } `
        -ExitCode ([ref]$initExitCode)
    if ($initExitCode -ne 0) {
        throw 'WeCom QR authorization failed.'
    }
}

Invoke-NativeCommand `
    -Command { & $wecom contact --help } `
    -ExitCode ([ref]$probeExitCode) `
    -DiscardOutput
if ($probeExitCode -ne 0) {
    throw 'WeCom QR authorization did not produce a usable local configuration.'
}
Write-Host 'WeCom CLI is installed and locally configured.'
