param(
    [Parameter(Mandatory)][string]$Profile,
    [Parameter(Mandatory)][string]$ResourceInventory,
    [Parameter(Mandatory)][string]$ExportReceipt,
    [switch]$ApprovedDelete
)
$ErrorActionPreference = 'Stop'
& uv run --frozen --extra azure python -m benchmark_harness.azure cleanup-plan --profile $Profile --resources $ResourceInventory --receipt $ExportReceipt
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if ($ApprovedDelete) {
    & uv run --frozen --extra azure python -m benchmark_harness.azure cleanup --profile $Profile --receipt $ExportReceipt --approved-delete
}
exit $LASTEXITCODE
