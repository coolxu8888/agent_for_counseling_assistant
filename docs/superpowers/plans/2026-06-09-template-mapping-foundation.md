# Template Mapping Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the non-LLM foundation for uploaded Word template understanding: extract template slots, export structured source paths, generate mapping JSON, and optionally fill DOCX by mapping.

**Architecture:** Extend `scripts/fill_docx_template.py` instead of creating a separate pipeline. The script will expose pure functions for slot extraction, source path export, mapping generation, and mapping-based filling; the CLI will optionally write `template_slots.json`, `source_paths.json`, and `template_mapping.json`.

**Tech Stack:** Python standard library (`argparse`, `json`, `pathlib`, `re`, `unittest`, `xml.etree.ElementTree`, `zipfile`), existing PowerShell wrapper.

---

## File Structure

- Modify: `scripts/fill_docx_template.py`
  - Add slot extraction, source path export, deterministic mapping, optional mapping input/output, and mapping-based fill.
- Modify: `scripts/test_fill_docx_template.py`
  - Add tests for slot extraction, source path export, mapping generation, and mapping-based fill.
- Modify: `scripts/fill-docx-template.ps1`
  - Add optional parameters for mapping artifacts.
- Modify: `README.md`
  - Document the template mapping foundation workflow.

---

## Task 1: Template Slot Extraction

**Files:**
- Modify: `scripts/test_fill_docx_template.py`
- Modify: `scripts/fill_docx_template.py`

- [ ] **Step 1: Add failing tests**

Add tests for:

```python
slots = extract_template_slots_from_xml(self.template_xml())
self.assertEqual(slots[0]["slot_id"], "table[0].row[0].cell[1]")
self.assertEqual(slots[0]["label"], "风险变化")
self.assertEqual(slots[0]["slot_type"], "table_adjacent_cell")
self.assertEqual(slots[1]["slot_id"], "paragraph[0]")
self.assertEqual(slots[1]["label"], "下次咨询重点")
self.assertEqual(slots[1]["slot_type"], "paragraph_placeholder")
```

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_fill_docx_template
```

Expected: import or missing function failure.

- [ ] **Step 3: Implement slot extraction**

Implement:

```python
def extract_template_slots_from_xml(document_xml): ...
def extract_template_slots(template_path): ...
```

Slot schema:

```json
{
  "slot_id": "table[0].row[0].cell[1]",
  "label": "风险变化",
  "location": "table[0].row[0].cell[1]",
  "slot_type": "table_adjacent_cell",
  "current_text": "____"
}
```

- [ ] **Step 4: Run test to verify pass**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_fill_docx_template
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add scripts/fill_docx_template.py scripts/test_fill_docx_template.py
git commit -m "Extract DOCX template slots"
```

---

## Task 2: Source Paths and Mapping JSON

**Files:**
- Modify: `scripts/test_fill_docx_template.py`
- Modify: `scripts/fill_docx_template.py`

- [ ] **Step 1: Add failing tests**

Add tests for:

```python
source_paths = build_source_paths(self.sample_w3())
self.assertIn("risk_change.content", [item["source_path"] for item in source_paths])

mapping = build_template_mapping(slots, source_paths)
self.assertEqual(mapping["mappings"][0]["source_path"], "risk_change.content")
self.assertEqual(mapping["mappings"][0]["fill_status"], "ready")
```

Also test unknown slot:

```python
self.assertEqual(mapping["mappings"][0]["source_path"], "unmapped")
self.assertEqual(mapping["mappings"][0]["fill_status"], "skipped")
```

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_fill_docx_template
```

- [ ] **Step 3: Implement source path export and mapping**

Implement:

```python
def build_source_paths(data): ...
def build_template_mapping(slots, source_paths): ...
```

Mapping schema:

```json
{
  "mappings": [
    {
      "slot_id": "paragraph[0]",
      "template_label": "下次咨询重点",
      "source_path": "next_session_focus",
      "confidence": "high",
      "fill_status": "ready",
      "reason": "Rule match."
    }
  ]
}
```

- [ ] **Step 4: Run test to verify pass**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_fill_docx_template
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add scripts/fill_docx_template.py scripts/test_fill_docx_template.py
git commit -m "Build DOCX template mapping artifacts"
```

---

## Task 3: Fill by Mapping

**Files:**
- Modify: `scripts/test_fill_docx_template.py`
- Modify: `scripts/fill_docx_template.py`

- [ ] **Step 1: Add failing tests**

Add tests that:

- write a `template_mapping.json` with a valid `risk_change.content` mapping.
- call `fill_docx_template(..., mapping_path=mapping_path)`.
- assert the output DOCX contains the mapped value.
- assert `template_fill_report.json` records `source_path` from the mapping.
- assert mappings with `fill_status: "skipped"` are not filled.

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_fill_docx_template
```

- [ ] **Step 3: Implement mapping-based fill**

Add:

```python
def fill_document_xml(document_xml, data, report, mapping=None): ...
def fill_slots_by_mapping(root, source_values, mapping, report): ...
```

Rules:

- fill only `fill_status: "ready"`;
- ignore `source_path: "unmapped"`;
- never overwrite non-placeholder text;
- preserve existing deterministic behavior when no mapping is supplied.

- [ ] **Step 4: Run test to verify pass**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_fill_docx_template
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add scripts/fill_docx_template.py scripts/test_fill_docx_template.py
git commit -m "Fill DOCX templates from mapping JSON"
```

---

## Task 4: CLI, Wrapper, and Docs

**Files:**
- Modify: `scripts/test_fill_docx_template.py`
- Modify: `scripts/fill_docx_template.py`
- Modify: `scripts/fill-docx-template.ps1`
- Modify: `README.md`

- [ ] **Step 1: Add failing CLI tests**

Add tests for parsing:

```text
--slots-output template_slots.json
--source-paths-output source_paths.json
--mapping-output template_mapping.json
--mapping-input reviewed_mapping.json
```

Add a `main()` test that writes all three artifact files.

- [ ] **Step 2: Run test to verify failure**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_fill_docx_template
```

- [ ] **Step 3: Implement CLI options**

Extend `parse_args()` and `main()` with:

```text
--slots-output
--source-paths-output
--mapping-output
--mapping-input
```

If `--mapping-input` is omitted, generate a deterministic mapping from extracted slots and source paths.

- [ ] **Step 4: Extend PowerShell wrapper**

Add optional parameters:

```powershell
[string]$SlotsOutput = ""
[string]$SourcePathsOutput = ""
[string]$MappingOutput = ""
[string]$MappingInput = ""
```

- [ ] **Step 5: Update README**

Document:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\fill-docx-template.ps1 -TemplatePath path\template.docx -StructuredPath agent-runs\<run>\structured_output.json -OutputPath path\filled_template.docx -SlotsOutput path\template_slots.json -SourcePathsOutput path\source_paths.json -MappingOutput path\template_mapping.json
```

- [ ] **Step 6: Run full tests**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest discover -s scripts -p "test_*.py"
```

- [ ] **Step 7: Commit**

Run:

```powershell
git add scripts/fill_docx_template.py scripts/test_fill_docx_template.py scripts/fill-docx-template.ps1 README.md
git commit -m "Expose DOCX template mapping artifacts"
```

---

## Final Verification

Run:

```powershell
git status --short
$env:PYTHONPATH='scripts'; python -m unittest discover -s scripts -p "test_*.py"
```

Expected:

- Full test suite passes.
- Only unrelated existing untracked files remain.
