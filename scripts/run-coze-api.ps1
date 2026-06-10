param(
  [string]$HostName = "127.0.0.1",
  [int]$Port = 8770
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $ScriptDir

Set-Location $Root
python scripts\coze_api_server.py --host $HostName --port $Port
