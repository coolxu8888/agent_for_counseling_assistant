# W5 Acceptance Agent Work Board

All work happens only in `C:\Users\win\Documents\Codex\2026-05-15\agent\.worktrees\w5-completion`. Preserve unrelated files. Product-facing UI text and browser assertions are Chinese; code identifiers, tests, and internal docs may be English.

## Shared Completion Rule

W5 is complete only after real-model evaluation, Web integration, hosted verification, and real-template verification pass in addition to the already-audited local tests gate. Completion must be derived by `workflow-completion.json` and `scripts/workflow_completion.py --check`; no agent may mark W5 complete from route-only evidence or unvalidated reports.

## Controller - Root Agent

- Own sequencing, final integrated verification, Notion sync, and push.
- Keep user-owned main-worktree changes isolated.
- Update this board as tasks finish.

## Task A - W5 Acceptance Contract

Status: complete - implementation and verification passed

Owned files:

- `scripts/w5_acceptance.py`
- `scripts/test_w5_acceptance.py`

Deliverables:

- TDD validators for W5 real-model, Web, hosted, and template reports.
- Require W5 route, Chinese visible label, structured PASS, editable DOCX artifact, framework, single-session goal/focus/interventions/questions/risk monitoring/between-session tasks/do-not-do boundaries, and boundary notes.
- Reject secrets, cookies, raw private material, direct server filesystem paths, invalid URLs, and incomplete evidence.

## Task B - W5 Real Model Evaluation

Status: pending

Owned files:

- `eval-results/acceptance/w5/real-model.json`
- generated W5 eval outputs under `eval-results/w5-api/`

## Task C - W5 Real Template

Status: pending

Owned files:

- `scripts/run_w5_template_acceptance.py`
- `scripts/test_run_w5_template_acceptance.py`
- `eval-data/w5-next-session-template-acceptance.json`
- `docs/w5-next-session-plan-template.docx`
- `eval-results/acceptance/w5/real-template.json`

## Task D - W5 Browser Acceptance

Status: pending

Owned files:

- `scripts/test_web_workbench_frontend.mjs`
- `eval-results/acceptance/w5/web-browser.json`

## Task E - W5 Hosted Evidence

Status: pending

Owned files:

- `scripts/hosted_smoke.py`
- `scripts/test_hosted_smoke.py`
- `eval-results/acceptance/w5/hosted.json`

## Closure - Integration

Status: pending

Owned files:

- `workflow-completion.json`
- generated section of `docs/product-loop-state.md`
- this work board

It may set only W5's four remaining gates to passed, using validated report paths. W1-W4 must remain complete; W6 must remain unchanged.

## Controller Checklist

- [x] Task A implementation complete
- [x] Task A verification passed
- [ ] Task B real-model evidence complete
- [ ] Task B verification passed
- [ ] Task C implementation and real run complete
- [ ] Task C verification passed
- [ ] Task D browser evidence complete
- [ ] Task D verification passed
- [ ] Task E implementation and hosted real run complete
- [ ] Task E verification passed
- [ ] Four sanitized W5 reports validate
- [ ] Matrix derives W5 complete and W1-W4/W6 unchanged
- [ ] Broader W5 regression passes
- [ ] Notion synchronized
