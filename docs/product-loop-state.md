# Product Loop State

Last updated: 2026-06-22

This file is the durable handoff state for autonomous product iterations. Future automation runs should read this file before planning. It exists so the project can continue from repository state instead of relying on chat context.

## Product Objective

Build a market-validation-ready web product for a counselor assistant agent.

The product is not just a generic web app. The core value is a counselor-facing agent that can understand raw counselor materials, route the user's intent, produce structured clinical-assistant outputs, use RAG-backed professional boundaries, generate editable documents, and preserve privacy/ethics constraints.

## Current Product Snapshot

- Repository: `C:\Users\win\Documents\Codex\2026-05-15\agent`
- Main branch status at last check: local `main` was ahead of `origin/main` by 20 commits.
- Hosted product URL: `https://counselor-agent-coze-api.onrender.com`
- Hosted health endpoint previously returned: `{"status":"ok"}`
- Current implementation shape:
  - Python backend / API service under `scripts/`
  - Deployable web workbench under `web-workbench/`
  - RAG source cards and retrieval map under `rag/`
  - Eval prompts/results under `eval-prompts/` and `eval-results/`
  - Local workbench runtime data under `workbench-data/` and `agent-runs/`; keep these out of git unless there is an explicit fixture need.

## Loop Operating Rules

Automation should continue from this file, not restart from a blank plan.

1. Prefer P0 agent capabilities over generic product polish.
2. Pick exactly one unfinished P0 capability per run unless all P0 items are complete or blocked.
3. Do not prioritize password changes, cosmetic UI tweaks, settings pages, or account-management polish unless they directly unblock a P0/P1 capability.
4. For model-behavior changes, update prompts/schemas/evals and run a real or fixture-backed eval. Use DeepSeek only through configured environment variables; never commit API keys.
5. For product behavior changes, update backend, frontend, tests, and docs together when needed.
6. Preserve privacy and ethics boundaries: do not ask users to enter direct identifiers in test data; do not produce diagnosis or final risk classification; keep risk changes separately documented.
7. After each run, update this file with the capability worked on, changes made, tests/evals run, remaining gaps, and next recommended capability.
8. Commit coherent changes after tests pass. Do not commit secrets, local runtime data, uploaded client documents, or generated private outputs.

## Definition Of Done For A Capability

A capability is not complete just because a prompt exists. It is considered productized only when it has:

- intent routing or a clear user-facing entry without exposing internal workflow codes as the main UX
- backend/API support
- prompt/schema/retrieval logic when model behavior is involved
- web workbench integration where relevant
- at least one automated test or eval fixture
- risk/privacy/ethics boundary handling
- documentation in this file

## Current Capability Backlog

| Priority | Capability | Status | Evidence | Next Step |
|---|---|---|---|---|
| P0 | Intent recognition across counselor tasks | partial | web workbench + Coze API now default to auto-routing, return route metadata, and cover mixed-intent eval cases W1-004/W2-004/W3-004/W4-002/W5-002/W6-002 | extend bilingual ambiguity coverage and verify the hosted deployment uses the new AUTO contract |
| P0 | W1 initial interview preparation guide | partial | workflow/eval exists | ensure UX distinguishes pre-interview question guide from post-interview summary |
| P0 | W1 initial interview summary into fixed template | partial | template filling prototype and W1 logic exist | strengthen raw-note-to-template mapping and missing-field prompts |
| P0 | W2 case background organization with BPS | partial | docs/eval/RAG structure exists | productize dedicated structured output and front-end rendering |
| P0 | W3 session summary and counseling record | partial | eval exists; risk-change section supported | strengthen crisis/risk-change handling and SOAP/DAP/BIRP variants |
| P0 | W4 case conceptualization by theory/framework | shipped partial | `W4` shipped in runner/web/RAG/eval | add more framework-specific eval cases and RAG cards |
| P0 | W5 bounded next-session plan | shipped partial | `W5` shipped in runner/web/RAG/eval | add framework-specific evals and hosted verification |
| P0 | Counseling roadmap / multi-session plan | shipped partial | `W6` shipped in runner/web/RAG/eval | add more framework-specific roadmap evals and hosted verification |
| P0 | RAG-backed ethics/risk/documentation retrieval | partial | chunks/map and validation scripts exist | expand retrieval eval matrix and failure tests |
| P0 | Theory-specific RAG support | partial | initial W4 support exists | add CBT/humanistic/psychodynamic/integrative source cards and routing |
| P0 | Word template understanding and filling | partial | prototype exists | make model-assisted section mapping reliable with merge/replace policy |
| P0 | Eval automation across workflows | partial | eval builder and cleaners exist | broaden bilingual rubric coverage and generate failure-reason reports |
| P1 | Case workspace/history | shipped partial | web workbench case history exists | verify privacy-safe deletion/export flows |
| P1 | File upload/download and docx export | partial | render_docx and template flow exist | improve UX for template upload, generated output, and error reporting |
| P1 | Audit log and data governance controls | partial | workbench run log and governance controls exist | confirm user-facing privacy copy and retention behavior |
| P1 | Hosted deployment diagnostics | partial | hosted smoke/health tests exist | run after pushing latest local commits |
| P2 | Minimal high-end web UX | partial | liquid-style workbench exists | continue only when it improves core workflow usability |
| P3 | Generic account settings | partial | password rotation exists | defer unless required for deployment validation |

## Recently Completed

### Intent Recognition Across Counselor Tasks

- Extended the product-facing router so the web workbench and Coze wrapper both use plain-language automatic routing instead of relying on explicit workflow ids.
- Added route metadata to API responses:
  - `detected_workflow`
  - `requested_workflow`
  - `route_status`
  - `route_notice`
  - `routing_candidates`
- Added a visible `Intent route` summary card in the web workbench so pilot users can see how the agent interpreted a request without exposing internal workflow buttons as the primary UX.
- Tightened mixed-intent handling for:
  - W1 pre-interview guide vs W3 post-interview record language
  - W5 single next-session planning vs W6 multi-session roadmap requests
- Expanded retrieval-backed eval coverage with:
  - `W1-004`
  - `W2-004`
  - `W3-004`
  - `W4-002`
  - `W5-002`
  - `W6-002`
- Regenerated `eval-prompts/manifest.json` so the new ambiguity cases are available to the DeepSeek eval runner.

### W4 Case Conceptualization

- Added framework-based case conceptualization workflow.
- Integrated runner, web workbench, RAG/eval support.
- Needs more per-framework live evals.

### W5 Next-Session Planning

- Completed an end-to-end bounded next-session planning workflow across:
  - `scripts/run_agent.py`
  - `scripts/run-retrieval.ps1`
  - `scripts/web_workbench.py`
  - `scripts/coze_api_server.py`
  - `scripts/render_docx.py`
  - `scripts/hosted_smoke.py`
  - `web-workbench/app.js`
  - `web-workbench/index.html`
  - `rag/next-session-planning/`
  - `rag/retrieval-map.v0.1.json`
- Added eval prompt `W5-001`.
- Added bilingual W5 clean/rubric checks.

### W6 Counseling Roadmap

- Completed an end-to-end bounded counseling roadmap workflow across:
  - `scripts/run_agent.py`
  - `scripts/run-retrieval.ps1`
  - `scripts/web_workbench.py`
  - `scripts/coze_api_server.py`
  - `scripts/render_docx.py`
  - `scripts/validate-rag.ps1`
  - `web-workbench/app.js`
  - `web-workbench/index.html`
  - `rag/roadmap-planning/`
  - `rag/retrieval-map.v0.1.json`
- Added eval prompt `W6-001`.
- Added bilingual W6 clean/rubric checks.
- Regenerated `eval-prompts/manifest.json` so retrieval-backed eval assets now include W6.

## Tests And Evals Recently Run

This run successfully completed:

- `python -m unittest scripts.test_web_workbench.WebWorkbenchTest.test_static_index_has_valid_title_markup scripts.test_web_workbench.WebWorkbenchTest.test_detect_workflow_details_marks_mixed_signal_when_roadmap_request_mentions_next_session scripts.test_web_workbench.WebWorkbenchTest.test_handle_run_auto_detects_workflow`
- `python -m unittest scripts.test_coze_api_server.CozeApiServerTest.test_openapi_spec_contains_two_tool_operations scripts.test_coze_api_server.CozeApiServerTest.test_build_run_workflow_response_includes_answer_and_docx_artifact scripts.test_coze_api_server.CozeApiServerTest.test_handle_coze_run_workflow_defaults_to_auto_routing`
- `python -m unittest scripts.test_web_workbench scripts.test_coze_api_server scripts.test_run_retrieval scripts.test_build_workflow_eval_prompts`
- `python scripts/build_workflow_eval_prompts.py`
- `python scripts/run_model_eval.py --ids W1-004,W2-004,W3-004,W4-002,W5-002,W6-002`
- `python scripts/clean_eval_outputs.py --result-dir eval-results/api --clean-dir eval-results/api/clean`

The earlier loop state had also recorded:

- `python scripts/test_run_agent.py`
- `python scripts/test_run_retrieval.py`
- `python scripts/test_web_workbench.py`
- `python scripts/test_clean_eval_outputs.py`
- `python scripts/test_render_docx.py`
- `python scripts/test_coze_api_server.py`
- `python scripts/test_hosted_smoke.py`
- `python scripts/test_build_workflow_eval_prompts.py`
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/validate-rag.ps1 -Json`
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-retrieval.ps1 -Query "Create a CBT next-session plan for this de-identified case." -Json`
- `python scripts/run_model_eval.py --ids W5-001`
- `python scripts/clean_eval_outputs.py`

Before deployment, rerun the relevant subset plus hosted smoke tests after pushing.

## Remaining Product Gaps

The bounded counseling roadmap capability now exists as `W6`, but it still needs more framework-specific eval depth and hosted verification before it can be treated as fully hardened.

Other important gaps:

- W1 needs clearer separation between:
  - pre-interview information collection guide
  - post-interview fixed-template summary
- Word template filling still needs stronger model-assisted mapping and handling of prefilled content.
- RAG coverage should be expanded for theory-specific conceptualization and roadmap planning.
- Eval coverage should continue expanding bilingual mixed-intent and framework-specific cases, especially for hosted validation.
- Latest local commits must be pushed and redeployed before online validation can be considered current.

## Next Recommended Capability

Improve `W1 initial interview summary into fixed template` as the next P0 capability.

Recommended scope:

- Accept raw first-interview notes and reliably map them into the fixed W1 initial interview template.
- Strengthen missing-field prompts so the output separates known facts, unclear facts, and follow-up questions.
- Reuse the improved intent routing so plain-language requests for "first interview notes" land on the summary/template path instead of the pre-interview guide.
- Add at least one automated regression test and one DeepSeek eval case focused on note-to-template transformation with risk/privacy boundaries intact.

## Deployment Readiness Notes

Do not claim deployment-ready until:

- `git status` is clean except allowed ignored runtime files.
- Tests for changed areas pass.
- Latest commits are pushed to the remote.
- Render deployment completes.
- Hosted health and at least one hosted workflow smoke test pass.
- No secrets or local sensitive runtime data are committed.
