# W1-W6 Unified Completion Matrix Design

## Goal

Create one authoritative, machine-checkable completion matrix for workflows W1 through W6. A workflow is complete only when all five required gates pass: local tests, real-model evaluation, Web integration, hosted verification, and real-template verification.

## Existing Progress Sources

The repository already has one durable project-management source, `docs/product-loop-state.md`. It contains the product objective, operating rules, definition of done, current capability backlog, historical evidence, and remaining gaps. It should remain the human-facing development handoff.

Other files serve narrower purposes and should not become competing progress trackers:

- `README.md` is an entry point and operating guide.
- `docs/superpowers/plans/*.md` are implementation plans and acceptance procedures.
- `eval-prompts/`, `eval-results/`, tests, and hosted-smoke commands are evidence sources.
- `workbench-run-log.jsonl`, `agent-runs/`, and `workbench-data/` are local runtime data, not authoritative project status.

The new matrix will therefore be integrated with `docs/product-loop-state.md` instead of creating a second narrative backlog.

## Recommended Architecture

Use three small layers:

1. `workflow-completion.json` is the single source of truth for W1-W6 gate status and evidence.
2. A Python validator computes workflow completion and rejects invalid or unsupported status declarations.
3. A generated Markdown table is embedded in `docs/product-loop-state.md`; `README.md` links to that section rather than duplicating status.

This keeps status machine-enforceable while preserving the existing handoff document as the place developers read and update during later work.

## Status Model

Each workflow has exactly five gates:

- `local_tests`
- `real_model_eval`
- `web_integration`
- `hosted_verification`
- `real_template_verification`

Each gate uses one of three states:

- `passed`: current, reproducible evidence exists.
- `failed`: verification ran and failed.
- `unverified`: no sufficient current evidence exists.

Each gate records a short evidence list. Evidence may reference a repository path, exact test/eval command, result artifact, or hosted URL and verification command. Historical prose or a commit message alone is not sufficient evidence.

Workflow completion is derived, never manually asserted:

```text
completed = all(five gate statuses == "passed")
```

If any gate is `failed` or `unverified`, the workflow is incomplete. The validator must reject any stored `completed` field, preventing status from drifting away from gate evidence.

## Initial Migration Rule

The first migration is conservative. Existing evidence is reviewed gate by gate, but ambiguous claims are imported as `unverified`. No workflow receives completion credit merely because `docs/product-loop-state.md` currently says `shipped partial`, a historical run mentions success, or a related route variant passed.

Evidence must apply to the workflow-level gate. For example, one W2 routing smoke test may support hosted routing but does not automatically prove all W2 real-template behavior.

## Validation Rules

The validator will fail when:

- a workflow from W1 through W6 is missing or an unknown workflow is present;
- a required gate is missing or an unknown gate is present;
- a status is outside `passed`, `failed`, or `unverified`;
- a `passed` gate has no evidence;
- an evidence path claimed as local does not exist;
- a manually maintained completion flag is present;
- the generated Markdown matrix differs from the checked-in section of `docs/product-loop-state.md`.

Hosted URLs and external services are not contacted by the ordinary validator. Hosted verification remains an explicit command whose successful result is recorded as evidence, keeping local checks deterministic.

## Progress-Management Integration

`docs/product-loop-state.md` remains the durable development-management file. Its workflow backlog rows for W1-W6 will point to the unified matrix and stop using free-form completion labels as authoritative status. The generated section will show the five gate states, derived overall state, and the next missing gate for each workflow.

After every development iteration affecting W1-W6:

1. Run the relevant verification.
2. Update the matching gate and evidence in `workflow-completion.json`.
3. Regenerate the matrix in `docs/product-loop-state.md`.
4. Run the validator and its unit tests.
5. Record broader narrative changes and next steps in `docs/product-loop-state.md` as today.

This merges structured workflow progress into the existing project loop without erasing useful historical run notes.

## Testing

Unit tests will cover all-five-pass completion, every incomplete combination, missing/unknown workflows and gates, invalid statuses, evidence requirements, rejection of manual completion, local evidence-path validation, and generated-document drift.

Repository verification will run the unit tests and validator. The implementation will preserve unrelated user changes already present in the worktree.

## Out of Scope

- Running every missing real-model, hosted, and real-template verification during the matrix implementation.
- Rewriting historical run logs.
- Making iOS/App Store completion depend on this workflow matrix; those release gates remain separately managed in `docs/product-loop-state.md`.
- Treating runtime data directories as committed evidence unless a deliberately sanitized fixture is added.
