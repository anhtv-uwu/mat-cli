# Windows PowerShell 5.1 and PowerShell 7. No external Java is required.
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$heapSize = if ($env:MAT_CLI_HEAP) { $env:MAT_CLI_HEAP } else { '2g' }
if ($heapSize -cnotmatch '^[1-9][0-9]*[mMgG]$') {
    [Console]::Error.WriteLine('MAT_CLI_HEAP must be a positive size, for example 2g or 4096m')
    exit 2
}
$application = 'CliMatPlugin.agent'
$userArguments = @($args)
if ($userArguments.Count -gt 0 -and $userArguments[0] -ceq 'legacy') {
    $application = 'CliMatPlugin.execute'
    $userArguments = @($userArguments | Select-Object -Skip 1)
}
$java = Join-Path $root 'jre/bin/java.exe'
$launchers = @(Get-ChildItem -LiteralPath (Join-Path $root 'mat/plugins') -Filter 'org.eclipse.equinox.launcher_*.jar')
if ($launchers.Count -ne 1 -or -not (Test-Path -LiteralPath $java -PathType Leaf)) {
    [Console]::Error.WriteLine('Incomplete bundle: expected bundled JRE and one Equinox launcher')
    exit 1
}
# Encode each argument using the Windows native argv quoting rules. This avoids
# Windows PowerShell 5.1 dropping embedded quotes from OQL expressions.
function ConvertTo-NativeArgument([string] $value) {
    $escaped = [regex]::Replace($value, '(\\*)"', '$1$1\"')
    $escaped = [regex]::Replace($escaped, '(\\+)$', '$1$1')
    return '"' + $escaped + '"'
}
# Java 21's Windows launcher can lose non-ANSI characters in native argv.
# Send the original working directory and user argv as UTF-8/Base64; the app
# decodes them before normal CLI parsing. No commands or scripts are evaluated.
$originalDirectory = (Get-Location).ProviderPath
$payload = (@($originalDirectory) + $userArguments) -join [char]0
$encodedArguments = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($payload))
$nativeArguments = @("-Xmx$heapSize", '-Djava.awt.headless=true', '-Dfile.encoding=UTF-8',
    '-Dstdout.encoding=UTF-8', '-Dstderr.encoding=UTF-8', "-Dmat.cli.arguments=$encodedArguments",
    '-jar', ('plugins/' + $launchers[0].Name), '-nosplash', '-data', '@none',
    '-configuration', 'configuration', '-application', $application)
$startInfo = New-Object System.Diagnostics.ProcessStartInfo
$startInfo.FileName = $java
$startInfo.UseShellExecute = $false
# Relative JVM/bootstrap paths also support a bundle path containing Unicode.
$startInfo.WorkingDirectory = Join-Path $root 'mat'
$startInfo.Arguments = ($nativeArguments | ForEach-Object { ConvertTo-NativeArgument $_ }) -join ' '
try {
    $process = [System.Diagnostics.Process]::Start($startInfo)
    $process.WaitForExit()
    $code = $process.ExitCode
    $process.Dispose()
    exit $code
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}
