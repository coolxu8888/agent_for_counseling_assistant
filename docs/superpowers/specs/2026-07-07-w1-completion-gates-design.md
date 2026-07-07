# W1 Completion Gates Design

## Goal

Move W1 from two passed gates to all five passed gates without weakening the unified completion rule. W1 covers both counselor-visible modes: initial-interview preparation and fixed-template initial-interview summary.

## Current State

The completion matrix already marks W1 local tests and real-model evaluation as passed. Three gates remain unverified:

- Web integration
- hosted verification
- real-template verification

Existing API and unit coverage proves routing and payload behavior, but it does not prove browser-visible results or export. Historical hosted prose and route-only checks are not durable workflow evidence. Existing template tests rely mainly on generated or synthetic fixtures and do not prove the real intake DOCX path.

## Acceptance Scope

### Web integration

Run browser-level acceptance against the local Web workbench for both W1 modes.

The preparation scenario must:

1. sign in through the visible UI;
2. submit a de-identified partial-clue request through AUTO routing;
3. visibly show W1 preparation mode and the generated structured result;
4. expose a downloadable editable DOCX artifact.

The summary scenario must:

1. sign in through the visible UI;
2. submit completed intake notes requesting the fixed initial-interview summary;
3. visibly show W1 summary mode and structured sections;
4. expose a downloadable editable DOCX artifact.

Passing requires automated browser assertions. API payload tests or the presence of rendering code alone remain partial evidence.

### Hosted verification

Run both W1 scenarios against the current hosted deployment using real model execution. Each successful report must record:

- public base URL;
- UTC timestamp;
- deployed version or commit when available;
- sanitized input scenario;
- detected workflow and W1 mode;
- route status;
- model-run success;
- structured validation result;
- expected artifact metadata.

The evidence must be committed as a sanitized machine-readable report. A route-only smoke result does not pass this gate. No secret, session cookie, direct identifier, raw private material, or server filesystem path may be committed.

### Real-template verification

Use the repository's real initial-interview DOCX under `docs/` for the fixed-summary scenario. The run must:

1. inspect the real template;
2. generate or load a valid W1 fixed-summary structured result;
3. fill the real DOCX through the shipped template path;
4. reopen the output and verify required W1 sections contain mapped content;
5. write a sanitized fill report with filled fields, unfilled fields, issues, source-template identity, and output verification.

The preparation mode is not forced into the fixed-summary template because that would test a false product contract. Its document requirement is covered by Web and hosted DOCX export. The real-template gate passes when the actual W1 fixed-summary template flow is proven, while both W1 modes still must pass Web and hosted acceptance.

## Evidence Layout

Create a committed evidence directory dedicated to W1 acceptance. It should contain small sanitized JSON reports and no generated client documents unless they are confirmed safe fixtures. Browser evidence, hosted evidence, and real-template evidence must be independently identifiable.

The completion matrix references these committed reports using `path` evidence. Commands may be recorded as supporting evidence, but a command by itself does not prove a successful run.

## Automation and Boundaries

- Browser acceptance should reuse the existing in-app browser/browser-testing workflow and exercise visible UI, not only HTTP handlers.
- Hosted acceptance may extend the existing smoke tooling, but must assert full W1 output and artifact metadata for both modes.
- Real-template verification should extend existing template inspection/fill helpers rather than create a second DOCX implementation.
- New verification code follows test-driven development.
- Existing unrelated iOS, backend, and uncommitted user changes remain untouched.
- Credentials remain in environment variables and never enter reports.

## Failure Handling

If either W1 mode fails Web or hosted acceptance, the corresponding gate remains unverified. If template inspection, filling, reopening, or required-field assertions fail, the template gate remains unverified. Failed attempts may be recorded for diagnosis, but the matrix changes to `passed` only after current successful evidence exists.

Network instability is reported separately from product assertion failures. A retry may be made, but reports must not disguise repeated product failures as transient network errors.

## Completion Update

After all three acceptance groups pass:

1. update W1 gate evidence in `workflow-completion.json`;
2. regenerate `docs/product-loop-state.md`;
3. run completion-matrix tests and `--check`;
4. update the Notion overview to show all five W1 gates passed;
5. confirm W1 is automatically derived as complete, without adding a manual completion field.

## Out of Scope

- Changing W2-W6 completion status.
- Adding new W1 routing ambiguity cases unless acceptance exposes a real defect.
- Treating native iOS acceptance as the Web gate.
- Committing real counselor data, secrets, or unsanitized generated documents.
