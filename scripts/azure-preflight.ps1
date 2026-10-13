param(
    [Parameter(Mandatory)][string]$Profile,
    [switch]$LiveChecks
)
$ErrorActionPreference = 'Stop'
$arguments = @('run', '--frozen', '--extra', 'azure', 'python', '-m', 'benchmark_harness.azure', 'preflight', '--profile', $Profile)
if ($LiveChecks) { $arguments += '--live-checks' }
& uv @arguments
exit $LASTEXITCODE
