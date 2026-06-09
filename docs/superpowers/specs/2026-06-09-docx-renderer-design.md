# DOCX Renderer Design

Date: 2026-06-09

## Goal

Add a fixed-template Word renderer that converts `structured_output.json` into an editable `.docx` file.

This is the first document-delivery layer for the counselor assistant. It should let a counselor run a workflow, request structured output, and receive a Word document that can be opened, edited, saved, and archived.

## Context

The project already has:

- W1/W2/W3 local agent runner.
- `structured_output.json` and `structured_check.json`.
- Real API structured smoke tests passing for W1, W2, and W3.

The next layer should not parse Markdown. It should consume `structured_output.json`.

The current Python environment does not include `python-docx`, so the first version should use Python standard library only and write a minimal OOXML `.docx` package with `zipfile` and XML escaping.

## Scope

In scope:

- Render W1, W2, and W3 structured JSON into fixed-format `.docx`.
- Add a standalone renderer CLI.
- Add optional `--docx` / `-Docx` support to the agent runner.
- Save `output.docx` in the agent run folder.
- Save `docx_check.json` with rendering status.
- Add tests that inspect the generated `.docx` zip and `word/document.xml`.

Out of scope:

- Uploaded user templates.
- Template slot detection.
- Complex Word styling.
- Headers/footers/page numbers.
- Track changes/comments.
- Images.
- PDF export.
- Speech-to-text.

## Command Interface

Standalone renderer:

```powershell
python scripts\render_docx.py --input agent-runs\<run>\structured_output.json --output agent-runs\<run>\output.docx
```

PowerShell wrapper:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\render-docx.ps1 -InputPath agent-runs\<run>\structured_output.json -OutputPath agent-runs\<run>\output.docx
```

Agent runner integration:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-agent.ps1 -Workflow W3 -Input "..." -Structured -Docx
```

`-Docx` should imply `-Structured`, because Word rendering depends on `structured_output.json`.

## Output Files

When `-Docx` succeeds:

```text
agent-runs/<timestamp>-W3/
  structured_output.json
  structured_check.json
  output.docx
  docx_check.json
```

`docx_check.json`:

```json
{
  "status": "PASS",
  "output_file": "agent-runs/.../output.docx",
  "issues": []
}
```

On failure:

```json
{
  "status": "FAIL",
  "issues": [
    {
      "level": "ERROR",
      "message": "Unsupported document_type: ..."
    }
  ]
}
```

## Rendering Rules

### General

All documents should include:

- Title as Word Heading 1.
- Workflow-specific sections.
- Boundary notes near the end.
- Missing information when present.

Text should remain editable as normal Word paragraphs and tables.

### W1: Intake Form

Input type: `document_type: intake_form`

Render:

- Title.
- Each section heading as Heading 2.
- Section fields as a table.
- Table columns:
  - 字段
  - 内容
  - 必填
  - 敏感
  - 风险信号
  - 备注
- Empty values should render as blank editable cells or `待填写`.

### W2: Case Summary

Input type: `document_type: case_summary`

Render:

- Title.
- Known facts as bullet list.
- Bio/Psycho/Social subsections.
- Risk signals.
- Information gaps.
- Suggested questions as numbered list.
- Boundary notes.

If `risk_signals` is an empty list, render `材料中未见明确风险信号，建议咨询师按需进一步评估。`

### W3: Session Note

Input type: `document_type: session_note`

Render:

- Title.
- Each item in `sections` as Heading 2 + paragraph.
- `risk_change` as a distinct section if not already covered.
- `next_session_focus` as bullet list.
- `missing_information` as bullet list.
- Boundary notes.

## DOCX Implementation

Generate a minimal OOXML package:

```text
[Content_Types].xml
_rels/.rels
word/document.xml
word/styles.xml
word/_rels/document.xml.rels
```

Use:

- `zipfile.ZipFile`
- `xml.sax.saxutils.escape`

The first version does not need external dependencies.

## Validation

Renderer should fail fast if:

- Input JSON is not an object.
- `document_type` is missing.
- `document_type` is unsupported.
- Required fields for the selected document type are missing.

Tests should inspect:

- `.docx` is a zip file.
- `word/document.xml` exists.
- Expected Chinese titles and section names appear in XML.
- Tables are generated for W1 fields.
- W2/W3 output contains risk/boundary sections.

## Acceptance Criteria

Implemented when:

- `scripts/render_docx.py` exists.
- `scripts/render-docx.ps1` exists.
- `scripts/run_agent.py` supports `--docx`.
- `scripts/run-agent.ps1` supports `-Docx`.
- Standalone renderer can convert sample W1/W2/W3 structured JSON to `.docx`.
- Agent runner with `-Structured -Docx` saves `output.docx`.
- `docx_check.json` is written.
- Unit tests pass.
- Real W3 structured-to-docx smoke succeeds.

## Future Extensions

After fixed DOCX rendering is stable:

1. Add branded/institution style profiles.
2. Add uploaded Word template parsing.
3. Add placeholder mapping from template to structured JSON.
4. Add speech-to-text before the agent input step.
