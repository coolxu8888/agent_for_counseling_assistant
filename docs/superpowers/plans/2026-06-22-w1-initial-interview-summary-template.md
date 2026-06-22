# W1 Initial Interview Summary Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Productize the W1 initial interview summary path so completed intake notes can be structured into the fixed summary template with explicit known facts, missing information, and follow-up questions.

**Architecture:** Reuse the existing W1 auto-routing and structured runner path instead of creating a new workflow. Add a shared W1 mode detector, switch the structured W1 prompt/metadata between intake-prep and intake-summary modes, surface that mode through the web API, and back it with regression tests plus a real DeepSeek eval fixture.

**Tech Stack:** Python runner and HTTP workbench, JSON structured contracts, DeepSeek API eval runner, unittest.

---

### Task 1: Lock the failing W1 mode tests

**Files:**
- Modify: `scripts/test_run_agent.py`
- Modify: `scripts/test_web_workbench.py`

- [ ] **Step 1: Keep the failing runner-mode tests**

```python
def test_detect_w1_mode_distinguishes_prep_vs_summary_requests(self):
    ...

def test_build_prompt_package_w1_summary_includes_section_specific_missing_field_guidance(self):
    ...
```

- [ ] **Step 2: Keep the failing workbench-mode tests**

```python
def test_detect_workflow_details_marks_mixed_signal_when_initial_interview_summary_mentions_notes(self):
    ...

def test_handle_run_returns_w1_summary_mode_metadata(self):
    ...
```

- [ ] **Step 3: Run the targeted tests and confirm RED**

Run: `python -m unittest scripts.test_run_agent.RunAgentTest.test_detect_w1_mode_distinguishes_prep_vs_summary_requests scripts.test_web_workbench.WebWorkbenchTest.test_handle_run_returns_w1_summary_mode_metadata`

Expected: import or key errors around missing `detect_w1_mode` / `w1_mode`.

### Task 2: Implement runner-side W1 summary mode

**Files:**
- Modify: `scripts/run_agent.py`
- Test: `scripts/test_run_agent.py`

- [ ] **Step 1: Add a shared W1 mode detector**

```python
def detect_w1_mode(user_input):
    ...
```

- [ ] **Step 2: Switch the W1 structured contract/prompt by mode**

```python
if workflow.workflow_id == "W1" and structured:
    w1_mode = detect_w1_mode(user_input)
```

- [ ] **Step 3: Persist `w1_mode` into run metadata**

```python
metadata["w1_mode"] = w1_mode
```

- [ ] **Step 4: Run runner tests and confirm GREEN**

Run: `python -m unittest scripts.test_run_agent`

Expected: W1 mode and structured validation tests pass.

### Task 3: Surface W1 mode through product routing

**Files:**
- Modify: `scripts/web_workbench.py`
- Test: `scripts/test_web_workbench.py`

- [ ] **Step 1: Reuse the shared W1 detector in auto-routing details**

```python
details["w1_mode"] = detect_w1_mode(user_input)
```

- [ ] **Step 2: Return `w1_mode` in `/api/run` responses**

```python
response_payload["w1_mode"] = ...
```

- [ ] **Step 3: Run workbench tests and confirm GREEN**

Run: `python -m unittest scripts.test_web_workbench`

Expected: W1 routing and response metadata tests pass.

### Task 4: Add eval coverage and document the loop state

**Files:**
- Modify or create: `eval-prompts/*` for one W1 summary fixture
- Modify or create: `scripts/*eval*` tests if needed
- Modify: `docs/product-loop-state.md`

- [ ] **Step 1: Add one DeepSeek-backed W1 summary eval fixture**

```text
W1-005: completed initial interview notes -> fixed summary template
```

- [ ] **Step 2: Run the targeted test suite, full suite, and live eval**

Run: `python -m unittest ...`
Run: `python scripts/run_model_eval.py --ids W1-005`

- [ ] **Step 3: Update loop state and commit**

```bash
git add ...
git commit -m "Productize W1 initial interview summary mode"
```
