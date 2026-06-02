# RAG Runtime Smoke Test 2026-05-30

## 测试目的

本轮测试用于验证最小 retrieval runner 是否能把用户输入映射到 v0.1 workflow、intent 和 priority chunks，并生成可用于 prompt 组装的 RAG context。

测试脚本：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-retrieval.ps1 -Query "<用户输入>" -SummaryOnly -Json
```

## 结果摘要

| 场景 | 输入摘要 | 期望 | 实际结果 |
|---|---|---|---|
| 初访综合评估 | 初访表 + 综合评估身心状态 | Workflow 1，命中 biopsychosocial chunk | PASS |
| 学生危机 | 高中生、同学排挤、成绩下降、不如消失 | Workflow 2，命中学生风险、学生危机、自杀/自伤风险 chunk | PASS |
| Session 风险记录 | 本次咨询记录 + 不想醒来念头 | Workflow 3，命中风险变化、自杀/自伤风险、自杀风险询问 chunk | PASS |
| 只粘贴笔记 | 29 岁，分手后低落、睡眠变差 | 不直接检索，先澄清任务 | PASS |

## 用例 1：初访综合评估

输入：

```text
帮我把初访表改成更适合综合评估来访者身心状态的版本
```

结果：

```json
{
  "status": "OK",
  "workflow": "workflow_1_intake_form",
  "intent": "生成咨询师访谈版初访表",
  "chunks": [
    "intake-assessment-biopsychosocial-client-assessment-001",
    "ethics-risk-cps-informed-consent-confidentiality-001",
    "ethics-risk-china-risk-boundary-self-harm-harm-to-others-001"
  ]
}
```

## 用例 2：学生危机

输入：

```text
这是一个高中生个案，最近被同学排挤，成绩下降，说过不如消失算了。帮我整理风险信号和后续需要问什么。
```

结果：

```json
{
  "status": "OK",
  "workflow": "workflow_2_case_summary",
  "intent": "学生个案",
  "chunks": [
    "intake-assessment-student-risk-factors-001",
    "ethics-risk-moe-student-crisis-management-boundary-001",
    "ethics-risk-china-risk-boundary-self-harm-harm-to-others-001",
    "ethics-risk-suicide-risk-inquiry-topics-001"
  ]
}
```

## 用例 3：Session 风险记录

输入：

```text
帮我生成本次咨询记录：来访者这次说最近几天有过不想醒来的念头，但没有具体计划。
```

结果：

```json
{
  "status": "OK",
  "workflow": "workflow_3_session_note",
  "intent": "出现自杀或自伤风险",
  "chunks": [
    "session-notes-risk-change-documentation-001",
    "ethics-risk-china-risk-boundary-self-harm-harm-to-others-001",
    "ethics-risk-suicide-risk-inquiry-topics-001"
  ]
}
```

## 用例 4：只粘贴笔记

输入：

```text
女，29岁，最近分手后持续低落，睡眠变差，工作效率下降。
```

结果：

```json
{
  "status": "NEEDS_CLARIFICATION",
  "action": "clarify_before_retrieval"
}
```

## 本轮修正

- 将 runner 源码改为 ASCII-only，避免 Windows PowerShell 以系统编码读取 UTF-8 `.ps1` 时破坏中文正则。
- 增加高风险词触发后的 chunk 增强逻辑，避免学生场景或普通记录场景漏掉自杀/自伤风险边界 chunk。
- 修复 `biopsychosocial-client-assessment-template.md` 中旧的相关 chunk 引用。

## 当前结论

最小 retrieval runner 已可用于 v0.1 的本地联调。它目前是规则路由，不是向量检索；后续接 embedding 检索器时，可以保留本 runner 作为安全兜底和 priority chunk 注入层。
