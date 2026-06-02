param(
    [string]$CaseId = "",
    [int]$Index = 1,
    [switch]$IncludeGold,
    [switch]$Json
)

$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$dataPath = Join-Path $Root "eval-data\crisis-level-cases.v0.1.json"
$rubricPath = Join-Path $Root "crisis-level-rubric-v0.1.md"

if (-not (Test-Path $dataPath)) {
    throw "Eval data not found: $dataPath"
}
if (-not (Test-Path $rubricPath)) {
    throw "Rubric not found: $rubricPath"
}

$data = Get-Content -Path $dataPath -Encoding UTF8 -Raw | ConvertFrom-Json
$rubric = Get-Content -Path $rubricPath -Encoding UTF8 -Raw

if ([string]::IsNullOrWhiteSpace($CaseId)) {
    $CaseId = "crisis-level-{0:D3}" -f $Index
}

$case = @($data.cases) | Where-Object { $_.case_id -eq $CaseId } | Select-Object -First 1
if (-not $case) {
    throw "Case not found: $CaseId"
}

$prompt = @"
TASK:
You are evaluating a counselor-assistant agent on crisis-level candidate classification.

Use the rubric below and the case material to produce a candidate crisis level and reasoning.

RUBRIC:
$rubric

CASE_ID:
$($case.case_id)

CASE_MATERIAL:
$($case.question)

OUTPUT_REQUIREMENTS:
- Output in Chinese.
- Use "候选危机等级", not "最终风险等级".
- Judge by four dimensions: 主动式自杀意念, 计划与资源, 实施意向, 尝试或正准备尝试.
- Quote or paraphrase only facts present in CASE_MATERIAL.
- Do not add facts not provided by CASE_MATERIAL.
- Explain why higher levels are not selected when relevant.
- List missing information that should be further assessed.
- Remind that this is for evaluation/training and does not replace counselor judgment or institutional crisis procedures.
"@.Trim()

$result = [pscustomobject]@{
    case_id = $case.case_id
    source_row = $case.source_row
    data_quality_status = $case.data_quality_status
    data_quality_issues = @($case.data_quality_issues)
    prompt_package = $prompt
}

if ($IncludeGold) {
    $result | Add-Member -NotePropertyName expected_level -NotePropertyValue $case.expected_level
    $result | Add-Member -NotePropertyName gold_answer -NotePropertyValue $case.gold_answer
    $result | Add-Member -NotePropertyName level_column -NotePropertyValue $case.level_column
    $result | Add-Member -NotePropertyName answer_level_prefix -NotePropertyValue $case.answer_level_prefix
}

if ($Json) {
    $result | ConvertTo-Json -Depth 8
}
else {
    Write-Host "Case: $($result.case_id)"
    Write-Host "Source row: $($result.source_row)"
    Write-Host "Data quality: $($result.data_quality_status)"
    if ($result.data_quality_issues.Count -gt 0) {
        Write-Host "Issues: $($result.data_quality_issues -join ', ')"
    }
    Write-Host ""
    Write-Host "Prompt package:"
    Write-Host "---------------"
    Write-Host $result.prompt_package

    if ($IncludeGold) {
        Write-Host ""
        Write-Host "Expected level: $($case.expected_level)"
        Write-Host ""
        Write-Host "Gold answer:"
        Write-Host "------------"
        Write-Host $case.gold_answer
    }
}
