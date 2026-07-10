# W4 Acceptance Agent Work Board

All work happens only in `C:\Users\win\Documents\Codex\2026-05-15\agent\.worktrees\w4-completion`. Preserve unrelated files. Product-facing UI text and browser assertions are Chinese; code identifiers, tests, and internal docs may be English.

## Shared Completion Rule

W4 is complete only after real-model evaluation, Web integration, hosted verification, and real-template verification pass in addition to the already-audited local tests gate. Completion must be derived by `workflow-completion.json` and `scripts/workflow_completion.py --check`; no agent may mark W4 complete from route-only evidence or unvalidated reports.

## Controller — Root Agent

- Own sequencing, final integrated verification, Notion sync, and push.
- Keep user-owned main-worktree changes isolated.
- Update this board as tasks finish.

## Task A — W4 Acceptance Contract

Status: complete — implementation and verification passed

Owned files:

- `scripts/w4_acceptance.py`
- `scripts/test_w4_acceptance.py`

Deliverables:

- TDD validators for W4 real-model, Web, hosted, and template reports.
- Require W4 route, Chinese visible label, structured PASS, editable DOCX artifact, framework, factors, risk considerations, working hypotheses, and verification questions.
- Reject secrets, cookies, raw private material, direct server filesystem paths, invalid URLs, and incomplete evidence.

## Task B — W4 Real Model Evaluation

Status: complete — real model eval run and verification passed

Owned files:

- `eval-results/acceptance/w4/real-model.json`
- existing eval summaries only if they already contain valid W4 evidence

## Task C — W4 Real Template

Status: pending

Owned files:

- `scripts/run_w4_template_acceptance.py`
- `scripts/test_run_w4_template_acceptance.py`
- `eval-data/w4-conceptualization-template-acceptance.json`
- `docs/w4-case-conceptualization-template.docx`
- `eval-results/acceptance/w4/real-template.json`

## Task D — W4 Browser Acceptance

Status: pending

Owned files:

- `scripts/test_web_workbench.py`
- `scripts/test_web_workbench_frontend.mjs`
- `web-workbench/app.js` only if needed
- `eval-results/acceptance/w4/web-browser.json`

## Task E — W4 Hosted Evidence

Status: pending

Owned files:

- `scripts/hosted_smoke.py`
- `scripts/test_hosted_smoke.py`
- `eval-results/acceptance/w4/hosted.json`

## Closure — Integration

Status: pending

Owned files:

- `workflow-completion.json`
- generated section of `docs/product-loop-state.md`
- this work board

It may set only W4's four remaining gates to passed, using validated report paths. W1-W3 must remain complete; W5-W6 must remain unchanged.

## Controller Checklist

- [x] Task A implementation complete
- [x] Task A verification passed
- [x] Task B real-model evidence complete
- [x] Task B verification passed
- [ ] Task C implementation and real run complete
- [ ] Task C verification passed
- [ ] Task D browser evidence complete
- [ ] Task D verification passed
- [ ] Task E implementation and hosted real run complete
- [ ] Task E verification passed
- [ ] Four sanitized W4 reports validate
- [ ] Matrix derives W4 complete and W1-W3/W5-W6 unchanged
- [ ] Broader W4 regression passes
- [ ] Notion synchronized
