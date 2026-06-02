# RAG Test Run 2026-05-30

## 测试目的

本轮测试用于验证咨询师助理 Agent v0.1 的第一批 RAG chunk 是否已经完成基础可用性检查：

- chunk 文件是否存在；
- chunk_id 是否可被索引；
- `RAG_RETRIEVAL_MAP.md` 是否能把典型用户意图路由到正确 chunk；
- `counselor-agent-v0.1-test-cases.md` 是否覆盖新增 RAG 专项场景；
- 高风险、敏感信息、诊断边界等约束是否有对应资料支撑。

本轮不是完整端到端模型测试。当前尚未接入真实向量库、embedding 检索器或线上 Agent runtime，因此结果只代表“资料库结构与路由设计可进入下一步联调”。

## 测试范围

| 项目 | 结果 |
|---|---|
| 正式 chunk 数量 | 18 |
| `ethics-risk` | 9 |
| `case-recording` | 3 |
| `session-notes` | 2 |
| `intake-assessment` | 2 |
| `forms-fields` | 2 |
| 空 `chunk_id` | 仅存在于 `rag/CHUNK_TEMPLATE.md`，不属于正式资料库 |

## Chunk 存在性检查

以下正式 chunk 均已在对应文件中找到 `chunk_id`：

| chunk_id | 状态 |
|---|---|
| `case-recording-apa-record-keeping-purpose-context-001` | PASS |
| `case-recording-bacp-accurate-relevant-records-001` | PASS |
| `case-recording-cps-professional-materials-recording-001` | PASS |
| `ethics-risk-china-mental-health-law-referral-boundary-001` | PASS |
| `ethics-risk-china-risk-boundary-self-harm-harm-to-others-001` | PASS |
| `ethics-risk-cps-case-report-deidentification-001` | PASS |
| `ethics-risk-cps-informed-consent-confidentiality-001` | PASS |
| `ethics-risk-cps-professional-boundary-001` | PASS |
| `ethics-risk-moe-student-crisis-management-boundary-001` | PASS |
| `ethics-risk-nhc-emergency-crisis-intervention-boundary-001` | PASS |
| `ethics-risk-suicide-ideation-behavior-screening-topics-001` | PASS |
| `ethics-risk-suicide-risk-inquiry-topics-001` | PASS |
| `forms-fields-pipl-minimum-necessary-001` | PASS |
| `forms-fields-pipl-sensitive-field-rules-001` | PASS |
| `intake-assessment-biopsychosocial-client-assessment-001` | PASS |
| `intake-assessment-student-risk-factors-001` | PASS |
| `session-notes-bacp-confidentiality-record-keeping-001` | PASS |
| `session-notes-risk-change-documentation-001` | PASS |

## RAG 专项用例检查

### Case 16：生物-心理-社会综合评估

| 检查项 | 结果 |
|---|---|
| 目标 workflow | Workflow 1：初访信息收集表生成 |
| 应命中 chunk | `intake-assessment-biopsychosocial-client-assessment-001` |
| 路由地图覆盖 | PASS |
| 测试用例覆盖 | PASS |
| 关键边界 | 该框架用于身心社会信息整理，不作为诊断工具 |
| 结论 | PASS |

### Case 17：系统字段与敏感信息

| 检查项 | 结果 |
|---|---|
| 目标 workflow | Workflow 1：系统字段版初访表 |
| 应命中 chunk | `forms-fields-pipl-sensitive-field-rules-001`, `forms-fields-pipl-minimum-necessary-001` |
| 路由地图覆盖 | PASS |
| 测试用例覆盖 | PASS |
| 关键边界 | 不应接受“所有字段都必填”；敏感字段和风险字段需要显式标注 |
| 结论 | PASS |

### Case 18：学生危机场景

| 检查项 | 结果 |
|---|---|
| 目标 workflow | Workflow 2：个案信息整理 |
| 应命中 chunk | `intake-assessment-student-risk-factors-001`, `ethics-risk-moe-student-crisis-management-boundary-001`, `ethics-risk-china-risk-boundary-self-harm-harm-to-others-001` |
| 路由地图覆盖 | PASS |
| 测试用例覆盖 | PASS |
| 关键边界 | 单独列出自杀/自伤相关风险信号；提示按学校/机构流程与必要转介处理；不替咨询师直接决定通知对象 |
| 结论 | PASS |

### Case 19：对外分享个案摘要

| 检查项 | 结果 |
|---|---|
| 目标 workflow | Workflow 2 或报告草稿辅助 |
| 应命中 chunk | `ethics-risk-cps-case-report-deidentification-001`, `forms-fields-pipl-sensitive-field-rules-001` |
| 路由地图覆盖 | PASS |
| 测试用例覆盖 | PASS |
| 关键边界 | 去除或泛化姓名、学校、年级、家庭结构等可识别信息 |
| 结论 | PASS |

### Case 20：精神科/诊断边界

| 检查项 | 结果 |
|---|---|
| 目标 workflow | Workflow 2 或 Workflow 3 |
| 应命中 chunk | `ethics-risk-china-mental-health-law-referral-boundary-001`, `ethics-risk-cps-professional-boundary-001` |
| 路由地图覆盖 | PASS |
| 测试用例覆盖 | PASS |
| 关键边界 | 不做精神障碍诊断；可记录疑似精神病性体验线索，并提醒必要时就医或联合精神科评估 |
| 结论 | PASS |

## 发现的问题

1. 当前测试仍是结构性测试，尚未验证真实检索排序、召回率、上下文拼接长度和最终回答稳定性。
2. `RAG_RETRIEVAL_MAP.md` 已有明确 chunk 推荐，但还没有机器可读版本。后续如果要接入程序，建议生成一个 `rag/retrieval-map.v0.1.json`。
3. `counselor-agent-v0.1-system-prompt.md` 目前是可读提示词草案，还没有拆成 runtime 可直接装载的模块，例如 role、routing、rag_policy、output_contract。
4. 目前没有自动化脚本检查 chunk 元数据完整性，例如 `chunk_id` 唯一性、`review_status`、`source_cards`、`intended_use` 等字段。

## 本轮结论

第一批 RAG chunk 已通过 v0.1 结构性测试，可以进入下一步：

1. 制作机器可读的检索配置；
2. 写一个轻量的 chunk 元数据校验脚本；
3. 用 Case 16-20 做一轮真实 Agent 输出样例测试；
4. 根据输出样例继续调整系统提示词和 RAG 拼接策略。
