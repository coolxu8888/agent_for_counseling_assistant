# Local Web Workbench Design

Date: 2026-06-10

## Goal

Build a first-version local web workbench for the counselor assistant agent.

The workbench turns the current script-based runtime into a visible, clickable local tool. A developer or product tester can choose W1/W2/W3, enter counselor material, run the existing agent pipeline, inspect Markdown/JSON/check results, optionally render a fixed Word document, and optionally fill a counselor-provided Word template.

This is a local development workbench, not a production counseling product.

## Context

The project already has:

- W1/W2/W3 agent runner through `scripts/run_agent.py` and `scripts/run-agent.ps1`.
- DeepSeek API configuration through local `.env`.
- Structured JSON extraction and validation.
- Fixed DOCX rendering through `scripts/render_docx.py`.
- DOCX template autofill through `scripts/fill_docx_template.py`.
- Eval prompts, API eval outputs, and regression checks.

The missing layer is a local UI that makes these capabilities easy to run and inspect without manually typing PowerShell commands.

## Product Scope

In scope:

- A local browser-based workbench.
- Explicit workflow selection for W1, W2, and W3.
- Text input for counselor material.
- Toggles for structured output and fixed DOCX generation.
- Run status display.
- Display of Markdown output, structured JSON, and validation/check result.
- Display of output paths from the latest run.
- DOCX template fill panel that uses the current structured JSON.
- Template path selection or upload-style file input for local use.
- Generated template DOCX path and template fill report display.
- Clear error messages when input, API, JSON, DOCX rendering, or template filling fails.

Out of scope:

- Login, account management, permissions, or multi-user collaboration.
- Cloud deployment.
- Persistent case database.
- Multi-turn chat memory.
- Browser-based editing of generated Word files.
- Audio transcription.
- Semantic template understanding beyond the existing template mapper.
- Automatic crisis intervention or final clinical decision making.

## Recommended Architecture

Use a small Python web app that wraps the existing scripts as library functions.

Recommended stack:

- Python HTTP layer: FastAPI or a similarly small local web framework.
- Frontend: server-served HTML, CSS, and lightweight JavaScript.
- Runtime reuse: call existing Python functions from `run_agent.py`, `render_docx.py`, and `fill_docx_template.py` instead of shelling out where practical.

This keeps the first version close to the current codebase. It avoids introducing a React/Node build system before the workflow and output contracts are stable.

## Page Layout

The first screen is the actual workbench, not a landing page.

### Left: Workflow Navigation

The left rail contains:

- `W1 初访信息收集`
- `W2 个案信息整理`
- `W3 Session 记录`

Each workflow item shows a short operational description. W1 must distinguish:

- default mode: initial interview information collection / question guide.
- confirmed summary mode: summarize already completed initial interview material when the user clearly asks for that.

The left rail should also show whether the latest run succeeded, failed, or has not run.

### Center: Result Observation Area

The center is the main visual area.

It has tabs or segmented controls for:

- `模型输出`: cleaned Markdown answer.
- `结构化 JSON`: parsed structured output, formatted and readable.
- `校验结果`: structured validation, rubric/basic check result, and issues.

The center area should stay readable for long records. It should support scrolling inside the result pane without shifting the whole layout.

### Bottom: Input And Run Controls

The bottom panel contains:

- Large textarea for counselor material.
- Checkbox/toggle: structured output.
- Checkbox/toggle: generate fixed Word.
- Run button.
- Optional dry-run button for prompt package inspection.
- Latest run directory and generated file paths.
- Basic runtime status: idle, running, success, warning, failed.

This bottom placement follows the user's preferred layout: the output stays central, while inputs and controls remain available below.

### Right: Template Fill Panel

The right panel contains:

- Template file selector or local path input.
- Button: fill template with current structured JSON.
- Optional checkbox: use LLM mapping for unresolved fields if local DeepSeek configuration is available.
- Output path for `filled_template.docx`.
- Template fill report summary:
  - status.
  - filled field count.
  - unfilled field count.
  - important issues.
- Detailed report view for field mapping audit.

The template panel is disabled until a structured JSON output exists for the current run.

## Data Flow

Main agent run:

```text
workflow + counselor input + run options
  -> local web API
  -> run_agent.py
  -> agent-runs/<timestamp-workflow>/
  -> raw_output.txt + clean_output.md + structured_output.json + structured_check.json
  -> web UI result panes
```

Fixed DOCX rendering:

```text
structured_output.json
  -> render_docx.py
  -> output.docx + docx_check.json
  -> web UI output path
```

Template fill:

```text
template.docx + current structured_output.json
  -> fill_docx_template.py
  -> filled_template.docx + template_fill_report.json
  -> web UI template report
```

## Local API Endpoints

First version endpoints:

```text
GET  /                  Serve the workbench UI.
POST /api/run           Run W1/W2/W3.
POST /api/render-docx   Render fixed DOCX from a structured output path.
POST /api/fill-template Fill an uploaded or path-referenced DOCX template.
GET  /api/runs/latest   Return latest run metadata.
GET  /files/<path>      Serve generated local files for browser download/open.
```

`/files/<path>` must only serve files under approved local output directories such as `agent-runs/`. It must not become a general filesystem browser.

## Request And Response Shapes

### POST /api/run

Request:

```json
{
  "workflow": "W1",
  "input": "咨询师输入的材料",
  "structured": true,
  "render_docx": false,
  "dry_run": false
}
```

Response:

```json
{
  "status": "success",
  "workflow": "W1",
  "run_dir": "agent-runs/2026-06-10-120000-W1",
  "clean_output": "...",
  "structured_output": {},
  "structured_check": {},
  "docx": {
    "status": "skipped",
    "path": null,
    "check": null
  },
  "issues": []
}
```

### POST /api/fill-template

Request:

```json
{
  "run_dir": "agent-runs/2026-06-10-120000-W1",
  "template_path": "C:/Users/win/Desktop/template.docx",
  "llm_map": false
}
```

Response:

```json
{
  "status": "success",
  "output_path": "agent-runs/2026-06-10-120000-W1/filled_template.docx",
  "report_path": "agent-runs/2026-06-10-120000-W1/template_fill_report.json",
  "report": {
    "status": "PASS",
    "filled_fields": [],
    "unfilled_fields": [],
    "issues": []
  }
}
```

## Error Handling

The UI should show errors in the relevant area:

- Missing input: bottom input panel.
- Missing `.env` or API failure: run status and center check tab.
- No structured JSON available: right template panel.
- DOCX parse/fill failure: right template report.
- Validation warning: center check tab.

Errors should include a short human-readable message and the local path of any diagnostic JSON file when available.

The UI should never display the API key.

## Privacy And Safety Boundaries

The workbench is local and may handle sensitive counseling material.

Rules:

- Generated run folders remain under `agent-runs/`, which is ignored by git.
- The UI must not send data anywhere except the configured model API call already performed by the runner.
- API keys must not appear in logs, responses, HTML, or metadata.
- Boundary text from the agent output remains visible in the result panes.
- W1 default output must remain a pre-intake guide unless the user clearly asks to summarize completed initial interview material.
- The UI must not present risk checks as final clinical risk decisions.

## Testing Strategy

Unit tests:

- API request validation.
- Successful run with mocked agent runner.
- Failed run with mocked API error.
- Template fill endpoint with a fixture DOCX and structured JSON.
- File-serving path guard rejects paths outside approved output directories.

Integration smoke tests:

- Start local server.
- Open the workbench.
- Select W1, enter sample input, run with mocked or dry-run mode.
- Confirm result panes populate.
- Confirm template panel stays disabled until structured JSON exists.

Manual test:

- Run a real DeepSeek W1/W2/W3 sample.
- Render fixed DOCX.
- Fill a known local template and inspect the report.

## Acceptance Criteria

Implemented when:

- A local server command starts the workbench.
- The browser opens a single workbench screen with left, center, bottom, and right regions.
- W1/W2/W3 can be selected explicitly.
- A run can be executed from the UI.
- Markdown output, structured JSON, and validation results appear in the center area.
- Fixed DOCX rendering can be triggered when structured JSON exists.
- Template filling can be triggered when structured JSON and a DOCX template are available.
- Generated file paths are visible and usable.
- Tests cover endpoint behavior and path safety.
- Full existing Python test suite still passes.

## Future Extensions

Possible later work:

- React or Next.js product UI once workflow contracts stabilize.
- Case list and persistent local project storage.
- Audio transcription input.
- Template preview and editable field mapping table.
- Model-provider selector.
- Safer production deployment with authentication and encrypted storage.
