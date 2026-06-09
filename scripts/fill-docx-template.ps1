param(
  [Parameter(Mandatory = $true)]
  [string]$TemplatePath,
  [Parameter(Mandatory = $true)]
  [string]$StructuredPath,
  [Parameter(Mandatory = $true)]
  [string]$OutputPath,
  [string]$ReportPath = "",
  [string]$SlotsOutput = "",
  [string]$SourcePathsOutput = "",
  [string]$MappingOutput = "",
  [string]$MappingInput = "",
  [switch]$LlmMap
)

$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "fill_docx_template.py"
$argsList = @($scriptPath, "--template", $TemplatePath, "--structured", $StructuredPath, "--output", $OutputPath)

if (-not [string]::IsNullOrWhiteSpace($ReportPath)) {
  $argsList += "--report"
  $argsList += $ReportPath
}
if (-not [string]::IsNullOrWhiteSpace($SlotsOutput)) {
  $argsList += "--slots-output"
  $argsList += $SlotsOutput
}
if (-not [string]::IsNullOrWhiteSpace($SourcePathsOutput)) {
  $argsList += "--source-paths-output"
  $argsList += $SourcePathsOutput
}
if (-not [string]::IsNullOrWhiteSpace($MappingOutput)) {
  $argsList += "--mapping-output"
  $argsList += $MappingOutput
}
if (-not [string]::IsNullOrWhiteSpace($MappingInput)) {
  $argsList += "--mapping-input"
  $argsList += $MappingInput
}
if ($LlmMap) {
  $argsList += "--llm-map"
}

python @argsList
exit $LASTEXITCODE
