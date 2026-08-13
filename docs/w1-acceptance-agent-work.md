# W1 Acceptance Agent Work Board

All agents work only in `C:\Users\win\Documents\Codex\2026-05-15\agent\.worktrees\w1-completion`. Read the approved design and implementation plan before acting. Preserve unrelated files. Product-facing text and browser assertions are Chinese; code identifiers, tests, and internal docs may be English.

## Shared Completion Rule

W1 is complete only after both W1 modes pass Web and hosted acceptance, the real fixed-summary template path passes, three sanitized reports are committed, and `workflow-completion.json` derives W1 complete. No agent may mark a gate passed from a command's existence or from route-only output.

## Controller — Root Agent

- Assign ownership and dependencies.
- Perform spec review before quality review for every implementation task.
- Run local Chinese browser acceptance through visible UI.
- Run integrated verification and update matrix/Notion only after evidence passes.
- Keep user-owned main-worktree changes isolated.

## Agent A — Acceptance Contract

Status: complete — implementation, spec review, and quality review approved

Owned files:

- `scripts/w1_acceptance.py`
- `scripts/test_w1_acceptance.py`

Deliverables:

- TDD red/green acceptance validators for Web, hosted, and template reports.
- Secret, cookie, direct server path, missing-mode, and incomplete-assertion rejection.
- Stable sanitized JSON writing.
- Commit only owned files.

## Agent B — Real Template

Status: complete — implementation, real run, spec review, and quality review approved

Owned files:

- `scripts/run_w1_template_acceptance.py`
- `scripts/test_run_w1_template_acceptance.py`
- `eval-data/w1-summary-template-acceptance.json`
- `eval-results/acceptance/w1/real-template.json` only after a real successful run

Deliverables:

- Reuse the shipped template filler.
- Use `docs/4.心理咨询初始访谈表_20210906.docx`.
- Reopen and verify the generated DOCX.
- Commit only a sanitized report, never the temporary filled client document.

## Agent C — Hosted Evidence Tooling

Status: complete — implementation, hosted real runs, spec review, and quality review approved

Owned files:

- `scripts/hosted_smoke.py`
- `scripts/test_hosted_smoke.py`
- `eval-results/acceptance/w1/hosted.json` only after both real hosted scenarios pass

Deliverables:

- Preserve existing smoke CLI behavior.
- Require full real-model, structured-validation, and artifact assertions for W1 prep and summary.
- Never commit credentials, cookies, raw private material, or server filesystem paths.

## Browser Acceptance — Root Agent

Owned success report:

- `eval-results/acceptance/w1/web-browser.json`

Required visible Chinese assertions:

- W1 preparation mode and structured result.
- W1 fixed-summary mode and structured sections.
- Editable DOCX download affordance for both.

Product defects discovered by browser testing receive a failing automated contract test before a fix.

## Agent D — Real Template Mapping Fix

Status: complete — mapping defect fixed and review approved

Owned files:

- `scripts/fill_docx_template.py`
- `scripts/test_fill_docx_template.py`

Deliverables:

- Add explicit W1 fixed-summary mappings for the real initial-interview template blocks.
- Preserve existing content and unrelated workflow mappings.
- Prove the seven missing canonical sections fill and survive DOCX reopen.
- Do not weaken the acceptance runner or report contract.

## Agent E — W1 Chinese Browser Product Fix

Status: complete — Chinese browser defects fixed and review approved

Owned files:

- `scripts/web_workbench.py`
- `scripts/test_web_workbench.py`
- `scripts/test_web_workbench_frontend.mjs`
- `web-workbench/app.js`
- `web-workbench/index.html` only if required

Deliverables:

- Route an explicit Chinese “初访准备、不要初访总结” request to W1 `intake_prep`.
- Show mode-specific user-visible text in Chinese when Chinese is selected.
- Expose a visible downloadable Word artifact after successful W1 runs requesting Word.
- Add failing automated contract tests before product fixes.

## Closure — Integration Agent

Status: complete — matrix derives W1 complete from evidence.

Owned files:

- `workflow-completion.json`
- generated section of `docs/product-loop-state.md`

It may set only W1's three remaining gates to passed, using report paths. W2-W6 must remain unchanged.

## Controller Checklist

- [x] Agent A implementation complete
- [x] Agent A spec review approved
- [x] Agent A quality review approved
- [x] Agent B implementation and real run complete
- [x] Agent B spec and quality reviews approved
- [x] Agent D real-template mapping defect fixed
- [x] Agent C implementation and hosted real runs complete
- [x] Agent C spec and quality reviews approved
- [x] Agent E Chinese browser defects fixed
- [x] Chinese browser acceptance passes both W1 modes
- [x] Three sanitized reports validate
- [x] Matrix derives W1 complete and W2-W6 unchanged
- [x] Broader W1 regression passes
- [x] Notion synchronized
