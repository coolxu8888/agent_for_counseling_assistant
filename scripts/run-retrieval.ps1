param(
    [Parameter(Mandatory = $true)]
    [string]$Query,

    [string]$Workflow = "",
    [string]$Intent = "",
    [int]$MaxChunks = 4,
    [switch]$SummaryOnly,
    [switch]$Json
)

$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ragRoot = Join-Path $Root "rag"
$retrievalMapPath = Join-Path $ragRoot "retrieval-map.v0.1.json"

$allowedSections = @(
    "ethics-risk",
    "case-recording",
    "session-notes",
    "intake-assessment",
    "forms-fields",
    "theory-frameworks",
    "next-session-planning",
    "roadmap-planning"
)

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
        body = ($lines[($endIndex + 1)..($lines.Count - 1)] -join "`n").Trim()
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

function Test-AnyPattern {
    param(
        [string]$Text,
        [string[]]$Patterns
    )

    foreach ($pattern in $Patterns) {
        if ($Text -match $pattern) {
            return $true
        }
    }
    return $false
}

function U {
    param([string]$Text)
    return [regex]::Replace($Text, "\\u([0-9a-fA-F]{4})", {
        param($Match)
        return [char]([Convert]::ToInt32($Match.Groups[1].Value, 16))
    })
}

function Get-WorkflowScore {
    param(
        [string]$Text,
        [string[]]$Patterns
    )

    $score = 0
    foreach ($pattern in $Patterns) {
        if ($Text -match $pattern) {
            $score += 1
        }
    }
    return $score
}

function Select-Workflow {
    param([string]$Text)

    $negatedSessionNote = Test-AnyPattern $Text @(
        "not a session note",
        "not the session note",
        "not a counseling record",
        "not the counseling record",
        "not a session record",
        "not a progress note",
        "do not write.*session note",
        "don't write.*session note",
        "do not write.*counseling record",
        "don't write.*counseling record",
        "不要写成.*session note",
        "不要写成.*咨询记录"
    )

    if (-not $negatedSessionNote) {
        $negatedSessionNote = Test-AnyPattern $Text @(
            "not asking for (a )?(session note|progress note|counseling record)",
            "rather than (a )?(session note|progress note|counseling record)",
            "instead of (a )?(session note|progress note|counseling record)",
            "don't need (a )?(session note|progress note|counseling record)",
            "do not need (a )?(session note|progress note|counseling record)",
            (U "\u4e0d\u8981\u5199\u6210.*session note"),
            (U "\u4e0d\u8981\u5199\u6210.*progress note"),
            (U "\u4e0d\u8981\u5199\u6210.*counseling record"),
            (U "\u4e0d\u8981\u5199\u6210.*\u54a8\u8be2\u8bb0\u5f55"),
            (U "\u4e0d\u662f.*session note"),
            (U "\u4e0d\u662f.*progress note"),
            (U "\u4e0d\u662f.*counseling record"),
            (U "\u4e0d\u662f.*\u54a8\u8be2\u8bb0\u5f55"),
            (U "\u4e0d\u662f\u8981.*session note"),
            (U "\u4e0d\u662f\u8981.*progress note"),
            (U "\u4e0d\u662f\u8981.*counseling record"),
            (U "\u4e0d\u662f\u8981.*\u54a8\u8be2\u8bb0\u5f55"),
            (U "\u4e0d\u7528.*session note"),
            (U "\u4e0d\u7528.*progress note"),
            (U "\u4e0d\u7528.*counseling record"),
            (U "\u4e0d\u7528.*\u54a8\u8be2\u8bb0\u5f55"),
            (U "\u5148\u4e0d\u505a.*session note"),
            (U "\u5148\u4e0d\u505a.*progress note"),
            (U "\u5148\u4e0d\u505a.*counseling record"),
            (U "\u5148\u4e0d\u505a.*\u54a8\u8be2\u8bb0\u5f55"),
            (U "\u800c\u4e0d\u662f.*session note"),
            (U "\u800c\u4e0d\u662f.*progress note"),
            (U "\u800c\u4e0d\u662f.*counseling record"),
            (U "\u800c\u4e0d\u662f.*\u54a8\u8be2\u8bb0\u5f55")
        )
    }

    if (Test-AnyPattern $Text @(
            "before (the )?first (interview|session)",
            "intake question guide",
            "intake guide",
            "intake checklist",
            "information collection",
            "information gathering",
            "what .*still need to ask",
            "still need to ask",
            "initial interview summary",
            "first interview summary",
            "summarize (these|this)? ?(initial|first) interview notes",
            "organize (these|this)? ?(initial|first) interview notes",
            "fixed intake template",
            "initial interview template",
            (U "\u521d\u8bbf\u603b\u7ed3"),
            (U "\u521d\u8bbf\u7b14\u8bb0"),
            (U "\u521d\u59cb\u8bbf\u8c08\u6750\u6599\u603b\u7ed3"),
            (U "\u521d\u59cb\u8bbf\u8c08\u6a21\u677f"),
            (U "\u56fa\u5b9a\u521d\u8bbf\u6a21\u677f")
        )) {
        return "workflow_1_intake_form"
    }

    if ((-not $negatedSessionNote) -and (Test-AnyPattern $Text @(
            "session note",
            "progress note",
            "counseling record",
            "session record",
            "risk update",
            "next session focus",
            "notes from today"
        ))) {
        return "workflow_3_session_note"
    }

    if (Test-AnyPattern $Text @(
            "counseling\s*roadmap",
            "multi-session",
            "multi session",
            "phased roadmap",
            "phase plan",
            "next several sessions",
            "later phases",
            (U "\u54a8\u8be2\u8def\u7ebf\u56fe"),
            (U "\u591a\u8282\u54a8\u8be2"),
            (U "\u591a\u9636\u6bb5"),
            (U "\u5206\u9636\u6bb5"),
            (U "\u8def\u7ebf\u56fe")
        )) {
        return "workflow_6_counseling_roadmap"
    }

    if (Test-AnyPattern $Text @(
            "next-session\s*plan",
            "next session\s*plan",
            "rather than (a )?(session note|progress note|counseling record).*(next session|session agenda)",
            "instead of (a )?(session note|progress note|counseling record).*(next session|session agenda)",
            "session agenda",
            "upcoming( counseling)? session",
            "single upcoming( counseling)? session",
            "plan for the single upcoming( counseling)? session",
            "risk check points",
            (U "\u4e0b\u6b21\u54a8\u8be2\u8ba1\u5212"),
            (U "\u4e0b\u6b21\u4f1a\u8c08\u8ba1\u5212"),
            (U "\u4e0b\u4e00\u6b21\u54a8\u8be2"),
            (U "\u53ea\u505a.*\u4e0b\u6b21\u54a8\u8be2"),
            (U "\u53ea\u505a.*\u4e0b\u4e00\u6b21\u54a8\u8be2"),
            (U "\u53ea\u9700.*\u4e0b\u6b21\u54a8\u8be2"),
            (U "\u800c\u4e0d\u662f.*(?:session note|progress note|counseling record|\u54a8\u8be2\u8bb0\u5f55).*\u4e0b\u6b21\u54a8\u8be2"),
            (U "\u4f1a\u8c08\u8bae\u7a0b"),
            (U "\u4e0b\u6b65\u5de5\u4f5c\u91cd\u70b9")
        )) {
        return "workflow_5_next_session_plan"
    }

    $workflowPatterns = @{
        workflow_1_intake_form = @(
            "before (the )?first (interview|session)",
            "intake question guide",
            "intake guide",
            "intake checklist",
            "information collection",
            "information gathering",
            "what .*still need to ask",
            "still need to ask",
            "initial interview summary",
            "first interview summary",
            "summarize (these|this)? ?(initial|first) interview notes",
            "organize (these|this)? ?(initial|first) interview notes",
            "fixed intake template",
            "initial interview template",
            "initial interview",
            "\bintake\b",
            (U "\u521d\u8bbf"),
            (U "\u521d\u8bbf\u603b\u7ed3"),
            (U "\u521d\u8bbf\u7b14\u8bb0"),
            (U "\u4fe1\u606f\u6536\u96c6\u8868"),
            (U "\u521d\u59cb\u8bbf\u8c08"),
            (U "\u521d\u59cb\u8bbf\u8c08\u6750\u6599\u603b\u7ed3"),
            (U "\u521d\u59cb\u8bbf\u8c08\u6a21\u677f"),
            (U "\u56fa\u5b9a\u521d\u8bbf\u6a21\u677f"),
            (U "\u8bbf\u8c08\u63d0\u7eb2"),
            (U "\u9884\u586b\u5199"),
            "JSON\s*Schema",
            "schema",
            (U "\u5b57\u6bb5"),
            (U "\u8868\u5355"),
            (U "\u8865\u5145.*\u95ee"),
            (U "\u8fd8.*\u95ee"),
            (U "\u8eab\u5fc3\u72b6\u6001"),
            (U "\u7efc\u5408\u8bc4\u4f30")
        )
        workflow_2_case_summary = @(
            "case summary",
            "organi[sz]e the case",
            "case background",
            "biopsychosocial",
            "\bbps\b",
            "supervision summary",
            "protective factors?",
            "follow-up questions?",
            "case background organization",
            "diagnosis questions",
            "risk signals",
            "missing facts",
            "information gaps?",
            "de-identified case",
            (U "\u4e2a\u6848"),
            (U "\u80cc\u666f"),
            (U "\u6574\u7406"),
            (U "\u4e3b\u8bc9"),
            (U "\u98ce\u9669\u4fe1\u53f7"),
            (U "\u4fe1\u606f\u7f3a\u53e3"),
            (U "\u6458\u8981"),
            (U "\u7763\u5bfc"),
            (U "\u5bf9\u5916\u5206\u4eab"),
            (U "\u8bca\u65ad"),
            (U "\u7cbe\u795e\u5206\u88c2"),
            (U "\u6291\u90c1\u75c7"),
            (U "\u7126\u8651\u75c7")
        )
        workflow_3_session_note = @(
            "session note",
            "progress note",
            "counseling note",
            "counselling note",
            "counseling record",
            "session record",
            "risk update",
            "next session focus",
            "notes from today",
            "session",
            "Session",
            (U "\u54a8\u8be2\u8bb0\u5f55"),
            "SOAP",
            "DAP",
            "BIRP",
            (U "\u7b2c\s*\d+\s*\u6b21"),
            (U "\u672c\u6b21"),
            (U "\u4eca\u5929\u8fd9\u6b21"),
            (U "\u4e0b\u6b21\u54a8\u8be2\u91cd\u70b9"),
            (U "\u603b\u7ed3\u4eca\u5929")
        )
        workflow_4_case_conceptualization = @(
            "conceptualization",
            "case formulation",
            "framework",
            "CBT",
            "psychodynamic",
            "humanistic",
            "integrative",
            (U "\u4e2a\u6848\u6982\u5ff5\u5316"),
            (U "\u8ba4\u77e5\u884c\u4e3a"),
            (U "\u4eba\u672c"),
            (U "\u7cbe\u795e\u52a8\u529b"),
            (U "\u6574\u5408\u53d6\u5411"),
            (U "\u6d41\u6d3e")
        )
        workflow_5_next_session_plan = @(
            "next-session\s*plan",
            "next session\s*plan",
            "plan (only )?the next (counseling )?session",
            "rather than (a )?(session note|progress note|counseling record).*(next session|session agenda)",
            "instead of (a )?(session note|progress note|counseling record).*(next session|session agenda)",
            "session agenda",
            "upcoming( counseling)? session",
            "single upcoming( counseling)? session",
            "plan for the single upcoming( counseling)? session",
            "immediate next session",
            "risk check points",
            "between-session task",
            (U "\u4e0b\u6b21\u54a8\u8be2\u8ba1\u5212"),
            (U "\u4e0b\u6b21\u4f1a\u8c08\u8ba1\u5212"),
            (U "\u4e0b\u4e00\u6b21\u54a8\u8be2"),
            (U "\u53ea\u505a.*\u4e0b\u6b21\u54a8\u8be2"),
            (U "\u53ea\u505a.*\u4e0b\u4e00\u6b21\u54a8\u8be2"),
            (U "\u53ea\u9700.*\u4e0b\u6b21\u54a8\u8be2"),
            (U "\u800c\u4e0d\u662f.*(?:session note|progress note|counseling record|\u54a8\u8be2\u8bb0\u5f55).*\u4e0b\u6b21\u54a8\u8be2"),
            (U "\u4f1a\u8c08\u8bae\u7a0b"),
            (U "\u4e0b\u6b65\u5de5\u4f5c\u91cd\u70b9")
        )
        workflow_6_counseling_roadmap = @(
            "counseling\s*roadmap",
            "multi-session",
            "multi session",
            "phased roadmap",
            "phase plan",
            "next several sessions",
            "later phases",
            "roadmap",
            (U "\u54a8\u8be2\u8def\u7ebf\u56fe"),
            (U "\u591a\u8282\u54a8\u8be2"),
            (U "\u591a\u9636\u6bb5"),
            (U "\u5206\u9636\u6bb5"),
            (U "\u8def\u7ebf\u56fe")
        )
    }

    $scores = @{}
    foreach ($name in $workflowPatterns.Keys) {
        $scores[$name] = Get-WorkflowScore $Text $workflowPatterns[$name]
    }

    if ($negatedSessionNote) {
        $scores["workflow_3_session_note"] = 0
    }

    $winner = $scores.GetEnumerator() | Sort-Object -Property Value -Descending | Select-Object -First 1
    if (-not $winner -or $winner.Value -eq 0) {
        return ""
    }
    return $winner.Key
}

function Select-Intent {
    param(
        [string]$Text,
        [string]$WorkflowName
    )

    $isStudent = Test-AnyPattern $Text @((U "\u5b66\u751f"), (U "\u9ad8\u4e2d"), (U "\u521d\u4e2d"), (U "\u5927\u5b66"), (U "\u7814\u7a76\u751f"), (U "\u5b66\u6821"), (U "\u6821\u56ed"), (U "\u540c\u5b66"))
    $hasRisk = Test-AnyPattern $Text @((U "\u98ce\u9669"), (U "\u81ea\u6740"), (U "\u81ea\u4f24"), (U "\u4e0d\u60f3\u6d3b"), (U "\u6d88\u5931"), (U "\u4ed6\u4f24"), (U "\u4f24\u5bb3"), (U "\u5371\u673a"), (U "\u4e0d\u9192\u6765"), (U "\u4e0d\u60f3\u9192\u6765"))
    $requestsDiagnosis = Test-AnyPattern $Text @((U "\u8bca\u65ad"), (U "\u662f\u4e0d\u662f.*\u75c7"), (U "\u6291\u90c1\u75c7"), (U "\u7cbe\u795e\u5206\u88c2"), (U "\u53cc\u76f8"), (U "\u7126\u8651\u75c7"))
    $involvesPsychiatry = Test-AnyPattern $Text @((U "\u7cbe\u795e\u79d1"), (U "\u5c31\u533b"), (U "\u5e7b\u542c"), (U "\u5984\u60f3"), (U "\u76d1\u89c6"), (U "\u73b0\u5b9e\u68c0\u9a8c"), (U "\u7cbe\u795e\u75c5"))

    if ($WorkflowName -eq "workflow_1_intake_form") {
        if ($isStudent) {
            return (U "\u5b66\u751f\u573a\u666f")
        }
        if (Test-AnyPattern $Text @("JSON\s*Schema", "schema", (U "\u7cfb\u7edf\u5b57\u6bb5"), (U "\u843d\u5e93"), (U "\u5b57\u6bb5"))) {
            return (U "\u751f\u6210\u7cfb\u7edf\u5b57\u6bb5\u7248")
        }
        if (Test-AnyPattern $Text @((U "\u9884\u586b\u5199"), (U "\u6765\u8bbf\u8005.*\u586b"), (U "\u81ea\u5df1\u586b"), (U "\u586b\u5199\u7248"))) {
            return (U "\u751f\u6210\u6765\u8bbf\u8005\u9884\u586b\u5199\u7248")
        }
        if (Test-AnyPattern $Text @((U "\u8865\u5145"), (U "\u8fd8.*\u95ee"), (U "\u7f3a.*\u95ee\u9898"), (U "\u5df2\u6709.*\u7b14\u8bb0"))) {
            return (U "\u57fa\u4e8e\u7b14\u8bb0\u751f\u6210\u8865\u5145\u8868")
        }
        return (U "\u751f\u6210\u54a8\u8be2\u5e08\u8bbf\u8c08\u7248\u521d\u8bbf\u8868")
    }

    if ($WorkflowName -eq "workflow_2_case_summary") {
        if (Test-AnyPattern $Text @((U "\u5bf9\u5916"), (U "\u5206\u4eab"), (U "\u7763\u5bfc"), (U "\u62a5\u544a"), (U "\u53bb\u8bc6\u522b"), (U "\u8131\u654f"))) {
            return (U "\u5916\u90e8\u5206\u4eab\u6216\u62a5\u544a")
        }
        if ($isStudent) {
            return (U "\u5b66\u751f\u4e2a\u6848")
        }
        if ($requestsDiagnosis) {
            return (U "\u7528\u6237\u8981\u6c42\u8bca\u65ad")
        }
        if ($hasRisk) {
            return (U "\u63d0\u53d6\u98ce\u9669\u4fe1\u53f7")
        }
        return (U "\u6574\u7406\u4e2a\u6848\u80cc\u666f")
    }

    if ($WorkflowName -eq "workflow_3_session_note") {
        if (Test-AnyPattern $Text @("SOAP")) {
            return (U "\u0053\u004f\u0041\u0050 \u683c\u5f0f\u8bb0\u5f55")
        }
        if ($isStudent -and $hasRisk) {
            return (U "\u5b66\u751f\u5371\u673a")
        }
        if ($involvesPsychiatry) {
            return (U "\u6d89\u53ca\u5c31\u533b\u6216\u7cbe\u795e\u79d1")
        }
        if (Test-AnyPattern $Text @("confidentiality", "informed consent", "who can read", "record keeping", "documentation boundaries", "documentation boundary", (U "\u4fdd\u5bc6"), (U "\u8bb0\u5f55\u4fdd\u5b58"), (U "\u77e5\u60c5\u540c\u610f"))) {
            return (U "\u6d89\u53ca\u4fdd\u5bc6\u6216\u8bb0\u5f55\u4fdd\u5b58")
        }
        if ($hasRisk) {
            return (U "\u51fa\u73b0\u81ea\u6740\u6216\u81ea\u4f24\u98ce\u9669")
        }
        return (U "\u666e\u901a session \u8bb0\u5f55")
    }

    if ($WorkflowName -eq "workflow_4_case_conceptualization") {
        if (Test-AnyPattern $Text @("CBT", (U "\u8ba4\u77e5\u884c\u4e3a"))) {
            return "CBT conceptualization"
        }
        if (Test-AnyPattern $Text @("psychodynamic", (U "\u7cbe\u795e\u52a8\u529b"))) {
            return "Psychodynamic conceptualization"
        }
        if (Test-AnyPattern $Text @("humanistic", (U "\u4eba\u672c"))) {
            return "Humanistic conceptualization"
        }
        return "Integrative conceptualization"
    }

    if ($WorkflowName -eq "workflow_5_next_session_plan") {
        if (Test-AnyPattern $Text @("CBT", (U "\u8ba4\u77e5\u884c\u4e3a"))) {
            return "CBT next-session plan"
        }
        if (Test-AnyPattern $Text @("psychodynamic", (U "\u7cbe\u795e\u52a8\u529b"))) {
            return "Psychodynamic next-session plan"
        }
        if (Test-AnyPattern $Text @("humanistic", (U "\u4eba\u672c"))) {
            return "Humanistic next-session plan"
        }
        if (Test-AnyPattern $Text @("integrative", (U "\u6574\u5408\u53d6\u5411"))) {
            return "Integrative next-session plan"
        }
        return "Generic next-session plan"
    }

    if ($WorkflowName -eq "workflow_6_counseling_roadmap") {
        if (Test-AnyPattern $Text @("CBT", (U "\u8ba4\u77e5\u884c\u4e3a"))) {
            return "CBT counseling roadmap"
        }
        if (Test-AnyPattern $Text @("psychodynamic", (U "\u7cbe\u795e\u52a8\u529b"))) {
            return "Psychodynamic counseling roadmap"
        }
        if (Test-AnyPattern $Text @("humanistic", (U "\u4eba\u672c"))) {
            return "Humanistic counseling roadmap"
        }
        if (Test-AnyPattern $Text @("integrative", (U "\u6574\u5408\u53d6\u5411"))) {
            return "Integrative counseling roadmap"
        }
        return "Generic counseling roadmap"
    }

    return ""
}

function Read-ChunkIndex {
    $chunks = @{}
    $files = Get-ChildItem -Path $ragRoot -Recurse -File -Include "*.md" |
        Where-Object {
            $relative = Get-RelativePath $ragRoot $_.FullName
            $top = $relative.Split("/")[0]
            $allowedSections -contains $top
        }

    foreach ($file in $files) {
        $parsed = Read-ChunkFrontMatter $file.FullName
        if (-not $parsed) {
            continue
        }

        $meta = $parsed.metadata
        $chunkId = [string]$meta["chunk_id"]
        if ([string]::IsNullOrWhiteSpace($chunkId)) {
            continue
        }

        $chunks[$chunkId] = [pscustomobject]@{
            chunk_id = $chunkId
            title = $meta["title"]
            source_id = $meta["source_id"]
            source_url = $meta["source_url"]
            source_type = $meta["source_type"]
            rag_section = $meta["rag_section"]
            workflow_scope = @($meta["workflow_scope"])
            topic = @($meta["topic"])
            risk_level = $meta["risk_level"]
            review_status = $meta["review_status"]
            last_reviewed = $meta["last_reviewed"]
            file = Get-RelativePath $Root $file.FullName
            content = $parsed.body
        }
    }
    return $chunks
}

function Build-RagContext {
    param([object[]]$Chunks)

    $parts = [System.Collections.Generic.List[string]]::new()
    foreach ($chunk in $Chunks) {
        $parts.Add(@"
### $($chunk.chunk_id)

title: $($chunk.title)
source_id: $($chunk.source_id)
source_type: $($chunk.source_type)
rag_section: $($chunk.rag_section)
risk_level: $($chunk.risk_level)

$($chunk.content)
"@.Trim()) | Out-Null
    }

    return ($parts -join "`n`n---`n`n")
}

function Build-PromptPackage {
    param(
        [string]$WorkflowName,
        [string]$WorkflowDisplayName,
        [string]$IntentName,
        [string[]]$Topics,
        [string]$RagContext,
        [string]$OriginalQuery,
        [string[]]$BoundaryNotes
    )

    $topicText = $Topics -join ", "
    $boundaryText = if ($BoundaryNotes.Count -gt 0) { $BoundaryNotes -join "`n- " } else { "Follow the v0.1 boundaries defined in the system prompt." }

    return @"
WORKFLOW:
$WorkflowName - $WorkflowDisplayName

INTENT:
$IntentName

QUERY_TOPICS:
$topicText

RAG_CONTEXT:
$RagContext

USER_INPUT:
$OriginalQuery

OUTPUT_CONSTRAINTS:
- Use only USER_INPUT and RAG_CONTEXT.
- Do not add background, symptoms, events, relationship details, or history that the user did not provide.
- Treat "not provided" differently from "denied" or "absent"; only use "denied" when USER_INPUT explicitly says the client denied it.
- Do not write an assessment or intervention as completed unless USER_INPUT explicitly says the counselor did it.
- Do not fill counselor observation fields with inferred appearance, emotion, reality testing, coherence, cooperation, or behavior. If USER_INPUT does not provide observation data, mark it as not provided.
- Do not upgrade "discussed a friend who can be contacted" into a safety plan, crisis plan, action plan, trusted friend, past friend, emergency support, or client agreement to contact unless USER_INPUT explicitly says so.
- Do not turn concrete support-system wording into stronger conclusions such as social avoidance, active isolation, or inactive support system unless you mark them as tentative hypotheses.
- Keep risk categories precise. If USER_INPUT only supports suicide-related ideation, do not merge it into self-harm risk; mark self-harm, harm-to-others, reality testing, and substance-use risks as not provided when absent.
- Do not output deterministic diagnosis.
- Do not replace counselor judgment, risk grading, crisis handling, or institutional procedures.
- Separate known facts, tentative hypotheses, and missing information.
- If risk appears, list risk signals separately and recommend further professional assessment.
- $boundaryText
"@.Trim()
}

if (-not (Test-Path $retrievalMapPath)) {
    throw "Retrieval map not found: $retrievalMapPath"
}

$retrievalMap = Get-Content -Path $retrievalMapPath -Encoding UTF8 -Raw | ConvertFrom-Json
$chunksById = Read-ChunkIndex

$selectedWorkflow = if (-not [string]::IsNullOrWhiteSpace($Workflow)) { $Workflow } else { Select-Workflow $Query }
$boundaryNotes = [System.Collections.Generic.List[string]]::new()

if ($selectedWorkflow -notin @("workflow_4_case_conceptualization", "workflow_5_next_session_plan") -and (Test-AnyPattern $Query @("CBT", (U "\u8ba4\u77e5\u884c\u4e3a"), (U "\u4eba\u672c"), (U "\u7cbe\u795e\u52a8\u529b"), (U "\u5bb6\u5ead\u7cfb\u7edf"), (U "\u6d41\u6d3e")))) {
    $boundaryNotes.Add("The query mentions a modality preference; v0.1 does not use modality-specific chunks to alter the basic information capture structure.") | Out-Null
}

$queryHasRisk = Test-AnyPattern $Query @("risk", "suicid", "self-harm", "harm to others", "crisis", "disappear", (U "\u98ce\u9669"), (U "\u81ea\u6740"), (U "\u81ea\u4f24"), (U "\u4e0d\u60f3\u6d3b"), (U "\u6d88\u5931"), (U "\u4ed6\u4f24"), (U "\u4f24\u5bb3"), (U "\u5371\u673a"), (U "\u4e0d\u9192\u6765"), (U "\u4e0d\u60f3\u9192\u6765"))
$queryHasSuicideSignal = Test-AnyPattern $Query @("suicid", "disappear", "don't want to live", "do not want to live", "not wake up", (U "\u81ea\u6740"), (U "\u81ea\u6740\u610f\u5ff5"), (U "\u4e0d\u60f3\u6d3b"), (U "\u6d88\u5931"), (U "\u4e0d\u9192\u6765"), (U "\u4e0d\u60f3\u9192\u6765"))
$queryHasConfidentiality = Test-AnyPattern $Query @("confidentiality", "informed consent", "who can read", "record keeping", "documentation boundaries", "documentation boundary", (U "\u4fdd\u5bc6"), (U "\u77e5\u60c5\u540c\u610f"), (U "\u8bb0\u5f55\u4fdd\u5b58"))
$queryRequestsDiagnosis = Test-AnyPattern $Query @((U "\u8bca\u65ad"), (U "\u662f\u4e0d\u662f.*\u75c7"), (U "\u6291\u90c1\u75c7"), (U "\u7cbe\u795e\u5206\u88c2"), (U "\u53cc\u76f8"), (U "\u7126\u8651\u75c7"))
$queryInvolvesPsychiatry = Test-AnyPattern $Query @((U "\u7cbe\u795e\u79d1"), (U "\u5c31\u533b"), (U "\u5e7b\u542c"), (U "\u5984\u60f3"), (U "\u76d1\u89c6"), (U "\u73b0\u5b9e\u68c0\u9a8c"), (U "\u7cbe\u795e\u75c5"))

if ([string]::IsNullOrWhiteSpace($selectedWorkflow)) {
    $result = [pscustomobject]@{
        status = "NEEDS_CLARIFICATION"
        query = $Query
        action = $retrievalMap.fallback.unclear_user_intent.action
        message = $retrievalMap.fallback.unclear_user_intent.message
        selected_chunks = @()
    }
}
elseif (-not ($retrievalMap.workflows.PSObject.Properties.Name -contains $selectedWorkflow)) {
    $result = [pscustomobject]@{
        status = "ERROR"
        query = $Query
        message = "Unknown workflow: $selectedWorkflow"
        selected_chunks = @()
    }
}
else {
    $workflowConfig = $retrievalMap.workflows.$selectedWorkflow
    $selectedIntent = if (-not [string]::IsNullOrWhiteSpace($Intent)) { $Intent } else { Select-Intent $Query $selectedWorkflow }

    $route = @($workflowConfig.intent_routes) | Where-Object { $_.intent -eq $selectedIntent } | Select-Object -First 1
    if (-not $route) {
        $route = @($workflowConfig.intent_routes) | Select-Object -First 1
        $boundaryNotes.Add("No exact intent match was found; the runner fell back to the workflow default intent.") | Out-Null
    }

    $selectedChunks = [System.Collections.Generic.List[object]]::new()
    $chunkPlan = [System.Collections.Generic.List[string]]::new()
    foreach ($chunkId in @($route.priority_chunks)) {
        $chunkPlan.Add($chunkId) | Out-Null
    }

    if ($queryHasConfidentiality) {
        if ($selectedWorkflow -eq "workflow_1_intake_form") {
            $chunkPlan.Add("ethics-risk-cps-informed-consent-confidentiality-001") | Out-Null
        }
        elseif ($selectedWorkflow -eq "workflow_3_session_note") {
            $chunkPlan.Add("session-notes-bacp-confidentiality-record-keeping-001") | Out-Null
            $chunkPlan.Add("ethics-risk-cps-informed-consent-confidentiality-001") | Out-Null
        }
    }

    if ($queryHasRisk) {
        $chunkPlan.Add("ethics-risk-china-risk-boundary-self-harm-harm-to-others-001") | Out-Null
    }
    if ($queryHasSuicideSignal) {
        $chunkPlan.Add("ethics-risk-suicide-risk-inquiry-topics-001") | Out-Null
    }
    if ($queryRequestsDiagnosis -or $queryInvolvesPsychiatry) {
        $chunkPlan.Add("ethics-risk-china-mental-health-law-referral-boundary-001") | Out-Null
        $chunkPlan.Add("ethics-risk-cps-professional-boundary-001") | Out-Null
    }

    foreach ($chunkId in ($chunkPlan | Select-Object -Unique)) {
        if ($selectedChunks.Count -ge $MaxChunks) {
            break
        }
        if ($chunksById.ContainsKey($chunkId)) {
            $selectedChunks.Add($chunksById[$chunkId]) | Out-Null
        }
    }

    $ragContext = Build-RagContext @($selectedChunks)
    $promptPackage = Build-PromptPackage `
        -WorkflowName $selectedWorkflow `
        -WorkflowDisplayName $workflowConfig.name `
        -IntentName $route.intent `
        -Topics @($route.topics) `
        -RagContext $ragContext `
        -OriginalQuery $Query `
        -BoundaryNotes @($boundaryNotes)

    $result = [pscustomobject]@{
        status = "OK"
        query = $Query
        route = [pscustomobject]@{
            workflow = $selectedWorkflow
            workflow_name = $workflowConfig.name
            intent = $route.intent
            topics = @($route.topics)
            boundary_notes = @($boundaryNotes)
        }
        selected_chunks = @($selectedChunks | ForEach-Object {
            [pscustomobject]@{
                chunk_id = $_.chunk_id
                title = $_.title
                file = $_.file
                rag_section = $_.rag_section
                risk_level = $_.risk_level
                source_id = $_.source_id
                topics = $_.topic
            }
        })
        rag_context = $ragContext
        prompt_package = $promptPackage
    }
}

if ($SummaryOnly) {
    $summaryResult = if ($result.status -eq "OK") {
        [pscustomobject]@{
            status = $result.status
            query = $result.query
            route = $result.route
            selected_chunks = $result.selected_chunks
        }
    }
    else {
        [pscustomobject]@{
            status = $result.status
            query = $result.query
            action = $result.action
            message = $result.message
            selected_chunks = @()
        }
    }

    if ($Json) {
        $summaryResult | ConvertTo-Json -Depth 8
    }
    else {
        if ($summaryResult.status -ne "OK") {
            Write-Host "Retrieval status: $($summaryResult.status)"
            Write-Host $summaryResult.message
        }
        else {
            Write-Host "Retrieval status: OK"
            Write-Host "Workflow: $($summaryResult.route.workflow) - $($summaryResult.route.workflow_name)"
            Write-Host "Intent: $($summaryResult.route.intent)"
            Write-Host "Topics: $($summaryResult.route.topics -join ', ')"
            Write-Host ""
            Write-Host "Selected chunks:"
            $summaryResult.selected_chunks | Format-Table chunk_id, rag_section, risk_level, file -AutoSize
        }
    }
    exit 0
}

if ($Json) {
    $result | ConvertTo-Json -Depth 12
}
else {
    if ($result.status -ne "OK") {
        Write-Host "Retrieval status: $($result.status)"
        Write-Host $result.message
        exit 0
    }

    Write-Host "Retrieval status: OK"
    Write-Host "Workflow: $($result.route.workflow) - $($result.route.workflow_name)"
    Write-Host "Intent: $($result.route.intent)"
    Write-Host "Topics: $($result.route.topics -join ', ')"
    if ($result.route.boundary_notes.Count -gt 0) {
        Write-Host "Boundary notes: $($result.route.boundary_notes -join ' / ')"
    }
    Write-Host ""
    Write-Host "Selected chunks:"
    $result.selected_chunks | Format-Table chunk_id, rag_section, risk_level, file -AutoSize
    Write-Host ""
    Write-Host "Prompt package:"
    Write-Host "---------------"
    Write-Host $result.prompt_package
}
