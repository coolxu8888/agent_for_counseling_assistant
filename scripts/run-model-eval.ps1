param(
  [string]$Ids = "",
  [switch]$All,
  [switch]$DryRun,
  [switch]$NoClean,
  [switch]$StopOnError,
  [string]$ResultDir = "",
  [string]$Manifest = ""
)

$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "run_model_eval.py"
$argsList = @($scriptPath)

if (-not [string]::IsNullOrWhiteSpace($Ids)) {
  $argsList += "--ids"
  $argsList += $Ids
}

if ($All) {
  $argsList += "--all"
}

if ($DryRun) {
  $argsList += "--dry-run"
}

if ($NoClean) {
  $argsList += "--no-clean"
}

if ($StopOnError) {
  $argsList += "--stop-on-error"
}

if (-not [string]::IsNullOrWhiteSpace($ResultDir)) {
  $argsList += "--result-dir"
  $argsList += $ResultDir
}

if (-not [string]::IsNullOrWhiteSpace($Manifest)) {
  $argsList += "--manifest"
  $argsList += $Manifest
}

python @argsList
exit $LASTEXITCODE
