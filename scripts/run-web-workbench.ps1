param(
  [string]$HostName = "127.0.0.1",
  [int]$Port = 8765
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir

Set-Location $Root
python scripts\web_workbench.py --host $HostName --port $Port
