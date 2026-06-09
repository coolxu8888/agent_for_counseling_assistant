param(
  [Parameter(Mandatory = $true)]
  [string]$TemplatePath,
  [Parameter(Mandatory = $true)]
  [string]$StructuredPath,
  [Parameter(Mandatory = $true)]
  [string]$OutputPath,
  [string]$ReportPath = ""
)

$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "fill_docx_template.py"
$argsList = @($scriptPath, "--template", $TemplatePath, "--structured", $StructuredPath, "--output", $OutputPath)

if (-not [string]::IsNullOrWhiteSpace($ReportPath)) {
  $argsList += "--report"
  $argsList += $ReportPath
}

python @argsList
exit $LASTEXITCODE
