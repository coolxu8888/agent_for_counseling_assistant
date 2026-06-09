# Structured Output Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add optional structured JSON output to the local v0.1 agent runner, saving `structured_output.json` and `structured_check.json` alongside existing Markdown artifacts.

**Architecture:** Extend `scripts/run_agent.py` with structured prompt contracts, fenced JSON extraction, per-workflow validation, and `--structured` runtime integration. Keep non-structured behavior unchanged and avoid adding external JSON schema dependencies.

**Tech Stack:** Python standard library (`json`, `re`, `argparse`, `unittest`, `tempfile`), existing local runner, PowerShell wrapper.

---

## File Structure

- Modify: `scripts/run_agent.py`
  - Add structured output contracts, extraction, validation, runner integration, CLI flag.
- Modify: `scripts/test_run_agent.py`
  - Add unit coverage for extraction, validation, fake API structured output, CLI flag.
- Modify: `scripts/run-agent.ps1`
  - Add `-Structured` switch and forward `--structured`.
- Modify: `README.md`
  - Document structured runner usage and output files.

---

## Task 1: Structured JSON Extraction

**Files:**
- Modify: `scripts/test_run_agent.py`
- Modify: `scripts/run_agent.py`

- [ ] **Step 1: Add failing extraction tests**

Add tests for:

```python
extract_structured_json("text\n```json\n{\"workflow\":\"W3\"}\n```\nAGENT_DONE_W3", workflow)
```

Expected parsed data:

```python
{"workflow": "W3"}
```

Also test:

- Last fenced JSON block wins.
- `**AGENT_DONE_W3**` is treated as a marker.
- Missing JSON block returns a FAIL check.

- [ ] **Step 2: Run failing tests**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_run_agent
```

Expected: import or assertion failures for missing structured extraction functions.

- [ ] **Step 3: Implement extractor**

Implement:

```python
extract_structured_json(raw_text, workflow)
structured_failure(workflow, message, path="structured_output")
```

Use regex for fenced `json` blocks and `json.loads` for parsing.

- [ ] **Step 4: Run tests**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_run_agent
```

Expected: extraction tests pass.

- [ ] **Step 5: Commit**

Run:

```powershell
git add scripts/run_agent.py scripts/test_run_agent.py
git commit -m "Extract structured JSON blocks from agent output"
```

---

## Task 2: Per-Workflow Structured Validation

**Files:**
- Modify: `scripts/test_run_agent.py`
- Modify: `scripts/run_agent.py`

- [ ] **Step 1: Add failing validation tests**

Add tests for:

- W1 passes when it has `workflow: W1`, `document_type: intake_form`, non-empty `sections`, non-empty `boundary_notes`, at least one field with `sensitive: true`, and at least one field with `risk_signal: true`.
- W2 passes when it has `workflow: W2`, `document_type: case_summary`, `known_facts`, `bio_psycho_social`, `risk_signals`, `information_gaps`, `suggested_questions`, and `boundary_notes`.
- W3 passes when it has `workflow: W3`, `document_type: session_note`, `sections` with required headings, `risk_change`, `next_session_focus`, `missing_information`, and `boundary_notes`.
- Any workflow fails when JSON contains `确诊为` or `诊断为`.

- [ ] **Step 2: Run failing tests**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_run_agent
```

Expected: validation tests fail because validator is missing.

- [ ] **Step 3: Implement validator**

Implement:

```python
validate_structured_output(workflow, data)
```

Return:

```python
{"status": "PASS"|"FAIL", "workflow": "W3", "issues": [...]}
```

- [ ] **Step 4: Run tests**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_run_agent
```

Expected: validation tests pass.

- [ ] **Step 5: Commit**

Run:

```powershell
git add scripts/run_agent.py scripts/test_run_agent.py
git commit -m "Validate structured agent outputs"
```

---

## Task 3: Prompt and Runner Integration

**Files:**
- Modify: `scripts/test_run_agent.py`
- Modify: `scripts/run_agent.py`

- [ ] **Step 1: Add failing integration tests**

Add tests that verify:

- `build_prompt_package(..., structured=True)` includes fenced JSON output instructions.
- `run_agent_once(..., structured=True)` with fake API success writes `structured_output.json` and `structured_check.json`.
- Structured validation failure writes `structured_check.json` with `status: "FAIL"` and records `structured_status` in `metadata.json`.
- Dry run with `structured=True` includes structured instructions in `prompt_package.txt` and does not write structured output files.

- [ ] **Step 2: Run failing tests**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_run_agent
```

Expected: integration tests fail because runner has no `structured` flag.

- [ ] **Step 3: Implement integration**

Modify:

```python
build_prompt_package(workflow, user_input, rag_chunks, structured=False)
run_agent_once(..., structured=False)
```

When structured is enabled:

- Add workflow-specific JSON contract to the prompt.
- After API success, extract JSON.
- Save `structured_output.json` when parsing succeeds.
- Save `structured_check.json` for parse/validation result.
- Add `structured_status` to metadata.

- [ ] **Step 4: Run tests**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_run_agent
```

Expected: integration tests pass.

- [ ] **Step 5: Commit**

Run:

```powershell
git add scripts/run_agent.py scripts/test_run_agent.py
git commit -m "Integrate structured output into agent runner"
```

---

## Task 4: CLI, PowerShell, and Docs

**Files:**
- Modify: `scripts/test_run_agent.py`
- Modify: `scripts/run_agent.py`
- Modify: `scripts/run-agent.ps1`
- Modify: `README.md`

- [ ] **Step 1: Add failing CLI test**

Add test:

```python
args = parse_args(["--workflow", "W3", "--input", "text", "--structured"])
self.assertTrue(args.structured)
```

- [ ] **Step 2: Implement CLI flag**

Add `--structured` to Python argparse and pass it to `run_agent_once`.

- [ ] **Step 3: Implement PowerShell switch**

Add `[switch]$Structured` to `scripts/run-agent.ps1` and forward `--structured`.

- [ ] **Step 4: Update README**

Add examples:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-agent.ps1 -Workflow W3 -Input "..." -Structured
```

Mention `structured_output.json` and `structured_check.json`.

- [ ] **Step 5: Run tests**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest discover -s scripts -p "test_*.py"
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

Run:

```powershell
git add scripts/run_agent.py scripts/test_run_agent.py scripts/run-agent.ps1 README.md
git commit -m "Add structured output CLI option"
```

---

## Task 5: Verification and Real Structured Smoke

**Files:**
- No code changes expected unless smoke exposes defects.

- [ ] **Step 1: Run full unit tests**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest discover -s scripts -p "test_*.py"
```

Expected: all tests pass.

- [ ] **Step 2: Run dry-run structured smoke**

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-agent.ps1 -Workflow W3 -Input "来访者本次谈到和母亲沟通后很委屈。" -Structured -DryRun
```

Expected: prompt package includes JSON instructions; no structured output files are written.

- [ ] **Step 3: Run real structured smoke**

Run W1, W2, and W3 with `-Structured` using low-risk sample inputs.

Expected:

- `structured_output.json` exists for each run.
- `structured_check.json` has `status: "PASS"` for each run.
- Existing `safety_check.json` remains PASS.

- [ ] **Step 4: Fix only if smoke exposes a concrete defect**

If smoke fails due to prompt contract weakness or parser bug:

- Add a failing test for the defect.
- Fix the smallest root cause.
- Re-run full tests and the affected smoke.
- Commit with a focused message.

---

## Final Verification

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest discover -s scripts -p "test_*.py"
git status --short
```

Expected:

- Tests pass.
- Only intentionally untracked local run/eval artifacts remain.

## Self-Review

Spec coverage:

- `--structured` option: Task 4.
- Prompt JSON contract: Task 3.
- JSON extraction and parsing: Task 1.
- Per-workflow validation: Task 2.
- Structured files and metadata: Task 3.
- Dry run behavior: Task 3 and Task 5.
- Real API smoke: Task 5.

Scope check:

- The plan does not implement Word rendering, uploaded templates, speech-to-text, backend API, or workflow auto-classification.

Placeholder scan:

- No open implementation placeholders are intentionally left in this plan.
