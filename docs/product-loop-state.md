# Product Loop State

## Current Priority
P0: Agent core capabilities before generic product polish.

## Capability Worked This Run
Case conceptualization by theory/framework (`W4`).

## What Changed
- Added a new end-to-end `W4` workflow for framework-based case conceptualization in [C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\run_agent.py](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\run_agent.py) with:
  - workflow aliases and routing support
  - structured output contract and validator
  - privacy, risk, and scope boundaries that forbid diagnosis, treatment plans, and roadmaps
- Productized `W4` in the workbench and API:
  - workflow detection and demo scenario in [C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\web_workbench.py](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\web_workbench.py)
  - fallback catalog and labeling in [C:\Users\win\Documents\Codex\2026-05-15\agent\web-workbench\app.js](C:\Users\win\Documents\Codex\2026-05-15\agent\web-workbench\app.js)
  - user-facing copy in [C:\Users\win\Documents\Codex\2026-05-15\agent\web-workbench\index.html](C:\Users\win\Documents\Codex\2026-05-15\agent\web-workbench\index.html)
  - API/OpenAPI workflow enum in [C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\coze_api_server.py](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\coze_api_server.py)
- Connected `W4` to retrieval:
  - added framework chunks under [C:\Users\win\Documents\Codex\2026-05-15\agent\rag\theory-frameworks](C:\Users\win\Documents\Codex\2026-05-15\agent\rag\theory-frameworks)
  - updated retrieval routing in [C:\Users\win\Documents\Codex\2026-05-15\agent\rag\retrieval-map.v0.1.json](C:\Users\win\Documents\Codex\2026-05-15\agent\rag\retrieval-map.v0.1.json) and [C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\run-retrieval.ps1](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\run-retrieval.ps1)
- Added rendering support for `case_conceptualization` in [C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\render_docx.py](C:\Users\win\Documents\Codex\2026-05-15\agent\scripts\render_docx.py)
- Extended eval automation:
  - new prompt builder entry `W4-001`
  - bilingual W4 clean/rubric checks so Chinese model outputs do not false-warn

## Tests And Evals Run
- `python scripts/test_run_agent.py`
- `python scripts/test_web_workbench.py`
- `python scripts/test_clean_eval_outputs.py`
- `python scripts/test_render_docx.py`
- `python scripts/test_coze_api_server.py`
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/validate-rag.ps1 -Json`
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-retrieval.ps1 -Query "Build a CBT case conceptualization for this de-identified case." -Json`
- `python scripts/run_model_eval.py --ids W4-001`
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
| Next-session plan | not started | roadmap only | design schema + workflow |
| Counseling roadmap | not started | roadmap only | design workflow with strict scope boundaries |
| Word template filling | partial | prototype exists | model-assisted mapping |
| RAG retrieval | partial | chunks/map exist | expand retrieval eval matrix and failure tests |
| Eval automation | partial | scripts exist | broaden bilingual rubric coverage across workflows |

## Remaining Gaps
- `W4` has one live eval case; each framework still needs its own model eval and regression fixture.
- Hosted smoke coverage now accepts `W4`, but no deployed environment verification was run in this iteration.
- Capability sequencing after conceptualization is still missing: no next-session plan or counseling roadmap workflow yet.

## Next Recommended Capability
Build `Next-session plan` as the next highest-impact P0 gap, reusing `W4` conceptualization outputs while keeping treatment and diagnosis boundaries explicit.
