# RAG Retrieval Map

本文档定义咨询师助理 Agent v0.1 在不同 workflow 下应检索哪些 RAG 分区和 topic。

## 总原则

- 先根据用户意图确定 workflow。
- 再根据 workflow 检索对应分区。
- 高风险主题优先检索 `ethics-risk`。
- 记录类任务优先检索 `case-recording` 和 `session-notes`。
- 系统字段类任务检索 `forms-fields`。
- v0.1 不检索 CBT、人本、精神动力、家庭系统等流派 chunk 来改变基础信息抓取结构。

---

# Workflow 1：初访信息收集表生成

## 默认检索分区

- `intake-assessment`
- `ethics-risk`
- `forms-fields`

## 推荐 topic

| 用户意图 | topic |
|---|---|
| 生成咨询师访谈版初访表 | `intake_basic_info`, `presenting_concern`, `current_functioning`, `biopsychosocial_assessment`, `risk_screening`, `informed_consent` |
| 初始访谈材料总结 | `fact_vs_missing_info`, `biopsychosocial_assessment`, `risk_screening`, `intake_gap_check` |
| 生成来访者预填写版 | `client_facing_language`, `informed_consent`, `risk_screening`, `optional_disclosure` |
| 生成系统字段版 | `form_schema`, `sensitive_field`, `risk_signal_field`, `required_field` |
| 基于笔记生成补充表 | `intake_gap_check`, `biopsychosocial_assessment`, `risk_screening`, `fact_vs_missing_info` |
| 用户要求删掉风险问题 | `risk_screening`, `professional_boundary` |

## 检索示例

```text
workflow = workflow_1_intake_form
query_topics = [
  "intake_basic_info",
  "biopsychosocial_assessment",
  "risk_screening",
  "informed_consent",
  "sensitive_field"
]
```

## 推荐 chunk

| 场景 | 优先 chunk |
|---|---|
| 默认初访表 | `intake-assessment-biopsychosocial-client-assessment-001`, `ethics-risk-cps-informed-consent-confidentiality-001`, `ethics-risk-china-risk-boundary-self-harm-harm-to-others-001` |
| 初始访谈材料总结 | `intake-assessment-biopsychosocial-client-assessment-001`, `case-recording-cps-professional-materials-recording-001`, `ethics-risk-china-risk-boundary-self-harm-harm-to-others-001` |
| 来访者预填写版 | `ethics-risk-cps-informed-consent-confidentiality-001`, `forms-fields-pipl-sensitive-field-rules-001`, `forms-fields-pipl-minimum-necessary-001` |
| 系统字段版 | `forms-fields-pipl-sensitive-field-rules-001`, `forms-fields-pipl-minimum-necessary-001` |
| 基于笔记生成补充表 | `intake-assessment-biopsychosocial-client-assessment-001`, `ethics-risk-china-risk-boundary-self-harm-harm-to-others-001`, `ethics-risk-suicide-risk-inquiry-topics-001` |
| 学生场景 | `intake-assessment-student-risk-factors-001`, `ethics-risk-moe-student-crisis-management-boundary-001` |

---

# Workflow 2：个案信息整理

## 默认检索分区

- `case-recording`
- `ethics-risk`
- `intake-assessment`

## 推荐 topic

| 用户意图 | topic |
|---|---|
| 整理个案背景 | `case_summary_structure`, `biopsychosocial_assessment`, `fact_vs_inference`, `presenting_concern`, `information_gap` |
| 提取风险信号 | `risk_signal`, `self_harm`, `suicide_risk`, `harm_to_others`, `abuse_safeguarding` |
| 提取关系线索 | `relationship_context`, `family_context`, `social_support` |
| 区分事实和推测 | `fact_vs_inference`, `clinical_hypothesis_boundary` |
| 用户要求诊断 | `diagnosis_boundary`, `professional_boundary` |

## 检索示例

```text
workflow = workflow_2_case_summary
query_topics = [
  "fact_vs_inference",
  "biopsychosocial_assessment",
  "case_summary_structure",
  "risk_signal",
  "information_gap"
]
```

## 推荐 chunk

| 场景 | 优先 chunk |
|---|---|
| 整理个案背景 | `intake-assessment-biopsychosocial-client-assessment-001`, `case-recording-cps-professional-materials-recording-001`, `case-recording-bacp-accurate-relevant-records-001` |
| 提取风险信号 | `ethics-risk-china-risk-boundary-self-harm-harm-to-others-001`, `ethics-risk-suicide-risk-inquiry-topics-001`, `ethics-risk-china-mental-health-law-referral-boundary-001` |
| 用户要求诊断 | `ethics-risk-cps-professional-boundary-001`, `ethics-risk-china-mental-health-law-referral-boundary-001` |
| 学生个案 | `intake-assessment-student-risk-factors-001`, `ethics-risk-moe-student-crisis-management-boundary-001` |
| 外部分享/报告 | `ethics-risk-cps-case-report-deidentification-001`, `forms-fields-pipl-sensitive-field-rules-001` |

---

# Workflow 3：Session 总结与咨询记录生成

## 默认检索分区

- `session-notes`
- `case-recording`
- `ethics-risk`

## 推荐 topic

| 用户意图 | topic |
|---|---|
| 生成普通咨询记录 | `session_note_structure`, `client_statement`, `counselor_intervention`, `client_response`, `next_step` |
| 生成 SOAP | `soap_format`, `subjective_objective_assessment_plan` |
| 生成 DAP | `dap_format`, `data_assessment_plan` |
| 生成 BIRP | `birp_format`, `behavior_intervention_response_plan` |
| 记录风险变化 | `risk_change_documentation`, `suicide_risk`, `self_harm`, `safeguarding` |
| 用户要求治疗方案 | `treatment_plan_boundary`, `professional_boundary` |

## 检索示例

```text
workflow = workflow_3_session_note
query_topics = [
  "session_note_structure",
  "risk_change_documentation",
  "fact_vs_inference",
  "next_step"
]
```

## 推荐 chunk

| 场景 | 优先 chunk |
|---|---|
| 普通 session 记录 | `session-notes-risk-change-documentation-001`, `case-recording-cps-professional-materials-recording-001`, `case-recording-apa-record-keeping-purpose-context-001` |
| 出现自杀/自伤风险 | `session-notes-risk-change-documentation-001`, `ethics-risk-china-risk-boundary-self-harm-harm-to-others-001`, `ethics-risk-suicide-risk-inquiry-topics-001` |
| 涉及就医/精神科 | `ethics-risk-china-mental-health-law-referral-boundary-001`, `ethics-risk-cps-professional-boundary-001` |
| 涉及保密/记录保存 | `session-notes-bacp-confidentiality-record-keeping-001`, `ethics-risk-cps-informed-consent-confidentiality-001` |
| 学生危机 | `ethics-risk-moe-student-crisis-management-boundary-001`, `ethics-risk-china-risk-boundary-self-harm-harm-to-others-001` |

---

# 路由不确定时

如果用户只粘贴笔记，且没有明确任务，不检索正式 RAG，先澄清：

```text
你希望我把这些笔记整理成个案信息摘要，还是生成本次 session 的咨询记录？如果这是初访材料，我也可以基于它生成后续需要补充询问的信息表。
```

如果用户要求流派分析，v0.1 不检索流派库，回复：

```text
v0.1 阶段先生成统一基础信息抓取结果。CBT、人本、精神动力、家庭系统等流派框架更适合用于后续个案概念化或咨询方案设计。
```
