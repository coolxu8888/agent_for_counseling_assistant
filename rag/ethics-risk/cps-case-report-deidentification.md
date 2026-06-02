---
chunk_id: ethics-risk-cps-case-report-deidentification-001
title: "案例报告与去识别化"
source_id: cps-recording-confidentiality-001
source_url: "https://journal.psych.ac.cn/xlxb/article/2018/0439-755X/0439-755X-50-11-1314.shtml"
source_type: official_association_journal_publication
rag_section: ethics-risk
workflow_scope:
  - workflow_2_case_summary
  - workflow_3_session_note
topic:
  - deidentification
  - case_report
  - confidentiality
risk_level: high
review_status: approved
last_reviewed: "2026-05-30"
---

# 核心规则

在教学、科研、督导或报告中使用个案材料时，应保护服务对象身份，避免可识别信息暴露。去识别化不只是删除姓名，还应考虑年龄、职业、学校、家庭结构、事件细节等组合后是否仍可识别。

# Agent 使用方式

当用户要求生成报告、案例摘要或可外部分享材料时，Agent 应提示去识别化，并尽量泛化可识别细节。若材料含高度敏感经历，应提醒咨询师确认授权和使用范围。

外部分享或督导群摘要应默认使用更强的泛化策略：

- 姓名、昵称、学号、具体学校、院系、单位、地名等直接标识符不得出现在输出中。
- 精确年级、职级、职业身份应泛化为与咨询理解相关的较宽类别，例如“高校学生”“研究生阶段学生”“青年职场来访者”。
- 家庭结构细节应默认泛化为“重要家庭结构变化”“家庭支持相关议题”等表述；只有当该信息与督导问题直接相关且已确认分享授权时，才可在更抽象层级保留。
- 独特事件细节、时间点和关系组合可能形成再识别风险，应优先保留功能性描述，例如“与重要学业/工作关系中的权威人物发生冲突”，而不是完整复述可识别情节。
- 去识别不仅适用于“已知事实”栏目，也适用于“信息缺口”“后续询问问题”“初步假设”等所有输出部分。

示例转换：

- “北师大研二”应写为“某高校研究生阶段学生”，不得写“某高校研究生二年级学生”。
- “父母离异”应写为“重要家庭结构变化”或“家庭支持相关议题”，不得原样保留“父母离异”“父母离婚”等具体家庭结构。
- “小林”应写为“来访者”或“个案 A”，不得保留姓名或化名线索。

# 禁止用法

不得输出可直接识别来访者身份的案例材料。不得将“已去掉姓名”视为充分去识别化。不得在外部分享版中原样保留姓名、具体学校、精确年级、具体家庭结构等组合识别信息。不得替机构判断发布或分享是否合法合规。

# 适用范围

适用于个案摘要、session 总结、报告草稿、督导材料和教学案例草稿。

# 相关 chunk

- `case-recording-cps-professional-materials-recording-001`
- `forms-fields-pipl-sensitive-field-rules-001`
