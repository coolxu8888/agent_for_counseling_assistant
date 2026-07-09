# W3 Completion Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete W3 by adding durable evidence for Web integration, hosted verification, and real-template verification while keeping workflow completion derived from evidence.

**Architecture:** Reuse the W2 acceptance pattern with a W3-specific contract for counseling records. W3 evidence must prove visible Chinese product output, structured PASS, editable DOCX artifact, real hosted model execution, and a real SOAP/DAP/BIRP DOCX template fill-and-reopen check.

**Tech Stack:** Python unittest, existing `scripts/web_workbench.py`, `scripts/hosted_smoke.py`, `scripts/fill_docx_template.py`, frontend DOM contract tests, DOCX zip/XML inspection.

## Global Constraints

- Product-facing text and browser assertions must be Chinese.
- W3 completion is derived, never manually asserted.
- The ordinary workflow validator must not contact hosted URLs or external services.
- Hosted verification remains an explicit command whose successful result is recorded as evidence.
- Do not mark W3 complete unless local tests, real model eval, Web integration, hosted verification, and real-template verification are all passed.
- Do not modify W1 or W2 completed evidence except to preserve it; W4-W6 must remain incomplete.
- Do not commit credentials, cookies, raw private material, temporary filled client documents, direct server filesystem paths, or private absolute paths in acceptance reports.

---

### Task 1: W3 Acceptance Contract

**Files:**
- Create: `scripts/w3_acceptance.py`
- Create: `scripts/test_w3_acceptance.py`

**Interfaces:**
- Produces: `validate_web_report(report: dict) -> None`
- Produces: `validate_hosted_report(report: dict) -> None`
- Produces: `validate_template_report(report: dict, repo_root: Path) -> None`
- Produces: `write_sanitized_report(path: Path, report: dict) -> None`

- [ ] Write failing tests covering valid W3 Web, hosted, and template reports.
- [ ] Write failing tests rejecting W1/W2 workflow values, English-only visible labels, missing counseling-record sections, missing risk-change fields, missing DOCX artifact, missing real-model hosted metadata, secrets/cookies, direct server paths, non-public hosted URLs, and invalid template hashes.
- [ ] Implement the minimal W3 acceptance module, reusing safe patterns from `scripts/w2_acceptance.py` without weakening W1 or W2.
- [ ] Run: `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_w3_acceptance -q`
- [ ] Commit: `Add W3 acceptance report contract`

### Task 2: W3 Real Template Acceptance

**Files:**
- Create: `scripts/run_w3_template_acceptance.py`
- Create: `scripts/test_run_w3_template_acceptance.py`
- Create: `eval-data/w3-session-note-template-acceptance.json`
- Create or reuse: `docs/w3-soap-session-note-template.docx`
- Create after real run: `eval-results/acceptance/w3/real-template.json`
- Modify if needed: `scripts/fill_docx_template.py`
- Modify if needed: `scripts/test_fill_docx_template.py`

**Interfaces:**
- Consumes: `w3_acceptance.validate_template_report`
- Produces: sanitized template report at `eval-results/acceptance/w3/real-template.json`

- [ ] Write failing tests for exact W3 real-template runner behavior.
- [ ] Create or select a real DOCX SOAP/DAP/BIRP counseling-record template in the repository.
- [ ] Create a de-identified W3 structured fixture with record format, session sections, risk change, next-session focus, and boundary notes.
- [ ] Implement the runner: fill the DOCX, reopen it, verify canonical W3 content appears, validate the sanitized report.
- [ ] If filler mapping misses canonical W3 labels, add explicit mappings with failing tests first.
- [ ] Run the real template acceptance command and write `eval-results/acceptance/w3/real-template.json`.
- [ ] Run: `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_run_w3_template_acceptance scripts.test_fill_docx_template -q`
- [ ] Commit: `Add W3 real-template acceptance evidence`

### Task 3: W3 Browser Acceptance

**Files:**
- Modify as needed: `scripts/test_web_workbench.py`
- Modify as needed: `scripts/test_web_workbench_frontend.mjs`
- Modify as needed: `web-workbench/app.js`
- Modify as needed: `web-workbench/index.html`
- Create after browser/local Web evidence: `eval-results/acceptance/w3/web-browser.json`

**Interfaces:**
- Consumes: `w3_acceptance.validate_web_report`
- Produces: sanitized browser report at `eval-results/acceptance/w3/web-browser.json`

- [ ] Write/extend automated tests proving visible Chinese W3 counseling-record label and visible editable Word action.
- [ ] Run local Web workbench in Chinese with a W3 counseling-record prompt.
- [ ] Verify visible W3 result, structured PASS, risk-change/next-focus fields, and downloadable editable DOCX link.
- [ ] If a product defect appears, write the failing automated contract test before fixing it.
- [ ] Write and validate `eval-results/acceptance/w3/web-browser.json`.
- [ ] Run: `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_web_workbench scripts.test_w3_acceptance -q`
- [ ] Run: `node scripts/test_web_workbench_frontend.mjs`
- [ ] Commit: `Record W3 Chinese browser acceptance`

### Task 4: W3 Hosted Acceptance

**Files:**
- Modify: `scripts/hosted_smoke.py`
- Modify: `scripts/test_hosted_smoke.py`
- Create after real hosted run: `eval-results/acceptance/w3/hosted.json`

**Interfaces:**
- Consumes: `w3_acceptance.validate_hosted_report`
- Produces: CLI flag `--w3-acceptance`

- [ ] Write failing tests for `--w3-acceptance` and `run_w3_acceptance`.
- [ ] Implement W3 hosted scenario using a de-identified counseling-record prompt that requests SOAP/DAP/BIRP structure.
- [ ] Require detected W3, real model metadata, structured PASS, HTTP 200, risk-change fields, next-session focus, and DOCX PASS.
- [ ] Run hosted W3 against `https://counselor-agent-coze-api.onrender.com` after the branch is deployed.
- [ ] Write `eval-results/acceptance/w3/hosted.json`.
- [ ] Run: `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_hosted_smoke scripts.test_w3_acceptance -q`
- [ ] Commit: `Record hosted W3 acceptance evidence`

### Task 5: W3 Matrix Closure

**Files:**
- Modify: `workflow-completion.json`
- Modify generated section: `docs/product-loop-state.md`
- Modify: `docs/w3-acceptance-agent-work.md`

**Interfaces:**
- Consumes: three validated W3 reports.
- Produces: W3 complete derived by `scripts/workflow_completion.py --check`.

- [ ] Validate all three W3 reports using `scripts.test_w3_acceptance`.
- [ ] Update only W3 Web, hosted, and real-template gates to passed with report paths.
- [ ] Run `python scripts/workflow_completion.py --write`.
- [ ] Verify W3 is complete, W1 and W2 remain complete, W4-W6 remain incomplete.
- [ ] Sync the Notion overview page: W3 becomes ✅ 完成; W1 and W2 remain ✅ 完成; W4-W6 stay incomplete.
- [ ] Run final verification commands and commit: `Complete W3 acceptance matrix`.
