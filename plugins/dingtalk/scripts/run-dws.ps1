param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$DwsArguments
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $scriptDirectory 'invoke-dws.ps1')
$dws = & (Join-Path $scriptDirectory 'install-dws.ps1') -PrintPath |
    Select-Object -Last 1
$dwsExitCode = -1
Invoke-NativeCommand `
    -Command { & $dws @DwsArguments } `
    -ExitCode ([ref]$dwsExitCode)
exit $dwsExitCode
