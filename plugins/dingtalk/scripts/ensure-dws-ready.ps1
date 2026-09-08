$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $scriptDirectory 'invoke-dws.ps1')
$dwsExitCode = -1
Invoke-NativeCommand `
    -Command { & (Join-Path $scriptDirectory 'run-dws.ps1') plugin-health } `
    -ExitCode ([ref]$dwsExitCode)
exit $dwsExitCode
