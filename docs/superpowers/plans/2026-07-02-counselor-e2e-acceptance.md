# Counselor End-to-End Acceptance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate the product through one realistic counselor workflow from sign-in to a reviewable, exportable case artifact, fixing only blockers found on that path.

**Architecture:** Treat the shipped web workbench as the system under test and exercise it through its visible UI against the real model-backed runtime. Use existing unit tests and hosted smoke checks as supporting evidence, but make counselor-visible completion—not additional routing fixtures—the acceptance gate.

**Tech Stack:** Python standard-library web server, vanilla JavaScript workbench, DeepSeek API, DOCX/template tooling, in-app browser automation.

---

### Task 1: Establish the acceptance baseline

**Files:**
- Inspect: `scripts/web_workbench.py`
- Inspect: `web-workbench/index.html`
- Inspect: `web-workbench/app.js`
- Test: `scripts/test_web_workbench.py`

- [ ] **Step 1: Run the current workbench regression suite**

Run: `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_web_workbench -v`

Expected: all tests pass before UI acceptance begins.

- [ ] **Step 2: Start the local workbench with real model configuration**

Run: `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-web-workbench.ps1`

Expected: `GET http://127.0.0.1:8765/health` returns a healthy response.

### Task 2: Execute a realistic counselor journey

**Files:**
- Verify: `web-workbench/index.html`
- Verify: `web-workbench/app.js`
- Runtime artifacts: `agent-runs/`
- Runtime artifacts: `workbench-data/`

- [ ] **Step 1: Sign in through the visible login form**

Use the configured local validation account and verify that the workspace, privacy boundary, demo catalog, and case controls become available.

- [ ] **Step 2: Create or select a de-identified case**

Use only synthetic, de-identified counselor notes. Confirm the selected case remains visible throughout the journey.

- [ ] **Step 3: Load one representative session-record scenario and run it**

Use a realistic W3 counselor note with presenting issue, intervention, client response, risk status, and next step. Expected: a real model response, structured output, validation status, route summary, and run-history entry appear without a page error.

- [ ] **Step 4: Generate the counselor-facing artifact**

Generate the fixed DOCX output from the structured result. Expected: the UI shows a downloadable artifact tied to the selected case and run.

- [ ] **Step 5: Export the case bundle**

Export the selected case. Expected: a ZIP download contains case notes/metadata, recent run data, and generated outputs without exposing API credentials.

### Task 3: Fix only journey blockers

**Files:**
- Modify if required: `scripts/web_workbench.py`
- Modify if required: `web-workbench/app.js`
- Modify if required: `web-workbench/index.html`
- Test if required: `scripts/test_web_workbench.py`

- [ ] **Step 1: Capture the first counselor-visible blocker as a failing test**

Run: `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_web_workbench.WebWorkbenchTest.<new_regression_test> -v`

Expected: FAIL for the exact blocker reproduced in Task 2.

- [ ] **Step 2: Implement the smallest correction**

Change only the code needed to restore the acceptance journey; do not add new intent-routing boundary cases.

- [ ] **Step 3: Verify the correction**

Run: `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_web_workbench -v`

Expected: all workbench tests pass, followed by a successful repeat of Task 2.

### Task 4: Record the product decision and evidence

**Files:**
- Modify: `docs/product-loop-state.md`

- [ ] **Step 1: Replace the next-capability recommendation**

Record counselor end-to-end acceptance as the active P0 and explicitly freeze additional routing-boundary expansion unless a route defect blocks the acceptance journey.

- [ ] **Step 2: Record evidence and remaining pilot blockers**

Include the exact journey tested, pass/fail status, generated artifact evidence, and operational blockers such as default credentials, retention, or ephemeral storage.
