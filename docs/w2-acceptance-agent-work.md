# W2 Acceptance Agent Work Board

All agents work only in `C:\Users\win\Documents\Codex\2026-05-15\agent\.worktrees\w2-completion`. Preserve unrelated files. Product-facing UI text and browser assertions are Chinese; code identifiers, tests, and internal docs may be English.

## Shared Completion Rule

W2 is complete only after Web integration, hosted verification, and real-template verification pass in addition to the already-audited local tests and real-model eval gates. Completion must be derived by `workflow-completion.json` and `scripts/workflow_completion.py --check`; no agent may mark W2 complete from a route-only result or an unvalidated report.

## Controller — Root Agent

- Own overall sequencing, final integrated verification, Notion sync, and push.
- Keep user-owned main-worktree changes isolated.
- Update this board as agents finish.

## Agent A — W2 Acceptance Contract

Status: complete — implementation and verification passed

Owned files:

- `scripts/w2_acceptance.py`
- `scripts/test_w2_acceptance.py`

Deliverables:

- TDD acceptance validators for W2 Web, hosted, and template reports.
- Require W2 route, Chinese visible label, structured PASS, editable DOCX artifact, and BPS-specific required fields.
- Reject secrets, cookies, raw private material, direct server filesystem paths, invalid URLs, and incomplete evidence.
- Stable sanitized JSON writer or safe reuse of W1 writer.

## Agent B — W2 Real Template

Status: complete — implementation, real run, and verification passed

Owned files:

- `scripts/run_w2_template_acceptance.py`
- `scripts/test_run_w2_template_acceptance.py`
- `eval-data/w2-bps-template-acceptance.json`
- `docs/w2-bps-case-background-template.docx` if no suitable real BPS template exists in the repository
- `eval-results/acceptance/w2/real-template.json` only after a real successful run

Deliverables:

- Use a real DOCX BPS/case-background template committed in the repository, not a fake JSON-only fixture.
- Reopen the generated DOCX and verify canonical W2 fields survived in the output.
- Commit only sanitized evidence, never temporary filled client documents.

## Agent C — Hosted Evidence Tooling

Status: complete — implementation, hosted real run, and verification passed

Owned files:

- `scripts/hosted_smoke.py`
- `scripts/test_hosted_smoke.py`
- `eval-results/acceptance/w2/hosted.json` only after a real hosted W2 scenario passes

Deliverables:

- Preserve existing smoke CLI behavior.
- Add a W2 acceptance mode requiring real hosted `/api/run`, HTTP 200, detected W2, real model success, structured PASS, and editable DOCX PASS.
- Never commit credentials, cookies, raw private material, or server filesystem paths.

## Agent D — W2 Browser Acceptance

Status: complete — browser evidence and verification passed

Owned files:

- `scripts/test_web_workbench.py`
- `scripts/test_web_workbench_frontend.mjs`
- `web-workbench/app.js`
- `web-workbench/index.html` only if required
- `eval-results/acceptance/w2/web-browser.json` only after browser/local Web evidence passes

Deliverables:

- Product UI remains Chinese.
- Browser evidence proves visible W2/BPS label, structured result, and editable Word download affordance.
- Add failing automated contract tests before product fixes if browser testing exposes defects.

## Closure — Integration Agent

Status: complete — matrix derives W2 complete from evidence.

Owned files:

- `workflow-completion.json`
- generated section of `docs/product-loop-state.md`

It may set only W2's three remaining gates to passed, using validated report paths. W1 must remain complete; W3-W6 must remain unchanged.

## Controller Checklist

- [x] Agent A implementation complete
- [x] Agent A verification passed
- [x] Agent B implementation and real run complete
- [x] Agent B verification passed
- [x] Agent C implementation and hosted real run complete
- [x] Agent C verification passed
- [x] Agent D browser evidence complete
- [x] Three sanitized W2 reports validate
- [x] Matrix derives W2 complete and W1/W3-W6 unchanged
- [x] Broader W2 regression passes
- [x] Notion synchronized
