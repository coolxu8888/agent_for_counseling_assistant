# Source Cards Index

资料卡用于记录候选来源及审核状态。只有 `approved` 的资料卡可以切分为正式 RAG chunk。

## 第一批候选来源

| 优先级 | source_id | 来源 | 主要用途 | 状态 |
|---|---|---|---|---|
| P0 | `cps-ethics-001` | 中国心理学会：临床与咨询心理学工作伦理守则（第二版） | 本地伦理原则、专业边界、知情同意与保密 | approved |
| P0 | `bacp-standards-001` | BACP Ethical Framework: Working to Professional Standards | 记录准确性、转介、专业标准 | approved |
| P0 | `bacp-conf-record-001` | BACP Good Practice in Action 065 | 保密、记录保存、知情同意 | approved |
| P0 | `china-mental-health-law-risk-001` | 中华人民共和国精神卫生法 + CPS 伦理 | 自伤、自杀、他伤及疑似精神障碍风险边界 | approved |
| P0 | `samhsa-safe-t-001` | SAMHSA SAFE-T | 自杀风险询问、保护因素、记录 | pending |
| P0 | `cps-recording-confidentiality-001` | 中国心理学会：专业资料、记录、保密与去识别化 | 中文语境下记录资料、录音录像、案例去识别化 | approved |
| P0 | `china-pipl-sensitive-fields-001` | 中华人民共和国个人信息保护法 | 敏感个人信息与表单字段规范 | approved |
| P0 | `biopsychosocial-assessment-001` | 生物-心理-社会模型 | 来访综合身心状态评估模板 | approved |
| P1 | `nhc-emergency-crisis-principles-001` | 卫生部紧急心理危机干预指导原则 | 突发事件心理危机干预原则、重点人群、报告边界 | approved |
| P1 | `moe-student-mental-health-management-001` | 教育部加强学生心理健康管理工作的通知 | 学生筛查预警、精准干预、医校协同 | approved |
| P1 | `moe-student-mental-health-action-001` | 教育部等十七部门学生心理健康专项行动计划 | 学生心理危机预警、转介、医教协同 | pending |
| P1 | `apa-record-keeping-001` | APA Record Keeping Guidelines | 记录保存原则，需确认版本有效性 | approved |
| P2 | `csrs-samhsa-001` | SAMHSA C-SSRS catalog entry | 自杀意念与行为筛查主题，需审授权 | pending |

## 建议审核顺序

1. 先审核 P0：CPS 中国本地伦理资料、CPS 记录与保密资料、《中华人民共和国精神卫生法》风险边界、个人信息保护法字段规范、BACP、SAMHSA SAFE-T。
2. 再审核 P1：卫生部紧急心理危机干预指导原则、教育部学生心理健康管理通知、教育部学生心理健康专项行动计划、APA 记录保存指南。
3. 最后处理 P2：C-SSRS 需要确认官方来源、版本和授权后再决定是否入库。

## 审核后动作

- `approved`：切成正式 chunk，放入 `rag/ethics-risk/`、`rag/case-recording/`、`rag/intake-assessment/` 或 `rag/session-notes/`。
- `pending`：保留资料卡，不进入检索。
- `rejected`：移动或复制摘要到 `rag/rejected-sources/`，写明拒绝原因。
