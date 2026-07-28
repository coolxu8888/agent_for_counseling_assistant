# Web Agent Rehearsal UI Design

Date: 2026-07-28

## Goal

Turn the existing Web Workbench into a pre-release rehearsal surface that looks like the counselor-facing product by default and exposes an expandable test drawer when diagnostic detail is needed.

The first acceptance journey is:

```text
sign in
  -> create or select a de-identified case
  -> enter counselor material
  -> let the server route the intent automatically
  -> call the real DeepSeek API
  -> review generated output and safety checks
  -> download the Word artifact
  -> reopen the run from case history
```

This is a rehearsal-grade validation surface. It is not the final iOS UI and it does not introduce production-grade durable analytics storage.

## Existing System

The implementation must reuse the current stack:

- `web-workbench/index.html`, `styles.css`, and `app.js` for the browser UI.
- `scripts/web_workbench.py` for authenticated Web APIs, cases, run history, and artifact delivery.
- `scripts/run_agent.py` for routing, RAG retrieval, DeepSeek calls, validation, and document generation.
- Existing `workbench-data/` SQLite and `agent-runs/` artifacts for rehearsal data.
- Existing Render Web service configuration.

The current runner already writes the exact DeepSeek `usage` object returned by the provider into each run's `metadata.json`. The UI work will surface and aggregate that provider-reported value; it will not estimate tokens locally.

## Chosen Interface

### Product mode

The normal interface prioritizes the counselor task:

- De-identified case navigation on the left.
- Current case and generated result in the center.
- Material input, run action, Word export, and history access in the main workflow.
- No raw workflow codes, filesystem paths, provider credentials, or diagnostic JSON in the default view.

### Expandable test mode

A `测试模式` control opens a right-side drawer without navigating away from the current case or run.

The drawer contains:

1. **Run overview**
   - Provider: DeepSeek.
   - Model name.
   - Automatically detected workflow.
   - Request status.
   - Latency.

2. **Token usage**
   - Input/prompt tokens.
   - Output/completion tokens.
   - Total tokens.
   - Current case cumulative tokens.
   - A clear `API 未返回用量` state instead of displaying zero when usage is absent.

3. **Validation**
   - Structured-output validation.
   - Safety/rubric validation.
   - Word generation status.

4. **Diagnostics**
   - Expandable sanitized JSON.
   - Rehearsal usage export.
   - No API key, authorization header, direct client identifier, or unredacted provider error.

The drawer is closed by default. On narrower screens it becomes an overlay panel so it does not compress the counselor content into an unusable column.

## Token Recording

### Source of truth

Only the DeepSeek response `usage` object is authoritative. The normalization layer accepts the provider's prompt/input, completion/output, and total token fields while preserving the raw sanitized usage object for diagnostics.

### Per-run behavior

For every successful provider response:

- Preserve the provider usage in `metadata.json`.
- Normalize the three display values.
- Return them in the authenticated run detail payload.
- Display them in the test drawer.
- Preserve them when the run is reopened from case history.

If generation succeeds but structured validation or Word rendering fails, token usage is still recorded because the provider call already consumed tokens.

For timeouts, connection failures, or responses without usage:

- Record the run status and sanitized error as today.
- Store token usage as unavailable, not zero.
- Do not include unavailable usage in cumulative totals.

### Rehearsal aggregation

The current case cumulative total is calculated from runs that:

- Belong to the authenticated workspace.
- Are attached to the selected case.
- Have provider-reported token usage.

The test drawer can export usage rows for the selected case as JSON or CSV with:

- Opaque run name that does not contain a server path.
- Timestamp.
- Provider and model.
- Detected workflow.
- Input, output, and total tokens.
- Status and latency.

The export excludes counselor material, model output, API keys, raw authorization data, and server filesystem paths. Workspace-wide and cross-case exports are outside this rehearsal scope.

### Retention boundary

Usage records use the existing run artifacts and local SQLite registration. They remain subject to the configured rehearsal retention/pruning policy and may be lost when a free Render instance is rebuilt or replaced. The UI will describe them as rehearsal statistics, not billing records.

No managed database, persistent disk, cost calculator, organization-wide billing reconciliation, or cross-deployment migration is included.

## Data Flow

```text
Counselor product UI
  -> authenticated POST /api/run
  -> automatic workflow routing
  -> RAG retrieval and prompt assembly
  -> DeepSeek /chat/completions
  -> generated content + provider usage
  -> validation and optional Word generation
  -> metadata/artifacts + authenticated run registration
  -> product result view + expandable test drawer
```

History reopen:

```text
case history selection
  -> authenticated run detail
  -> ownership/path guard
  -> saved output, checks, metadata, and normalized usage
  -> restore product result and test drawer state
```

Usage export:

```text
selected case
  -> authenticated usage export request
  -> accessible registered runs only
  -> sanitized JSON or CSV download
```

## Error Handling

- Missing counselor input stays attached to the input area.
- Missing `DEEPSEEK_API_KEY` is reported as unavailable model access; the key value is never displayed.
- DeepSeek timeout and API failures show a short retryable status and a sanitized diagnostic category.
- Missing or malformed provider usage shows `API 未返回用量`.
- Structured validation warnings remain distinct from API failures.
- Word generation failures do not discard the generated text or recorded token usage.
- Unauthorized case, run, or export access returns the existing authentication/ownership error and reveals no artifact path.
- The test drawer never exposes a Python traceback or provider credential.

## Testing

### Backend tests

- Exact provider usage is preserved in run metadata.
- Prompt/input, completion/output, and total token fields normalize correctly.
- Missing and malformed usage stays unavailable rather than becoming zero.
- Usage remains present when downstream validation or Word generation fails.
- Case aggregation includes only owned runs attached to that case.
- JSON and CSV exports contain allowed diagnostic fields and exclude sensitive content.
- Cross-workspace run and export access is rejected.

### Frontend tests

- Test mode opens and closes without losing the current run.
- Product mode does not show workflow codes or diagnostic JSON.
- Current-run and case-total Token values render correctly.
- Missing usage renders the unavailable state.
- Reopening history restores output, checks, and usage.
- The drawer becomes an overlay at the narrow breakpoint.
- The main run and Word download controls remain usable with the drawer open.

### Integration acceptance

- Mocked runs cover success, missing usage, timeout, validation warning, and Word failure.
- One real DeepSeek smoke run uses the configured local `.env` without printing or copying the key.
- The complete acceptance journey passes locally.
- Render deployment is smoke-tested separately after the local implementation is accepted.

## Scope Boundaries

Included:

- Product-first layout refinement.
- Expandable right test drawer.
- Exact DeepSeek Token usage display and rehearsal aggregation.
- Sanitized JSON/CSV usage export.
- Local browser and automated validation.

Excluded:

- React, Next.js, or another frontend framework migration.
- A new model provider.
- Long-term analytics storage or production billing reconciliation.
- Changes to DeepSeek credentials.
- Copying the Web UI into the iOS application package.
- Render production deployment before local review and verification.

## Acceptance Criteria

The design is implemented when:

- The default Web interface reads as a counselor product rather than an engineering console.
- The right test drawer opens on demand and stays tied to the current run.
- A real DeepSeek run displays provider, model, route, latency, validation state, and exact returned Token usage.
- Per-run usage survives history reopen.
- Current case totals exclude unavailable usage and other workspaces.
- Sanitized usage export works in JSON and CSV.
- The full counselor rehearsal journey passes locally.
- Existing backend and Web tests remain passing.
- No API key or sensitive counselor content is introduced into source control, browser diagnostics, or usage exports.
