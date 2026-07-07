---
source_id: biopsychosocial-assessment-001
title: "Biopsychosocial Model and Comprehensive Client Assessment"
organization: "George L. Engel / NCBI Bookshelf secondary review"
url: "https://www.ncbi.nlm.nih.gov/books/NBK552030/"
source_type: scholarly_model_review
publication_date: "2019-03-29"
accessed_date: "2026-05-29"
jurisdiction: "international"
language: "en"
workflow_scope:
  - workflow_1_intake_form
  - workflow_2_case_summary
rag_section:
  - intake-assessment
review_status: approved
reviewer: "assistant"
copyright_note: "Use summary and model-derived assessment structure only. Do not reproduce copyrighted article text."
---

# 摘要

本资料卡中的模型指 biopsychosocial model，即“生物-心理-社会模型”，不是 British Psychological Society。该模型通常追溯到 George L. Engel 1977 年提出的新医学模型，用于提醒临床工作不能只从生物医学角度理解健康和疾病，也需要纳入个人经验、心理过程、社会处境和照护系统等因素。NCBI Bookshelf 2019 年相关综述指出，该模型在医疗、心理、社会工作等临床与教学场景中常被用作综合评估框架，但也存在过于宽泛、需要结合具体问题具体化的局限。对 v0.1 来说，它适合用于“来访综合身心状态评估模板”，帮助 Agent 系统收集生物、心理和社会三个层面的信息。

# 可用内容

- 生物维度：身体健康、睡眠、食欲、精力、药物、既往疾病、精神科就诊和物质使用等。
- 心理维度：主诉、情绪、认知、行为、应对方式、创伤/压力、风险信号、资源和咨询目标等。
- 社会维度：家庭、亲密关系、学习/工作、经济、居住、社会支持、文化和环境压力等。
- 适合作为初访信息收集、个案信息整理和信息缺口检查的框架。
- 可与中国本地伦理、精神卫生法风险边界、个人信息保护法字段规则结合使用。

# 不适用或需谨慎内容

- 生物-心理-社会模型不是诊断工具，不应生成诊断结论。
- 不应把“生物、心理、社会”三栏机械填满；应根据来访者问题和场景选择最小必要信息。
- 不应替代风险评估、伦理判断、医学诊断或机构流程。
- 涉及医疗、药物、精神障碍诊断和危机风险时，应提醒咨询师建议进一步专业评估或就医。

# 建议入库位置

- `rag/intake-assessment/biopsychosocial-client-assessment-template.md`
- `rag/intake-assessment/biopsychosocial-information-gap-check.md`
- `rag/case-recording/biopsychosocial-case-summary-structure.md`

# 人工审核备注

- 本卡已初步审核为 approved，用于 v0.1 的综合身心状态评估模板。
- 需注意缩写歧义：在项目内统一写作 `biopsychosocial` 或“生物-心理-社会模型”，避免与 British Psychological Society 混淆。
