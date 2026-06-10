# Template Intelligent Drafting Design

## Goal

Upgrade Word template filling from "map structured JSON fields into blanks" to "read counselor raw material, understand a counselor-provided Word template, draft field-level content, and fill the template with an auditable report."

This addresses three product needs:

- The counselor may paste raw notes, dictation, or a rough session record instead of first running W1/W2/W3.
- The uploaded template may contain many blank fields whose labels do not exactly match the agent's fixed JSON schema.
- The uploaded template may already contain partial content, so the agent needs a clear policy for keeping, appending, revising, or replacing existing text.

## Recommended Approach

Use a hybrid workflow:

1. Extract template slots and current content deterministically from the DOCX.
2. Ask the model to produce a constrained `template_draft.json`.
3. Validate the draft before any Word file is edited.
4. Fill the Word file deterministically from the validated draft.
5. Save a report listing filled, revised, kept, skipped, and warning fields.

The old structured-JSON filler remains available as a fallback and as a safer path when a structured workflow output already exists.

## User Workflow

In the local web workbench, the right panel becomes "智能模板填充".

Inputs:

- Word template path.
- Raw counselor material. By default this reuses the bottom input box; the user can edit it for template filling.
- Language style:
  - `professional_concise`: professional and concise.
  - `warm_clinical`: warmer but still clinical.
  - `institutional_record`: formal institutional record.
  - `supervision_summary`: supervision-oriented summary.
  - `custom`: user-provided style note.
- Existing content policy:
  - `merge`: preserve existing content and append or polish when the raw material adds useful information. This is the default.
  - `ask`: do not overwrite non-empty slots; report fields that need user confirmation.
  - `replace`: replace recognizable existing slot content with a newly organized version.
  - `blank_only`: fill only blank placeholders.

Outputs:

- `filled_template.docx`
- `template_draft.json`
- `template_fill_report.json`

## Draft Contract

The model must return JSON only:

```json
{
  "drafts": [
    {
      "slot_id": "table[0].row[2].cell[1]",
      "template_label": "主要困扰",
      "action": "fill_blank",
      "content": "来访者近期因分手后情绪低落前来咨询，伴随社交退缩。",
      "confidence": "medium",
      "evidence": ["分手后低落", "很久没有告诉朋友自己的状态"],
      "reason": "The template label asks for the presenting concern and the raw note contains this information."
    }
  ],
  "global_warnings": [
    "材料出现被动自杀意念，需由咨询师完成正式风险评估。"
  ]
}
```

Allowed actions:

- `fill_blank`: fill an empty placeholder.
- `append_to_existing`: keep existing text and append a new paragraph.
- `revise_existing`: rewrite existing text using both existing content and raw material.
- `replace_existing`: replace existing text. Allowed only when policy is `replace`.
- `keep_existing`: leave existing text unchanged.
- `leave_blank`: leave the slot blank because the source material does not support a safe answer.

Allowed confidence values:

- `high`
- `medium`
- `low`
- `none`

Only `high` and `medium` drafts are filled automatically. Low and none are reported for review.

## Safety Rules

The model must not:

- Invent facts not present in raw material or existing template content.
- Produce a final psychiatric diagnosis unless the raw material explicitly says a qualified professional already made one.
- Produce a final self-harm or violence risk level as if it were a clinical determination.
- Fill identity, contact, medical, medication, emergency contact, or test result fields unless the information is explicitly present.
- Delete existing template content unless policy is `replace` and the slot draft action is `replace_existing`.

The report must preserve uncertainty by listing missing information and warnings instead of silently filling unsupported fields.

## Backend API

Add a new endpoint:

```text
POST /api/draft-template
```

Request:

```json
{
  "template_path": "C:/Users/win/Desktop/template.docx",
  "raw_input": "咨询师粘贴的原始材料",
  "style": "professional_concise",
  "custom_style": "",
  "existing_content_policy": "merge",
  "run_dir": "optional existing agent-runs directory"
}
```

Response:

```json
{
  "status": "success",
  "output_path": "C:/.../filled_template.docx",
  "draft_path": "C:/.../template_draft.json",
  "report_path": "C:/.../template_fill_report.json",
  "report": {}
}
```

If `run_dir` is absent, the server creates a standalone run directory under `agent-runs/`.

## Validation

Before filling a DOCX:

- Reject unknown `slot_id` values.
- Reject unknown actions and confidence values.
- Convert unsafe actions to `leave_blank` when the policy does not allow them.
- Skip drafts with empty content unless action is `keep_existing` or `leave_blank`.
- Record any dropped or changed draft item in `issues`.

## Scope

In scope:

- Table adjacent-cell placeholders.
- Paragraph placeholders.
- Single-cell table block sections already supported by the old filler.
- Prefilled slots detected by the same slot extractor.
- Model-assisted draft generation for raw material.
- UI controls for style and existing-content policy.

Out of scope for this iteration:

- Speech-to-text.
- Native file upload; local path input remains acceptable for the current desktop workbench.
- Manual field-by-field editing inside the browser.
- Content controls in modern DOCX templates.

## Acceptance Criteria

- A counselor can paste raw material and fill a Word template without first running W1/W2/W3.
- Existing non-empty template fields are preserved by default and appended or polished only when the selected policy allows it.
- The generated report clearly lists filled, revised, kept, skipped, and warning fields.
- The old `/api/fill-template` structured JSON path still works.
- Unit tests cover validation, existing-content policy, backend endpoint behavior, and deterministic fill from a fake model draft.
