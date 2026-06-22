# Product Loop State

Last updated: 2026-06-23

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
| P0 | W1 initial interview summary into fixed template | shipped partial | W1 runner now detects intake-prep vs initial-interview-summary mode, switches the structured contract to the fixed summary template, persists `w1_mode`, and returns it through the web workbench with live eval `W1-005` passing | strengthen structured validation coverage and verify the hosted deployment uses the new summary-mode contract |
| P0 | W2 case background organization with BPS | shipped partial | dedicated BPS structure, AUTO routing, DOCX rendering, and live eval `W2-005` now ship in runner/web/eval | verify hosted deployment and extend uploaded-template fill alignment |
| P0 | W3 session summary and counseling record | shipped partial | generic + SOAP + DAP structured paths, risk-change documentation, DOCX/template mapping, and live eval `W3-005` now ship in runner/web/eval | add BIRP-specific coverage and hosted verification |
| P0 | W4 case conceptualization by theory/framework | shipped partial | `W4` shipped in runner/web/RAG/eval and now includes humanistic + psychodynamic retrieval-backed boundary coverage (`W4-002`, `W4-003`) | add more framework-specific source cards and hosted verification |
| P0 | W5 bounded next-session plan | shipped partial | `W5` shipped in runner/web/RAG/eval and now includes psychodynamic boundary coverage (`W5-003`) | verify hosted deployment and continue theory-specific source-card expansion |
| P0 | Counseling roadmap / multi-session plan | shipped partial | `W6` shipped in runner/web/RAG/eval and now includes humanistic roadmap coverage (`W6-003`) | add more framework-specific roadmap source cards and hosted verification |
| P0 | RAG-backed ethics/risk/documentation retrieval | shipped partial | runner now validates retrieval coverage before model calls, the retrieval selector locks confidentiality/risk/documentation chunk mixes, and eval coverage now includes `W1-006`, `W3-006`, `W4-003`, `W5-003`, and `W6-003` with live `W5-003` passing | expand theory-specific source cards and run hosted retrieval smoke tests |
| P0 | Theory-specific RAG support | partial | initial W4 support exists | add CBT/humanistic/psychodynamic/integrative source cards and routing |
| P0 | Word template understanding and filling | partial | web workbench now supports guarded LLM-assisted structured template mapping, dedicated template-fill eval `TF-001` ships, and DeepSeek-backed structured-template mapping passes on a real fixture | expand W1/W2 template-label coverage and run hosted template smoke after deployment |
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

## This Run: Word Template Understanding And Filling

Capability worked on:

- `Word template understanding and filling`, specifically the model-assisted mapping path for structured template fill inside the shipped web product.

What changed:

- Added a shared structured-template helper in [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/fill_docx_template.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/fill_docx_template.py>) that:
  - builds deterministic slot mappings from `structured_output.json`
  - runs DeepSeek only on unresolved slots
  - fills the DOCX deterministically from the reviewed mapping
  - writes `template_mapping.json` plus `llm_status` back into the final report
- Tightened the LLM mapping prompt with explicit safe guidance that common counselor template labels such as `咨询目标`, `后续目标`, and `后续计划` can map to bounded follow-up fields like `next_session_focus` or `recommended_focus` when the structured source supports that interpretation.
- Exposed the guarded model-assisted mapping path through the web workbench in:
  - [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/web_workbench.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/web_workbench.py>)
  - [`/Users/win/Documents/Codex/2026-05-15/agent/web-workbench/index.html`](</Users/win/Documents/Codex/2026-05-15/agent/web-workbench/index.html>)
  - [`/Users/win/Documents/Codex/2026-05-15/agent/web-workbench/app.js`](</Users/win/Documents/Codex/2026-05-15/agent/web-workbench/app.js>)
  so counselors can keep structured fill as the primary path while enabling model assistance only for unfamiliar template labels.
- Added dedicated template-fill eval automation:
  - eval fixture manifest [`/Users/win/Documents/Codex/2026-05-15/agent/eval-prompts/template-fill-manifest.json`](</Users/win/Documents/Codex/2026-05-15/agent/eval-prompts/template-fill-manifest.json>)
  - fixture assets under [`/Users/win/Documents/Codex/2026-05-15/agent/eval-prompts/template-fill`](</Users/win/Documents/Codex/2026-05-15/agent/eval-prompts/template-fill>)
  - DeepSeek-backed runner [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/run_template_fill_eval.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/run_template_fill_eval.py>)
- Added regression coverage in:
  - [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/test_fill_docx_template.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/test_fill_docx_template.py>)
  - [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/test_web_workbench.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/test_web_workbench.py>)
  - [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/test_run_template_fill_eval.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/test_run_template_fill_eval.py>)

Tests and evals run:

- `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_fill_docx_template scripts.test_web_workbench scripts.test_run_template_fill_eval`
- `$env:PYTHONPATH='scripts'; python -m unittest discover -s scripts -p "test_*.py"`
- `$env:PYTHONPATH='scripts'; python scripts/run_template_fill_eval.py --ids TF-001`

Outcome:

- The shipped web product now exposes the guarded model-assisted mapping path for structured template filling instead of leaving it trapped in the CLI-only workflow.
- A dedicated real-template eval fixture now exists for this capability, and the live DeepSeek-backed run for `TF-001` passed after tightening the mapping prompt for common counselor planning labels.

Remaining gaps:

- The structured-template helper still needs broader alias coverage for W1 intake-summary and W2 biopsychosocial templates beyond the initial planning-label fix.
- Hosted deployment verification is still stale until the latest local commits are pushed and the public Render URL is smoke-tested with template upload + structured fill.
- Raw-material template drafting remains separate from structured fill; template understanding is stronger, but the overall capability is still partial until more real counselor template shapes are covered.

## Next Recommended Capability

Improve `W1 initial interview summary into fixed template` as the next P0 capability.

Recommended scope:

- Use the stronger template-mapping layer to turn raw initial interview notes into the fixed intake summary structure with explicit known facts, unclear/missing facts, and follow-up questions.
- Add missing-field prompt behavior for incomplete intake notes instead of leaving generic blanks.
- Add at least one live DeepSeek-backed eval for this fixed-template W1 summary path.

## This Run: W1 Initial Interview Summary Into Fixed Template

Capability worked on:

- `W1 initial interview summary into fixed template`, specifically the productized summary-mode path for completed intake notes.

What changed:

- Added shared W1 mode detection in [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/run_agent.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/run_agent.py>) so the runner can distinguish `intake_prep` from `initial_interview_summary`.
- Switched the structured W1 prompt contract to the fixed initial interview summary template when summary mode is detected, instead of always showing the generic intake-form contract first.
- Tightened the W1 summary prompt so every section must explicitly separate `known_facts`, `unclear_or_missing`, and `follow_up_questions`, and so empty sections still record a concise missing-information item instead of collapsing to vague blanks.
- Persisted `w1_mode` into runner metadata for dry runs, successful runs, and API-error runs so downstream product surfaces can distinguish the W1 mode safely.
- Exposed `w1_mode` through the web workbench in [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/web_workbench.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/web_workbench.py>) so AUTO routing and `/api/run` responses keep the intake-summary interpretation visible to the user instead of silently flattening it into generic W1.
- Added regression coverage in:
  - [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/test_run_agent.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/test_run_agent.py>)
  - [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/test_web_workbench.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/test_web_workbench.py>)

Tests and evals run:

- `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_run_agent.RunAgentTest.test_detect_w1_mode_distinguishes_prep_vs_summary_requests scripts.test_run_agent.RunAgentTest.test_build_prompt_package_w1_summary_includes_section_specific_missing_field_guidance`
- `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_web_workbench.WebWorkbenchTest.test_detect_workflow_details_marks_mixed_signal_when_initial_interview_summary_mentions_notes scripts.test_web_workbench.WebWorkbenchTest.test_handle_run_returns_w1_summary_mode_metadata`
- `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_run_agent scripts.test_web_workbench`
- `$env:PYTHONPATH='scripts'; python -m unittest discover -s scripts -p "test_*.py"`
- `$env:PYTHONPATH='scripts'; python scripts/run_model_eval.py --ids W1-005` initially timed out at the default 120-second DeepSeek limit but still produced partial output.
- `$env:PYTHONPATH='scripts'; $env:DEEPSEEK_TIMEOUT_SECONDS='240'; python scripts/run_model_eval.py --ids W1-005`

Outcome:

- The shipped product now has a productized W1 summary mode rather than only a loosely implied prompt branch.
- AUTO routing still lands on W1 for completed intake-note summary requests, but the runner and API now preserve the narrower `initial_interview_summary` mode so counselors can distinguish it from pre-interview preparation.
- The live DeepSeek-backed eval `W1-005` passed after increasing the request timeout to 240 seconds for this longer prompt.

Remaining gaps:

- The W1 summary path still relies on prompt compliance rather than a dedicated post-run structural normalizer for raw-note mapping quality.
- Hosted deployment verification is still stale until the latest local commits are pushed and the public Render URL is smoke-tested with an AUTO-routed W1 summary request.
- The workbench currently exposes W1 mode via route metadata, but there is not yet a dedicated W1 summary-specific result card or export affordance beyond the standard run payload.

## This Run: RAG-Backed Ethics/Risk/Documentation Retrieval

Capability worked on:

- `RAG-backed ethics/risk/documentation retrieval`, specifically retrieval coverage validation plus adjacent-workflow boundary selection for theory-specific and confidentiality-sensitive requests.

What changed:

- Added retrieval coverage guards in [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/run_agent.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/run_agent.py>) so `run_agent_once` now fails before any model call when a workflow's retrieved chunk set is missing required section classes such as `ethics-risk`, `session-notes`, `theory-frameworks`, `next-session-planning`, or `roadmap-planning`.
- Extended chunk metadata indexing in the same runner so coverage checks use `rag_section` plus workflow-specific anchor chunks like `session-notes-risk-change-documentation-001`, `next-session-planning-bounded-next-session-plan-001`, and `ethics-risk-cps-professional-boundary-001`.
- Hardened the retrieval selector in [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/run-retrieval.ps1`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/run-retrieval.ps1>) by:
  - recognizing English confidentiality/documentation boundary wording for W3
  - explicitly adding confidentiality chunks when the request mentions record access or informed-consent boundaries
  - tightening the W5 single-session wording so psychodynamic next-session planning no longer falls into W3 just because it says `session`
- Expanded retrieval-backed eval coverage in [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/build_workflow_eval_prompts.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/build_workflow_eval_prompts.py>) with:
  - `W1-006` intake confidentiality + suicide-follow-up boundary
  - `W3-006` session-note confidentiality/documentation boundary
  - `W4-003` humanistic conceptualization boundary
  - `W5-003` psychodynamic single-session planning boundary
  - `W6-003` humanistic roadmap boundary
- Regenerated the committed eval assets under [`/Users/win/Documents/Codex/2026-05-15/agent/eval-prompts`](</Users/win/Documents/Codex/2026-05-15/agent/eval-prompts>) so the manifest and prompt files now reflect the corrected retrieval routes and chunk sets.
- Added regression coverage in:
  - [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/test_run_agent.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/test_run_agent.py>)
  - [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/test_run_retrieval.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/test_run_retrieval.py>)
  - [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/test_build_workflow_eval_prompts.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/test_build_workflow_eval_prompts.py>)

Tests and evals run:

- `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_run_agent scripts.test_build_workflow_eval_prompts scripts.test_run_retrieval`
- `$env:PYTHONPATH='scripts'; python -m unittest discover -s scripts -p "test_*.py"`
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/validate-rag.ps1 -Json`
- `$env:PYTHONPATH='scripts'; python scripts/build_workflow_eval_prompts.py`
- `$env:PYTHONPATH='scripts'; $env:DEEPSEEK_TIMEOUT_SECONDS='240'; python scripts/run_model_eval.py --ids W5-003`

Outcome:

- Retrieval failures that previously would have reached the model with an incomplete evidence set are now blocked at the runner boundary.
- W3 confidentiality/documentation requests now retrieve the intended record-keeping and informed-consent chunks instead of silently falling back to the generic session-note bundle.
- The new psychodynamic W5 boundary case now routes to W5 correctly, and the live DeepSeek-backed eval `W5-003` passed.

Remaining gaps:

- Hosted deployment verification is still stale until the latest local commits are pushed and the public Render URL is smoke-tested on at least one confidentiality-sensitive W3 request and one theory-specific W5/W6 request.
- Theory-specific RAG support is still partial because the current framework cards cover the main CBT/humanistic/psychodynamic/integrative concepts but not a broader reference set or richer per-framework subtopics.
- Eval automation is broader now, but the rubric layer still needs more bilingual failure-reason reporting instead of only pass/fail summary output.

## Next Recommended Capability

Improve `Theory-specific RAG support` as the next P0 capability.

Recommended scope:

- Expand the theory-framework source cards and retrieval-map routes for CBT, humanistic, psychodynamic, and integrative work beyond the current single-card-per-framework baseline.
- Add source-backed evals that distinguish conceptualization vs next-session planning vs roadmap language within each framework.
- Run hosted retrieval smokes after deployment to confirm the public product is using the updated framework-aware retrieval set.

## Deployment Readiness Notes

Do not claim deployment-ready until:

- `git status` is clean except allowed ignored runtime files.
- Tests for changed areas pass.
- Latest commits are pushed to the remote.
- Render deployment completes.
- Hosted health and at least one hosted workflow smoke test pass.
- No secrets or local sensitive runtime data are committed.
