# DOCX Template Autofill Design

Date: 2026-06-09

## Goal

Add a first-version Word template autofill layer that takes a counselor-provided `.docx` template and a workflow `structured_output.json`, fills recognizable blank fields, and writes an audit-friendly mapping report.

This supports the user scenario: a counselor already has their own form template and wants the agent output to be placed into that template instead of receiving only the project fixed-format `output.docx`.

## Context

The project already has:

- W1/W2/W3 structured output contracts.
- A local agent runner that can save `structured_output.json`.
- A fixed DOCX renderer that generates `output.docx` from structured JSON.

The fixed renderer creates a new document. This feature preserves a user-provided Word template and fills detected fields inside it.

## Scope

In scope:

- Accept a normal `.docx` template and a `structured_output.json`.
- Preserve the original DOCX package structure where possible.
- Fill common table patterns:
  - label cell followed by an empty cell.
  - label cell followed by a placeholder cell such as `____` or `待填写`.
- Fill common paragraph patterns:
  - `标签：____`
  - `标签：`
- Generate `filled_template.docx`.
- Generate `template_fill_report.json`.
- Support W1, W2, and W3 structured outputs.
- Use deterministic rule-based mapping in v0.1.

Out of scope:

- Scanned PDFs, images, handwriting, or screenshots.
- Complex merged-cell reconstruction.
- Header/footer/textbox filling.
- Track changes, comments, and Word content controls.
- LLM-based ambiguous field mapping.
- Web upload UI.
- Speech-to-text.

## Command Interface

Standalone Python CLI:

```powershell
python scripts\fill_docx_template.py --template path\template.docx --structured agent-runs\<run>\structured_output.json --output path\filled_template.docx --report path\template_fill_report.json
```

PowerShell wrapper:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\fill-docx-template.ps1 -TemplatePath path\template.docx -StructuredPath agent-runs\<run>\structured_output.json -OutputPath path\filled_template.docx
```

If `-ReportPath` is omitted, the wrapper writes `template_fill_report.json` beside the output file.

## Output Files

`template_fill_report.json` should make the result reviewable:

```json
{
  "status": "PASS",
  "template_file": "template.docx",
  "structured_file": "structured_output.json",
  "output_file": "filled_template.docx",
  "filled_fields": [
    {
      "template_label": "风险变化",
      "source_path": "risk_change.content",
      "confidence": "high",
      "location": "table[1].row[3].cell[2]"
    }
  ],
  "unfilled_fields": [
    {
      "template_label": "咨询目标",
      "reason": "No matching structured field",
      "location": "paragraph[8]"
    }
  ],
  "issues": []
}
```

Status rules:

- `PASS`: at least one field was filled and no blocking error occurred.
- `WARN`: no fields were filled, or some recognizable placeholders could not be mapped.
- `FAIL`: input cannot be read, the DOCX has no `word/document.xml`, JSON is invalid, or output cannot be written.

## Mapping Rules

The mapper should build a source map from the structured JSON.

### Shared

- `title`
- `boundary_notes`

### W1 Intake Form

- `sections[].heading`
- `sections[].fields[].label`
- `sections[].fields[].value`
- section-level rendered content from all fields

Common aliases:

- 基本信息
- 来访原因
- 当前困扰
- 风险评估
- 知情同意
- 边界说明

### W2 Case Summary

- `known_facts`
- `bio_psycho_social.biological`
- `bio_psycho_social.psychological`
- `bio_psycho_social.social`
- `risk_signals`
- `information_gaps`
- `suggested_questions`
- `boundary_notes`

Common aliases:

- 已知事实
- 生物维度
- 心理维度
- 社会维度
- 风险信号
- 信息缺口
- 建议进一步询问

### W3 Session Note

- `sections[].heading`
- `sections[].content`
- `risk_change.content`
- `next_session_focus`
- `missing_information`
- `boundary_notes`

Common aliases:

- 本次主题
- 来访者状态
- 关键内容
- 咨询师干预
- 来访者反应
- 风险变化
- 进展与阻滞
- 新增个案信息
- 咨询师判断或初步假设
- 待补充信息
- 下次咨询重点
- 边界说明

## Matching Rules

Normalize labels before matching:

- remove whitespace.
- remove punctuation such as `：`, `:`, `（`, `）`, `(`, `)`, `[`, `]`, `【`, `】`.
- remove placeholder characters such as `_`, `＿`, `—`, `-`.

Confidence:

- `high`: normalized template label exactly matches a source alias.
- `medium`: normalized template label contains a source alias, or source alias contains the template label.

The first version should not guess low-confidence matches. If no `high` or `medium` match exists, leave the field blank and report it as unfilled.

## Filling Rules

### Table Rows

For each table row:

1. Read plain text from each cell.
2. If cell `n` matches a source label and cell `n + 1` is empty or placeholder-like, fill cell `n + 1`.
3. If cell `n + 1` already has non-placeholder text, do not overwrite it; report a warning.

### Paragraphs

For each paragraph:

1. If it looks like `标签：____`, replace the paragraph text with `标签：<mapped value>`.
2. If it looks like `标签：` and has no value after the colon, replace it with `标签：<mapped value>`.
3. Preserve the original label text before the colon.

## Implementation Approach

Use Python standard library only:

- `zipfile` to copy the `.docx` package.
- `xml.etree.ElementTree` to parse and update `word/document.xml`.
- `json`, `argparse`, and `pathlib` for CLI and reporting.

The first version only edits `word/document.xml`. It should preserve all other files in the original package.

## Acceptance Criteria

Implemented when:

- `scripts/fill_docx_template.py` exists.
- `scripts/fill-docx-template.ps1` exists.
- Tests cover table-cell filling.
- Tests cover paragraph placeholder filling.
- Tests cover unfilled field reporting.
- CLI writes `filled_template.docx` and `template_fill_report.json`.
- `README.md` documents the command.
- Full Python unit tests pass.

## Future Extensions

1. Add content-control support for modern Word templates.
2. Add header/footer filling.
3. Add optional LLM mapping suggestions for unknown template labels.
4. Add a template mapping cache per counselor.
5. Add speech-to-text before template filling.
6. Add a UI flow for template upload, preview, and manual mapping confirmation.
