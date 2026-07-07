---
source_id: moe-student-mental-health-action-001
title: "全面加强和改进新时代学生心理健康工作专项行动计划（2023—2025年）"
organization: "教育部等十七部门"
url: "https://www.moe.gov.cn/srcsite/A17/moe_943/moe_946/202305/t20230511_1059219.html"
source_type: government_policy
publication_date: "2023-04-20"
accessed_date: "2026-05-28"
jurisdiction: "中国大陆"
language: "zh-CN"
workflow_scope:
  - workflow_1_intake_form
  - workflow_2_case_summary
  - workflow_3_session_note
rag_section:
  - ethics-risk
  - intake-assessment
review_status: approved
reviewer: ""
copyright_note: "政府公开文件。正式入库时使用摘要和规则化表达，并保留来源链接。"
---

# 摘要

《全面加强和改进新时代学生心理健康工作专项行动计划（2023—2025年）》由教育部等十七部门印发，面向学生心理健康工作体系建设。该文件强调健全心理问题预防和监测机制、关注学业就业压力、经济困难、情感危机、家庭变故、校园欺凌等风险因素，并提出学校、家庭、精神卫生医疗机构、妇幼保健机构等协同机制，及早发现严重心理健康问题，监测预警学生自伤或伤人等危险行为，畅通预防、转介、干预、就医通道。对 v0.1 来说，它适合补充学生/学校场景下的风险识别和转介协同边界。

# 可用内容

- 学生心理健康工作应贯通学校、家庭、社会多方。
- 应重点关注学业就业压力、经济困难、情感危机、家庭变故、校园欺凌、实习实践环境变化等风险因素。
- 应及早发现严重心理健康问题，监测预警自伤或伤人等危险行为。
- 应畅通预防、转介、干预、就医通道。
- 可用于学生咨询场景下的初访风险筛查、信息缺口提示和转介提醒。

# 不适用或需谨慎内容

- 该文件面向学生心理健康工作体系，不是个体心理咨询记录模板。
- 不应将学校治理要求直接套用于成人个体咨询或非学校场景。
- 不应让 Agent 直接调度学校、家庭、公安、医疗等主体，只能提示咨询师按机构流程处理。

# 建议入库位置

- `rag/ethics-risk/moe-student-crisis-warning-referral.md`
- `rag/intake-assessment/student-risk-factors.md`

# 人工审核备注

- 建议审核后切分为“学生风险因素”“自伤/伤人预警”“医教协同与转介通道”“场景限制”四类 chunk。

