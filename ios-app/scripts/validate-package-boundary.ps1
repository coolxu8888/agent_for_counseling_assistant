$ErrorActionPreference = "Stop"

$iosRoot = Split-Path -Parent $PSScriptRoot
$repoRoot = Split-Path -Parent $iosRoot

$required = @(
    "project.yml",
    "Config/Shared.xcconfig",
    "Config/Debug.xcconfig",
    "Config/Release.xcconfig",
    "CounselorAssistant/App/CounselorAssistantApp.swift",
    "CounselorAssistant/Resources/Info.plist",
    "CounselorAssistant/Resources/PrivacyInfo.xcprivacy"
)

$errors = @()
foreach ($relative in $required) {
    $path = Join-Path $iosRoot $relative
    if (-not (Test-Path -LiteralPath $path)) {
        $errors += "Missing required iOS file: $relative"
    }
}

$forbiddenNames = @(".env", "render.yaml", "requirements.txt", "workbench-run-log.jsonl")
foreach ($name in $forbiddenNames) {
    $matches = Get-ChildItem -LiteralPath $iosRoot -Recurse -Force -File | Where-Object { $_.Name -eq $name }
    foreach ($match in $matches) {
        $errors += "Forbidden packaged file: $($match.FullName)"
    }
}

$forbiddenSegments = @("web-workbench", "agent-runs", "workbench-data", "eval-results", "rag", "coze")
$allPaths = Get-ChildItem -LiteralPath $iosRoot -Recurse -Force
foreach ($item in $allPaths) {
    $relative = $item.FullName.Substring($iosRoot.Length).TrimStart([char[]]@("\", "/")).Replace("\", "/").ToLowerInvariant()
    foreach ($segment in $forbiddenSegments) {
        if (($relative -split "/") -contains $segment) {
            $errors += "Forbidden iOS package segment '$segment': $relative"
        }
    }
}

$secretPattern = '(?i)(sk-[a-z0-9]{16,}|deepseek_api_key\s*=\s*[^$\s]|coze_demo_api_key\s*=\s*[^$\s])'
$textFiles = Get-ChildItem -LiteralPath $iosRoot -Recurse -Force -File | Where-Object {
    $_.Extension -in @(".swift", ".plist", ".xcprivacy", ".xcconfig", ".yml", ".yaml", ".md", ".json")
}
foreach ($file in $textFiles) {
    $content = Get-Content -LiteralPath $file.FullName -Raw
    if ($content -match $secretPattern) {
        $errors += "Possible secret in iOS package: $($file.FullName)"
    }
}

if ($errors.Count -gt 0) {
    $errors | ForEach-Object { Write-Error $_ }
    exit 1
}

Write-Output "PASS: iOS package boundary is clean."
Write-Output "iOS root: $iosRoot"
Write-Output "Repository root: $repoRoot"
