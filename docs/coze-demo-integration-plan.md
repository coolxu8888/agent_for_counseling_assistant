# Coze Demo Integration Plan

## Positioning

Coze is a demo shell, not the source of truth for the counseling assistant.

The core product logic remains in this repository:

- workflow prompts and RAG retrieval
- structured output validation
- risk and ethics boundary checks
- DOCX rendering
- intelligent template drafting and fill reports
- eval data and regression tests

Coze should call these capabilities through API endpoints once the Web MVP has a stable local/server deployment.

## Demo Goal

Let a reviewer experience the counselor assistant as a conversational bot:

1. User tells Coze what they want: initial intake guide, case summary, session note, or template fill.
2. Coze asks for missing inputs when needed.
3. Coze calls our backend API.
4. Coze returns the generated text and links to downloadable artifacts.

## Recommended Demo Scope

### Demo 1: Session Note

Input:

- raw session note
- preferred output style

Backend call:

- `POST /api/run`
- workflow: `W3`
- structured: `true`
- render_docx: `true`

Output:

- session record text
- structured validation summary
- Word download link

### Demo 2: Intelligent Template Fill

Input:

- raw counselor note
- template path or uploaded template reference
- existing-content policy
- style

Backend call:

- `POST /api/draft-template`

Output:

- filled Word file link
- template draft JSON link
- fill report summary

## API Requirement Before Coze

The current workbench is local-first. Before Coze can call it reliably, expose a small HTTP service with:

- public or intranet URL
- API key protection
- file upload endpoint or temporary object storage
- artifact download URLs
- request size limits
- log redaction for counseling material

## Coze Bot Design

Bot role:

> 你是咨询师助理的演示入口。你帮助咨询师选择工作流、收集必要输入，并调用后端生成咨询文档。你不进行诊断，不替代正式风险评估，不承诺危机等级判断。

Top intents:

- 生成初访信息收集表
- 整理个案背景
- 生成 session 咨询记录
- 按模板填充 Word
- 查看风险/伦理边界提醒

Fallback:

- If the user asks for clinical judgment, Coze should return a boundary reminder and offer to generate questions, records, or a risk-assessment checklist.

## Implementation Order

1. Finish Web MVP usability for local testing.
2. Add a backend API wrapper that is separate from the static workbench server.
3. Add upload/download artifact handling.
4. Deploy to a controlled test environment.
5. Create Coze bot with two tool calls: `run_workflow` and `draft_template`.
6. Run the existing eval cases through the deployed endpoint.
7. Record a demo script and known limitations.

## Not For Demo V1

- User accounts
- long-term case storage
- WeChat mini program
- speech-to-text
- direct diagnosis or final crisis grading
