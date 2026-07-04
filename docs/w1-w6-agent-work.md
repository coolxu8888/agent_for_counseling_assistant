# W1-W6 Completion Matrix Agent Work Board

This file is the collaboration contract for delegated work. Every agent must read it before acting, edit only the files assigned to that role, preserve unrelated changes, and report evidence instead of claiming completion without verification.

## Shared Definition of Done

A workflow is derived as complete only when all five gates are `passed`: local tests, real-model evaluation, Web integration, hosted verification, and real-template verification. No stored/manual `completed` field is allowed.

## Controller Responsibilities

Owner: root agent.

- Assign tasks and enforce file boundaries.
- Review specification compliance before code quality.
- Run integrated and full verification.
- Merge commits and resolve conflicts.
- Update the Notion project overview only after a checklist item is actually complete.
- Never mark W1-W6 complete from prose or commit history alone.

## Agent A — Completion Engine

Status: complete — implementation, spec review, and quality review approved

Owned files:

- `scripts/workflow_completion.py`
- `scripts/test_workflow_completion.py`

Tasks:

- Implement the validated status model with TDD.
- Enforce exact W1-W6 and exact five-gate keys.
- Reject manual `completed`, bad statuses, missing evidence for passed gates, and missing local evidence paths.
- Derive completion and missing gates.
- Render/check/write the marked Markdown matrix section.
- Do not edit JSON, README, or progress documents.

Acceptance:

- Focused tests show recorded red then green results.
- All owned-file tests pass.
- Commit only owned files and report the commit SHA.

## Agent B — Evidence Audit

Status: complete — audit, spec review, and quality review approved

Owned file:

- `docs/w1-w6-evidence-audit.md`

Read-only sources:

- `docs/product-loop-state.md`
- `eval-results/`
- `eval-prompts/`
- `scripts/test_*.py`
- `scripts/hosted_smoke.py`
- template fixtures and committed result artifacts

Tasks:

- Audit each W1-W6 gate conservatively.
- For each proposed `passed`, cite an exact command and/or committed path that proves the workflow-level gate.
- Mark insufficient or ambiguous evidence `unverified` and state what proof is missing.
- Do not edit implementation, JSON, README, or product-loop-state.

Acceptance:

- The report covers 30 cells (6 workflows × 5 gates).
- It distinguishes route-only evidence from complete workflow/template evidence.
- Commit only the audit report and report the commit SHA.

## Agent C — Repository Integration

Status: assigned — Agents A and B approved

Owned files:

- `workflow-completion.json`
- `README.md`
- `docs/product-loop-state.md`

Inputs:

- Agent A's validated schema/CLI.
- Agent B's evidence audit.

Tasks:

- Create conservative JSON using only sufficient audited evidence.
- Add the generated matrix section to product-loop-state.
- Point README to the authoritative progress source and validation command.
- Preserve the existing historical narrative.
- Do not edit Agent A or Agent B files.

Acceptance:

- Engine tests pass against repository data.
- `python scripts/workflow_completion.py --check` exits 0.
- No workflow is complete unless all five evidenced gates pass.
- Commit only owned files and report the commit SHA.

## Review Roles

Spec reviewer: read-only; compare each completed agent task with this file and the approved design.

Quality reviewer: read-only; inspect maintainability, edge cases, test quality, and unsafe path handling after spec approval.

## Controller Checklist

- [x] Isolated worktree established; full baseline recorded as timeout, focused baseline used
- [x] Agent A implementation complete
- [x] Agent A spec review approved
- [x] Agent A quality review approved
- [x] Agent B evidence audit complete
- [x] Agent B spec review approved
- [ ] Agent C repository integration complete
- [ ] Agent C spec review approved
- [ ] Agent C quality review approved
- [ ] Integrated verification passes
- [ ] Notion overview synchronized
