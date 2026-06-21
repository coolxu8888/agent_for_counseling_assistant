param(
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [switch]$Json
)

$ErrorActionPreference = "Stop"

$ragRoot = Join-Path $Root "rag"
$retrievalMapPath = Join-Path $ragRoot "retrieval-map.v0.1.json"

$allowedSections = @(
    "ethics-risk",
    "case-recording",
    "session-notes",
    "intake-assessment",
    "forms-fields",
    "theory-frameworks",
    "next-session-planning"
)

$allowedWorkflows = @(
    "workflow_1_intake_form",
    "workflow_2_case_summary",
    "workflow_3_session_note",
    "workflow_4_case_conceptualization",
    "workflow_5_next_session_plan"
)

$allowedRiskLevels = @("low", "medium", "high")
$requiredFields = @(
    "chunk_id",
    "title",
    "source_id",
    "source_url",
    "source_type",
    "rag_section",
    "workflow_scope",
    "topic",
    "risk_level",
    "review_status",
    "last_reviewed"
)

function Add-Issue {
    param(
        [System.Collections.Generic.List[object]]$List,
        [string]$Severity,
        [string]$File,
        [string]$Message
    )

    $List.Add([pscustomobject]@{
        severity = $Severity
        file = $File
        message = $Message
    }) | Out-Null
}

function Convert-Scalar {
    param([string]$Value)

    $trimmed = $Value.Trim()
    if ($trimmed.Length -ge 2 -and $trimmed.StartsWith('"') -and $trimmed.EndsWith('"')) {
        return $trimmed.Substring(1, $trimmed.Length - 2)
    }
    return $trimmed
}

function Read-ChunkFrontMatter {
    param([string]$Path)

    $lines = Get-Content -Path $Path -Encoding UTF8
    if ($lines.Count -lt 3 -or $lines[0] -ne "---") {
        return $null
    }

    $endIndex = -1
    for ($i = 1; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -eq "---") {
            $endIndex = $i
            break
        }
    }

    if ($endIndex -lt 0) {
        return $null
    }

    $meta = @{}
    $currentListKey = $null

    for ($i = 1; $i -lt $endIndex; $i++) {
        $line = $lines[$i]
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }

        if ($line -match "^\s*-\s+(.+?)\s*$") {
            if ($currentListKey) {
                $meta[$currentListKey] += ,(Convert-Scalar $Matches[1])
            }
            continue
        }

        if ($line -match "^([A-Za-z0-9_-]+):\s*(.*)$") {
            $key = $Matches[1]
            $value = $Matches[2]
            if ([string]::IsNullOrWhiteSpace($value)) {
                $meta[$key] = @()
                $currentListKey = $key
            }
            else {
                $meta[$key] = Convert-Scalar $value
                $currentListKey = $null
            }
        }
    }

    return [pscustomobject]@{
        metadata = $meta
        body = ($lines[($endIndex + 1)..($lines.Count - 1)] -join "`n")
    }
}

function Get-RelativePath {
    param(
        [string]$Base,
        [string]$Path
    )

    $baseFull = [System.IO.Path]::GetFullPath($Base)
    $pathFull = [System.IO.Path]::GetFullPath($Path)

    if (-not $baseFull.EndsWith([System.IO.Path]::DirectorySeparatorChar)) {
        $baseFull += [System.IO.Path]::DirectorySeparatorChar
    }

    $baseUri = [System.Uri]::new($baseFull)
    $pathUri = [System.Uri]::new($pathFull)
    return [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($pathUri).ToString()).Replace("\", "/")
}

if (-not (Test-Path $ragRoot)) {
    throw "RAG directory not found: $ragRoot"
}

$errors = [System.Collections.Generic.List[object]]::new()
$warnings = [System.Collections.Generic.List[object]]::new()
$chunkRecords = [System.Collections.Generic.List[object]]::new()
$chunkIds = @{}

$formalChunkFiles = Get-ChildItem -Path $ragRoot -Recurse -File -Include "*.md" |
    Where-Object {
        $relative = Get-RelativePath $ragRoot $_.FullName
        $top = $relative.Split("/")[0]
        $allowedSections -contains $top
    }

foreach ($file in $formalChunkFiles) {
    $relative = Get-RelativePath $Root $file.FullName
    $parsed = Read-ChunkFrontMatter -Path $file.FullName

    if (-not $parsed) {
        Add-Issue $errors "error" $relative "Missing or invalid YAML frontmatter."
        continue
    }

    $meta = $parsed.metadata

    foreach ($field in $requiredFields) {
        if (-not $meta.ContainsKey($field)) {
            Add-Issue $errors "error" $relative "Missing required field: $field."
            continue
        }

        $value = $meta[$field]
        if ($value -is [array]) {
            if ($value.Count -eq 0 -or ($value | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }).Count -eq 0) {
                Add-Issue $errors "error" $relative "Required list field is empty: $field."
            }
        }
        elseif ([string]::IsNullOrWhiteSpace([string]$value)) {
            Add-Issue $errors "error" $relative "Required field is empty: $field."
        }
    }

    if (-not $meta.ContainsKey("chunk_id") -or [string]::IsNullOrWhiteSpace([string]$meta["chunk_id"])) {
        continue
    }

    $chunkId = [string]$meta["chunk_id"]
    if ($chunkIds.ContainsKey($chunkId)) {
        Add-Issue $errors "error" $relative "Duplicate chunk_id also used in $($chunkIds[$chunkId])."
    }
    else {
        $chunkIds[$chunkId] = $relative
    }

    $sectionFromPath = (Get-RelativePath $ragRoot $file.FullName).Split("/")[0]

    if ($meta.ContainsKey("rag_section")) {
        if ($allowedSections -notcontains $meta["rag_section"]) {
            Add-Issue $errors "error" $relative "Invalid rag_section: $($meta["rag_section"])."
        }
        elseif ($meta["rag_section"] -ne $sectionFromPath) {
            Add-Issue $errors "error" $relative "rag_section does not match parent directory: $($meta["rag_section"]) vs $sectionFromPath."
        }
    }

    if ($meta.ContainsKey("workflow_scope")) {
        foreach ($workflow in @($meta["workflow_scope"])) {
            if ($allowedWorkflows -notcontains $workflow) {
                Add-Issue $errors "error" $relative "Invalid workflow_scope: $workflow."
            }
        }
    }

    if ($meta.ContainsKey("risk_level") -and $allowedRiskLevels -notcontains $meta["risk_level"]) {
        Add-Issue $errors "error" $relative "Invalid risk_level: $($meta["risk_level"])."
    }

    if ($meta.ContainsKey("review_status") -and $meta["review_status"] -ne "approved") {
        Add-Issue $errors "error" $relative "Formal chunk review_status must be approved."
    }

    if ($meta.ContainsKey("last_reviewed") -and $meta["last_reviewed"] -notmatch "^\d{4}-\d{2}-\d{2}$") {
        Add-Issue $errors "error" $relative "last_reviewed should use YYYY-MM-DD."
    }

    $chunkRecords.Add([pscustomobject]@{
        chunk_id = $chunkId
        file = $relative
        rag_section = $meta["rag_section"]
        workflow_scope = @($meta["workflow_scope"])
        topic = @($meta["topic"])
        risk_level = $meta["risk_level"]
    }) | Out-Null
}

$sourceCardFiles = Get-ChildItem -Path (Join-Path $ragRoot "source-cards") -File -Include "*.md" -ErrorAction SilentlyContinue
$sourceCardIds = @{}
foreach ($sourceFile in $sourceCardFiles) {
    $content = Get-Content -Path $sourceFile.FullName -Encoding UTF8 -Raw
    $candidateIds = [regex]::Matches($content, "(?m)^(source_id|id):\s*`?([^`\r\n]+)`?\s*$") |
        ForEach-Object { $_.Groups[2].Value.Trim() }

    foreach ($id in $candidateIds) {
        if (-not [string]::IsNullOrWhiteSpace($id)) {
            $sourceCardIds[$id] = Get-RelativePath $Root $sourceFile.FullName
        }
    }
}

foreach ($record in $chunkRecords) {
    $fullPath = Join-Path $Root $record.file
    $parsed = Read-ChunkFrontMatter -Path $fullPath
    $sourceId = $parsed.metadata["source_id"]
    if ($sourceCardIds.Count -gt 0 -and -not $sourceCardIds.ContainsKey($sourceId)) {
        Add-Issue $warnings "warning" $record.file "source_id was not found in source-cards by simple id scan: $sourceId."
    }

    $body = $parsed.body
    $relatedRefs = [regex]::Matches($body, '`([^`]+)`') |
        ForEach-Object { $_.Groups[1].Value } |
        Where-Object { $_ -match '^[a-z0-9-]+-\d{3}$' } |
        Sort-Object -Unique

    foreach ($relatedRef in $relatedRefs) {
        if (-not $chunkIds.ContainsKey($relatedRef)) {
            Add-Issue $warnings "warning" $record.file "Related chunk reference not found: $relatedRef."
        }
    }
}

$retrievalMap = $null
if (Test-Path $retrievalMapPath) {
    try {
        $retrievalMap = Get-Content -Path $retrievalMapPath -Encoding UTF8 -Raw | ConvertFrom-Json
    }
    catch {
        Add-Issue $errors "error" "rag/retrieval-map.v0.1.json" "Invalid JSON: $($_.Exception.Message)"
    }
}
else {
    Add-Issue $errors "error" "rag/retrieval-map.v0.1.json" "Retrieval map JSON is missing."
}

if ($retrievalMap) {
    foreach ($workflow in @($retrievalMap.allowed_workflows)) {
        if ($allowedWorkflows -notcontains $workflow) {
            Add-Issue $errors "error" "rag/retrieval-map.v0.1.json" "Invalid allowed workflow: $workflow."
        }
    }

    foreach ($section in @($retrievalMap.allowed_sections)) {
        if ($allowedSections -notcontains $section) {
            Add-Issue $errors "error" "rag/retrieval-map.v0.1.json" "Invalid allowed section: $section."
        }
    }

    foreach ($workflowName in $retrievalMap.workflows.PSObject.Properties.Name) {
        if ($allowedWorkflows -notcontains $workflowName) {
            Add-Issue $errors "error" "rag/retrieval-map.v0.1.json" "Unknown workflow key: $workflowName."
            continue
        }

        $workflowConfig = $retrievalMap.workflows.$workflowName
        foreach ($section in @($workflowConfig.default_sections)) {
            if ($allowedSections -notcontains $section) {
                Add-Issue $errors "error" "rag/retrieval-map.v0.1.json" "Invalid default section in $workflowName`: $section."
            }
        }

        foreach ($route in @($workflowConfig.intent_routes)) {
            foreach ($chunkId in @($route.priority_chunks)) {
                if (-not $chunkIds.ContainsKey($chunkId)) {
                    Add-Issue $errors "error" "rag/retrieval-map.v0.1.json" "Missing priority chunk in $workflowName / $($route.intent): $chunkId."
                }
            }
        }
    }
}

$summary = [pscustomobject]@{
    status = if ($errors.Count -eq 0) { "PASS" } else { "FAIL" }
    formal_chunk_count = $chunkRecords.Count
    unique_chunk_id_count = $chunkIds.Count
    error_count = $errors.Count
    warning_count = $warnings.Count
    sections = $chunkRecords |
        Group-Object rag_section |
        Sort-Object Name |
        ForEach-Object {
            [pscustomobject]@{
                section = $_.Name
                count = $_.Count
            }
        }
    errors = $errors
    warnings = $warnings
}

if ($Json) {
    $summary | ConvertTo-Json -Depth 8
}
else {
    Write-Host "RAG validation: $($summary.status)"
    Write-Host "Formal chunks: $($summary.formal_chunk_count)"
    Write-Host "Unique chunk ids: $($summary.unique_chunk_id_count)"
    Write-Host "Errors: $($summary.error_count)"
    Write-Host "Warnings: $($summary.warning_count)"
    Write-Host ""
    Write-Host "Sections:"
    $summary.sections | Format-Table -AutoSize

    if ($errors.Count -gt 0) {
        Write-Host ""
        Write-Host "Errors:"
        $errors | Format-Table -AutoSize
    }

    if ($warnings.Count -gt 0) {
        Write-Host ""
        Write-Host "Warnings:"
        $warnings | Format-Table -AutoSize
    }
}

if ($errors.Count -gt 0) {
    exit 1
}
