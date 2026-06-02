$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "clean_eval_outputs.py"
python $scriptPath
