param(
  [string]$PromptDir = "eval-prompts",
  [string]$ResultDir = "eval-results",
  [string[]]$Ids = @(),
  [int]$WaitStablePolls = 3,
  [int]$PollSeconds = 5,
  [int]$MaxPolls = 72
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName UIAutomationClient

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class DeepSeekWin32 {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int X, int Y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint dwFlags, uint dx, uint dy, int dwData, UIntPtr dwExtraInfo);
}
"@

New-Item -ItemType Directory -Force -Path $ResultDir | Out-Null

$SelectedIds = @()
foreach ($idValue in $Ids) {
  if ($idValue -and $idValue.Contains(",")) {
    $SelectedIds += ($idValue -split "," | ForEach-Object { $_.Trim() } | Where-Object { $_ })
  } elseif ($idValue) {
    $SelectedIds += $idValue
  }
}

function Get-DeepSeekRoot {
  $edge = Get-Process msedge | Where-Object {
    $_.MainWindowTitle -like "*DeepSeek*" -and $_.MainWindowHandle -ne 0
  } | Select-Object -First 1
  if (-not $edge) {
    throw "DeepSeek Edge window not found. Open chat.deepseek.com in Edge first."
  }
  [DeepSeekWin32]::ShowWindow($edge.MainWindowHandle, 3) | Out-Null
  [DeepSeekWin32]::SetForegroundWindow($edge.MainWindowHandle) | Out-Null
  Start-Sleep -Milliseconds 500
  return [System.Windows.Automation.AutomationElement]::FromHandle($edge.MainWindowHandle)
}

function Find-Controls($root, $controlType) {
  $cond = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
    $controlType
  )
  return $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $cond)
}

function Invoke-Button($button) {
  try {
    $invoke = $button.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
    $invoke.Invoke()
  } catch {
    throw "Button does not support InvokePattern: $($button.Current.Name)"
  }
}

function Click-NewChat($root) {
  $buttons = Find-Controls $root ([System.Windows.Automation.ControlType]::Button)
  for ($i = 0; $i -lt $buttons.Count; $i++) {
    $button = $buttons.Item($i)
    if ($button.Current.Name -like "*开启新对话*") {
      Invoke-Button $button
      Start-Sleep -Seconds 2
      return
    }
  }
  # DeepSeek sometimes exposes the visible new-chat control without an accessible name.
  [DeepSeekWin32]::SetCursorPos(200, 235) | Out-Null
  [DeepSeekWin32]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
  [DeepSeekWin32]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
  Start-Sleep -Seconds 2
}

function Get-Composer($root) {
  for ($attempt = 0; $attempt -lt 20; $attempt++) {
    if ($attempt -gt 0) {
      $root = Get-DeepSeekRoot
    }
    $edits = Find-Controls $root ([System.Windows.Automation.ControlType]::Edit)
    for ($i = 0; $i -lt $edits.Count; $i++) {
      $edit = $edits.Item($i)
      $rect = $edit.Current.BoundingRectangle
      if (
        -not [double]::IsInfinity($rect.X) -and
        $rect.X -gt 500 -and
        $rect.Y -gt 400 -and
        $rect.Width -gt 300 -and
        $rect.Height -gt 40
      ) {
        return $edit
      }
    }
    Start-Sleep -Milliseconds 500
  }
  throw "DeepSeek composer edit box not found."
}

function Get-SendButton($root) {
  $buttons = Find-Controls $root ([System.Windows.Automation.ControlType]::Button)
  $candidate = $null
  for ($i = 0; $i -lt $buttons.Count; $i++) {
    $button = $buttons.Item($i)
    $rect = $button.Current.BoundingRectangle
    if ([double]::IsInfinity($rect.X) -or [double]::IsInfinity($rect.Y)) {
      continue
    }
    if ($rect.X -ge 1450 -and $rect.X -le 1560 -and $rect.Y -ge 580 -and $rect.Y -le 1000) {
      $candidate = $button
    }
  }
  if (-not $candidate) {
    throw "Send button near composer bottom-right not found."
  }
  return $candidate
}

function Get-PageText($root, [int]$maxChars = 400000) {
  $docs = Find-Controls $root ([System.Windows.Automation.ControlType]::Document)
  if (-not $docs -or $docs.Count -eq 0) {
    return ""
  }
  $doc = if ($docs -is [System.Windows.Automation.AutomationElement]) { $docs } else { $docs.Item(0) }
  $tp = $doc.GetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern)
  return $tp.DocumentRange.GetText($maxChars)
}

function Send-Prompt($root, [string]$prompt) {
  $composer = Get-Composer $root
  $composer.SetFocus()
  $value = $composer.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern)
  $value.SetValue($prompt)
  Start-Sleep -Milliseconds 800
  $send = Get-SendButton $root
  Invoke-Button $send
  Start-Sleep -Seconds 3
  $remaining = $value.Current.Value.Length
  if ($remaining -ne 0) {
    throw "Composer was not cleared after sending; prompt may not have been sent."
  }
}

function Wait-ForStableReply($root) {
  $lastLength = 0
  $stableCount = 0
  $lastText = ""
  for ($poll = 0; $poll -lt $MaxPolls; $poll++) {
    Start-Sleep -Seconds $PollSeconds
    $text = Get-PageText $root
    $length = $text.Length
    Write-Host ("poll={0} chars={1}" -f $poll, $length)
    if ($length -eq $lastLength -and $length -gt 1000) {
      $stableCount++
    } else {
      $stableCount = 0
    }
    $lastLength = $length
    $lastText = $text
    if ($stableCount -ge $WaitStablePolls) {
      break
    }
  }
  return $lastText
}

$manifestPath = Join-Path $PromptDir "manifest.json"
$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$items = if ($manifest.PSObject.Properties.Name -contains "items") { $manifest.items } else { $manifest }

foreach ($item in $items) {
  $id = $item.id
  if ($SelectedIds.Count -gt 0 -and $SelectedIds -notcontains $id) {
    continue
  }
  $promptPath = $item.prompt_file
  if (-not [System.IO.Path]::IsPathRooted($promptPath)) {
    $promptPath = Join-Path $PromptDir $promptPath
  }
  $resultPath = Join-Path $ResultDir ($id + "-deepseek-raw.txt")
  if (-not (Test-Path -LiteralPath $promptPath)) {
    throw "Prompt file not found: $promptPath"
  }

  Write-Host "=== Running $id ==="
  $root = Get-DeepSeekRoot
  Click-NewChat $root
  Start-Sleep -Seconds 5
  $root = Get-DeepSeekRoot
  $prompt = Get-Content -LiteralPath $promptPath -Raw -Encoding UTF8
  $prompt = $prompt + "`n`nAt the very end, output exactly one separate line: EVAL_DONE_$($id.Replace('-', '_'))"
  Send-Prompt $root $prompt
  $text = Wait-ForStableReply $root
  $text | Set-Content -LiteralPath $resultPath -Encoding UTF8
  Write-Host ("saved={0} chars={1}" -f $resultPath, $text.Length)
}
