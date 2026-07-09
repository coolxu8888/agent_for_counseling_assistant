# W2 Completion Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete W2 by adding durable evidence for Web integration, hosted verification, and real-template verification while keeping completion derived from evidence.

**Architecture:** Reuse the W1 acceptance pattern, but define a W2-specific single-scenario contract for BPS case background output. Each evidence runner writes sanitized JSON under `eval-results/acceptance/w2/`, and the final matrix update points only to those validated reports.

**Tech Stack:** Python unittest, existing `scripts/run_agent.py`, `scripts/web_workbench.py`, `scripts/hosted_smoke.py`, `scripts/fill_docx_template.py`, browser/frontend DOM tests, DOCX zip/XML inspection.

## Global Constraints

- Product-facing text and browser assertions must be Chinese.
- W2 completion is derived, never manually asserted.
- The ordinary workflow validator must not contact hosted URLs or external services.
- Hosted verification remains an explicit command whose successful result is recorded as evidence.
- Do not mark W2 complete unless local tests, real model eval, Web integration, hosted verification, and real-template verification are all passed.
- Do not modify W1 evidence or W3-W6 gate status except to preserve them.
- Do not commit credentials, cookies, raw private material, temporary filled client documents, direct server filesystem paths, or private absolute paths in acceptance reports.

---

### Task 1: W2 Acceptance Contract

**Files:**
- Create: `scripts/w2_acceptance.py`
- Create: `scripts/test_w2_acceptance.py`

**Interfaces:**
- Produces: `validate_web_report(report: dict) -> None`
- Produces: `validate_hosted_report(report: dict) -> None`
- Produces: `validate_template_report(report: dict, repo_root: Path) -> None`
- Produces: `write_sanitized_report(path: Path, report: dict) -> None`

- [ ] Write failing tests covering valid W2 Web, hosted, and template reports.
- [ ] Write failing tests rejecting W1/W3 workflow values, English-only visible labels, missing BPS fields, missing DOCX artifacts, missing real-model hosted metadata, secrets/cookies, direct server paths, non-public hosted URLs, and invalid template hashes.
- [ ] Implement the minimal W2 acceptance module, reusing safe patterns from `scripts/w1_acceptance.py` without weakening W1.
- [ ] Run: `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_w2_acceptance -q`
- [ ] Commit: `Add W2 acceptance report contract`

### Task 2: W2 Real Template Acceptance

**Files:**
- Create: `scripts/run_w2_template_acceptance.py`
- Create: `scripts/test_run_w2_template_acceptance.py`
- Create: `eval-data/w2-bps-template-acceptance.json`
- Create or reuse: `docs/w2-bps-case-background-template.docx`
- Create after real run: `eval-results/acceptance/w2/real-template.json`
- Modify if needed: `scripts/fill_docx_template.py`
- Modify if needed: `scripts/test_fill_docx_template.py`

**Interfaces:**
- Consumes: `w2_acceptance.validate_template_report`
- Produces: sanitized template report at `eval-results/acceptance/w2/real-template.json`

- [ ] Write failing tests for exact W2 real-template runner behavior.
- [ ] Create or select a real DOCX BPS case-background template in the repository.
- [ ] Create a de-identified W2 structured fixture with presenting concerns, case overview, BPS dimensions, protective factors, risk formulation, recommended focus, and boundary notes.
- [ ] Implement the runner: fill the DOCX, reopen it, verify canonical W2 content appears, validate the sanitized report.
- [ ] If filler mapping misses canonical W2 labels, add explicit mappings with failing tests first.
- [ ] Run the real template acceptance command and write `eval-results/acceptance/w2/real-template.json`.
- [ ] Run: `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_run_w2_template_acceptance scripts.test_fill_docx_template -q`
- [ ] Commit: `Add W2 real-template acceptance evidence`

### Task 3: W2 Hosted Acceptance

**Files:**
- Modify: `scripts/hosted_smoke.py`
- Modify: `scripts/test_hosted_smoke.py`
- Create after real run: `eval-results/acceptance/w2/hosted.json`

**Interfaces:**
- Consumes: `w2_acceptance.validate_hosted_report`
- Produces: CLI flag `--w2-acceptance`

- [ ] Write failing tests for `--w2-acceptance` and `run_w2_acceptance`.
- [ ] Implement W2 hosted scenario using a de-identified BPS/supervision case-background prompt.
- [ ] Require detected W2, real model metadata, structured PASS, HTTP 200, and DOCX PASS.
- [ ] Run hosted W2 against `https://counselor-agent-coze-api.onrender.com` after the branch is deployed.
- [ ] Write `eval-results/acceptance/w2/hosted.json`.
- [ ] Run: `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_hosted_smoke scripts.test_w2_acceptance -q`
- [ ] Commit: `Record hosted W2 acceptance evidence`

### Task 4: W2 Browser Acceptance

**Files:**
- Modify as needed: `scripts/test_web_workbench.py`
- Modify as needed: `scripts/test_web_workbench_frontend.mjs`
- Modify as needed: `web-workbench/app.js`
- Modify as needed: `web-workbench/index.html`
- Create after browser run: `eval-results/acceptance/w2/web-browser.json`

**Interfaces:**
- Consumes: `w2_acceptance.validate_web_report`
- Produces: sanitized browser report at `eval-results/acceptance/w2/web-browser.json`

- [ ] Write/extend automated tests proving visible Chinese W2 label and visible editable Word action.
- [ ] Run local Web workbench in Chinese with a W2 BPS prompt.
- [ ] Verify visible W2/BPS result, structured PASS, and downloadable editable DOCX link.
- [ ] If a product defect appears, write the failing automated contract test before fixing it.
- [ ] Write and validate `eval-results/acceptance/w2/web-browser.json`.
- [ ] Run: `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_web_workbench scripts.test_w2_acceptance -q`
- [ ] Run: `node scripts/test_web_workbench_frontend.mjs`
- [ ] Commit: `Record W2 Chinese browser acceptance`

### Task 5: W2 Matrix Closure

**Files:**
- Modify: `workflow-completion.json`
- Modify generated section: `docs/product-loop-state.md`
- Modify: `docs/w2-acceptance-agent-work.md`

**Interfaces:**
- Consumes: three validated W2 reports.
- Produces: W2 complete derived by `scripts/workflow_completion.py --check`.

- [ ] Validate all three W2 reports using `scripts.test_w2_acceptance`.
- [ ] Update only W2 Web, hosted, and real-template gates to passed with report paths.
- [ ] Run `python scripts/workflow_completion.py --write`.
- [ ] Verify W2 is complete, W1 remains complete, W3-W6 remain unchanged.
- [ ] Sync the Notion overview page: W2 becomes ✅ 完成; W1 remains ✅ 完成; W3-W6 stay incomplete.
- [ ] Run final verification commands and commit: `Complete W2 acceptance matrix`.

