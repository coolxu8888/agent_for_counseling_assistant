param(
  [Parameter(Mandatory = $true)]
  [string]$InputPath,
  [Parameter(Mandatory = $true)]
  [string]$OutputPath,
  [string]$CheckOutput = ""
)

$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "render_docx.py"
$argsList = @($scriptPath, "--input", $InputPath, "--output", $OutputPath)

if (-not [string]::IsNullOrWhiteSpace($CheckOutput)) {
  $argsList += "--check-output"
  $argsList += $CheckOutput
}

python @argsList
exit $LASTEXITCODE
