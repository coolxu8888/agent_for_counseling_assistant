# W5 Completion Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete W5 by adding durable evidence for real-model evaluation, Web integration, hosted verification, and real-template verification while keeping workflow completion derived from evidence.

**Architecture:** Follow the W4 evidence pattern with a W5-specific acceptance contract for bounded next-session planning. Evidence must prove a real model result, visible Chinese product output, hosted real-model execution, editable DOCX export, and real DOCX template fill-and-reopen verification.

**Tech Stack:** Python unittest, local Web workbench JavaScript DOM contract, DeepSeek model eval runner, hosted smoke CLI, DOCX package inspection.

## Global Constraints

- Product-facing UI and browser assertions stay Chinese.
- W5 completion is derived, never manually asserted.
- The ordinary workflow validator must not contact hosted URLs or external services.
- Hosted verification remains an explicit command whose successful result is recorded as evidence.
- Do not mark W5 complete unless local tests, real-model eval, Web integration, hosted verification, and real-template verification are all passed.
- W1-W4 must remain complete; W6 must remain incomplete.
- Do not commit credentials, cookies, raw private material, temporary filled client documents, direct server filesystem paths, or private absolute paths in acceptance reports.

---

### Task 1: W5 Acceptance Contract

**Files:**
- Create: `scripts/w5_acceptance.py`
- Create: `scripts/test_w5_acceptance.py`

**Interfaces:**
- Produces: `W5_REQUIRED_FIELDS`, `W5_VISIBLE_LABEL`, `W5_TEMPLATE_PATH`
- Produces: `validate_model_eval_report(report: dict, repo_root: Path) -> None`
- Produces: `validate_web_report(report: dict) -> None`
- Produces: `validate_hosted_report(report: dict) -> None`
- Produces: `validate_template_report(report: dict, repo_root: Path) -> None`
- Produces: `write_sanitized_report(path: Path, report: dict) -> None`

- [ ] Write failing tests for valid W5 real-model, Web, hosted, and template reports.
- [ ] Write failing tests rejecting W1-W4/W6 workflow values, English-only visible labels, unsupported frameworks, missing next-session plan fields, missing single-session boundaries, missing DOCX artifact, missing hosted real-model metadata, secrets/cookies, server paths, non-public hosted URLs, and invalid template hashes.
- [ ] Implement the minimal W5 acceptance module, reusing safe patterns from W4 without weakening W1-W4.
- [ ] Run: `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_w5_acceptance -q`
- [ ] Commit: `Add W5 acceptance report contract`

### Task 2: W5 Real Model Evaluation

**Files:**
- Create after run: `eval-results/acceptance/w5/real-model.json`
- Use generated W5 eval outputs under `eval-results/w5-api/`

**Interfaces:**
- Consumes: `w5_acceptance.validate_model_eval_report`
- Produces: sanitized model-eval report at `eval-results/acceptance/w5/real-model.json`

- [ ] Run a real model eval for W5 cases, preferring `W5-001,W5-006,W5-007,W5-008` if available.
- [ ] Keep generated meta files out of git if they contain API-key telemetry.
- [ ] Build sanitized W5 real-model report with W5 fields: selected framework, session goal, focus areas, planned interventions, suggested questions, risk monitoring, between-session tasks, do-not-do, and boundary notes.
- [ ] Validate with `scripts.test_w5_acceptance`.
- [ ] Commit: `Add W5 real-model acceptance evidence`

### Task 3: W5 Real Template

**Files:**
- Create: `scripts/run_w5_template_acceptance.py`
- Create: `scripts/test_run_w5_template_acceptance.py`
- Create: `eval-data/w5-next-session-template-acceptance.json`
- Create: `docs/w5-next-session-plan-template.docx`
- Create after real run: `eval-results/acceptance/w5/real-template.json`
- Modify: `scripts/fill_docx_template.py` only if W5 canonical labels are not mapped

**Interfaces:**
- Consumes: `w5_acceptance.validate_template_report`
- Produces: sanitized template report at `eval-results/acceptance/w5/real-template.json`

- [ ] Write failing tests for the W5 real-template runner.
- [ ] Create a de-identified W5 structured fixture with every canonical W5 field.
- [ ] Create the real W5 DOCX template fixture with visible counselor-facing field labels.
- [ ] Implement the runner: fill the DOCX, reopen it, verify canonical W5 content appears, validate the sanitized report.
- [ ] If filler mapping misses canonical W5 labels, add explicit mappings with failing tests first.
- [ ] Run the real template acceptance command and write `eval-results/acceptance/w5/real-template.json`.
- [ ] Commit: `Add W5 real-template acceptance evidence`

### Task 4: W5 Browser Acceptance

**Files:**
- Modify: `scripts/test_web_workbench_frontend.mjs`
- Create: `eval-results/acceptance/w5/web-browser.json`

**Interfaces:**
- Consumes: `w5_acceptance.validate_web_report`
- Produces: sanitized browser report at `eval-results/acceptance/w5/web-browser.json`

- [ ] Extend frontend DOM contract for W5 visible Chinese label `下次会谈计划`.
- [ ] Assert W5 Word output renders in the visible download action area.
- [ ] Write and validate `eval-results/acceptance/w5/web-browser.json`.
- [ ] Run: `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_web_workbench scripts.test_w5_acceptance -q`
- [ ] Run: `node scripts/test_web_workbench_frontend.mjs`
- [ ] Commit: `Record W5 Chinese browser acceptance`

### Task 5: W5 Hosted Evidence

**Files:**
- Modify: `scripts/hosted_smoke.py`
- Modify: `scripts/test_hosted_smoke.py`
- Create: `eval-results/acceptance/w5/hosted.json`

**Interfaces:**
- Consumes: `w5_acceptance.validate_hosted_report`
- Produces: CLI flag `--w5-acceptance`

- [ ] Write failing tests for `--w5-acceptance` and `run_w5_acceptance`.
- [ ] Implement W5 hosted scenario using a de-identified single-session next-session planning prompt.
- [ ] Require detected W5, real model metadata, structured PASS, HTTP 200, W5 fields, and DOCX PASS.
- [ ] Run hosted W5 against `https://counselor-agent-coze-api.onrender.com`.
- [ ] Write `eval-results/acceptance/w5/hosted.json`.
- [ ] Commit: `Record hosted W5 acceptance evidence`

### Task 6: W5 Matrix Closure

**Files:**
- Modify: `workflow-completion.json`
- Modify generated section of `docs/product-loop-state.md`
- Modify: `docs/w5-acceptance-agent-work.md`

**Interfaces:**
- Consumes: four validated W5 reports.
- Produces: W5 complete derived by `scripts/workflow_completion.py --check`.

- [ ] Validate all W5 reports using `scripts.test_w5_acceptance`.
- [ ] Update only W5's four remaining gates to passed with report paths.
- [ ] Run `python scripts/workflow_completion.py --write`.
- [ ] Verify W5 is complete, W1-W4 remain complete, W6 remains incomplete.
- [ ] Sync Notion overview: W5 becomes ✅ 完成; W1-W4 remain ✅ 完成; W6 stays incomplete.
- [ ] Run final verification commands and commit: `Complete W5 acceptance matrix`.
