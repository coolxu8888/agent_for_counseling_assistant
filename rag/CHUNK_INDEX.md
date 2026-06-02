# RAG Chunk Index

本索引汇总当前已切分的正式 RAG chunk。所有条目均为 `review_status: approved`。

## 统计

| 分区 | 数量 |
|---|---:|
| `ethics-risk` | 9 |
| `case-recording` | 3 |
| `session-notes` | 2 |
| `intake-assessment` | 2 |
| `forms-fields` | 2 |
| 合计 | 18 |

## ethics-risk

| chunk_id | 文件 | 主要用途 |
|---|---|---|
| `ethics-risk-cps-professional-boundary-001` | `ethics-risk/cps-professional-boundary.md` | 不诊断、不替代咨询师判断 |
| `ethics-risk-cps-informed-consent-confidentiality-001` | `ethics-risk/cps-informed-consent-confidentiality.md` | 知情同意、保密、保密例外 |
| `ethics-risk-cps-case-report-deidentification-001` | `ethics-risk/cps-case-report-deidentification.md` | 案例报告、去识别化 |
| `ethics-risk-china-mental-health-law-referral-boundary-001` | `ethics-risk/china-mental-health-law-referral-boundary.md` | 精神卫生法下心理咨询边界与就医建议 |
| `ethics-risk-china-risk-boundary-self-harm-harm-to-others-001` | `ethics-risk/china-risk-boundary-self-harm-harm-to-others.md` | 自伤、自杀、他伤风险边界 |
| `ethics-risk-nhc-emergency-crisis-intervention-boundary-001` | `ethics-risk/nhc-emergency-crisis-intervention-boundary.md` | 危机干预原则与机构流程边界 |
| `ethics-risk-moe-student-crisis-management-boundary-001` | `ethics-risk/moe-student-crisis-management-boundary.md` | 学生心理危机、医校协同边界 |
| `ethics-risk-suicide-risk-inquiry-topics-001` | `ethics-risk/suicide-risk-inquiry-topics.md` | 自杀风险询问主题 |
| `ethics-risk-suicide-ideation-behavior-screening-topics-001` | `ethics-risk/suicide-ideation-behavior-screening-topics.md` | 自杀意念与行为筛查主题 |

## case-recording

| chunk_id | 文件 | 主要用途 |
|---|---|---|
| `case-recording-cps-professional-materials-recording-001` | `case-recording/cps-professional-materials-recording.md` | 专业资料、个案记录、敏感信息处理 |
| `case-recording-bacp-accurate-relevant-records-001` | `case-recording/bacp-accurate-relevant-records.md` | 记录准确、相关、限于必要 |
| `case-recording-apa-record-keeping-purpose-context-001` | `case-recording/apa-record-keeping-purpose-context.md` | 记录目的、服务连续性、语境限制 |

## session-notes

| chunk_id | 文件 | 主要用途 |
|---|---|---|
| `session-notes-risk-change-documentation-001` | `session-notes/risk-change-documentation.md` | session 风险变化记录 |
| `session-notes-bacp-confidentiality-record-keeping-001` | `session-notes/bacp-confidentiality-record-keeping.md` | session 记录中的保密与记录保存 |

## intake-assessment

| chunk_id | 文件 | 主要用途 |
|---|---|---|
| `intake-assessment-biopsychosocial-client-assessment-001` | `intake-assessment/biopsychosocial-client-assessment-template.md` | 生物-心理-社会综合评估 |
| `intake-assessment-student-risk-factors-001` | `intake-assessment/student-risk-factors.md` | 学生场景风险因素 |

## forms-fields

| chunk_id | 文件 | 主要用途 |
|---|---|---|
| `forms-fields-pipl-sensitive-field-rules-001` | `forms-fields/pipl-sensitive-field-rules.md` | 敏感字段、risk_signal 标注 |
| `forms-fields-pipl-minimum-necessary-001` | `forms-fields/pipl-minimum-necessary-fields.md` | 表单字段最小必要原则 |

## Workflow 检索建议

### Workflow 1：初访信息收集表生成

优先检索：

- `intake-assessment-biopsychosocial-client-assessment-001`
- `ethics-risk-cps-informed-consent-confidentiality-001`
- `ethics-risk-china-risk-boundary-self-harm-harm-to-others-001`
- `forms-fields-pipl-sensitive-field-rules-001`
- `forms-fields-pipl-minimum-necessary-001`

学生场景额外检索：

- `intake-assessment-student-risk-factors-001`
- `ethics-risk-moe-student-crisis-management-boundary-001`

### Workflow 2：个案信息整理

优先检索：

- `intake-assessment-biopsychosocial-client-assessment-001`
- `case-recording-cps-professional-materials-recording-001`
- `case-recording-bacp-accurate-relevant-records-001`
- `ethics-risk-china-risk-boundary-self-harm-harm-to-others-001`
- `ethics-risk-cps-professional-boundary-001`

### Workflow 3：Session 总结与咨询记录生成

优先检索：

- `session-notes-risk-change-documentation-001`
- `session-notes-bacp-confidentiality-record-keeping-001`
- `case-recording-cps-professional-materials-recording-001`
- `case-recording-apa-record-keeping-purpose-context-001`
- `ethics-risk-china-mental-health-law-referral-boundary-001`

