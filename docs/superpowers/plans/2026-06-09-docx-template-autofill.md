# DOCX Template Autofill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fill counselor-provided `.docx` templates from workflow `structured_output.json` files and produce an auditable mapping report.

**Architecture:** Add a standalone standard-library DOCX template filler that edits only `word/document.xml` inside a copied DOCX package. The filler builds a source map from W1/W2/W3 structured JSON, applies deterministic table and paragraph fill rules, and writes `template_fill_report.json`.

**Tech Stack:** Python standard library (`argparse`, `json`, `pathlib`, `re`, `tempfile`, `unittest`, `xml.etree.ElementTree`, `zipfile`), PowerShell wrapper.

---

## File Structure

- Create: `scripts/fill_docx_template.py`
  - Source-map creation, DOCX XML parsing, table/paragraph field detection, filling, CLI, JSON report.
- Create: `scripts/test_fill_docx_template.py`
  - Unit tests for table filling, paragraph filling, unfilled fields, and CLI output.
- Create: `scripts/fill-docx-template.ps1`
  - PowerShell wrapper for the standalone CLI.
- Modify: `README.md`
  - Add user-facing command examples for template filling.

---

## Task 1: Source Map and Matching Tests

**Files:**
- Create: `scripts/test_fill_docx_template.py`
- Create: `scripts/fill_docx_template.py`

- [ ] **Step 1: Write failing tests for source mapping and label matching**

Add tests that expect:

```python
from fill_docx_template import build_source_map, find_source_match, normalize_label


def sample_w3():
    return {
        "workflow": "W3",
        "document_type": "session_note",
        "title": "本次咨询记录",
        "sections": [
            {"heading": "本次主题", "content": "讨论分手后的低落情绪。"},
            {"heading": "咨询师干预", "content": "支持性回应并讨论社会支持。"},
        ],
        "risk_change": {"content": "出现被动自杀意念，无具体计划。"},
        "next_session_focus": ["继续评估安全情况", "回顾联系朋友的结果"],
        "missing_information": ["风险意念频率与强度"],
        "boundary_notes": ["本记录不替代正式风险评估。"],
    }


def test_normalize_label_removes_punctuation_and_placeholders():
    assert normalize_label(" 风险变化：____ ") == "风险变化"


def test_build_source_map_exposes_w3_core_fields():
    source_map = build_source_map(sample_w3())
    match = find_source_match("风险变化", source_map)
    assert match is not None
    assert match["source_path"] == "risk_change.content"
    assert match["value"] == "出现被动自杀意念，无具体计划。"


def test_find_source_match_supports_medium_contains_match():
    source_map = build_source_map(sample_w3())
    match = find_source_match("下次咨询重点安排", source_map)
    assert match is not None
    assert match["confidence"] == "medium"
    assert "继续评估安全情况" in match["value"]
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_fill_docx_template
```

Expected: import failure or missing function failure.

- [ ] **Step 3: Implement minimal source map and matching**

Implement:

```python
def normalize_label(label): ...
def render_value(value): ...
def build_source_map(data): ...
def find_source_match(template_label, source_map): ...
```

Include W1/W2/W3 aliases from `docs/superpowers/specs/2026-06-09-docx-template-autofill-design.md`.

- [ ] **Step 4: Run tests and verify pass**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_fill_docx_template
```

Expected: tests pass.

- [ ] **Step 5: Commit**

Run:

```powershell
git add scripts/fill_docx_template.py scripts/test_fill_docx_template.py
git commit -m "Add DOCX template source mapping"
```

---

## Task 2: Table and Paragraph Filling

**Files:**
- Modify: `scripts/fill_docx_template.py`
- Modify: `scripts/test_fill_docx_template.py`

- [ ] **Step 1: Add failing DOCX fill tests**

Use `render_docx.write_docx_package()` from the existing renderer to build a minimal template package with:

```xml
<w:tbl>
  <w:tr>
    <w:tc><w:p><w:r><w:t>风险变化</w:t></w:r></w:p></w:tc>
    <w:tc><w:p><w:r><w:t>____</w:t></w:r></w:p></w:tc>
  </w:tr>
</w:tbl>
<w:p><w:r><w:t>下次咨询重点：____</w:t></w:r></w:p>
```

Add tests that:

- call `fill_docx_template(template, structured, output, report)`.
- inspect `word/document.xml`.
- assert the risk text fills the table cell.
- assert paragraph placeholder becomes `下次咨询重点：继续评估安全情况...`.
- assert report contains two `filled_fields`.

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_fill_docx_template
```

Expected: missing `fill_docx_template` or unimplemented fill behavior.

- [ ] **Step 3: Implement DOCX XML fill**

Implement:

```python
def fill_docx_template(template_path, structured_path, output_path, report_path): ...
def fill_document_xml(document_xml, data): ...
def fill_tables(root, source_map, report): ...
def fill_paragraphs(root, source_map, report): ...
def element_text(element): ...
def set_element_text(element, text): ...
```

Use namespace `http://schemas.openxmlformats.org/wordprocessingml/2006/main`.

Rules:

- Fill only empty or placeholder-like target cells.
- Do not overwrite non-placeholder text.
- Report location strings such as `table[0].row[0].cell[1]` and `paragraph[2]`.

- [ ] **Step 4: Run tests and verify pass**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_fill_docx_template
```

Expected: tests pass.

- [ ] **Step 5: Commit**

Run:

```powershell
git add scripts/fill_docx_template.py scripts/test_fill_docx_template.py
git commit -m "Fill DOCX template fields"
```

---

## Task 3: Report Quality and Failure Handling

**Files:**
- Modify: `scripts/fill_docx_template.py`
- Modify: `scripts/test_fill_docx_template.py`

- [ ] **Step 1: Add failing report tests**

Add tests that:

- unknown placeholder `咨询目标：____` is listed in `unfilled_fields`.
- non-placeholder target cell is not overwritten and creates an issue.
- invalid JSON returns `FAIL`.
- a DOCX missing `word/document.xml` returns `FAIL`.

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_fill_docx_template
```

Expected: assertions fail until report handling is complete.

- [ ] **Step 3: Implement report status and issue handling**

Implement:

```python
def success_status(report): ...
def report_failure(message, template_path=None, structured_path=None, output_path=None): ...
def write_report(path, report): ...
```

Status rules:

- `PASS` if one or more fields were filled and no error issue exists.
- `WARN` if zero fields were filled or any unfilled fields/issues exist without a blocking error.
- `FAIL` for blocking errors.

- [ ] **Step 4: Run tests and verify pass**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_fill_docx_template
```

Expected: tests pass.

- [ ] **Step 5: Commit**

Run:

```powershell
git add scripts/fill_docx_template.py scripts/test_fill_docx_template.py
git commit -m "Report DOCX template fill results"
```

---

## Task 4: CLI, PowerShell Wrapper, and Docs

**Files:**
- Modify: `scripts/fill_docx_template.py`
- Modify: `scripts/test_fill_docx_template.py`
- Create: `scripts/fill-docx-template.ps1`
- Modify: `README.md`

- [ ] **Step 1: Add failing CLI test**

Add tests for:

```python
parse_args([
    "--template", "template.docx",
    "--structured", "structured_output.json",
    "--output", "filled_template.docx",
    "--report", "template_fill_report.json",
])
```

Add a `main()` test that writes output and report from temporary files.

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_fill_docx_template
```

Expected: missing `parse_args` or `main`.

- [ ] **Step 3: Implement CLI**

Add:

```text
--template
--structured
--output
--report
```

Default report path should be `template_fill_report.json` next to the output when `--report` is omitted.

- [ ] **Step 4: Add PowerShell wrapper**

Create `scripts/fill-docx-template.ps1` with parameters:

```powershell
param(
  [Parameter(Mandatory=$true)][string]$TemplatePath,
  [Parameter(Mandatory=$true)][string]$StructuredPath,
  [Parameter(Mandatory=$true)][string]$OutputPath,
  [string]$ReportPath = ""
)
```

It should call `python scripts\fill_docx_template.py`.

- [ ] **Step 5: Update README**

Document:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\fill-docx-template.ps1 -TemplatePath path\template.docx -StructuredPath agent-runs\<run>\structured_output.json -OutputPath path\filled_template.docx
```

Explain that v0.1 fills recognizable table and paragraph blanks and writes `template_fill_report.json` for manual review.

- [ ] **Step 6: Run tests and wrapper smoke**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_fill_docx_template
```

Then run the full test suite:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest discover -s scripts -p "test_*.py"
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

Run:

```powershell
git add scripts/fill_docx_template.py scripts/test_fill_docx_template.py scripts/fill-docx-template.ps1 README.md
git commit -m "Add DOCX template autofill CLI"
```

---

## Final Verification

Run:

```powershell
git status --short
$env:PYTHONPATH='scripts'; python -m unittest discover -s scripts -p "test_*.py"
```

Expected:

- Only unrelated ignored/untracked local files remain.
- Full test suite passes.

Then merge the worktree branch back to `main` after review.
