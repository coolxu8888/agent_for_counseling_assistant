# Intent Routing Bilingual Ambiguity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Strengthen AUTO intent recognition for mixed Chinese/English counselor prompts and expose concise route-explanation details that are usable in the product and eval outputs.

**Architecture:** Extend the existing regex-weight routing layer in `scripts/web_workbench.py` instead of adding a second classifier. Add bilingual ambiguity fixtures and route-explanation assertions first, then minimally expand routing rules and response formatting so the backend and UI both preserve route reasons and top-candidate summaries.

**Tech Stack:** Python `unittest`, PowerShell/Python runners, static web workbench assets.

---

### Task 1: Add failing bilingual-routing tests

**Files:**
- Modify: `scripts/test_web_workbench.py`
- Test: `scripts/test_web_workbench.py`

- [ ] **Step 1: Write the failing tests**

```python
    def test_detect_workflow_prefers_w1_for_bilingual_initial_interview_summary_prompt(self):
        details = web_workbench.detect_workflow_details(
            "请把 first interview notes 整理成固定初访总结模板，不要写成 session note。"
        )

        self.assertEqual(details["workflow"], "W1")
        self.assertEqual(details["w1_mode"], "initial_interview_summary")
        self.assertEqual(details["route_status"], "mixed_signals")

    def test_detect_workflow_prefers_w5_for_bilingual_single_session_plan_prompt(self):
        details = web_workbench.detect_workflow_details(
            "用 CBT 做下次咨询计划，只规划 next session，不要做多阶段 roadmap。"
        )

        self.assertEqual(details["workflow"], "W5")
        self.assertEqual(details["route_status"], "mixed_signals")
        self.assertEqual(details["top_candidates"][0]["workflow"], "W5")
        self.assertEqual(details["top_candidates"][1]["workflow"], "W6")

    def test_handle_run_returns_route_explanation_summary_for_auto_route(self):
        ...
        self.assertIn("routing_reasons_summary", payload)
        self.assertIn("W1", payload["routing_reasons_summary"])
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `python -m unittest scripts.test_web_workbench.WebWorkbenchTest.test_detect_workflow_prefers_w1_for_bilingual_initial_interview_summary_prompt scripts.test_web_workbench.WebWorkbenchTest.test_detect_workflow_prefers_w5_for_bilingual_single_session_plan_prompt scripts.test_web_workbench.WebWorkbenchTest.test_handle_run_returns_route_explanation_summary_for_auto_route`

Expected: FAIL because the bilingual phrases or the explanation field are not handled yet.

### Task 2: Implement minimal routing and explanation changes

**Files:**
- Modify: `scripts/web_workbench.py`
- Modify: `web-workbench/app.js`

- [ ] **Step 1: Expand bilingual routing cues and explanation helpers**

```python
ROUTING_RULES["W1"]["positive"].extend([
    (r"first interview notes", 4),
    (r"初访.*template|固定初访.*模板", 5),
])

ROUTING_RULES["W5"]["positive"].extend([
    (r"下次咨询计划", 5),
    (r"只规划.*next session|next session.*不要.*roadmap", 5),
])

def summarize_routing_reasons(top_candidates):
    ...
```

- [ ] **Step 2: Include the new explanation summary in API responses**

```python
response_payload["routing_reasons_summary"] = summarize_routing_reasons(
    route_details.get("top_candidates", [])
)
```

- [ ] **Step 3: Render the explanation summary in the existing intent summary card**

```javascript
const reasonsSummary = data && data.routing_reasons_summary;
if (reasonsSummary) {
  lines.push(`Why: ${reasonsSummary}`);
}
```

- [ ] **Step 4: Run the same targeted tests to verify they pass**

Run: `python -m unittest scripts.test_web_workbench.WebWorkbenchTest.test_detect_workflow_prefers_w1_for_bilingual_initial_interview_summary_prompt scripts.test_web_workbench.WebWorkbenchTest.test_detect_workflow_prefers_w5_for_bilingual_single_session_plan_prompt scripts.test_web_workbench.WebWorkbenchTest.test_handle_run_returns_route_explanation_summary_for_auto_route`

Expected: PASS

### Task 3: Extend eval fixtures and run capability verification

**Files:**
- Modify: `scripts/build_workflow_eval_prompts.py`
- Modify: `scripts/test_build_workflow_eval_prompts.py`
- Update: `eval-prompts/manifest.json` and generated prompt assets
- Modify: `docs/product-loop-state.md`

- [ ] **Step 1: Add one bilingual ambiguity eval case for intent routing**

```python
{
    "id": "W1-008",
    "query": "请把 first interview notes 整理成固定初访总结模板，不要写成 session note。",
    ...
}
```

- [ ] **Step 2: Add/update the eval-builder test**

```python
    def test_evals_include_bilingual_intent_routing_cases(self):
        ...
```

- [ ] **Step 3: Run the builder, targeted tests, and one real eval**

Run: `python -m unittest scripts.test_web_workbench scripts.test_build_workflow_eval_prompts`
Run: `python scripts/build_workflow_eval_prompts.py`
Run: `python scripts/run_model_eval.py --ids W1-008`

Expected: tests PASS, manifest regenerated, live eval returns a passing route-aligned response if DeepSeek credentials are configured.

- [ ] **Step 4: Update loop-state docs with capability, tests, gaps, and next step**

```markdown
## This Run: Intent Recognition Across Counselor Tasks
...
```

- [ ] **Step 5: Commit the coherent change**

```bash
git add scripts/web_workbench.py scripts/test_web_workbench.py scripts/build_workflow_eval_prompts.py scripts/test_build_workflow_eval_prompts.py web-workbench/app.js eval-prompts docs/product-loop-state.md docs/superpowers/plans/2026-06-23-intent-routing-bilingual-ambiguity.md
git commit -m "Improve bilingual intent routing explanations"
```
