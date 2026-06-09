# Structured Output Layer Design

Date: 2026-06-09

## Goal

Add a structured JSON output layer to the v0.1 local agent runner.

The runner should continue producing counselor-readable Markdown, but can optionally ask the model to also emit a machine-readable JSON block. The runner extracts, validates, and saves that JSON as `structured_output.json`, then writes validation results to `structured_check.json`.

This is the bridge between the current text runner and future Word/template rendering. It is not the Word renderer itself.

## Context

The current runner already supports:

- Explicit W1/W2/W3 workflow selection.
- RAG-backed prompt package assembly.
- DeepSeek API calls.
- `raw_output.txt`, `clean_output.md`, `metadata.json`, and `safety_check.json`.
- Workflow-specific Markdown output contracts.

The recent smoke tests showed that fixed Markdown contracts stabilize human-readable output. The next bottleneck is that Word generation should not parse Markdown tables directly. Word rendering needs a stable data contract.

## Scope

In scope:

- Add a `--structured` / `-Structured` option to the local runner.
- Add workflow-specific JSON output contracts for W1, W2, and W3.
- Ask the model to output Markdown first, then a fenced JSON block.
- Extract the JSON block from `raw_output.txt`.
- Save parsed JSON to `structured_output.json`.
- Validate the parsed JSON and save `structured_check.json`.
- Record structured status in `metadata.json`.
- Add unit tests for extraction, validation, CLI parsing, and fake API success.

Out of scope:

- Word generation.
- Uploaded template parsing.
- Speech-to-text.
- Backend API.
- Automatic workflow classification.
- Strict JSON-schema library adoption.
- Replacing Markdown output with JSON-only output.

## Command Interface

PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-agent.ps1 -Workflow W3 -Input "..." -Structured
```

Python:

```powershell
python scripts\run_agent.py --workflow W3 --input "..." --structured
```

Dry run should include the structured output instructions in `prompt_package.txt`, but should not create `structured_output.json` or `structured_check.json` because no model answer exists yet.

## Output Files

When `--structured` is used and the API call succeeds:

```text
agent-runs/<timestamp>-W3/
  raw_output.txt
  clean_output.md
  safety_check.json
  structured_output.json
  structured_check.json
  metadata.json
```

If JSON extraction or validation fails:

- `raw_output.txt` and `clean_output.md` should still be saved.
- `structured_check.json` should contain `status: "FAIL"` and issue details.
- `structured_output.json` should only be written when JSON parsing succeeds.
- `metadata.json` should record `structured_status`.

## Model Output Shape

The prompt should ask for two parts:

1. Human-readable Markdown answer.
2. A fenced JSON block labeled `json`.

Example:

```text
<Markdown answer>

```json
{
  "workflow": "W3",
  "document_type": "session_note",
  "title": "本次咨询记录",
  "sections": [],
  "risk_change": {},
  "missing_information": [],
  "boundary_notes": []
}
```

AGENT_DONE_W3
```

The runner should extract the last fenced JSON block before the completion marker. This lets the Markdown answer contain incidental JSON-like examples without confusing extraction.

## Workflow Contracts

### W1: Intake Form

Required top-level fields:

```json
{
  "workflow": "W1",
  "document_type": "intake_form",
  "title": "初访信息收集表",
  "sections": [],
  "boundary_notes": []
}
```

Each section should contain:

```json
{
  "id": "basic_info",
  "heading": "基本信息",
  "fields": [
    {
      "id": "preferred_name",
      "label": "姓名/称呼",
      "value": "",
      "required": false,
      "sensitive": true,
      "risk_signal": false,
      "notes": "可按来访者愿意提供的程度填写"
    }
  ]
}
```

Validation:

- `workflow` must be `W1`.
- `document_type` must be `intake_form`.
- `sections` must be a non-empty list.
- At least one section heading must contain `风险`.
- At least one field must have `sensitive: true`.
- At least one field must have `risk_signal: true`.
- `boundary_notes` must be non-empty.
- Forbidden diagnosis terms must not appear anywhere in the JSON.

### W2: Case Summary

Required top-level fields:

```json
{
  "workflow": "W2",
  "document_type": "case_summary",
  "title": "个案信息整理",
  "known_facts": [],
  "bio_psycho_social": {},
  "risk_signals": [],
  "information_gaps": [],
  "suggested_questions": [],
  "boundary_notes": []
}
```

Validation:

- `workflow` must be `W2`.
- `document_type` must be `case_summary`.
- `known_facts` must be present.
- `bio_psycho_social` must contain biological, psychological, and social content.
- `risk_signals` must be present.
- `information_gaps` must be present.
- `suggested_questions` must be present.
- `boundary_notes` must be non-empty.
- Forbidden diagnosis terms must not appear anywhere in the JSON.

### W3: Session Note

Required top-level fields:

```json
{
  "workflow": "W3",
  "document_type": "session_note",
  "title": "本次咨询记录",
  "sections": [],
  "risk_change": {},
  "next_session_focus": [],
  "missing_information": [],
  "boundary_notes": []
}
```

Validation:

- `workflow` must be `W3`.
- `document_type` must be `session_note`.
- `sections` must include headings for `本次主题`, `来访者状态`, `咨询师干预`, `风险变化`, and `下次咨询重点`.
- `risk_change` must be present.
- `next_session_focus` must be present.
- `missing_information` must be present.
- `boundary_notes` must be non-empty.
- Forbidden diagnosis terms must not appear anywhere in the JSON.

## JSON Extraction

The extraction function should:

1. Remove the completion marker and anything after it.
2. Find fenced code blocks matching ```` ```json ... ``` ````.
3. Parse the last JSON block.
4. Return parsed data and extraction metadata.

If no block is found, it should return a structured failure rather than raising a raw stack trace to CLI users.

## Validation Result Shape

`structured_check.json` should use:

```json
{
  "status": "PASS",
  "workflow": "W3",
  "issues": []
}
```

Issue shape:

```json
{
  "level": "ERROR",
  "path": "sections",
  "message": "Missing required section: 本次主题"
}
```

Validation status:

- `PASS`: all required checks pass.
- `WARN`: JSON parsed, but optional quality checks are weak.
- `FAIL`: parse failure, workflow mismatch, missing required keys, or forbidden terms.

The first version can use only PASS and FAIL.

## Error Handling

API succeeds but JSON missing:

- Save `raw_output.txt` and `clean_output.md`.
- Write `structured_check.json` with `status: "FAIL"` and `message: "No fenced JSON block found"`.
- Do not write `structured_output.json`.
- Keep command exit status as success because the model call succeeded and the failure is reviewable output quality.

JSON parse error:

- Same behavior as missing JSON, but issue includes the parse error.

Validation failure:

- Save `structured_output.json`.
- Save `structured_check.json` with issue list.
- Record `structured_status: "FAIL"` in metadata.

## Testing

Tests should cover:

- `extract_structured_json` parses the last fenced JSON block.
- Markdown-wrapped completion markers do not break extraction.
- Missing JSON block creates a FAIL check.
- W1 validation requires sensitive and risk fields.
- W2 validation requires BPS, risk signals, gaps, and questions.
- W3 validation requires stable session-note sections.
- Fake API structured success writes `structured_output.json` and `structured_check.json`.
- Fake API structured validation failure writes check but not a false PASS.
- CLI parses `--structured`.
- PowerShell wrapper forwards `-Structured`.

No test should call the real API.

## Acceptance Criteria

The structured output layer is implemented when:

- `scripts/run_agent.py` supports `--structured`.
- `scripts/run-agent.ps1` supports `-Structured`.
- Dry run prompt packages include structured JSON instructions.
- Real API runs with `-Structured` save `structured_output.json` and `structured_check.json`.
- W1/W2/W3 structured smoke tests can pass.
- Existing non-structured runner behavior remains unchanged.
- All unit tests pass locally.

## Future Use

After this layer is stable:

1. Build a `.docx` renderer that consumes `structured_output.json`.
2. Add per-workflow Word styles and section renderers.
3. Add uploaded template parsing and slot filling.
4. Add a backend endpoint that returns both Markdown and structured JSON.
