---
source_id: moe-student-mental-health-management-001
title: "教育部办公厅关于加强学生心理健康管理工作的通知"
organization: "教育部办公厅"
url: "https://hudong.moe.gov.cn/srcsite/A12/moe_1407/s3020/202107/t20210720_545789.html"
source_type: government_policy
publication_date: "2021-07-07"
accessed_date: "2026-05-29"
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
reviewer: "user"
copyright_note: "政府公开文件。正式入库时使用摘要和规则化表达，并保留来源链接。"
---

# 摘要

《教育部办公厅关于加强学生心理健康管理工作的通知》面向学生心理健康管理工作，强调专业支撑、科学管理、心理测评、筛查预警、精准干预和心理危机事件干预处置能力。该通知要求加强结果管理，提高心理危机事件干预处置能力，并提出县级教育部门与卫生健康部门协同联动，建立精神卫生医疗机构对学校心理健康教育及心理危机干预的支持协作机制。对 v0.1 来说，它适合补充学校/学生场景下的预警、干预、转介和医校协同资料。

# 可用内容

- 定期开展学生心理健康测评，注重科学分析和合理应用。
- 健全筛查预警机制，及早实施精准干预。
- 加强结果管理，提高心理危机事件干预处置能力。
- 教育部门可与卫生健康部门协同，建立精神卫生医疗机构对学校心理健康教育及心理危机干预的支持协作机制。
- 可用于学生咨询场景下的风险筛查、信息缺口、转介提醒和学校场景限制说明。

# 不适用或需谨慎内容

- 该通知主要面向学校和学生心理健康管理，不适用于所有成人个体咨询场景。
- 不应将学校管理要求直接套用于社会心理咨询、企业 EAP 或医疗场景。
- Agent 不应直接建议学校行政措施，只能提示咨询师按机构流程和当地法规处理。

# 建议入库位置

- `rag/ethics-risk/moe-student-crisis-management-boundary.md`
- `rag/intake-assessment/student-screening-warning-topics.md`
- `rag/session-notes/student-risk-referral-documentation.md`

# 人工审核备注

- 审核结论：approved。
- 可与 `moe-student-mental-health-action-001` 合并或互补：本卡偏 2021 年具体管理通知，后者偏 2023-2025 专项行动计划。
- 建议切分“筛查预警”“精准干预”“医校协同”“学校场景限制”四类 chunk。
