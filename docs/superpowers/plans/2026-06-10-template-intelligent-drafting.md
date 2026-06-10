# Template Intelligent Drafting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an LLM-assisted raw-material-to-DOCX template drafting workflow while preserving the existing structured JSON template filler.

**Architecture:** Extend `scripts/fill_docx_template.py` with a validated draft contract and a deterministic draft-to-DOCX filler. Add `/api/draft-template` to `scripts/web_workbench.py`, then update the right-side web UI so template filling can use raw notes, style controls, and existing-content policy.

**Tech Stack:** Python standard library, existing DeepSeek client helpers in `run_model_eval.py`, DOCX XML manipulation via `zipfile` and `xml.etree.ElementTree`, plain HTML/CSS/JS.

---

### Task 1: Backend Draft Contract and Validation

**Files:**
- Modify: `scripts/fill_docx_template.py`
- Modify: `scripts/test_fill_docx_template.py`

- [ ] Add constants for allowed style values, existing-content policies, draft actions, and confidence values.
- [ ] Add `build_template_draft_prompt(slots, raw_input, style, custom_style, existing_content_policy)`.
- [ ] Add `extract_template_draft_json(answer_text)`.
- [ ] Add `validate_template_draft(raw_draft, slots, existing_content_policy)`.
- [ ] Unit-test that unknown slot IDs are rejected, low-confidence drafts are skipped, and `replace_existing` is downgraded when policy is not `replace`.

### Task 2: Deterministic Draft-to-DOCX Filling

**Files:**
- Modify: `scripts/fill_docx_template.py`
- Modify: `scripts/test_fill_docx_template.py`

- [ ] Add `fill_slots_by_draft(root, draft, report, existing_content_policy)`.
- [ ] Add report helpers for `drafted_fields`, `kept_fields`, and `skipped_fields` while keeping old `filled_fields` compatibility.
- [ ] Add `fill_docx_template_from_draft(template_path, draft, output_path, report_path, draft_path=None, source_label="raw_input")`.
- [ ] Unit-test blank fill, append to existing, keep existing, and replace-only policy.

### Task 3: DeepSeek Draft Generation

**Files:**
- Modify: `scripts/fill_docx_template.py`
- Modify: `scripts/test_fill_docx_template.py`

- [ ] Add `run_deepseek_template_draft(slots, raw_input, style, custom_style, existing_content_policy, config, http_post_json=post_json)`.
- [ ] Add `fill_docx_template_from_raw(template_path, raw_input, output_path, report_path, draft_path, style, custom_style, existing_content_policy, config=None, http_post_json=post_json)`.
- [ ] Unit-test the fake API path writes `template_draft.json`, fills the DOCX, and reports model warnings.

### Task 4: Workbench API

**Files:**
- Modify: `scripts/web_workbench.py`
- Modify: `scripts/test_web_workbench.py`

- [ ] Add a standalone template draft run directory helper under `agent-runs/`.
- [ ] Add `handle_draft_template(payload)` and route `POST /api/draft-template`.
- [ ] Accept optional `run_dir`; if missing, create a standalone run directory.
- [ ] Return `output_path`, `draft_path`, `report_path`, and `report`.
- [ ] Unit-test missing input, missing template, fake successful fill, and safe run directory handling.

### Task 5: Web UI Controls

**Files:**
- Modify: `web-workbench/index.html`
- Modify: `web-workbench/app.js`
- Modify: `web-workbench/styles.css`
- Modify: `README.md`

- [ ] Rename the right panel to "智能模板填充".
- [ ] Add raw-material source hint, style selector, custom style input, and existing-content policy selector.
- [ ] Change the primary template action to call `/api/draft-template` with the current input text.
- [ ] Keep a secondary structured JSON fill action when a structured run exists.
- [ ] Update README with the new raw-material template fill flow.

### Task 6: Verification and API Smoke Test

**Files:**
- Modify only if tests reveal a defect.

- [ ] Run `python -m unittest scripts.test_fill_docx_template`.
- [ ] Run `python -m unittest scripts.test_web_workbench`.
- [ ] Run `python -m unittest discover -s scripts -p "test_*.py"`.
- [ ] Start the web workbench and verify the local page loads.
- [ ] If `.env` has a DeepSeek key, run one real draft-fill smoke test against a small raw note and the user's interview template path if present.
- [ ] Commit the completed implementation.
