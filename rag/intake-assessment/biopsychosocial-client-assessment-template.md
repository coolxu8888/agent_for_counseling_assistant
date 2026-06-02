---
chunk_id: intake-assessment-biopsychosocial-client-assessment-001
title: "来访综合身心状态评估模板：生物-心理-社会模型"
source_id: biopsychosocial-assessment-001
source_url: "https://www.ncbi.nlm.nih.gov/books/NBK552030/"
source_type: scholarly_model_review
rag_section: intake-assessment
workflow_scope:
  - workflow_1_intake_form
  - workflow_2_case_summary
topic:
  - biopsychosocial_assessment
  - intake_assessment
  - information_gap
risk_level: medium
review_status: approved
last_reviewed: "2026-05-29"
---

# 核心规则

来访综合身心状态评估可采用生物-心理-社会模型作为基础框架。该框架用于系统收集来访者的身体健康、心理状态和社会处境信息，帮助咨询师形成对当前困扰的整体理解。它不是诊断工具，也不是治疗方案。

# Agent 使用方式

当生成初访信息收集表、补充型初访表或个案信息整理摘要时，Agent 可按以下维度组织信息：

## 生物维度

- 睡眠、食欲、精力、体重变化
- 既往身体疾病、疼痛、手术或慢性病
- 精神科就诊史、用药史、药物效果与副作用
- 物质使用，如酒精、药物或其他成瘾行为
- 家族精神健康或重大疾病相关信息

## 心理维度

- 主诉与当前困扰
- 情绪状态、痛苦程度、持续时间和触发因素
- 认知线索，如自我评价、核心担忧、自动化想法
- 行为模式和应对方式
- 创伤、长期压力或重大丧失线索
- 自伤、自杀、他伤、现实检验等风险信号
- 资源、优势和咨询目标

## 社会维度

- 家庭关系、亲密关系、同伴关系
- 学习、工作、经济和居住情况
- 社会支持系统和可求助对象
- 近期重大生活事件
- 文化、身份、环境和制度压力
- 学校、机构、医疗或其他服务系统关联

# 禁止用法

不得将生物-心理-社会模型用于输出确定性诊断。不得为了完整性强行收集与咨询目的无关的敏感信息。不得替代精神科诊断、医学建议、危机处置或机构转介流程。

# 适用范围

适用于咨询师助理 Agent v0.1 的初访信息收集、补充访谈问题生成、个案信息整理和信息缺口检查。涉及隐私字段时，应同时遵守个人信息保护法相关敏感字段规则。

# 相关 chunk

- `forms-fields-pipl-sensitive-field-rules-001`
- `ethics-risk-china-risk-boundary-self-harm-harm-to-others-001`
- `case-recording-cps-professional-materials-recording-001`
