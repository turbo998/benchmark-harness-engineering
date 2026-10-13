param(
    [Parameter(Mandatory)][string]$Profile,
    [Parameter(Mandatory)][string]$VmName,
    [Parameter(Mandatory)][string]$ScriptPath,
    [Parameter(Mandatory)][string]$AttemptId,
    [Parameter(Mandatory)][uri]$OutputBlobUri,
    [Parameter(Mandatory)][uri]$ErrorBlobUri,
    [ValidateRange(1, 3600)][int]$TimeoutSeconds = 900,
    [switch]$ApprovedRunCommand
)
$ErrorActionPreference = 'Stop'
if (-not $ApprovedRunCommand) { throw 'Explicit owned-VM command approval is required.' }
& uv run --frozen --extra azure python -m benchmark_harness.azure preflight --profile $Profile --live-checks
if ($LASTEXITCODE -ne 0) { throw 'Azure preflight failed; no VM command was dispatched.' }
$config = Get-Content -Raw -LiteralPath $Profile | ConvertFrom-Json
if (-not $config.approvals.cloud_apply) { throw 'Profile does not approve VM resource changes.' }
if ($AttemptId -notmatch '^[A-Za-z0-9_-]{1,20}$') { throw 'Unsafe attempt identifier.' }
$vmJson = & az vm show --resource-group $config.resource_group --name $VmName --subscription $config.subscription_id --output json --only-show-errors
if ($LASTEXITCODE -ne 0) { throw 'Cannot verify owned VM.' }
$vm = $vmJson | ConvertFrom-Json
if ($vm.tags.project -ne 'benchmark-harness-engineering' -or $vm.tags.run_id -ne $config.run_id) {
    throw 'VM is not owned by this experiment.'
}
if ($vm.identity -and $vm.identity.type -ne 'None') { throw 'Untrusted runner must not have a managed identity.' }
$commandName = "bh-$($config.run_id)-$AttemptId"
if ($commandName.Length -gt 64) { throw 'Run Command name exceeds its bound.' }
foreach ($uri in @($OutputBlobUri, $ErrorBlobUri)) {
    $expectedHost = "$($config.storage.account).blob.core.windows.net"
    $expectedPrefix = "/$($config.storage.artifacts_container)/$($config.run_id)/$AttemptId/"
    if ($uri.Scheme -ne 'https' -or $uri.Host -ne $expectedHost -or
        -not $uri.AbsolutePath.StartsWith($expectedPrefix, [StringComparison]::Ordinal) -or
        -not $uri.Query -or $uri.UserInfo -or $uri.Fragment) {
        throw 'Full append-log URIs must be privately authorized blobs scoped to this run/attempt.'
    }
}
if ($OutputBlobUri.AbsoluteUri -eq $ErrorBlobUri.AbsoluteUri) { throw 'Separate stdout/stderr append logs are required.' }
$existingJson = & az vm run-command list --resource-group $config.resource_group --vm-name $VmName --subscription $config.subscription_id --output json --only-show-errors
if ($LASTEXITCODE -ne 0) { throw 'Cannot verify fresh attempt command; nothing was dispatched.' }
$existing = $existingJson | ConvertFrom-Json
if ($existing | Where-Object { $_.name -eq $commandName -or $_.id.EndsWith("/runCommands/$commandName", [StringComparison]::OrdinalIgnoreCase) }) {
    throw 'Attempt command already exists; inspect its evidence instead of replaying it.'
}
$script = Get-Content -Raw -LiteralPath $ScriptPath
& az vm run-command create --resource-group $config.resource_group --vm-name $VmName --name $commandName --subscription $config.subscription_id --script $script --output-blob-uri $OutputBlobUri.AbsoluteUri --error-blob-uri $ErrorBlobUri.AbsoluteUri --timeout-in-seconds $TimeoutSeconds --output none --only-show-errors
if ($LASTEXITCODE -ne 0) { throw 'Dispatch failed or is uncertain; inspect the owned command before any retry.' }
$viewJson = & az vm run-command show --resource-group $config.resource_group --vm-name $VmName --name $commandName --subscription $config.subscription_id --expand instanceView --query "{executionState:instanceView.executionState,exitCode:instanceView.exitCode,startTime:instanceView.startTime,endTime:instanceView.endTime}" --output json --only-show-errors
if ($LASTEXITCODE -ne 0) { throw 'Could not retrieve script terminal state; completion is unknown.' }
$view = $viewJson | ConvertFrom-Json
if ($view.executionState -ne 'Succeeded' -or $view.exitCode -ne 0) {
    throw 'Script did not report successful terminal execution; preserve partial evidence before retry.'
}
Write-Output $viewJson
Write-Warning 'InstanceView contains only the last 4 KB. Verify full append-blob logs and artifact hashes separately.'
