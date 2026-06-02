# RAG Chunk Template

正式进入 RAG 的资料应使用本模板。每个 chunk 只处理一个主题，避免把多个规则混在一起。

```markdown
---
chunk_id: ""
title: ""
source_id: ""
source_url: ""
source_type: ""
rag_section: ""
workflow_scope:
  - workflow_1_intake_form
topic:
  - ""
risk_level: low
review_status: approved
last_reviewed: ""
---

# 核心规则

用简洁语言写出这条 chunk 的核心规则。不要复制大段原文。

# Agent 使用方式

说明 Agent 在哪个 workflow、什么用户意图下应使用本 chunk。

# 禁止用法

说明 Agent 不应如何使用本 chunk，例如不得诊断、不得自动分级、不得替代咨询师判断。

# 适用范围

说明该 chunk 的适用人群、地区、机构语境或限制。

# 相关 chunk

- 
```

## 字段说明

| 字段 | 说明 |
|---|---|
| `chunk_id` | 唯一 ID，建议使用 `分区-主题-序号` |
| `title` | chunk 标题 |
| `source_id` | 对应 source card ID |
| `source_url` | 来源链接 |
| `source_type` | 来源类型 |
| `rag_section` | RAG 分区 |
| `workflow_scope` | 适用 workflow |
| `topic` | 检索主题标签 |
| `risk_level` | `low` / `medium` / `high` |
| `review_status` | 正式 chunk 应为 `approved` |
| `last_reviewed` | 最近人工审核日期 |

## chunk_id 命名建议

```text
ethics-risk-confidentiality-001
ethics-risk-suicide-inquiry-001
intake-assessment-basic-info-001
case-recording-fact-vs-inference-001
session-notes-soap-format-001
forms-fields-sensitive-field-001
```

## 切块原则

- 一个 chunk 只讲一个主题。
- 主题应能被用户意图直接检索到。
- 高风险主题必须写“禁止用法”。
- 不能复制长段版权文本。
- 如果来源有地域限制，必须写进“适用范围”。
- 如果内容只适合人工专业判断，必须明确 Agent 不可自动决策。

