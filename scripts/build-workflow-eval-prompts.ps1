$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
python (Join-Path $Root "scripts\build_workflow_eval_prompts.py")
