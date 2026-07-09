# W3 Acceptance Agent Work Board

All work happens only in `C:\Users\win\Documents\Codex\2026-05-15\agent\.worktrees\w3-completion`. Preserve unrelated files. Product-facing UI text and browser assertions are Chinese; code identifiers, tests, and internal docs may be English.

## Shared Completion Rule

W3 is complete only after Web integration, hosted verification, and real-template verification pass in addition to the already-audited local tests and real-model eval gates. Completion must be derived by `workflow-completion.json` and `scripts/workflow_completion.py --check`; no agent may mark W3 complete from a route-only result or an unvalidated report.

## Controller — Root Agent

- Own sequencing, final integrated verification, Notion sync, and push.
- Keep user-owned main-worktree changes isolated.
- Update this board as tasks finish.

## Task A — W3 Acceptance Contract

Status: complete — implementation and verification passed

Owned files:

- `scripts/w3_acceptance.py`
- `scripts/test_w3_acceptance.py`

Deliverables:

- TDD acceptance validators for W3 Web, hosted, and template reports.
- Require W3 route, Chinese visible label, structured PASS, editable DOCX artifact, counseling-record sections, risk-change fields, and next-session focus.
- Reject secrets, cookies, raw private material, direct server filesystem paths, invalid URLs, and incomplete evidence.

## Task B — W3 Real Template

Status: pending

Owned files:

- `scripts/run_w3_template_acceptance.py`
- `scripts/test_run_w3_template_acceptance.py`
- `eval-data/w3-session-note-template-acceptance.json`
- `docs/w3-soap-session-note-template.docx` if no suitable real SOAP/DAP/BIRP template exists in the repository
- `eval-results/acceptance/w3/real-template.json` only after a real successful run

Deliverables:

- Use a real DOCX SOAP/DAP/BIRP counseling-record template committed in the repository, not a fake JSON-only fixture.
- Reopen the generated DOCX and verify canonical W3 fields survived in the output.
- Commit only sanitized evidence, never temporary filled client documents.

## Task C — W3 Browser Acceptance

Status: pending

Owned files:

- `scripts/test_web_workbench.py`
- `scripts/test_web_workbench_frontend.mjs`
- `web-workbench/app.js` only if needed
- `web-workbench/index.html` only if needed
- `eval-results/acceptance/w3/web-browser.json` only after browser/local Web evidence passes

Deliverables:

- Product UI remains Chinese.
- Browser evidence proves visible W3 counseling-record label, structured result, risk-change/next-focus fields, and editable Word download affordance.
- Add failing automated contract tests before product fixes if browser testing exposes defects.

## Task D — W3 Hosted Evidence Tooling

Status: pending

Owned files:

- `scripts/hosted_smoke.py`
- `scripts/test_hosted_smoke.py`
- `eval-results/acceptance/w3/hosted.json` only after a real hosted W3 scenario passes

Deliverables:

- Preserve existing smoke CLI behavior.
- Add a W3 acceptance mode requiring real hosted `/api/run`, HTTP 200, detected W3, real model success, structured PASS, risk-change/next-focus fields, and editable DOCX PASS.
- Never commit credentials, cookies, raw private material, or server filesystem paths.

## Closure — Integration

Status: pending

Owned files:

- `workflow-completion.json`
- generated section of `docs/product-loop-state.md`
- this work board

It may set only W3's three remaining gates to passed, using validated report paths. W1 and W2 must remain complete; W4-W6 must remain unchanged.

## Controller Checklist

- [x] Task A implementation complete
- [x] Task A verification passed
- [ ] Task B implementation and real run complete
- [ ] Task B verification passed
- [ ] Task C browser evidence complete
- [ ] Task C verification passed
- [ ] Task D implementation and hosted real run complete
- [ ] Task D verification passed
- [ ] Three sanitized W3 reports validate
- [ ] Matrix derives W3 complete and W1/W2/W4-W6 unchanged
- [ ] Broader W3 regression passes
- [ ] Notion synchronized
