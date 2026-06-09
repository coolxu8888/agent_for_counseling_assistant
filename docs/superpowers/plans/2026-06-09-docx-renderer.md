# DOCX Renderer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert workflow `structured_output.json` files into editable `.docx` documents and optionally generate `output.docx` from the local agent runner.

**Architecture:** Add a dependency-free OOXML renderer in `scripts/render_docx.py`, plus tests that inspect the generated DOCX zip. Integrate it into `scripts/run_agent.py` behind a `--docx` flag that implies structured output.

**Tech Stack:** Python standard library (`json`, `zipfile`, `xml.sax.saxutils`, `argparse`, `unittest`, `tempfile`), PowerShell wrapper.

---

## File Structure

- Create: `scripts/render_docx.py`
  - Standalone DOCX renderer and CLI.
- Create: `scripts/test_render_docx.py`
  - Unit tests for OOXML package and W1/W2/W3 rendering.
- Create: `scripts/render-docx.ps1`
  - PowerShell wrapper for standalone renderer.
- Modify: `scripts/run_agent.py`
  - Add `docx` integration after structured output succeeds.
- Modify: `scripts/test_run_agent.py`
  - Add tests for `--docx` and runner integration.
- Modify: `scripts/run-agent.ps1`
  - Add `-Docx`.
- Modify: `README.md`
  - Document standalone and integrated DOCX commands.

---

## Task 1: Minimal DOCX Package Writer

**Files:**
- Create: `scripts/test_render_docx.py`
- Create: `scripts/render_docx.py`

- [ ] **Step 1: Add failing DOCX package test**

Test that `render_docx(data, output_path)` creates a zip with:

```text
[Content_Types].xml
_rels/.rels
word/document.xml
word/styles.xml
```

Use a minimal W3 structured object.

- [ ] **Step 2: Run failing test**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_render_docx
```

Expected: import failure because renderer does not exist.

- [ ] **Step 3: Implement minimal writer**

Implement:

```python
render_docx(data, output_path)
build_document_xml(data)
write_docx_package(output_path, document_xml)
```

Use standard library only.

- [ ] **Step 4: Run test**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_render_docx
```

Expected: test passes.

- [ ] **Step 5: Commit**

Run:

```powershell
git add scripts/render_docx.py scripts/test_render_docx.py
git commit -m "Add minimal DOCX package renderer"
```

---

## Task 2: Workflow Renderers

**Files:**
- Modify: `scripts/render_docx.py`
- Modify: `scripts/test_render_docx.py`

- [ ] **Step 1: Add failing W1/W2/W3 rendering tests**

Tests should inspect `word/document.xml`:

- W1 contains `初访信息收集表`, `风险评估`, and table tags `<w:tbl>`.
- W2 contains `个案信息整理`, `生物维度`, `心理维度`, `社会维度`, `建议进一步询问`.
- W3 contains `本次咨询记录`, `本次主题`, `风险变化`, `下次咨询重点`.

- [ ] **Step 2: Run failing tests**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_render_docx
```

Expected: assertions fail until workflow renderers are implemented.

- [ ] **Step 3: Implement workflow renderers**

Implement:

```python
render_intake_form(data)
render_case_summary(data)
render_session_note(data)
```

Use paragraphs, headings, bullet-like paragraphs, numbered-like paragraphs, and simple tables.

- [ ] **Step 4: Run tests**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_render_docx
```

Expected: tests pass.

- [ ] **Step 5: Commit**

Run:

```powershell
git add scripts/render_docx.py scripts/test_render_docx.py
git commit -m "Render counselor structured outputs as DOCX"
```

---

## Task 3: Standalone CLI and PowerShell Wrapper

**Files:**
- Modify: `scripts/render_docx.py`
- Create: `scripts/render-docx.ps1`
- Modify: `scripts/test_render_docx.py`

- [ ] **Step 1: Add CLI tests**

Test:

```python
parse_args(["--input", "in.json", "--output", "out.docx"])
```

and `main()` with a temporary input JSON creates output and check JSON.

- [ ] **Step 2: Implement CLI**

Add:

```text
--input
--output
--check-output
```

Default check path should be beside output as `docx_check.json`.

- [ ] **Step 3: Add PowerShell wrapper**

Create `scripts/render-docx.ps1` with:

```powershell
param([string]$InputPath, [string]$OutputPath, [string]$CheckOutput = "")
python scripts\render_docx.py --input ... --output ...
```

- [ ] **Step 4: Run tests**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_render_docx
```

Expected: tests pass.

- [ ] **Step 5: Commit**

Run:

```powershell
git add scripts/render_docx.py scripts/test_render_docx.py scripts/render-docx.ps1
git commit -m "Add DOCX renderer CLI"
```

---

## Task 4: Agent Runner DOCX Integration

**Files:**
- Modify: `scripts/run_agent.py`
- Modify: `scripts/test_run_agent.py`
- Modify: `scripts/run-agent.ps1`

- [ ] **Step 1: Add failing runner tests**

Tests:

- `parse_args(["--workflow", "W3", "--input", "text", "--docx"])` sets `docx`.
- `--docx` causes `run_agent_once` to use structured mode.
- Fake structured API success with `docx=True` writes `output.docx` and `docx_check.json`.
- If structured validation fails, no `output.docx` is written and `docx_check.json` is FAIL.

- [ ] **Step 2: Implement integration**

Modify:

```python
run_agent_once(..., docx=False)
```

When `docx=True`:

- Force `structured=True`.
- After structured validation PASS, call `render_docx`.
- Write `docx_check.json`.
- Add `docx_status` to metadata.

- [ ] **Step 3: Add `-Docx` to PowerShell wrapper**

Forward `--docx`.

- [ ] **Step 4: Run tests**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest discover -s scripts -p "test_*.py"
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

Run:

```powershell
git add scripts/run_agent.py scripts/test_run_agent.py scripts/run-agent.ps1
git commit -m "Generate DOCX from agent runner"
```

---

## Task 5: Docs and Smoke

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README**

Add examples:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\render-docx.ps1 -InputPath agent-runs\<run>\structured_output.json -OutputPath agent-runs\<run>\output.docx
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-agent.ps1 -Workflow W3 -Input "..." -Structured -Docx
```

- [ ] **Step 2: Run full tests**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest discover -s scripts -p "test_*.py"
```

- [ ] **Step 3: Run real W3 structured-to-docx smoke**

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-agent.ps1 -Workflow W3 -Input "来访者本次谈到和母亲沟通后很委屈。" -Structured -Docx
```

Expected:

- `structured_check.json` PASS.
- `docx_check.json` PASS.
- `output.docx` exists.
- `word/document.xml` contains `本次咨询记录`.

- [ ] **Step 4: Commit**

Run:

```powershell
git add README.md
git commit -m "Document DOCX renderer usage"
```

---

## Final Verification

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest discover -s scripts -p "test_*.py"
git status --short
```

Expected:

- Tests pass.
- Only intended local artifact folders remain untracked.

## Self-Review

Spec coverage:

- Standalone renderer: Tasks 1-3.
- W1/W2/W3 fixed rendering: Task 2.
- `-Docx` runner integration: Task 4.
- `docx_check.json`: Tasks 3-4.
- Real smoke: Task 5.

Scope check:

- The plan does not implement uploaded templates, slot detection, PDF export, images, speech-to-text, or backend APIs.
