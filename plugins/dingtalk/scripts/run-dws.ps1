param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$DwsArguments
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $scriptDirectory 'invoke-dws.ps1')
$dwsExitCode = -1
Invoke-NativeCommand `
    -Command { & (Join-Path $scriptDirectory 'run-python.ps1') -ScriptPath (Join-Path $scriptDirectory 'dws.py') @DwsArguments } `
    -ExitCode ([ref]$dwsExitCode)
exit $dwsExitCode
