param(
  [Parameter(Mandatory = $true)]
  [string]$Workflow,
  [Alias("Input")]
  [string]$InputText = "",
  [string]$InputFile = "",
  [string]$RunRoot = "",
  [string]$RunDir = "",
  [switch]$DryRun,
  [switch]$NoClean,
  [switch]$Structured,
  [string]$Model = "",
  [string]$RetrievalMap = "",
  [string]$RagRoot = ""
)

$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "run_agent.py"
$argsList = @($scriptPath, "--workflow", $Workflow)

if (-not [string]::IsNullOrWhiteSpace($InputText)) {
  $argsList += "--input"
  $argsList += $InputText
}

if (-not [string]::IsNullOrWhiteSpace($InputFile)) {
  $argsList += "--input-file"
  $argsList += $InputFile
}

if (-not [string]::IsNullOrWhiteSpace($RunRoot)) {
  $argsList += "--run-root"
  $argsList += $RunRoot
}

if (-not [string]::IsNullOrWhiteSpace($RunDir)) {
  $argsList += "--run-dir"
  $argsList += $RunDir
}

if ($DryRun) {
  $argsList += "--dry-run"
}

if ($NoClean) {
  $argsList += "--no-clean"
}

if ($Structured) {
  $argsList += "--structured"
}

if (-not [string]::IsNullOrWhiteSpace($Model)) {
  $argsList += "--model"
  $argsList += $Model
}

if (-not [string]::IsNullOrWhiteSpace($RetrievalMap)) {
  $argsList += "--retrieval-map"
  $argsList += $RetrievalMap
}

if (-not [string]::IsNullOrWhiteSpace($RagRoot)) {
  $argsList += "--rag-root"
  $argsList += $RagRoot
}

python @argsList
exit $LASTEXITCODE
