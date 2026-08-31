$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

. (Join-Path $PSScriptRoot 'invoke-native-command.ps1')

$nativeExecutable = if (-not [string]::IsNullOrWhiteSpace($env:ComSpec)) {
    $env:ComSpec
} else {
    '/bin/sh'
}
$nativeArguments = if (-not [string]::IsNullOrWhiteSpace($env:ComSpec)) {
    @('/d', '/s', '/c', 'echo normal-output & echo normal-auth-progress 1>&2 & exit /b 3')
} else {
    @('-c', 'echo normal-output; echo normal-auth-progress >&2; exit 3')
}

$exitCode = -1
Invoke-NativeCommand `
    -Command { & $nativeExecutable @nativeArguments } `
    -ExitCode ([ref]$exitCode) `
    -DiscardOutput

if ($exitCode -ne 3) {
    throw "Expected native exit code 3, got $exitCode."
}

Write-Host 'Lark native-command boundary test passed.'
