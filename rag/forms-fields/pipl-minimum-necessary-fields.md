---
chunk_id: forms-fields-pipl-minimum-necessary-001
title: "表单字段的最小必要原则"
source_id: china-pipl-sensitive-fields-001
source_url: "https://www.npc.gov.cn/npc/c2597/c5854/bfflywwb/202311/t20231117_433007.html"
source_type: law
rag_section: forms-fields
workflow_scope:
  - workflow_1_intake_form
topic:
  - minimum_necessary
  - form_schema
  - privacy
risk_level: high
review_status: approved
last_reviewed: "2026-05-30"
---

# 核心规则

初访表和系统字段设计应遵循最小必要原则。字段应与咨询目的直接相关，不应为了完整性收集与咨询无关的个人信息。敏感字段原则上不应默认必填。

# Agent 使用方式

生成系统字段版初访表时，Agent 应对每个字段考虑：是否与咨询目的直接相关、是否敏感、是否必须填写、是否为风险信号。对敏感但非必要字段，默认设置 `required: false`。

# 禁止用法

不得将所有个人信息字段设为必填。不得收集与咨询目标无关的身份、家庭、医疗或财务细节。不得替代隐私政策和法务合规审查。

# 适用范围

适用于 Workflow 1 的初访表、来访者预填写表、系统字段版和前端表单配置。

# 相关 chunk

- `forms-fields-pipl-sensitive-field-rules-001`
- `ethics-risk-cps-informed-consent-confidentiality-001`
