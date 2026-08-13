---
chunk_id: forms-fields-pipl-sensitive-field-rules-001
title: "个人信息保护法下的敏感字段标注规则"
source_id: china-pipl-sensitive-fields-001
source_url: "https://www.npc.gov.cn/npc/c2597/c5854/bfflywwb/202311/t20231117_433007.html"
source_type: law
rag_section: forms-fields
workflow_scope:
  - workflow_1_intake_form
topic:
  - sensitive_field
  - form_schema
  - minimum_necessary
risk_level: high
review_status: approved
last_reviewed: "2026-05-28"
---

# 核心规则

系统字段版初访表应遵循个人信息处理的明确目的、最小必要和敏感信息保护原则。凡涉及医疗健康、心理健康风险、危机信息、未成年人信息、身份识别、联系方式、紧急联系人、家庭关系、创伤经历、精神科就诊、药物使用、自伤/自杀/他伤风险等字段，应默认标注为敏感字段。

# Agent 使用方式

当 Agent 生成 JSON Schema 或前端表单字段时，应为敏感字段设置 `sensitive: true`。风险相关字段应同时设置 `risk_signal: true`。对不必须填写的敏感字段，默认 `required: false`，并在来访者预填写版中提示可选择填写或留空。

# 禁止用法

不得把所有字段默认设为必填。不得为了“资料完整”收集与咨询目的无关的信息。不得将 `sensitive: false` 用于医疗健康、心理风险、未成年人、身份识别或紧急联系人等字段。不得将本 chunk 作为完整隐私合规或法律意见。

# 适用范围

适用于中国大陆语境下咨询师助理 Agent 市场验证版的初访表、来访者预填写表和系统字段版表单设计。具体隐私政策、保存期限、授权文本和跨境处理仍需法务和机构制度确认。

# 相关 chunk

- `ethics-risk-cps-informed-consent-confidentiality-001`
- `forms-fields-pipl-minimum-necessary-001`
