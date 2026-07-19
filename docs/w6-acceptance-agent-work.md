# W6 Acceptance Agent Work Board

All work happens only in `C:\Users\win\Documents\Codex\2026-05-15\agent\.worktrees\w6-completion`. Preserve unrelated files. Product-facing UI text and browser assertions are Chinese; code identifiers, tests, and internal docs may be English.

## Shared Completion Rule

W6 is complete only after real-model evaluation, Web integration, hosted verification, and real-template verification pass in addition to the already-audited local tests gate. Completion must be derived by `workflow-completion.json` and `scripts/workflow_completion.py --check`; no agent may mark W6 complete from route-only evidence or unvalidated reports.

## Controller - Root Agent

- Own sequencing, final integrated verification, Notion sync, and push.
- Keep user-owned main-worktree changes isolated.
- Update this board as tasks finish.

## Task A - W6 Acceptance Contract

Status: complete

Owned files:

- `scripts/w6_acceptance.py`
- `scripts/test_w6_acceptance.py`

## Task B - W6 Real Model Evaluation

Status: complete

Owned files:

- `eval-results/acceptance/w6/real-model.json`
- generated W6 eval outputs under `eval-results/w6-api/`

## Task C - W6 Real Template

Status: complete

Owned files:

- `scripts/run_w6_template_acceptance.py`
- `scripts/test_run_w6_template_acceptance.py`
- `eval-data/w6-roadmap-template-acceptance.json`
- `docs/w6-counseling-roadmap-template.docx`
- `eval-results/acceptance/w6/real-template.json`

## Task D - W6 Browser Acceptance

Status: complete

Owned files:

- `scripts/test_web_workbench_frontend.mjs`
- `eval-results/acceptance/w6/web-browser.json`

## Task E - W6 Hosted Evidence

Status: complete

Owned files:

- `scripts/hosted_smoke.py`
- `scripts/test_hosted_smoke.py`
- `eval-results/acceptance/w6/hosted.json`

## Closure - Integration

Status: complete

Owned files:

- `workflow-completion.json`
- generated section of `docs/product-loop-state.md`
- this work board

## Controller Checklist

- [x] Task A implementation complete
- [x] Task A verification passed
- [x] Task B real-model evidence complete
- [x] Task B verification passed
- [x] Task C implementation and real run complete
- [x] Task C verification passed
- [x] Task D browser evidence complete
- [x] Task D verification passed
- [x] Task E implementation complete
- [x] Task E hosted real run complete
- [x] Task E verification passed
- [x] Four sanitized W6 reports validate
- [x] Matrix derives W6 complete and W1-W5 unchanged
- [x] Broader W6 regression passes
- [x] Notion synchronized
