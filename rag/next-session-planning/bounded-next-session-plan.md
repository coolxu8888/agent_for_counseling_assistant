---
chunk_id: next-session-planning-bounded-next-session-plan-001
title: Bounded next-session planning frame
source_id: local-next-session-planning-001
source_type: product_framework_note
source_url: local://rag/next-session-planning/bounded-next-session-plan.md
rag_section: next-session-planning
workflow_scope:
  - workflow_5_next_session_plan
topic:
  - single_session_focus
  - risk_monitoring
  - between_session_task_boundary
risk_level: medium
review_status: approved
last_reviewed: 2026-06-22
---

# Core rule

Generate a plan for one upcoming counseling session only. The plan should help the counselor decide what to review, explore, monitor, and possibly try in that single session, without implying a complete treatment sequence.

# Agent use

Use this chunk in Workflow 5 when the counselor asks for a next-session plan, next meeting agenda, or immediate next-step focus. Keep the output practical and bounded: session goal, focus areas, suggested interventions, questions to ask, risk checks, and optional between-session tasks that still require counselor judgment.

# Forbidden use

Do not turn the answer into a multi-session roadmap, deterministic treatment plan, or full intervention protocol. Do not prescribe crisis handling, final risk grading, or homework that would be unsafe, unsupported by the material, or outside the counselor's judgment.

# Scope

Applies to counselor-facing planning support for de-identified case reflection, supervision preparation, and note-to-plan transitions.

# Related chunks

- `theory-frameworks-cbt-case-conceptualization-001`
- `ethics-risk-cps-professional-boundary-001`
