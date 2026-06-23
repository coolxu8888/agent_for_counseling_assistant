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
| P0 | Intent recognition across counselor tasks | shipped partial | web workbench AUTO routing now also catches Chinese-first W1-vs-W3 summary requests that negate `BIRP` or `咨询记录`, retrieval preserves a dedicated W1 `初始访谈材料总结` intent for that boundary, eval prompt generation/scoring include `W1-011`, and committed fixtures now cover this mixed-signal route | verify the hosted deployment uses the new AUTO contract, confirm the W1 summary route metadata end to end, and extend more Chinese-heavy `not X, do Y` route fixtures plus hosted smoke coverage |
| P0 | W1 initial interview preparation guide | shipped partial | W1 now extracts partial intake clues, prefills the intake guide contract, exposes an explicit product-facing prep-mode summary, and passes live DeepSeek eval `W1-007` plus a real structured run | extend bilingual clue extraction coverage and verify the hosted deployment shows the new prep-mode summary |
| P0 | W1 initial interview summary into fixed template | shipped partial | W1 now normalizes collapsed summary sections back into the fixed template, auto-fills missing split fields, exposes a dedicated `W1 summary brief` in the workbench, and passes live DeepSeek evals `W1-005` and `W1-009` plus a real structured run with `structured_status=PASS` | verify the hosted deployment uses the new summary brief and broaden section-label normalization for more bilingual raw-note variants |
| P0 | W2 case background organization with BPS | shipped partial | dedicated BPS structure, AUTO routing, DOCX rendering, split-template alias coverage, and live evals `W2-005` plus `W2-006` now ship in runner/web/eval | verify hosted deployment and extend more real counselor template label coverage |
| P0 | W3 session summary and counseling record | shipped partial | generic + SOAP + DAP structured paths now also include product-facing BIRP record summaries, a dedicated BIRP demo, cleaner/eval coverage through `W3-007`, and existing risk-change documentation plus DOCX/template mapping | run a live DeepSeek `W3-007` eval when credentials are available and verify the hosted deployment |
| P0 | W4 case conceptualization by theory/framework | shipped partial | `W4` shipped in runner/web/RAG/eval and now includes humanistic + psychodynamic retrieval-backed boundary coverage (`W4-002`, `W4-003`) plus dedicated W5/W6 sister framework cards to keep conceptualization separate from planning retrieval | add more per-framework subtopic cards and hosted verification |
| P0 | W5 bounded next-session plan | shipped partial | `W5` shipped in runner/web/RAG/eval and now includes psychodynamic + integrative theory-specific planning retrieval coverage (`W5-003`, `W5-004`) with dedicated framework planning chunks | verify hosted deployment and extend more bilingual framework-routing coverage |
| P0 | Counseling roadmap / multi-session plan | shipped partial | `W6` shipped in runner/web/RAG/eval and now includes humanistic + psychodynamic roadmap retrieval coverage (`W6-003`, `W6-004`) with dedicated framework roadmap chunks | verify hosted deployment and extend more framework-specific roadmap source cards |
| P0 | RAG-backed ethics/risk/documentation retrieval | shipped partial | runner now validates retrieval coverage before model calls, the retrieval selector locks confidentiality/risk/documentation chunk mixes, and eval coverage now includes `W1-006`, `W3-006`, `W4-003`, `W5-003`, and `W6-003` with live `W5-003` passing | expand theory-specific source cards and run hosted retrieval smoke tests |
| P0 | Theory-specific RAG support | shipped partial | dedicated CBT/humanistic/psychodynamic/integrative planning + roadmap source cards now back W5/W6 retrieval, and live DeepSeek evals `W5-004` + `W6-004` passed | add richer per-framework subtopics, bilingual route cues, and hosted retrieval verification |
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

## This Run: W1 Initial Interview Preparation Guide

Capability worked on:

- `W1 initial interview preparation guide`, specifically the productized intake-prep path for counselors who already know part of the case background before the first interview.

What changed:

- Added partial-clue extraction in [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/run_agent.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/run_agent.py>) so W1 intake-prep requests now capture usable known facts such as sleep issues, academic pressure, roommate conflict, and passive risk language before the model drafts the guide.
- Tightened the W1 intake-prep prompt contract so the model must prefill matching fields from the extracted clues, expose those clues at the top level as `known_clues`, and record field-level `known_clues_used` traces instead of falling back to an empty generic questionnaire.
- Hardened W1 structured validation so intake-prep outputs fail if known clues are present but none of the fields trace them, while risk-section detection now accepts section ids and risk-signal flags instead of relying only on heading text.
- Exposed a product-facing W1 mode summary in:
  - [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/web_workbench.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/web_workbench.py>)
  - [`/Users/win/Documents/Codex/2026-05-15/agent/web-workbench/index.html`](</Users/win/Documents/Codex/2026-05-15/agent/web-workbench/index.html>)
  - [`/Users/win/Documents/Codex/2026-05-15/agent/web-workbench/app.js`](</Users/win/Documents/Codex/2026-05-15/agent/web-workbench/app.js>)
  so counselors can clearly see when the agent interpreted a W1 run as `Initial interview prep` and which known clues were prefilled.
- Added eval coverage for this behavior in [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/build_workflow_eval_prompts.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/build_workflow_eval_prompts.py>) with new prompt `W1-007` (`partial-clue-prefill-intake-guide`) and regenerated the committed eval manifest.
- Added regression coverage in:
  - [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/test_run_agent.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/test_run_agent.py>)
  - [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/test_web_workbench.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/test_web_workbench.py>)
  - [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/test_build_workflow_eval_prompts.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/test_build_workflow_eval_prompts.py>)

Tests and evals run:

- `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_run_agent.RunAgentTest.test_extract_w1_intake_clues_captures_partial_known_risk_and_context scripts.test_run_agent.RunAgentTest.test_build_prompt_package_w1_prep_includes_known_clue_prefill_guidance scripts.test_run_agent.RunAgentTest.test_validate_structured_output_w1_requires_prefill_trace_when_known_clues_exist scripts.test_web_workbench.WebWorkbenchTest.test_handle_run_returns_w1_prep_mode_summary_for_product_ui`
- `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_run_agent scripts.test_web_workbench scripts.test_build_workflow_eval_prompts`
- `$env:PYTHONPATH='scripts'; python -m unittest discover -s scripts -p "test_*.py"`
- `$env:PYTHONPATH='scripts'; python scripts/build_workflow_eval_prompts.py`
- `$env:PYTHONPATH='scripts'; $env:DEEPSEEK_TIMEOUT_SECONDS='240'; python scripts/run_model_eval.py --ids W1-007`
- `$env:PYTHONPATH='scripts'; $env:DEEPSEEK_TIMEOUT_SECONDS='240'; python scripts/run_agent.py --workflow W1 --input "<partial-clue intake-prep request>" --structured`

Outcome:

- The shipped product now treats W1 intake preparation as a real agent capability instead of a generic questionnaire prompt branch.
- Real DeepSeek usage now prefills the intake guide from counselor-supplied clues and preserves those traces through structured validation.
- The product UI/API now distinguishes W1 prep from W1 summary in a counselor-visible way, which closes the prior gap where W1 mode differences were only visible in raw metadata.

Remaining gaps:

- Clue extraction is still heuristic and needs broader bilingual coverage for mixed Chinese/English intake requests.
- Hosted deployment verification is still stale until the latest local commits are pushed and the public Render URL is smoke-tested with an AUTO-routed W1 prep request.
- The W1 prep result is clearer in the workbench summary, but DOCX/template-fill alignment for intake-prep guides still needs broader label coverage.

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

## This Run: Intent Recognition Across Counselor Tasks

Capability worked on:

- `Intent recognition across counselor tasks`, specifically the Chinese-first W1-vs-W3 boundary where counselors ask for a fixed initial-interview summary from `首访原始记录` while explicitly negating `SOAP` or `session note`.

What changed:

- Extended negated-record detection in [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\web_workbench.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\web_workbench.py) so AUTO routing now treats `SOAP` and `DAP` as first-class record-format cues in the same Chinese-heavy `not X, do Y` family that already handled `BIRP`.
- Verified the product-side router keeps `请根据首访原始记录整理固定模板总结，保留风险变化线索，不要写成SOAP或session note。` inside `W1` with `initial_interview_summary` mode and `mixed_signals` status instead of drifting into `W3`.
- Brought retrieval into parity in [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\run-retrieval.ps1`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\run-retrieval.ps1) by extending the same negated-record cue family to `SOAP` / `DAP`, so the retrieval route preserves the dedicated W1 summary intent for this boundary.
- Expanded eval coverage in [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\build_workflow_eval_prompts.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\build_workflow_eval_prompts.py) with `W1-012`, a Chinese-first W1 summary boundary case that negates `SOAP` while preserving bounded risk-change wording.
- Added scorer/rubric coverage for `W1-012` in [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\clean_eval_outputs.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\clean_eval_outputs.py) and regenerated committed eval assets under [`C:\Users\win\Documents\Codex\2026-05-15\agent\eval-prompts`](C:\Users\win\Documents\Codex\2026-05-15\agent\eval-prompts), including [`C:\Users\win\Documents\Codex\2026-05-15\agent\eval-prompts\W1-012-chinese-first-initial-interview-summary-soap-boundary.txt`](C:\Users\win\Documents\Codex\2026-05-15\agent\eval-prompts\W1-012-chinese-first-initial-interview-summary-soap-boundary.txt).
- Added regression coverage in:
  - [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_web_workbench.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_web_workbench.py)
  - [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_run_retrieval.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_run_retrieval.py)
  - [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_run_agent.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_run_agent.py)
  - [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_build_workflow_eval_prompts.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_build_workflow_eval_prompts.py)
  - [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_clean_eval_outputs.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_clean_eval_outputs.py)

Tests and evals run:

- `python -m unittest scripts.test_web_workbench.WebWorkbenchTest.test_detect_workflow_prefers_w1_for_chinese_first_summary_prompt_that_negates_soap scripts.test_run_retrieval.RunRetrievalTest.test_routes_chinese_first_summary_request_that_negates_soap_to_w1_summary_intent scripts.test_build_workflow_eval_prompts.BuildWorkflowEvalPromptsTest.test_evals_include_chinese_first_w1_summary_soap_boundary_case scripts.test_clean_eval_outputs.CleanEvalOutputsTest.test_w1_012_chinese_first_soap_boundary_rubric_accepts_bounded_summary_output`
- `$env:PYTHONPATH='scripts'; python scripts/build_workflow_eval_prompts.py`
- `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_run_agent scripts.test_web_workbench scripts.test_run_retrieval scripts.test_build_workflow_eval_prompts scripts.test_clean_eval_outputs` -> 207 tests passed.
- `$env:PYTHONPATH='scripts'; python -m unittest discover -s scripts -p "test_*.py"` -> 327 tests ran with 2 unrelated pre-existing template-fill failures in `scripts.test_fill_docx_template`; the intent-routing slice itself remained green.
- Live DeepSeek eval for `W1-012` was blocked on 2026-06-23 because `DEEPSEEK_API_KEY` was missing in the environment.

Outcome:

- The shipped AUTO router now keeps a Chinese-first `首访原始记录 / 固定模板总结 / 不要写成SOAP` request inside W1 summary mode instead of letting W3 dominate.
- Retrieval selection and the eval matrix now agree with the product router for both `BIRP` and `SOAP` negation boundaries, so this intent-recognition slice has frontend, retrieval, and scorer parity.
- `W1-012` makes the SOAP negation case durable in regression coverage rather than leaving it implied by broader W1 summary tests.

Remaining gaps:

- Hosted deployment verification is still stale until the latest local commits are pushed and the public Render URL is smoke-tested with a `W1-012`-style prompt that exercises AUTO route metadata plus retrieval-backed generation.
- There is still no live DeepSeek evidence for `W1-012` in this environment because model credentials were missing.
- Broader Chinese-heavy W1-vs-W3 phrasing around `DAP` and looser `固定模板` wording still needs more explicit route fixtures before intent recognition can be considered deployment-ready.

## Next Recommended Capability

Improve `W1 initial interview preparation guide` as the next P0 capability.

Recommended scope:

- Give the workbench a clearer product distinction between pre-interview intake-question guidance and post-interview W1 summary results instead of relying mostly on route metadata.
- Add one stronger eval or structured check for partially known intake clues so the prep guide consistently pre-fills known facts and only asks follow-up questions for missing material.
- Run one hosted AUTO-routed smoke after deployment to confirm the public product still selects the prep-guide path correctly.

## This Run: Theory-Specific RAG Support

Capability worked on:

- `Theory-specific RAG support`, specifically dedicated framework retrieval for W5 next-session planning and W6 counseling roadmaps so those workflows no longer reuse conceptualization-only theory cards.

What changed:

- Added eight new framework source cards under [`/Users/win/Documents/Codex/2026-05-15/agent/rag/theory-frameworks`](</Users/win/Documents/Codex/2026-05-15/agent/rag/theory-frameworks>) for:
  - CBT next-session planning
  - psychodynamic next-session planning
  - humanistic next-session planning
  - integrative next-session planning
  - CBT counseling roadmap
  - psychodynamic counseling roadmap
  - humanistic counseling roadmap
  - integrative counseling roadmap
- Updated [`/Users/win/Documents/Codex/2026-05-15/agent/rag/retrieval-map.v0.1.json`](</Users/win/Documents/Codex/2026-05-15/agent/rag/retrieval-map.v0.1.json>) so W5 and W6 theory-specific routes now pull the new planning/roadmap chunks instead of reusing conceptualization-only chunks.
- Extended [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/run-retrieval.ps1`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/run-retrieval.ps1>) so integrative W5 requests route to `Integrative next-session plan` instead of silently falling back to the generic route.
- Expanded eval coverage in [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/build_workflow_eval_prompts.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/build_workflow_eval_prompts.py>) with:
  - `W5-004` integrative next-session boundary
  - `W6-004` psychodynamic roadmap boundary
- Regenerated the committed eval assets in [`/Users/win/Documents/Codex/2026-05-15/agent/eval-prompts`](</Users/win/Documents/Codex/2026-05-15/agent/eval-prompts>) so the manifest and prompt packages now point to the new theory-specific retrieval chunks.
- Added regression coverage in:
  - [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/test_run_retrieval.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/test_run_retrieval.py>)
  - [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/test_build_workflow_eval_prompts.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/test_build_workflow_eval_prompts.py>)

Tests and evals run:

- `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_run_retrieval scripts.test_build_workflow_eval_prompts`
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/validate-rag.ps1 -Json`
- `$env:PYTHONPATH='scripts'; python scripts/build_workflow_eval_prompts.py`
- `$env:PYTHONPATH='scripts'; python -m unittest discover -s scripts -p "test_*.py"`
- `$env:PYTHONPATH='scripts'; $env:DEEPSEEK_TIMEOUT_SECONDS='240'; python scripts/run_model_eval.py --ids W5-004,W6-004`

Outcome:

- W5 and W6 now retrieve framework-specific planning/roadmap guidance rather than relying on conceptualization cards that were too coarse for session-plan and roadmap generation.
- Integrative next-session requests now route to an explicit integrative planning intent instead of generic fallback behavior.
- The new live DeepSeek-backed evals `W5-004` and `W6-004` both passed, giving real-model coverage for the expanded framework retrieval set.

Remaining gaps:

- Hosted deployment verification is still stale until the latest local commits are pushed and the public Render URL is smoke-tested on at least one W5 integrative request and one W6 psychodynamic roadmap request.
- Theory-specific RAG coverage is still partial because the new cards are workflow-level guidance cards, not yet richer per-framework subtopics such as alliance ruptures, readiness/pace, referral thresholds, or framework-specific risk-monitoring nuances.
- The bilingual routing matrix is stronger than before but still lighter for non-English framework phrasing beyond the current explicit keywords.

## This Run: Intent Recognition Across Counselor Tasks

Capability worked on:

- `Intent recognition across counselor tasks`, specifically mixed Chinese/English ambiguity handling plus product-facing route-explanation visibility for AUTO-routed requests.

What changed:

- Extended the weighted router in [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/web_workbench.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/web_workbench.py>) so bilingual boundary phrasing now better separates:
  - W1 fixed initial-interview summary vs W3 session-note wording
  - W5 single next-session planning vs W6 roadmap wording when the prompt explicitly says to plan only the next session and not a roadmap
- Added a compact `routing_reasons_summary` field in the same backend so AUTO-routed responses now return a counselor-readable explanation string built from the top candidate workflows instead of only raw regex reasons.
- Wired the explanation summary into the shipped workbench UI in [`/Users/win/Documents/Codex/2026-05-15/agent/web-workbench/app.js`](</Users/win/Documents/Codex/2026-05-15/agent/web-workbench/app.js>) so the existing `Intent route` card now shows both the route notice and the top-candidate summary.
- Expanded eval coverage in [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/build_workflow_eval_prompts.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/build_workflow_eval_prompts.py>) with new bilingual ambiguity case `W1-008` and regenerated the committed eval manifest/assets in [`/Users/win/Documents/Codex/2026-05-15/agent/eval-prompts`](</Users/win/Documents/Codex/2026-05-15/agent/eval-prompts>).
- Added regression coverage in:
  - [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/test_web_workbench.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/test_web_workbench.py>)
  - [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/test_build_workflow_eval_prompts.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/test_build_workflow_eval_prompts.py>)

Tests and evals run:

- `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_web_workbench.WebWorkbenchTest.test_detect_workflow_prefers_w1_for_bilingual_initial_interview_summary_prompt scripts.test_web_workbench.WebWorkbenchTest.test_detect_workflow_prefers_w5_for_bilingual_single_session_plan_prompt scripts.test_web_workbench.WebWorkbenchTest.test_handle_run_returns_route_explanation_summary_for_auto_route`
- `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_web_workbench scripts.test_build_workflow_eval_prompts`
- `$env:PYTHONPATH='scripts'; python scripts/build_workflow_eval_prompts.py`
- `$env:PYTHONPATH='scripts'; $env:DEEPSEEK_TIMEOUT_SECONDS='240'; python scripts/run_model_eval.py --ids W1-008`
- `$env:PYTHONPATH='scripts'; python -m unittest discover -s scripts -p "test_*.py"`

Outcome:

- AUTO routing is now less opaque in the shipped product because counselors can see a concise route explanation instead of only workflow labels or regex fragments.
- Mixed-language W1 summary prompts and bilingual W5-vs-W6 prompts now route more reliably in the local product surface, with dedicated regression coverage.
- The live DeepSeek-backed eval `W1-008` passed, giving real-model coverage for the new bilingual ambiguity case.

Remaining gaps:

- Hosted deployment verification is still stale until the latest local commits are pushed and the public Render URL is smoke-tested with a bilingual AUTO-routed request so the product-facing route summary can be confirmed end to end.
- Bilingual ambiguity coverage is stronger for W1 and W5/W6, but still lighter for mixed-language W3/W4 prompts and more varied negation patterns.
- Eval automation still reports route outcomes more clearly than before, but it does not yet produce dedicated failure-reason summaries across the whole bilingual routing matrix.

## This Run: W1 Initial Interview Summary Into Fixed Template

Capability worked on:

- `W1 initial interview summary into fixed template`, specifically the post-run normalization path for mixed-language intake notes that do not cleanly follow the fixed structured contract.

What changed:

- Added W1 summary normalization in [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/run_agent.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/run_agent.py>) so structured W1 summary outputs now:
  - map heading aliases such as `Main complaint` and Chinese risk headings back to canonical W1 section ids
  - recover `known_facts`, `unclear_or_missing`, and `follow_up_questions` from collapsed `content` blocks before validation
  - fill missing sections with bounded missing-information placeholders instead of failing because the model omitted split fields
- Tightened the W1 summary prompt in the same runner so the model is explicitly told to keep canonical section ids and not collapse a whole summary section into one content string.
- Normalized structured W1 summary JSON before validation and persistence, which means `structured_output.json` now stores the repaired fixed-template shape rather than only the raw model JSON.
- Added a dedicated workbench-facing W1 summary brief in:
  - [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/web_workbench.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/web_workbench.py>)
  - [`/Users/win/Documents/Codex/2026-05-15/agent/web-workbench/index.html`](</Users/win/Documents/Codex/2026-05-15/agent/web-workbench/index.html>)
  - [`/Users/win/Documents/Codex/2026-05-15/agent/web-workbench/app.js`](</Users/win/Documents/Codex/2026-05-15/agent/web-workbench/app.js>)
  so counselors can immediately review the main distress, risk highlight, priority follow-up, and biggest gap for W1 summary runs without opening raw JSON.
- Expanded eval coverage in [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/build_workflow_eval_prompts.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/build_workflow_eval_prompts.py>) with new mixed-language summary case `W1-009`, then regenerated the committed eval prompt assets.
- Added regression coverage in:
  - [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/test_run_agent.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/test_run_agent.py>)
  - [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/test_web_workbench.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/test_web_workbench.py>)
  - [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/test_build_workflow_eval_prompts.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/test_build_workflow_eval_prompts.py>)

Tests and evals run:

- `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_run_agent.RunAgentTest.test_normalize_structured_output_w1_summary_recovers_sections_from_content_and_aliases scripts.test_run_agent.RunAgentTest.test_run_agent_once_structured_w1_summary_normalizes_before_validation scripts.test_web_workbench.WebWorkbenchTest.test_handle_run_returns_w1_summary_mode_metadata`
- `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_run_agent scripts.test_web_workbench scripts.test_build_workflow_eval_prompts`
- `$env:PYTHONPATH='scripts'; python scripts/build_workflow_eval_prompts.py`
- `$env:PYTHONPATH='scripts'; python -m unittest discover -s scripts -p "test_*.py"`
- `$env:PYTHONPATH='scripts'; $env:DEEPSEEK_TIMEOUT_SECONDS='240'; python scripts/run_model_eval.py --ids W1-009`
- `$env:PYTHONPATH='scripts'; $env:DEEPSEEK_TIMEOUT_SECONDS='240'; python scripts/run_agent.py --workflow W1 --structured --input "<mixed-language completed first-interview notes>"`

Outcome:

- W1 summary mode no longer depends purely on prompt compliance for fixed-template section splits. Common collapsed-summary outputs are repaired before validation, which makes the structured contract materially more reliable for market validation.
- The shipped workbench now has a dedicated W1 summary brief, which closes the earlier product gap where counselors had to infer summary value from route metadata or open the raw JSON pane.
- Live DeepSeek validation passed on the new mixed-language case `W1-009`, and a real W1 structured run succeeded with `structured_status=PASS` in [`/Users/win/Documents/Codex/2026-05-15/agent/agent-runs/2026-06-23-073017-W1`](</Users/win/Documents/Codex/2026-05-15/agent/agent-runs/2026-06-23-073017-W1>).

Remaining gaps:

- The W1 normalizer currently covers canonical ids plus a narrow set of English/Chinese heading aliases; broader counselor shorthand variants still need to be mapped.
- Hosted deployment verification is still stale until the latest local commits are pushed and the public Render URL is smoke-tested with an AUTO-routed W1 summary request that exercises the new brief.
- The live run passed structural validation, but the rubric layer still returned `WARN`, so W1 summary quality checks remain less granular than the fixed-template shape checks.

## This Run: W2 Case Background Organization With BPS

Capability worked on:

- `W2 case background organization with BPS`, specifically uploaded-template alignment for split biopsychosocial fields plus a mixed-language routing/eval boundary case.

What changed:

- Extended the structured template source-map aliases in [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/fill_docx_template.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/fill_docx_template.py>) so W2 case-background outputs can deterministically fill more split template labels such as dimension-specific known facts, follow-up questions, risk follow-up questions, and recommended focus instead of collapsing into coarse case-overview matches.
- Added a retrieval-router guard in [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/run-retrieval.ps1`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/run-retrieval.ps1>) so mixed-language W2 prompts that say `not a session note` no longer misroute into W3 just because they contain the phrase `session note` in a negated boundary sentence.
- Expanded eval coverage in [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/build_workflow_eval_prompts.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/build_workflow_eval_prompts.py>) with `W2-006`, a mixed-language BPS case-background prompt that exercises bounded risk follow-up and the negated-session-note route boundary.
- Updated eval cleaning/rubric coverage in [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/clean_eval_outputs.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/clean_eval_outputs.py>) so `W2-006` is scored as a W2 case-background capability instead of being left outside the cleaner contract.
- Added regression coverage in:
  - [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/test_fill_docx_template.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/test_fill_docx_template.py>)
  - [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/test_run_retrieval.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/test_run_retrieval.py>)
  - [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/test_build_workflow_eval_prompts.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/test_build_workflow_eval_prompts.py>)
  - [`/Users/win/Documents/Codex/2026-05-15/agent/scripts/test_clean_eval_outputs.py`](</Users/win/Documents/Codex/2026-05-15/agent/scripts/test_clean_eval_outputs.py>)

Tests and evals run:

- `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_fill_docx_template scripts.test_build_workflow_eval_prompts scripts.test_clean_eval_outputs scripts.test_run_retrieval`
- `$env:PYTHONPATH='scripts'; python scripts/build_workflow_eval_prompts.py`
- `$env:PYTHONPATH='scripts'; python -m unittest discover -s scripts -p "test_*.py"`
- `$env:PYTHONPATH='scripts'; $env:DEEPSEEK_TIMEOUT_SECONDS='240'; python scripts/run_model_eval.py --ids W2-006`

Outcome:

- W2 mixed-language case-background prompts now stay on the W2 path even when they explicitly negate session-note formatting, which closes a real retrieval/eval misroute discovered during this run.
- Uploaded W2 template filling now has better deterministic coverage for split case-background sections instead of overusing coarse case-overview matches.
- The live DeepSeek-backed eval `W2-006` passed after the route fix, so this W2 slice now has real model coverage in addition to local regression tests.

Remaining gaps:

- Hosted deployment verification is still stale until the latest local commits are pushed and the public Render URL is smoke-tested with a W2 mixed-language request plus a W2 template-fill flow.
- Template alignment is stronger for split BPS/risk/focus labels, but it still needs more real counselor template synonyms beyond the current deterministic alias set.
- The shipped workbench template-fill UX is unchanged this run; counselors can use the stronger mapping path now, but the UI still does not explain W2-specific alias coverage or unresolved slot reasons as clearly as it could.

## This Run: W3 Session Summary And Counseling Record

Capability worked on:

- `W3 session summary and counseling record`, specifically productizing BIRP-specific record handling instead of leaving W3 as generic/SOAP/DAP-only in the shipped product surface and eval matrix.

What changed:

- Added a dedicated product-facing W3 record brief in [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\web_workbench.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\web_workbench.py), [`C:\Users\win\Documents\Codex\2026-05-15\agent\web-workbench\index.html`](C:\Users\win\Documents\Codex\2026-05-15\agent\web-workbench\index.html), and [`C:\Users\win\Documents\Codex\2026-05-15\agent\web-workbench\app.js`](C:\Users\win\Documents\Codex\2026-05-15\agent\web-workbench\app.js) so W3 runs now expose record-format, behavior/data highlight, intervention highlight, risk highlight, and next-session focus directly in the workbench without opening raw JSON.
- Added a dedicated `W3 Demo: BIRP record` scenario in the backend and frontend demo catalogs so counselors can trigger a mixed-language BIRP counseling-record flow from the shipped product instead of relying on ad hoc prompts.
- Expanded eval coverage in [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\build_workflow_eval_prompts.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\build_workflow_eval_prompts.py) with `W3-007`, a mixed-language BIRP record case that requires bounded risk-change documentation plus confidentiality-boundary handling.
- Updated eval cleaning/rubric coverage in [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\clean_eval_outputs.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\clean_eval_outputs.py) so `W3-007` is now recognized, scored, and checked for BIRP structure, risk handling, privacy minimization, and scope boundaries.
- Added regression coverage in:
  - [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_web_workbench.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_web_workbench.py)
  - [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_build_workflow_eval_prompts.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_build_workflow_eval_prompts.py)
  - [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_clean_eval_outputs.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_clean_eval_outputs.py)

Tests and evals run:

- `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_web_workbench.WebWorkbenchTest.test_handle_run_returns_w3_birp_brief_for_product_ui scripts.test_build_workflow_eval_prompts.BuildWorkflowEvalPromptsTest.test_evals_include_w3_birp_risk_change_case scripts.test_clean_eval_outputs.CleanEvalOutputsTest.test_w3_007_birp_rubric_accepts_bounded_record`
- `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_web_workbench scripts.test_build_workflow_eval_prompts scripts.test_clean_eval_outputs`
- `$env:PYTHONPATH='scripts'; python scripts/build_workflow_eval_prompts.py`
- `$env:PYTHONPATH='scripts'; python -m unittest discover -s scripts -p "test_*.py"`
- DeepSeek live eval attempt blocked in this environment because `DEEPSEEK_API_KEY` was missing on 2026-06-23.

Outcome:

- W3 now treats BIRP as a first-class counseling-record mode in the shipped product rather than as a runner-only hidden format.
- Counselors can see the key BIRP record highlights directly in the workbench, which makes W3 materially easier to validate in pilot-style usage.
- The eval pipeline now has dedicated fixture and cleaner coverage for mixed-language BIRP risk-change records, preventing future regressions from being hidden inside generic W3 coverage.

Remaining gaps:

- Hosted deployment verification is still stale until the latest local commits are pushed and the public Render URL is smoke-tested with one BIRP record request that exercises the new W3 record brief end to end.
- Live DeepSeek validation for `W3-007` is still missing because API credentials were not present in this run environment.
- Mixed-language W3 routing is stronger through the new BIRP eval case, but negated/boundary-heavy W3-vs-W2/W5 prompts still need broader explicit route coverage.

## This Run: Intent Recognition Across Counselor Tasks

Capability worked on:

- `Intent recognition across counselor tasks`, specifically the W3-vs-W2/W5 boundary where counselors mention `session note` or `counseling record` only to negate that format while asking for case-background organization or one-session planning.

What changed:

- Tightened the product-side router in [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\web_workbench.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\web_workbench.py) so negated record-format language now:
  - reduces stray W3 dominance when W2 or W5 also have strong positive cues
  - marks W2-vs-W3 and W5-vs-W3 cases as `mixed_signals`
  - returns counselor-readable route notices for those boundary pairs instead of a generic overlap message
- Brought retrieval/eval routing into parity in [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\run-retrieval.ps1`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\run-retrieval.ps1) by expanding the negated-record guard to include `not a counseling record`, `not a session record`, `not a progress note`, and `do not/don't write counseling record`.
- Expanded eval coverage in [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\build_workflow_eval_prompts.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\build_workflow_eval_prompts.py) with new intent-routing boundary case `W2-007`, then regenerated committed assets in [`C:\Users\win\Documents\Codex\2026-05-15\agent\eval-prompts`](C:\Users\win\Documents\Codex\2026-05-15\agent\eval-prompts).
- Added cleaner/rubric coverage for `W2-007` in [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\clean_eval_outputs.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\clean_eval_outputs.py) so the new route fixture is scored as a bounded case-background capability rather than being unscored.
- Added regression coverage in:
  - [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_web_workbench.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_web_workbench.py)
  - [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_run_retrieval.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_run_retrieval.py)
  - [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_build_workflow_eval_prompts.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_build_workflow_eval_prompts.py)
  - [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_clean_eval_outputs.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_clean_eval_outputs.py)

Tests and evals run:

- `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_web_workbench.WebWorkbenchTest.test_detect_workflow_prefers_w2_when_case_background_request_negates_record_format scripts.test_web_workbench.WebWorkbenchTest.test_detect_workflow_prefers_w5_when_bilingual_next_session_request_negates_session_note scripts.test_build_workflow_eval_prompts.BuildWorkflowEvalPromptsTest.test_evals_include_w2_session_note_boundary_case scripts.test_build_workflow_eval_prompts.BuildWorkflowEvalPromptsTest.test_evals_include_ambiguity_and_mixed_intent_cases scripts.test_clean_eval_outputs.CleanEvalOutputsTest.test_w2_007_session_note_boundary_background_case_passes_rules_and_rubric`
- `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_run_retrieval.RunRetrievalTest.test_routes_session_note_boundary_case_background_to_w2_when_negating_counseling_record scripts.test_run_retrieval.RunRetrievalTest.test_routes_mixed_language_bps_background_to_w2_even_when_negating_session_note scripts.test_build_workflow_eval_prompts.BuildWorkflowEvalPromptsTest.test_evals_include_w2_session_note_boundary_case`
- `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_web_workbench scripts.test_run_retrieval scripts.test_build_workflow_eval_prompts scripts.test_clean_eval_outputs`
- `$env:PYTHONPATH='scripts'; python scripts/build_workflow_eval_prompts.py`
- `$env:PYTHONPATH='scripts'; python -m unittest discover -s scripts -p "test_*.py"` -> 308 tests passed.
- DeepSeek live eval for the new routing case was blocked on 2026-06-23 because `DEEPSEEK_API_KEY` was missing in this environment.

Outcome:

- The product-facing AUTO router now treats negated record-format requests as first-class mixed-signal counselor tasks instead of silently flattening them into W3 or hiding the competing W2/W5 interpretation.
- Eval prompt generation and retrieval now agree with the web router for the new `W2-007` supervision boundary case, which closes a backend parity gap that would otherwise have undermined route-validation evidence.
- The eval/scoring layer now has durable fixture coverage for this boundary, which makes future W2-vs-W3 regressions visible in both routing tests and answer scoring.

Remaining gaps:

- Hosted deployment verification is still stale until the latest local commits are pushed and the public Render URL is smoke-tested with at least one AUTO-routed W2 supervision request and one W5 request that explicitly negates record formatting.
- Live DeepSeek validation for the new route boundary is still missing because API credentials were not present in this run environment.
- Bilingual negation coverage is stronger for W2 case-background boundaries than before, but broader Chinese-heavy W3-vs-W5 phrasing and more varied `not X, do Y` formulations still need explicit route fixtures.

## This Run: Intent Recognition Across Counselor Tasks

Capability worked on:

- `Intent recognition across counselor tasks`, specifically the W3-vs-W5 boundary where counselors negate record formatting and ask for only one upcoming session plan.

What changed:

- Extended product-side W5 routing in [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\web_workbench.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\web_workbench.py) so AUTO routing now recognizes stronger English and Chinese negation phrasing such as `rather than a counseling record`, `不是要写 session note`, and `只做下一次咨询计划`, while still surfacing W5/W3 as `mixed_signals` for counselor review.
- Brought retrieval routing into parity in [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\run-retrieval.ps1`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\run-retrieval.ps1) by expanding the negated-record detection and the W5 one-session cue set so the same bilingual boundary language lands on `workflow_5_next_session_plan`.
- Expanded eval coverage in [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\build_workflow_eval_prompts.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\build_workflow_eval_prompts.py) with new boundary case `W5-005`, then regenerated committed eval prompt assets under [`C:\Users\win\Documents\Codex\2026-05-15\agent\eval-prompts`](C:\Users\win\Documents\Codex\2026-05-15\agent\eval-prompts).
- Added cleaner/rubric coverage for `W5-005` in [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\clean_eval_outputs.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\clean_eval_outputs.py) so the new route fixture is scored as a bounded next-session-planning capability rather than remaining unscored.
- Added regression coverage in:
  - [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_web_workbench.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_web_workbench.py)
  - [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_run_retrieval.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_run_retrieval.py)
  - [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_build_workflow_eval_prompts.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_build_workflow_eval_prompts.py)
  - [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_clean_eval_outputs.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_clean_eval_outputs.py)

Tests and evals run:

- `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_web_workbench scripts.test_run_retrieval scripts.test_build_workflow_eval_prompts scripts.test_clean_eval_outputs`
- `$env:PYTHONPATH='scripts'; python scripts/build_workflow_eval_prompts.py`
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-retrieval.ps1 -Query "<W5-005 bilingual negated-record prompt>" -SummaryOnly -Json`
- `$env:PYTHONPATH='scripts'; python -m unittest discover -s scripts -p "test_*.py"` -> 313 tests passed.
- `python scripts/run_model_eval.py --ids W5-005` with `DEEPSEEK_API_KEY` loaded from local `.env` and `DEEPSEEK_TIMEOUT_SECONDS=240` -> success.

Outcome:

- The product-facing AUTO router now treats stronger Chinese-heavy `not a record, just plan the next session` prompts as first-class W5 mixed-signal cases instead of letting W3 dominate.
- Retrieval selection, eval prompt generation, and scorer coverage now agree on the new `W5-005` boundary, which closes the earlier backend parity gap for this slice of intent recognition.
- The new W5 boundary has real DeepSeek evidence rather than fixture-only coverage, which materially improves market-validation readiness for this agent-core capability.

Remaining gaps:

- Hosted deployment verification is still stale until the latest local commits are pushed and the public Render URL is smoke-tested with the new W5/W3 mixed-signal boundary prompt.
- The retrieval route for Chinese-first W1 summary prompts still falls back to the generic W1 intake route rather than exposing a narrower W1 summary-mode route, so intent recognition is still partial overall.
- Broader Chinese-heavy `not X, do Y` variants across W3-vs-W5 and W1-vs-W3 still need additional explicit fixtures before routing can be considered deployment-ready.

## This Run: Intent Recognition Across Counselor Tasks

Capability worked on:

- `Intent recognition across counselor tasks`, specifically retrieval-side disambiguation for Chinese-first completed initial-interview summary prompts that were still collapsing into the generic W1 intake intent.

What changed:

- Added a dedicated W1 retrieval intent branch in [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\run-retrieval.ps1`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\run-retrieval.ps1) so completed initial-interview summary prompts now resolve to `初始访谈材料总结` instead of the generic `生成咨询师访谈版初访表` intent when the wording signals an already-finished intake record plus fixed-summary-template organization.
- Added a dedicated W1 summary intent route in [`C:\Users\win\Documents\Codex\2026-05-15\agent\rag\retrieval-map.v0.1.json`](C:\Users\win\Documents\Codex\2026-05-15\agent\rag\retrieval-map.v0.1.json) and documented it in [`C:\Users\win\Documents\Codex\2026-05-15\agent\rag\RAG_RETRIEVAL_MAP.md`](C:\Users\win\Documents\Codex\2026-05-15\agent\rag\RAG_RETRIEVAL_MAP.md), using summary-appropriate chunk priorities: biopsychosocial intake structure, professional-recording boundaries, and bounded risk documentation.
- Expanded eval coverage in [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\build_workflow_eval_prompts.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\build_workflow_eval_prompts.py) with `W1-010`, a Chinese-first completed-intake summary boundary case that explicitly negates `session note` / `counseling record` wording.
- Added scorer coverage for `W1-010` in [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\clean_eval_outputs.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\clean_eval_outputs.py) by mapping it to the existing W1 summary rule/rubric contract, so the new route case is evaluated as fixed-template intake summarization rather than generic W1 intake prep.
- Added regression coverage in:
  - [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_run_retrieval.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_run_retrieval.py)
  - [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_build_workflow_eval_prompts.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_build_workflow_eval_prompts.py)
  - [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_clean_eval_outputs.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_clean_eval_outputs.py)
- Regenerated committed eval assets in [`C:\Users\win\Documents\Codex\2026-05-15\agent\eval-prompts`](C:\Users\win\Documents\Codex\2026-05-15\agent\eval-prompts), including [`C:\Users\win\Documents\Codex\2026-05-15\agent\eval-prompts\W1-010-chinese-first-initial-interview-summary-boundary.txt`](C:\Users\win\Documents\Codex\2026-05-15\agent\eval-prompts\W1-010-chinese-first-initial-interview-summary-boundary.txt) and the updated manifest entries showing the new W1 summary intent and chunk selection.

Tests and evals run:

- `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_run_retrieval.RunRetrievalTest.test_routes_chinese_first_completed_initial_interview_summary_to_summary_intent scripts.test_build_workflow_eval_prompts.BuildWorkflowEvalPromptsTest.test_evals_include_chinese_first_w1_summary_boundary_case scripts.test_clean_eval_outputs.CleanEvalOutputsTest.test_w1_010_chinese_first_summary_rubric_accepts_bounded_summary_output`
- `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_run_retrieval scripts.test_build_workflow_eval_prompts scripts.test_clean_eval_outputs`
- `$env:PYTHONPATH='scripts'; python scripts/build_workflow_eval_prompts.py`
- `$env:PYTHONPATH='scripts'; python -m unittest discover -s scripts -p "test_*.py"` -> 316 tests passed.
- `$env:PYTHONPATH='scripts'; $env:DEEPSEEK_TIMEOUT_SECONDS='240'; python scripts/run_model_eval.py --ids W1-010` -> success.

Outcome:

- Retrieval no longer flattens Chinese-first completed-intake summary prompts into generic W1 intake-form prep; it now preserves the narrower W1 summary intent and retrieves summary-appropriate support chunks.
- The eval matrix and scorer now treat this boundary case as a first-class agent-core capability rather than leaving it hidden inside broader W1 coverage.
- This closes the specific retrieval-side gap called out in the prior loop state and adds real DeepSeek evidence for the new route case.

Remaining gaps:

- Hosted deployment verification is still stale until the latest local commits are pushed and the public Render URL is smoke-tested with a Chinese-first W1 summary request that exercises the current AUTO route metadata plus retrieval-backed generation path.
- The product-facing web router already exposes `w1_mode`, but there is still no hosted proof in this run that the deployed endpoint returns the latest W1 summary route metadata and brief for this new boundary case.
- Broader Chinese-heavy `not X, do Y` phrasing across W1-vs-W3 and W3-vs-W5 still needs more explicit fixtures before intent recognition can be considered deployment-ready.

## This Run: Intent Recognition Across Counselor Tasks

Capability worked on:

- `Intent recognition across counselor tasks`, specifically the Chinese-first W1-vs-W3 boundary where counselors ask for a fixed initial-interview summary from `首访原始记录` while explicitly negating `BIRP` or `咨询记录`.

What changed:

- Tightened the product-side router in [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\web_workbench.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\web_workbench.py) so W1 now recognizes additional Chinese-first summary cues such as `首访`, `首次访谈`, `首访原始记录`, and `固定模板总结`.
- Extended negated-record detection in the same router to treat `BIRP` as a record-format cue and to down-rank W3 when a negated record request overlaps with strong W1 summary signals, instead of only doing that for W2/W5 boundary cases.
- Updated W1 mode detection in [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\run_agent.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\run_agent.py) so the same Chinese-first `首访原始记录 + 固定模板总结 + 不要写成BIRP` phrasing is preserved as `initial_interview_summary` rather than falling back to intake-prep mode.
- Brought retrieval into parity in [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\run-retrieval.ps1`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\run-retrieval.ps1) by:
  - treating `BIRP` as a negated record-format target
  - recognizing the same `首访` / `首访原始记录` / `固定模板总结` summary cues during W1 workflow selection
  - mapping those queries back to the dedicated W1 summary intent instead of drifting into W2 risk extraction
- Expanded eval coverage in [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\build_workflow_eval_prompts.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\build_workflow_eval_prompts.py) with `W1-011`, a Chinese-first W1 summary boundary case that negates `BIRP` while preserving bounded risk-change wording.
- Added scorer/rubric coverage for `W1-011` in [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\clean_eval_outputs.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\clean_eval_outputs.py) and regenerated committed eval assets under [`C:\Users\win\Documents\Codex\2026-05-15\agent\eval-prompts`](C:\Users\win\Documents\Codex\2026-05-15\agent\eval-prompts), including [`C:\Users\win\Documents\Codex\2026-05-15\agent\eval-prompts\W1-011-chinese-first-initial-interview-summary-birp-boundary.txt`](C:\Users\win\Documents\Codex\2026-05-15\agent\eval-prompts\W1-011-chinese-first-initial-interview-summary-birp-boundary.txt).
- Added regression coverage in:
  - [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_web_workbench.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_web_workbench.py)
  - [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_run_retrieval.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_run_retrieval.py)
  - [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_run_agent.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_run_agent.py)
  - [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_build_workflow_eval_prompts.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_build_workflow_eval_prompts.py)
  - [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_clean_eval_outputs.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_clean_eval_outputs.py)

Tests and evals run:

- `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_web_workbench.WebWorkbenchTest.test_detect_workflow_prefers_w1_for_chinese_first_summary_prompt_that_negates_birp scripts.test_run_retrieval.RunRetrievalTest.test_routes_chinese_first_summary_request_that_negates_birp_to_w1_summary_intent`
- `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_run_agent.RunAgentTest.test_detect_w1_mode_distinguishes_prep_vs_summary_requests scripts.test_build_workflow_eval_prompts.BuildWorkflowEvalPromptsTest.test_evals_include_chinese_first_w1_summary_birp_boundary_case scripts.test_clean_eval_outputs.CleanEvalOutputsTest.test_w1_011_chinese_first_birp_boundary_rubric_accepts_bounded_summary_output`
- `$env:PYTHONPATH='scripts'; python scripts/build_workflow_eval_prompts.py`
- `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_run_agent scripts.test_web_workbench scripts.test_run_retrieval scripts.test_build_workflow_eval_prompts scripts.test_clean_eval_outputs` -> 203 tests passed.
- `$env:PYTHONPATH='scripts'; python -m unittest discover -s scripts -p "test_*.py"` -> 320 tests passed.
- Live DeepSeek eval was blocked in this environment on 2026-06-23 because `DEEPSEEK_API_KEY` was missing.
- Hosted health verification against `https://counselor-agent-coze-api.onrender.com/health` timed out on 2026-06-23, so deployment-side confirmation of this route remains unresolved.

Outcome:

- The shipped AUTO router now keeps a Chinese-first `首访原始记录 / 固定模板总结 / 不要写成BIRP` request inside W1 summary mode instead of letting W3 or W2 dominate.
- Retrieval selection and the eval matrix now agree with the product router for this boundary, so the capability is no longer split between frontend routing and retrieval behavior.
- The new `W1-011` fixture makes this specific mixed-signal boundary durable in regression coverage rather than leaving it implicit inside broader W1 summary cases.

Remaining gaps:

- Hosted deployment verification is still stale until the latest local commits are pushed and the public Render URL is smoke-tested with a `W1-011`-style prompt that exercises AUTO route metadata plus retrieval-backed generation.
- There is still no live DeepSeek evidence for `W1-011` in this environment because model credentials were missing.
- Broader Chinese-heavy W1-vs-W3 phrasing around `SOAP`, `DAP`, and looser `固定模板` wording still needs more explicit route fixtures before intent recognition can be considered deployment-ready.

## This Run: Intent Recognition Across Counselor Tasks

Capability worked on:

- `Intent recognition across counselor tasks`, specifically the Chinese-first W1-vs-W3 boundary where counselors ask for a fixed initial-interview summary while explicitly negating `DAP` or `session note`.

What changed:

- Added DAP-specific W1 summary regression coverage in:
  - [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_run_agent.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_run_agent.py)
  - [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_web_workbench.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_web_workbench.py)
  - [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_run_retrieval.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\test_run_retrieval.py)
  so the shipped runner, product-side AUTO router, and retrieval selector all have an explicit durable check for `首访原始记录 + 固定模板总结 + 不要写成DAP或session note`.
- Expanded eval coverage in [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\build_workflow_eval_prompts.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\build_workflow_eval_prompts.py) with `W1-013`, then regenerated committed eval assets including [`C:\Users\win\Documents\Codex\2026-05-15\agent\eval-prompts\W1-013-chinese-first-initial-interview-summary-dap-boundary.txt`](C:\Users\win\Documents\Codex\2026-05-15\agent\eval-prompts\W1-013-chinese-first-initial-interview-summary-dap-boundary.txt) and the updated manifest.
- Added scorer/rubric coverage for `W1-013` in [`C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\clean_eval_outputs.py`](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\clean_eval_outputs.py) by mapping it to the same bounded W1 summary contract already used for `W1-005`, `W1-010`, `W1-011`, and `W1-012`.

Tests and evals run:

- `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_build_workflow_eval_prompts.BuildWorkflowEvalPromptsTest.test_evals_include_chinese_first_w1_summary_dap_boundary_case scripts.test_clean_eval_outputs.CleanEvalOutputsTest.test_w1_013_chinese_first_dap_boundary_rubric_accepts_bounded_summary_output scripts.test_web_workbench.WebWorkbenchTest.test_detect_workflow_prefers_w1_for_chinese_first_summary_prompt_that_negates_dap scripts.test_run_retrieval.RunRetrievalTest.test_routes_chinese_first_summary_request_that_negates_dap_to_w1_summary_intent scripts.test_run_agent.RunAgentTest.test_detect_w1_mode_distinguishes_prep_vs_summary_requests`
- `$env:PYTHONPATH='scripts'; python scripts/build_workflow_eval_prompts.py`
- `$env:PYTHONPATH='scripts'; python -m unittest scripts.test_run_agent scripts.test_web_workbench scripts.test_run_retrieval scripts.test_build_workflow_eval_prompts scripts.test_clean_eval_outputs` -> 211 tests passed.
- Live DeepSeek eval for `W1-013` was blocked on 2026-06-24 because `DEEPSEEK_API_KEY` was missing in the environment.

Outcome:

- The DAP variant of the Chinese-first W1 summary vs W3 record boundary is now durable across runner mode detection, product-side AUTO routing, retrieval selection, eval-prompt generation, and answer scoring.
- This closes the remaining explicit `DAP` fixture gap called out in the prior loop state without drifting into lower-priority product work.

Remaining gaps:

- Hosted deployment verification is still stale until the latest local commits are pushed and the public Render URL is smoke-tested with a `W1-013`-style prompt that exercises AUTO route metadata plus retrieval-backed generation.
- There is still no live DeepSeek evidence for `W1-013` in this environment because model credentials were missing.
- Broader Chinese-heavy W1-vs-W3 phrasing around looser `固定模板` wording and hosted route-proof still remains before this P0 capability can be considered deployment-ready.

## Next Recommended Capability

Improve `intent recognition across counselor tasks` again as the next P0 capability.

Recommended scope:

- Verify the hosted deployment shows the current W1 summary route metadata and brief end to end for a `W1-013`-style Chinese-first prompt.
- If hosted verification is blocked again, extend another Chinese-heavy W1-vs-W3 boundary fixture around looser `固定模板` phrasing rather than record-format keywords.
- Only move to a different P0 capability after the hosted AUTO-route proof for the current W1 summary boundary family exists or is concretely blocked outside the repo.

## Deployment Readiness Notes

Do not claim deployment-ready until:

- `git status` is clean except allowed ignored runtime files.
- Tests for changed areas pass.
- Latest commits are pushed to the remote.
- Render deployment completes.
- Hosted health and at least one hosted workflow smoke test pass.
- No secrets or local sensitive runtime data are committed.
