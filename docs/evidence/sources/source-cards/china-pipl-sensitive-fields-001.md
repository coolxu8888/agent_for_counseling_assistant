---
source_id: china-pipl-sensitive-fields-001
title: "中华人民共和国个人信息保护法：敏感个人信息与表单字段规范"
organization: "全国人民代表大会常务委员会"
url: "https://www.npc.gov.cn/npc/c2597/c5854/bfflywwb/202311/t20231117_433007.html"
source_type: law
publication_date: "2021-08-20"
accessed_date: "2026-05-28"
jurisdiction: "中国大陆"
language: "zh-CN"
workflow_scope:
  - workflow_1_intake_form
rag_section:
  - forms-fields
  - ethics-risk
review_status: approved
reviewer: "user"
copyright_note: "法律文本公开可引用；正式 RAG 中仍应使用摘要化、规则化表达。"
---

# 摘要

《中华人民共和国个人信息保护法》为 v0.1 的系统字段版初访表、敏感字段标注和最小必要收集原则提供本地法律依据。该法将个人信息定义为以电子或其他方式记录的、与已识别或可识别自然人有关的各种信息，并规定处理个人信息应当具有明确、合理目的，限于实现处理目的的最小范围。该法还规定了敏感个人信息的范围，包括医疗健康、特定身份、行踪轨迹、不满十四周岁未成年人的个人信息等。对咨询师助理 Agent 来说，它可用于字段层面标注 `sensitive`、`required`、`risk_signal` 和最小必要原则。

# 可用内容

- 个人信息处理应有明确、合理目的，并与处理目的直接相关。
- 收集个人信息应限于实现处理目的的最小范围。
- 敏感个人信息包括一旦泄露或非法使用，容易导致人格尊严受侵害或人身、财产安全受危害的信息。
- 医疗健康信息、特定身份信息、不满十四周岁未成年人的个人信息等应被视为敏感个人信息。
- 处理敏感个人信息应具有特定目的、充分必要性，并采取严格保护措施。
- 可用于系统字段版初访表的 `sensitive: true`、`required: false`、`risk_signal: true` 等字段设计。

# 不适用或需谨慎内容

- 本资料卡不是完整隐私合规方案，不能替代法务审查。
- 不应仅凭该卡决定数据保存期限、跨境传输、授权文本或产品隐私政策。
- 未成年人信息、医疗健康信息、风险信息应在产品设计中额外谨慎处理。

# 建议入库位置

- `rag/forms-fields/pipl-sensitive-field-rules.md`
- `rag/forms-fields/pipl-minimum-necessary-fields.md`
- `rag/ethics-risk/pipl-sensitive-health-information.md`

# 人工审核备注

- 审核结论：approved。
- 建议优先切分“敏感个人信息定义”“最小必要原则”“未成年人信息”“系统字段标注规则”四类 chunk。

