# 咨询师助理 Agent v0.1 运行时架构

本文档说明最终 Agent 接入时的运行链路。它回答一个问题：用户输入进入系统后，怎样经过路由、RAG 检索、提示词组装和输出检查，最终生成稳定回答。

## 1. 总体链路

```text
user_input
  ↓
input_precheck
  ↓
intent_router
  ↓
workflow_selector
  ↓
rag_retrieval
  ↓
prompt_builder
  ↓
model_generation
  ↓
output_boundary_check
  ↓
final_answer
```

## 2. 模块说明

### 2.1 input_precheck

作用：

- 判断用户是否提供了材料
- 判断是否只是粘贴笔记
- 检测是否包含高风险关键词
- 检测是否要求诊断、治疗方案或流派分析

输出：

```json
{
  "has_case_material": true,
  "has_explicit_task": true,
  "possible_risk_signal": true,
  "requests_diagnosis": false,
  "requests_modality_analysis": false
}
```

### 2.2 intent_router

作用：

将用户输入路由到三个 P0 workflow：

| 条件 | 路由 |
|---|---|
| 请求初访表、初访提纲、来访者预填写表、系统字段 | Workflow 1 |
| 请求整理个案背景、笔记、主诉、风险信号、信息缺口 | Workflow 2 |
| 请求总结本次 session、生成咨询记录、SOAP/DAP/BIRP | Workflow 3 |
| 只粘贴笔记，没有任务 | 先澄清，不进入 RAG |
| 请求流派概念化或 Road Map | 说明属于后续能力 |

输出：

```json
{
  "workflow": "workflow_2_case_summary",
  "needs_clarification": false,
  "clarification_question": ""
}
```

### 2.3 workflow_selector

作用：

根据 workflow 选择输出结构和缺省策略。

示例：

```json
{
  "workflow": "workflow_1_intake_form",
  "output_variant": "counselor_interview",
  "default_client_type": "adult_individual",
  "format": "markdown_table"
}
```

### 2.4 rag_retrieval

作用：

根据 `rag/RAG_RETRIEVAL_MAP.md` 检索 chunk。

输入：

```json
{
  "workflow": "workflow_3_session_note",
  "topics": [
    "session_note_structure",
    "risk_change_documentation",
    "fact_vs_inference"
  ]
}
```

输出：

```json
{
  "chunks": [
    {
      "chunk_id": "session-notes-soap-format-001",
      "title": "SOAP 记录结构",
      "content": "..."
    }
  ]
}
```

### 2.5 prompt_builder

作用：

组装最终模型输入：

1. 系统提示词
2. workflow 规则
3. 检索到的 RAG chunk
4. 用户输入
5. 输出格式要求

建议结构：

```text
SYSTEM:
  counselor-agent-v0.1-system-prompt

WORKFLOW:
  selected workflow rules

RAG_CONTEXT:
  approved chunks only

USER_INPUT:
  original user input

OUTPUT_CONSTRAINTS:
  required structure, boundaries, no diagnosis, no fabrication
```

### 2.6 model_generation

作用：

调用模型生成结果。

模型输出需要满足：

- 结构符合 workflow
- 事实和推测分开
- 风险单独列出
- 不做诊断
- 不编造
- 不越过 v0.1 能力范围

### 2.7 output_boundary_check

作用：

对模型输出进行后置检查。可以先人工检查，后续再做自动检查。

检查项：

| 检查项 | 失败表现 |
|---|---|
| 是否诊断 | 输出“这是抑郁症”等确定性结论 |
| 是否编造 | 增加用户未提供的事实 |
| 是否忽略风险 | 有自伤/自杀内容但未单独列风险 |
| 是否越过流派边界 | v0.1 直接做 CBT/精神动力完整概念化 |
| 是否格式错误 | 未按 workflow 输出 |
| 是否隐私扩散 | 输出无关敏感细节 |

如果失败：

- 可要求模型重写
- 或返回安全提示
- 或转人工审核

### 2.8 crisis_level_eval_mode

作用：

在训练、评测或督导辅助语境中，根据 `crisis-level-rubric-v0.1.md` 和 `eval-data/crisis-level-cases.v0.1.json` 生成危机等级候选判断。

该模式不属于真实个案的最终自动风险分级。真实个案中，输出只能作为候选等级和材料依据，并必须提示咨询师结合面询、机构流程和必要转介进行最终判断。

输入：

```json
{
  "case_id": "crisis-level-001",
  "case_material": "...",
  "rubric": "crisis-level-rubric-v0.1.md"
}
```

输出：

```json
{
  "candidate_level": "一级",
  "dimensions": {
    "active_suicidal_ideation": "不满足",
    "plan_and_resource": "不满足",
    "implementation_intent": "不满足",
    "attempt_or_preparation": "不满足"
  },
  "evidence": ["..."],
  "missing_information": ["..."],
  "boundary_note": "候选等级，不构成最终风险等级。"
}
```

## 3. 最小实现版本

最小实现可以先不做复杂工程：

```text
手动选择 system prompt
  ↓
手动输入测试 case
  ↓
人工选择相关 RAG chunk
  ↓
模型生成
  ↓
人工按测试用例评分
```

第二阶段再做自动路由和自动检索。

## 4. 伪代码

```pseudo
function runCounselorAgent(userInput):
    precheck = inputPrecheck(userInput)

    route = intentRouter(userInput, precheck)

    if route.needs_clarification:
        return route.clarification_question

    if route.workflow not in ["workflow_1", "workflow_2", "workflow_3"]:
        return boundaryResponse(route)

    retrievalPlan = buildRetrievalPlan(route.workflow, userInput)
    chunks = retrieveApprovedChunks(retrievalPlan)

    prompt = buildPrompt(
        systemPrompt,
        workflowRules[route.workflow],
        chunks,
        userInput
    )

    output = model.generate(prompt)
    checked = outputBoundaryCheck(output)

    if checked.failed:
        return reviseOrEscalate(output, checked)

    return output
```

## 5. v0.1 结束状态

当以下条件满足时，v0.1 可以进入产品原型：

1. 三个 P0 workflow 稳定。
2. 系统提示词通过测试用例。
3. 第一批 RAG chunk 完成人工审核。
4. 检索映射表可以覆盖三个 workflow。
5. 输出边界检查能发现诊断、编造、风险遗漏和流派越界。
