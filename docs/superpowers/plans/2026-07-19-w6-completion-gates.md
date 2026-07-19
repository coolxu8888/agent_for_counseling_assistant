# W6 Completion Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete W6 counseling roadmap only when local tests, real-model evaluation, Web integration, hosted verification, and real-template verification all pass.

**Architecture:** Reuse the W5 acceptance pattern with W6-specific fields and validators. W6 remains a bounded, revisable multi-session roadmap, not a fixed treatment protocol or guaranteed outcome plan. Completion is derived from `workflow-completion.json` and `scripts/workflow_completion.py`.

**Tech Stack:** Python `unittest`, existing `scripts/run_agent.py`, `scripts/clean_eval_outputs.py`, `scripts/web_workbench.py`, `scripts/hosted_smoke.py`, `scripts/fill_docx_template.py`, DOCX zip/XML inspection, Node frontend DOM test.

## Global Constraints

- Product-facing UI text must remain Chinese.
- Workflow completion is derived, never manually asserted.
- Ordinary local validators must not contact hosted URLs; hosted verification remains an explicit command whose successful result is recorded as evidence.
- W6 completion requires all five gates passed: local tests, real-model evaluation, Web integration, hosted verification, real-template verification.
- Work only in `C:\Users\win\Documents\Codex\2026-05-15\agent\.worktrees\w6-completion`.

---

### Task A: W6 Acceptance Contract

**Files:**
- Create: `scripts/w6_acceptance.py`
- Create: `scripts/test_w6_acceptance.py`
- Modify: `docs/w6-acceptance-agent-work.md`

**Interfaces:**
- Produces: `validate_model_eval_report(report: dict, repo_root: Path) -> None`
- Produces: `validate_web_report(report: dict) -> None`
- Produces: `validate_hosted_report(report: dict) -> None`
- Produces: `validate_template_report(report: dict, repo_root: Path) -> None`
- Produces: `write_sanitized_report(path: Path, report: dict) -> None`
- W6 required fields: `selected_framework`, `overview`, `phases`, `hypotheses_to_verify`, `session_focus_options`, `risk_monitoring_checkpoints`, `collaboration_or_referral_reminders`, `missing_information`, `do_not_do`, `boundary_notes`

- [ ] **Step 1: Write failing validator tests**

Add `scripts/test_w6_acceptance.py` with valid reports and negative cases:

```python
def roadmap_fields():
    return {
        "selected_framework": "INTEGRATIVE",
        "overview": "Bounded, revisable roadmap for counselor planning.",
        "phases": ["Phase 1: engagement and assessment."],
        "hypotheses_to_verify": ["Criticism may activate shame and avoidance."],
        "session_focus_options": ["Next session: clarify the recent criticism trigger."],
        "risk_monitoring_checkpoints": ["Re-check ideation, self-harm, sleep, and supports at phase transitions."],
        "collaboration_or_referral_reminders": ["Consider referral only if new safety or medical concerns emerge."],
        "missing_information": ["Prior counseling response is not yet documented."],
        "do_not_do": ["Do not diagnose, promise outcomes, or prescribe a fixed protocol."],
        "boundary_notes": ["This is a revisable roadmap, not a diagnosis or rigid treatment plan."],
    }
```

- [ ] **Step 2: Verify RED**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_w6_acceptance -q
```

Expected: import failure for `w6_acceptance`.

- [ ] **Step 3: Implement W6 validator**

Mirror `scripts/w5_acceptance.py`, changing constants, field names, template path, visible label, and report messages.

- [ ] **Step 4: Verify GREEN**

Run:

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_w6_acceptance -q
```

Expected: all W6 acceptance tests pass.

- [ ] **Step 5: Commit**

```powershell
git add scripts/w6_acceptance.py scripts/test_w6_acceptance.py docs/w6-acceptance-agent-work.md
git commit -m "Add W6 acceptance report contract"
```

### Task B: W6 Real Model Evaluation Evidence

**Files:**
- Modify if needed: `scripts/clean_eval_outputs.py`
- Modify if needed: `scripts/test_clean_eval_outputs.py`
- Create: `eval-results/acceptance/w6/real-model.json`
- Generated evidence under: `eval-results/w6-api/`

**Interfaces:**
- Consumes: `w6_acceptance.validate_model_eval_report`
- Produces: sanitized W6 real-model report.

- [ ] **Step 1: Add failing rubric test only if real W6 Chinese headings are missed**

Use natural Chinese W6 headings such as `咨询路线图`, `阶段`, `待验证假设`, `会谈聚焦选项`, `风险监测检查点`, `协作或转介提醒`, `不做什么`, `边界说明`.

- [ ] **Step 2: Run real W6 model eval**

Run with real DeepSeek env loaded from local `.env` without printing secrets:

```powershell
$envFile='C:\Users\win\Documents\Codex\2026-05-15\agent\.env'
Get-Content $envFile | ForEach-Object {
  if ($_ -match '^DEEPSEEK_API_KEY=(.+)$') { $env:DEEPSEEK_API_KEY=$Matches[1].Trim() }
  if ($_ -match '^DEEPSEEK_MODEL=(.+)$') { $env:DEEPSEEK_MODEL=$Matches[1].Trim() }
  if ($_ -match '^DEEPSEEK_BASE_URL=(.+)$') { $env:DEEPSEEK_BASE_URL=$Matches[1].Trim() }
}
python scripts/run_model_eval.py --ids W6-001,W6-003,W6-004,W6-005 --result-dir eval-results/w6-api --stop-on-error
```

- [ ] **Step 3: Remove uncommitted meta files**

```powershell
$target = Join-Path $env:TEMP 'w6-api-meta-uncommitted'
New-Item -ItemType Directory -Force $target | Out-Null
Move-Item eval-results\w6-api\*-meta.json $target -Force
```

- [ ] **Step 4: Write sanitized acceptance report**

Create `eval-results/acceptance/w6/real-model.json` referencing only passing W6 rows and sanitized raw/clean files.

- [ ] **Step 5: Verify**

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_w6_acceptance scripts.test_clean_eval_outputs -q
rg -n "DEEPSEEK|api_key|password|Bearer|sk-|C:\\|/Users|/srv|/opt/render|run_dir|Cookie|session=" eval-results/acceptance/w6 eval-results/w6-api
```

Expected: tests pass; `rg` returns no secret/path hits except intentionally reviewed safe route text.

- [ ] **Step 6: Commit**

```powershell
git add scripts/clean_eval_outputs.py scripts/test_clean_eval_outputs.py eval-results/acceptance/w6 eval-results/w6-api
git commit -m "Add W6 real-model acceptance evidence"
```

### Task C: W6 Real Template Evidence

**Files:**
- Create: `scripts/run_w6_template_acceptance.py`
- Create: `scripts/test_run_w6_template_acceptance.py`
- Modify: `scripts/fill_docx_template.py`
- Create: `eval-data/w6-roadmap-template-acceptance.json`
- Create: `docs/w6-counseling-roadmap-template.docx`
- Create: `eval-results/acceptance/w6/real-template.json`

**Interfaces:**
- Consumes: `w6_acceptance.validate_template_report`
- Produces: fill-and-reopen report proving all W6 canonical fields are present in the real DOCX.

- [ ] **Step 1: Write failing template runner tests**

Mirror `scripts/test_run_w5_template_acceptance.py`; use W6 field probes and `document_type: "counseling_roadmap"`.

- [ ] **Step 2: Verify RED**

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_run_w6_template_acceptance -q
```

Expected: import failure for `run_w6_template_acceptance`.

- [ ] **Step 3: Implement runner and filler aliases**

Add W6 alias map to `fill_docx_template.py`:

```python
aliases = {
    "selected_framework": ["Selected framework", "理论框架", "咨询框架"],
    "overview": ["Overview", "路线图概览", "整体概览"],
    "phases": ["Phases", "阶段", "阶段安排"],
    "hypotheses_to_verify": ["Hypotheses to verify", "待验证假设"],
    "session_focus_options": ["Session focus options", "会谈聚焦选项"],
    "risk_monitoring_checkpoints": ["Risk monitoring checkpoints", "风险监测检查点"],
    "collaboration_or_referral_reminders": ["Collaboration or referral reminders", "协作或转介提醒"],
    "missing_information": ["Missing information", "待补充信息"],
    "do_not_do": ["Do not do", "不做什么"],
    "boundary_notes": ["Boundary notes", "边界说明"],
}
```

- [ ] **Step 4: Generate real template and report**

Use `render_docx.write_docx_package` with UTF-8 XML and Chinese labels, then run:

```powershell
$env:PYTHONPATH='scripts'; python scripts/run_w6_template_acceptance.py --template docs/w6-counseling-roadmap-template.docx --structured-result eval-data/w6-roadmap-template-acceptance.json --report eval-results/acceptance/w6/real-template.json
```

- [ ] **Step 5: Verify and commit**

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_run_w6_template_acceptance scripts.test_w6_acceptance -q
git add scripts/run_w6_template_acceptance.py scripts/test_run_w6_template_acceptance.py scripts/fill_docx_template.py docs/w6-counseling-roadmap-template.docx eval-data/w6-roadmap-template-acceptance.json eval-results/acceptance/w6/real-template.json
git commit -m "Add W6 real-template acceptance evidence"
```

### Task D: W6 Web Integration Evidence

**Files:**
- Modify: `scripts/test_web_workbench_frontend.mjs`
- Create: `eval-results/acceptance/w6/web-browser.json`

**Interfaces:**
- Consumes: `w6_acceptance.validate_web_report`
- Produces: visible Chinese Web evidence with editable DOCX assertion.

- [ ] **Step 1: Add failing W6 DOM contract if missing**

Add a W6 payload and assert `咨询路线图` appears, not English fallback.

- [ ] **Step 2: Write and validate report**

Create `eval-results/acceptance/w6/web-browser.json` with `visible_label: "咨询路线图"`, structured PASS, and DOCX artifact metadata.

- [ ] **Step 3: Verify and commit**

```powershell
node scripts/test_web_workbench_frontend.mjs
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_w6_acceptance scripts.test_web_workbench -q
git add scripts/test_web_workbench_frontend.mjs eval-results/acceptance/w6/web-browser.json
git commit -m "Add W6 web acceptance evidence"
```

### Task E: W6 Hosted Evidence

**Files:**
- Modify: `scripts/hosted_smoke.py`
- Modify: `scripts/test_hosted_smoke.py`
- Create: `eval-results/acceptance/w6/hosted.json`

**Interfaces:**
- Consumes: `w6_acceptance.validate_hosted_report`
- Produces: explicit hosted verification report; this command contacts the hosted service.

- [ ] **Step 1: Write failing hosted smoke tests**

Mirror W5 hosted tests and require HTTP 200, W6 route, real model success, structured PASS, and DOCX PASS.

- [ ] **Step 2: Implement `--w6-acceptance`**

Add `W6_HOSTED_SCENARIO`, `_w6_acceptance_scenario`, `run_w6_acceptance`, CLI flag, and sanitized report writer.

- [ ] **Step 3: Verify locally**

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_hosted_smoke scripts.test_w6_acceptance -q
```

- [ ] **Step 4: Push deployment code if needed, then run explicit hosted verification**

```powershell
$env:PYTHONPATH='scripts'
$env:WORKBENCH_USER='demo'
$env:WORKBENCH_PASSWORD='demo123'
python scripts/hosted_smoke.py --base-url https://counselor-agent-coze-api.onrender.com --username $env:WORKBENCH_USER --password $env:WORKBENCH_PASSWORD --timeout 300 --w6-acceptance --deployed-version <commit> --report-output eval-results/acceptance/w6/hosted.json
```

- [ ] **Step 5: Verify and commit**

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_hosted_smoke scripts.test_w6_acceptance -q
rg -n "DEEPSEEK|api_key|password|Bearer|sk-|C:\\|/Users|/srv|/opt/render|run_dir|Cookie|session=" eval-results/acceptance/w6/hosted.json
git add scripts/hosted_smoke.py scripts/test_hosted_smoke.py eval-results/acceptance/w6/hosted.json
git commit -m "Add W6 hosted acceptance evidence"
```

### Task F: Completion Matrix and Project Sync

**Files:**
- Modify: `workflow-completion.json`
- Modify generated section: `docs/product-loop-state.md`
- Modify: `docs/w6-acceptance-agent-work.md`

**Interfaces:**
- Consumes: all four W6 acceptance reports.
- Produces: derived W6 complete status.

- [ ] **Step 1: Update only W6 remaining gates**

Set W6 `real_model_eval`, `web_integration`, `hosted_verification`, and `real_template_verification` to `passed` with evidence paths. Do not add a `completed` field.

- [ ] **Step 2: Regenerate and check**

```powershell
$env:PYTHONPATH='scripts'; python scripts/workflow_completion.py --write
$env:PYTHONPATH='scripts'; python scripts/workflow_completion.py --check
```

- [ ] **Step 3: Final regression**

```powershell
$env:PYTHONPATH='scripts'; python -m unittest scripts.test_w6_acceptance scripts.test_run_w6_template_acceptance scripts.test_hosted_smoke scripts.test_workflow_completion scripts.test_run_agent scripts.test_web_workbench -q
node scripts/test_web_workbench_frontend.mjs
```

- [ ] **Step 4: Update Notion**

Insert a W6 completion update into page `393352da-f3cb-8149-83e8-ca51187b8856`, marking W1-W6 complete only after `workflow_completion.py --check` passes.

- [ ] **Step 5: Commit and push**

```powershell
git add workflow-completion.json docs/product-loop-state.md docs/w6-acceptance-agent-work.md
git commit -m "Complete W6 acceptance matrix"
git push origin HEAD:main
```

## Self-Review

- Spec coverage: all missing W6 gates have a task; completion remains derived.
- Placeholder scan: no task uses TBD/TODO/fill later language.
- Type consistency: W6 field names match `scripts/run_agent.py` structured output contract.
