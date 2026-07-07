# W1 Completion Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce durable evidence for W1 Web integration, hosted verification, and real-template verification across both W1 modes, then let the unified matrix derive W1 as complete.

**Architecture:** Add small acceptance-report helpers around the existing Web, hosted-smoke, and DOCX/template paths rather than creating parallel product implementations. Browser acceptance is executed through the visible Chinese Web UI for both W1 modes; hosted verification records sanitized real-model results; template verification uses the repository's real initial-interview DOCX. Only after all reports validate does the matrix move the three W1 gates to `passed`.

**Tech Stack:** Python standard library and existing project modules, `unittest`, in-app browser automation, existing Render/hosted smoke tooling, DOCX ZIP/XML inspection, JSON evidence reports.

---

## File Map

- Create `docs/w1-acceptance-agent-work.md`: delegated ownership and checklist.
- Create `scripts/w1_acceptance.py`: shared schema validation and sanitized report writing.
- Create `scripts/test_w1_acceptance.py`: report, secret/path, and two-mode coverage tests.
- Create `scripts/run_w1_template_acceptance.py`: real-template inspection/fill/reopen verification.
- Create `scripts/test_run_w1_template_acceptance.py`: real-template runner tests.
- Create `eval-data/w1-summary-template-acceptance.json`: de-identified valid W1 fixed-summary fixture used only to exercise deterministic real-template filling.
- Modify `scripts/hosted_smoke.py`: optional sanitized W1 acceptance report output with full-output assertions.
- Modify `scripts/test_hosted_smoke.py`: W1 prep/summary hosted report tests.
- Create `eval-results/acceptance/w1/`: committed sanitized successful reports only.
- Modify `workflow-completion.json`: reference successful Web, hosted, and template reports.
- Regenerate `docs/product-loop-state.md` and update Notion only after all gates pass.

### Task 1: Acceptance report contract

**Files:**
- Create: `scripts/test_w1_acceptance.py`
- Create: `scripts/w1_acceptance.py`

- [ ] **Step 1: Write failing tests**

Define tests for:

```python
def test_w1_web_report_requires_both_modes(self): ...
def test_w1_hosted_report_requires_model_and_artifact_assertions(self): ...
def test_report_rejects_secret_and_server_path_fields(self): ...
def test_write_report_is_stable_json(self): ...
```

The Web contract requires `intake_prep` and `initial_interview_summary`, Chinese visible labels, structured-result assertion, and DOCX-download assertion. Hosted scenarios additionally require base URL, UTC timestamp, workflow `W1`, mode, successful real run, structured PASS, and artifact metadata.

- [ ] **Step 2: Verify red**

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_w1_acceptance -v
```

Expected: import failure because `w1_acceptance` does not exist.

- [ ] **Step 3: Implement the minimal report validator**

Provide focused functions:

```python
W1_MODES = ("intake_prep", "initial_interview_summary")

class W1AcceptanceError(ValueError):
    pass

def validate_web_report(report: dict) -> None: ...
def validate_hosted_report(report: dict) -> None: ...
def validate_template_report(report: dict, repo_root: Path) -> None: ...
def write_sanitized_report(path: Path, report: dict) -> None: ...
```

Reject keys or values containing tokens/passwords/cookies, direct server filesystem paths, and missing mode coverage. User-visible labels stored in reports remain Chinese.

- [ ] **Step 4: Verify green and commit**

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_w1_acceptance -v
git add scripts/w1_acceptance.py scripts/test_w1_acceptance.py
git commit -m "Add W1 acceptance report contract"
```

### Task 2: Real-template acceptance

**Files:**
- Create: `scripts/test_run_w1_template_acceptance.py`
- Create: `scripts/run_w1_template_acceptance.py`
- Read/reuse: `scripts/fill_docx_template.py`

- [ ] **Step 1: Write failing tests**

Test real-template discovery under `docs/`, required W1 summary section mapping, fill helper invocation, reopening the generated DOCX, non-empty mapped cells, sanitized report validation, and refusal to pass synthetic XML fixtures.

- [ ] **Step 2: Verify red**

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_run_w1_template_acceptance -v
```

- [ ] **Step 3: Implement the runner**

The CLI accepts a real template path and either a structured-result path or a fixture explicitly marked de-identified. It calls the shipped fill helper, reopens the output as DOCX, verifies mapped W1 summary fields, and writes only a sanitized JSON report under `eval-results/acceptance/w1/`. Temporary filled DOCX output is not committed.

```powershell
python scripts/run_w1_template_acceptance.py `
  --template "docs/4.心理咨询初始访谈表_20210906.docx" `
  --structured-result eval-data/w1-summary-template-acceptance.json `
  --report eval-results/acceptance/w1/real-template.json
```

- [ ] **Step 4: Verify green and commit implementation**

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_run_w1_template_acceptance scripts.test_fill_docx_template -v
git add scripts/run_w1_template_acceptance.py scripts/test_run_w1_template_acceptance.py
git commit -m "Add W1 real-template acceptance runner"
```

- [ ] **Step 5: Run the real template and commit only the sanitized passing report**

Validate the report with `validate_template_report` before committing it. If assertions fail, keep the matrix unverified and fix the product path through TDD.

### Task 3: Hosted W1 full-workflow evidence

**Files:**
- Modify: `scripts/hosted_smoke.py`
- Modify: `scripts/test_hosted_smoke.py`

- [ ] **Step 1: Write failing hosted-report tests**

Tests cover W1 mode, real-run status, structured PASS, artifact metadata, URL/timestamp/version, sanitization, two-mode aggregation, and a failure when only route metadata passes.

- [ ] **Step 2: Verify red**

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_hosted_smoke -v
```

- [ ] **Step 3: Add optional report output**

Add an explicit W1 acceptance/report mode to the current smoke tool. Preserve existing CLI behavior. Reports contain assertions and sanitized summaries, never credentials, cookies, raw private material, or server paths.

- [ ] **Step 4: Verify green and commit**

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_hosted_smoke -v
git add scripts/hosted_smoke.py scripts/test_hosted_smoke.py
git commit -m "Record full hosted W1 acceptance evidence"
```

- [ ] **Step 5: Execute both hosted modes**

Use environment credentials and current public URL. Run a de-identified Chinese prep scenario and a de-identified Chinese fixed-summary scenario with real model calls. Commit the aggregated report only if both pass.

### Task 4: Browser-level Chinese product acceptance

**Files:**
- Create on success: `eval-results/acceptance/w1/web-browser.json`
- Product fixes, only if exposed: `web-workbench/app.js`, `web-workbench/index.html`, `scripts/web_workbench.py`, and matching tests.

- [ ] **Step 1: Start the local Web product with configured real model access**

Run on localhost with an isolated temporary data root. Keep all user-facing UI Chinese.

- [ ] **Step 2: Exercise W1 preparation through visible UI**

Use the in-app browser to sign in, submit a Chinese de-identified partial-clue request, assert the visible W1 preparation label and structured result, and verify the DOCX download affordance.

- [ ] **Step 3: Exercise W1 fixed summary through visible UI**

Submit Chinese completed intake notes, assert visible W1 fixed-summary mode, structured sections, and DOCX download affordance.

- [ ] **Step 4: Fix only acceptance-exposed defects with TDD**

For each defect, first add a failing backend/frontend contract test, observe red, make the smallest product change, then rerun the browser scenario. Product text remains Chinese; code/test identifiers may remain English.

- [ ] **Step 5: Write the sanitized browser report**

Record both modes, visible Chinese labels, structured assertions, artifact/download assertions, timestamp, local base URL, and commit. Validate it with `validate_web_report`.

### Task 5: Matrix, documentation, and Notion closure

**Files:**
- Modify: `workflow-completion.json`
- Modify: `docs/product-loop-state.md` through generator
- Modify: `docs/w1-acceptance-agent-work.md`

- [ ] **Step 1: Add three passing W1 gate evidence entries only after reports pass**

Reference the committed browser, hosted, and real-template reports using path evidence. Remove obsolete unverified notes. Never add `completed`.

- [ ] **Step 2: Regenerate and verify**

```powershell
python scripts/workflow_completion.py --write
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_workflow_completion scripts.test_w1_acceptance scripts.test_run_w1_template_acceptance scripts.test_hosted_smoke -v
python scripts/workflow_completion.py --check
git diff --check
```

Expected: W1 derives `已完成`; W2-W6 remain unchanged.

- [ ] **Step 3: Run broader W1 regression**

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_run_agent scripts.test_render_docx scripts.test_fill_docx_template scripts.test_web_workbench -v
```

- [ ] **Step 4: Update Notion**

Mark W1 Web, hosted, and real-template gates complete only after fresh report and matrix verification. Update W1's remaining-goal row; do not change W2-W6 checkboxes.

- [ ] **Step 5: Final review and commit**

Run independent spec and quality reviews, then commit the evidence/matrix/documentation closure.
