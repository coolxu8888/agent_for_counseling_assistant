# Product Loop State

## Current Priority
P0: Agent core capabilities before generic product polish.

## Capability Worked This Run
Next-session plan (`W5`).

## What Changed
- Completed the end-to-end `W5` workflow for a bounded next-session plan across the agent, retrieval, workbench, and hosted API:
  - workflow aliases, routing, structured output contract, and scope validation in [C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\run_agent.py](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\run_agent.py)
  - retrieval routing and workflow scoring in [C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\run-retrieval.ps1](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\run-retrieval.ps1)
  - new approved RAG chunk under [C:\Users\win\Documents\Codex\2026-05-15\agent\rag\next-session-planning\bounded-next-session-plan.md](C:\Users\win\Documents\Codex\2026-05-15\agent\rag\next-session-planning\bounded-next-session-plan.md)
  - retrieval map updates in [C:\Users\win\Documents\Codex\2026-05-15\agent\rag\retrieval-map.v0.1.json](C:\Users\win\Documents\Codex\2026-05-15\agent\rag\retrieval-map.v0.1.json)
- Productized `W5` in the deployable web product:
  - workbench workflow detection and demo scenario in [C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\web_workbench.py](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\web_workbench.py)
  - fallback catalog, workflow labels, and result rendering in [C:\Users\win\Documents\Codex\2026-05-15\agent\web-workbench\app.js](C:\Users\win\Documents\Codex\2026-05-15\agent\web-workbench\app.js)
  - user-facing workflow copy in [C:\Users\win\Documents\Codex\2026-05-15\agent\web-workbench\index.html](C:\Users\win\Documents\Codex\2026-05-15\agent\web-workbench\index.html)
  - hosted API/OpenAPI workflow enum handling in [C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\coze_api_server.py](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\coze_api_server.py)
- Extended document/export and smoke support for `next_session_plan` in:
  - [C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\render_docx.py](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\render_docx.py)
  - [C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\hosted_smoke.py](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\hosted_smoke.py)
- Extended eval automation:
  - new prompt builder entry `W5-001`
  - bilingual W5 clean/rubric checks so both English and Chinese DeepSeek outputs pass when bounded and safe

## Tests And Evals Run
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

## Current Capability Backlog

| Capability | Status | Evidence | Next Step |
|---|---|---|---|
| Intent recognition | partial | API runner exists | improve routing eval coverage, especially mixed prompts |
| W1 interview guide | partial | workflow/eval exists | frontend/API polish |
| W1 interview summary template | partial | template filling exists | improve raw-note mapping |
| W2 case background BPS | partial | docs/eval exists | productize UI/API |
| Case conceptualization by theory | partial | `W4` shipped in runner/web/RAG/eval | add more live eval cases per framework |
| W3 session records | partial | eval exists | strengthen risk handling |
| Next-session plan | partial | `W5` shipped in runner/web/RAG/eval | add more framework-specific eval cases and hosted verification |
| Counseling roadmap | not started | roadmap only | design workflow with strict scope boundaries |
| Word template filling | partial | prototype exists | model-assisted mapping |
| RAG retrieval | partial | chunks/map exist | expand retrieval eval matrix and failure tests |
| Eval automation | partial | scripts exist | broaden bilingual rubric coverage across workflows |

## Remaining Gaps
- `W5` now has one live eval case, but each framework still needs its own model eval and regression fixture.
- Hosted smoke coverage accepts `W5`, but no public deployed environment verification was run in this iteration.
- The remaining major product gap is capability sequencing beyond one session: no bounded counseling roadmap workflow yet.

## Next Recommended Capability
Build `Counseling roadmap` as the next highest-impact P0 gap, keeping it explicitly bounded, counselor-facing, and separate from diagnosis or prescriptive treatment planning.
