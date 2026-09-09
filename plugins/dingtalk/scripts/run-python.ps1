param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$ScriptPath,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ScriptArguments
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $scriptDirectory 'invoke-dws.ps1')

$python = Get-Command python3 -ErrorAction SilentlyContinue
$pythonPrefix = @()
if ($null -eq $python) {
    $python = Get-Command python -ErrorAction SilentlyContinue
}
if ($null -eq $python) {
    $python = Get-Command py -ErrorAction SilentlyContinue
    if ($null -ne $python) {
        $pythonPrefix = @('-3')
    }
}
if ($null -eq $python) {
    throw 'Python 3 is required (python3, python, or the Windows py launcher).'
}
$pythonExitCode = -1
Invoke-NativeCommand `
    -Command { & $python.Source @pythonPrefix $ScriptPath @ScriptArguments } `
    -ExitCode ([ref]$pythonExitCode)
exit $pythonExitCode
