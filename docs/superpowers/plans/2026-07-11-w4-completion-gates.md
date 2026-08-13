# W4 Completion Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete W4 by adding durable evidence for real-model evaluation, Web integration, hosted verification, and real-template verification while keeping workflow completion derived from evidence.

**Architecture:** Follow the W3 evidence pattern with a W4-specific contract for framework-based case conceptualization. Evidence must prove a real model result, visible Chinese product output, hosted real-model execution, editable DOCX export, and real DOCX template fill-and-reopen verification.

**Tech Stack:** Python unittest, existing `scripts/run_agent.py`, `scripts/web_workbench.py`, `scripts/hosted_smoke.py`, `scripts/fill_docx_template.py`, frontend DOM contract tests, DOCX zip/XML inspection, committed evaluation artifacts.

## Global Constraints

- Product-facing text and browser assertions must be Chinese.
- W4 completion is derived, never manually asserted.
- The ordinary workflow validator must not contact hosted URLs or external services.
- Hosted verification remains an explicit command whose successful result is recorded as evidence.
- Do not mark W4 complete unless local tests, real model eval, Web integration, hosted verification, and real-template verification are all passed.
- W1-W3 must remain complete; W5-W6 must remain incomplete.
- Do not commit credentials, cookies, raw private material, temporary filled client documents, direct server filesystem paths, or private absolute paths in acceptance reports.

---

### Task 1: W4 Acceptance Contract

**Files:**
- Create: `scripts/w4_acceptance.py`
- Create: `scripts/test_w4_acceptance.py`

**Interfaces:**
- Produces: `validate_model_eval_report(report: dict, repo_root: Path) -> None`
- Produces: `validate_web_report(report: dict) -> None`
- Produces: `validate_hosted_report(report: dict) -> None`
- Produces: `validate_template_report(report: dict, repo_root: Path) -> None`
- Produces: `write_sanitized_report(path: Path, report: dict) -> None`

- [ ] Write failing tests for valid W4 model-eval, Web, hosted, and template reports.
- [ ] Reject W1-W3 workflow values, English-only visible labels, unsupported frameworks, missing conceptualization factors, missing risk/hypothesis fields, missing DOCX artifact, missing hosted real-model metadata, secrets/cookies, server paths, non-public hosted URLs, and invalid template hashes.
- [ ] Implement the minimal W4 acceptance module, reusing safe patterns from W3 without weakening W1-W3.
- [ ] Run: `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_w4_acceptance -q`
- [ ] Commit: `Add W4 acceptance report contract`

### Task 2: W4 Real Model Evaluation Evidence

**Files:**
- Create after run: `eval-results/acceptance/w4/real-model.json`
- Reuse: `eval-results/eval-rubric-summary.v0.1.json`
- Reuse or extend if needed: `eval-results/eval-clean-summary.v0.1.json`

**Interfaces:**
- Consumes: `w4_acceptance.validate_model_eval_report`
- Produces: sanitized model-eval report at `eval-results/acceptance/w4/real-model.json`

- [ ] Confirm committed W4 evaluation cases exist and validate their rubric/clean summaries.
- [ ] If W4 raw/clean evidence is missing, run real W4 evals explicitly.
- [ ] Write a sanitized report referencing committed W4 eval artifacts and rubric PASS decisions.
- [ ] Validate with `scripts.test_w4_acceptance`.
- [ ] Commit: `Add W4 real-model acceptance evidence`

### Task 3: W4 Real Template Acceptance

**Files:**
- Create: `scripts/run_w4_template_acceptance.py`
- Create: `scripts/test_run_w4_template_acceptance.py`
- Create: `eval-data/w4-conceptualization-template-acceptance.json`
- Create or reuse: `docs/w4-case-conceptualization-template.docx`
- Create after real run: `eval-results/acceptance/w4/real-template.json`
- Modify if needed: `scripts/fill_docx_template.py`
- Modify if needed: `scripts/test_fill_docx_template.py`

**Interfaces:**
- Consumes: `w4_acceptance.validate_template_report`
- Produces: sanitized template report at `eval-results/acceptance/w4/real-template.json`

- [ ] Write failing tests for exact W4 real-template runner behavior.
- [ ] Create or select a real DOCX case-conceptualization template in the repository.
- [ ] Create a de-identified W4 structured fixture with framework, facts, patterns, factors, risk, hypotheses, questions, and boundaries.
- [ ] Implement the runner: fill the DOCX, reopen it, verify canonical W4 content appears, validate the sanitized report.
- [ ] Add narrow W4 filler mappings with failing tests first if existing mappings miss canonical labels.
- [ ] Run the real template acceptance command and write `eval-results/acceptance/w4/real-template.json`.
- [ ] Commit: `Add W4 real-template acceptance evidence`

### Task 4: W4 Browser Acceptance

**Files:**
- Modify as needed: `scripts/test_web_workbench.py`
- Modify as needed: `scripts/test_web_workbench_frontend.mjs`
- Modify as needed: `web-workbench/app.js`
- Create after browser/local Web evidence: `eval-results/acceptance/w4/web-browser.json`

**Interfaces:**
- Consumes: `w4_acceptance.validate_web_report`
- Produces: sanitized browser report at `eval-results/acceptance/w4/web-browser.json`

- [ ] Extend frontend/API tests proving visible Chinese W4 concept-label and editable Word action.
- [ ] Verify visible W4 result, structured PASS, conceptualization fields, and downloadable editable DOCX link.
- [ ] Write and validate `eval-results/acceptance/w4/web-browser.json`.
- [ ] Run Web and frontend regression commands.
- [ ] Commit: `Record W4 Chinese browser acceptance`

### Task 5: W4 Hosted Acceptance

**Files:**
- Modify: `scripts/hosted_smoke.py`
- Modify: `scripts/test_hosted_smoke.py`
- Create after real hosted run: `eval-results/acceptance/w4/hosted.json`

**Interfaces:**
- Consumes: `w4_acceptance.validate_hosted_report`
- Produces: CLI flag `--w4-acceptance`

- [ ] Write failing tests for `--w4-acceptance` and `run_w4_acceptance`.
- [ ] Implement W4 hosted scenario using a de-identified CBT conceptualization prompt.
- [ ] Require detected W4, real model metadata, structured PASS, conceptualization factors, risk considerations, working hypotheses, questions, and DOCX PASS.
- [ ] Run hosted W4 against `https://counselor-agent-coze-api.onrender.com` after the branch is deployed.
- [ ] Write `eval-results/acceptance/w4/hosted.json`.
- [ ] Commit: `Record hosted W4 acceptance evidence`

### Task 6: W4 Matrix Closure

**Files:**
- Modify: `workflow-completion.json`
- Modify generated section: `docs/product-loop-state.md`
- Modify: `docs/w4-acceptance-agent-work.md`

**Interfaces:**
- Consumes: four validated W4 reports.
- Produces: W4 complete derived by `scripts/workflow_completion.py --check`.

- [ ] Validate all W4 reports using `scripts.test_w4_acceptance`.
- [ ] Update only W4 real-model, Web, hosted, and real-template gates to passed with report paths.
- [ ] Run `python scripts/workflow_completion.py --write`.
- [ ] Verify W4 is complete, W1-W3 remain complete, W5-W6 remain incomplete.
- [ ] Sync Notion overview: W4 becomes ✅ 完成; W1-W3 remain ✅ 完成; W5-W6 stay incomplete.
- [ ] Run final verification commands and commit: `Complete W4 acceptance matrix`.
