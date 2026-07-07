# 咨询师助理 Agent v0.1 RAG 建库计划

## 1. 目标

本文档定义咨询师助理 Agent v0.1 的 RAG 资料库建设流程。

目标不是让 AI 无审核地从网络自动抓取资料，而是建立一条可控流程：

> 搜索权威资料 → 过滤来源 → 生成资料卡 → 人工审核 → 切块 → 写入 RAG 文档库 → 绑定到工作流

v0.1 的 RAG 资料只服务于三个 P0 能力：

1. 初访信息收集表生成
2. 个案信息整理
3. Session 总结与咨询记录生成

CBT、人本、精神动力、家庭系统等流派资料暂不进入 v0.1 的基础信息抓取 RAG，后续用于 v0.2 的个案概念化和咨询方案设计。

## 2. 建库原则

### 2.1 AI 可以做什么

AI 可以辅助：

- 搜索公开资料
- 初步判断来源类型
- 摘要资料内容
- 提取与 v0.1 workflow 相关的规则
- 生成资料卡
- 建议 RAG 分类
- 将已审核资料切成可检索 chunk
- 生成 metadata

### 2.2 AI 不可以自动做什么

AI 不应自动：

- 将未审核资料直接写入正式 RAG
- 把网络文章当作专业准则
- 使用来源不明的心理学内容
- 改写版权受限资料为大段可复用文本
- 基于单一来源形成高风险规则
- 把不同国家、机构、法律语境下的规范混为一谈
- 用流派资料替代伦理、记录和风险规范

## 3. 资料来源等级

### 3.1 优先来源

优先检索和使用：

| 来源类型 | 示例 | 用途 |
|---|---|---|
| 官方专业协会 | CPS、中国心理学会、BACP、APA、ACA 等 | 伦理、记录、专业实践、风险边界 |
| 政府或公共医疗机构 | NHS、WHO、SAMHSA、CDC 等 | 风险识别、危机转介、公共健康规范 |
| 大学或教学机构 | 大学公开课、培训手册、咨询中心指南 | 初访评估、记录模板、督导材料 |
| 机构公开模板 | 合规咨询机构公开表格 | 初访表、知情同意、记录模板 |
| 同行评审或出版资料 | 期刊文章、教材节选、出版社资料页 | 辅助理解，不直接替代规范 |

### 3.2 谨慎来源

可以参考但不能直接入库，除非人工审核：

- 心理咨询师个人博客
- 培训机构文章
- 媒体科普文章
- 商业平台帮助文档
- 二手整理资料
- AI 生成内容

### 3.3 禁止来源

不得进入 RAG：

- 无作者、无机构、无日期的文章
- 论坛、贴吧、问答社区内容
- 社交媒体碎片内容
- 明显营销导向材料
- 未经授权转载的书籍或课程资料
- 提供危险、非法或不符合伦理建议的内容
- 将自杀、自伤、虐待等高风险内容轻描淡写的资料

## 4. v0.1 RAG 分区

建议将 RAG 资料库拆成以下分区：

```text
rag/
  ethics-risk/
  intake-assessment/
  case-recording/
  session-notes/
  forms-fields/
  source-cards/
  rejected-sources/
```

### 4.1 ethics-risk

用途：

- 保密原则
- 保密例外
- 知情同意
- 风险识别
- 转介原则
- 危机服务边界
- 专业胜任力与边界

服务 workflow：

- Workflow 1：风险评估与知情同意栏目
- Workflow 2：风险信号识别
- Workflow 3：风险变化记录

### 4.2 intake-assessment

用途：

- 初访信息收集结构
- 初访访谈问题
- 来访者预填写表
- 初访风险筛查
- 信息缺口检查

服务 workflow：

- Workflow 1：初访表生成
- Workflow 1：基于已有笔记生成补充型初访表
- Workflow 2：初访资料整理

### 4.3 case-recording

用途：

- 个案资料记录原则
- 事实与推测区分
- 主诉、观察、判断的区分
- 敏感信息最小必要原则
- 记录保存与隐私保护

服务 workflow：

- Workflow 2：个案信息整理
- Workflow 3：session 记录

### 4.4 session-notes

用途：

- 普通咨询记录模板
- SOAP 格式
- DAP 格式
- BIRP 格式
- 本次主题、干预、反应、计划的记录方式

服务 workflow：

- Workflow 3：Session 总结与咨询记录生成

### 4.5 forms-fields

用途：

- 初访表字段设计
- JSON Schema 字段规范
- sensitive 字段标注
- risk_signal 字段标注
- 前端表单配置参考

服务 workflow：

- Workflow 1：系统字段版初访表

### 4.6 source-cards

用途：

- 保存每个候选来源的资料卡
- 记录来源 URL、机构、发布日期、适用模块、审核状态

### 4.7 rejected-sources

用途：

- 保存被拒绝来源的原因
- 避免后续重复采集不可靠资料

## 5. 资料卡格式

每个候选来源先生成一张资料卡，人工审核通过后才能进入正式 RAG。

建议格式：

```markdown
---
source_id: cps-ethics-001
title: ""
organization: ""
url: ""
source_type: official_association
publication_date: ""
accessed_date: ""
jurisdiction: ""
language: ""
workflow_scope:
  - workflow_1_intake_form
  - workflow_2_case_summary
  - workflow_3_session_note
rag_section:
  - ethics-risk
review_status: pending
reviewer: ""
copyright_note: ""
---

# 摘要

用 3 到 6 句话概括该资料与 v0.1 的关系。

# 可用内容

- 

# 不适用或需谨慎内容

- 

# 建议入库位置

- 

# 人工审核备注

- 
```

## 6. 正式 RAG 文档格式

人工审核通过后，将资料转为正式 RAG 文档。

建议格式：

```markdown
---
chunk_id: ethics-risk-confidentiality-001
title: "保密原则与保密例外"
source_id: cps-ethics-001
source_url: ""
source_type: official_association
rag_section: ethics-risk
workflow_scope:
  - workflow_1_intake_form
  - workflow_3_session_note
topic:
  - confidentiality
  - informed_consent
risk_level: medium
review_status: approved
last_reviewed: ""
---

# 核心规则

...

# Agent 使用方式

当生成知情同意栏目或咨询记录隐私说明时，参考本条规则。

# 禁止用法

不得将本条规则解释为绝对保密；涉及保密例外时需要提醒咨询师按机构流程处理。
```

## 7. Chunk 切分原则

RAG chunk 不应太长，也不应混合多个主题。

建议：

- 每个 chunk 只解决一个主题
- 每个 chunk 约 300 到 800 中文字
- 风险、伦理、记录格式分开切
- 保留来源 URL 和 source_id
- 对高风险内容增加 `risk_level`
- 对适用 workflow 增加 `workflow_scope`

示例主题：

- 保密原则
- 保密例外
- 知情同意
- 自伤风险询问
- 自杀风险询问
- 他伤风险询问
- 初访基本信息字段
- SOAP 记录结构
- DAP 记录结构
- 事实与推测区分

## 8. Metadata 字段建议

正式 RAG 文档建议至少包含：

| 字段 | 说明 |
|---|---|
| chunk_id | 唯一 ID |
| title | chunk 标题 |
| source_id | 来源资料卡 ID |
| source_url | 来源链接 |
| source_type | 来源类型 |
| rag_section | RAG 分区 |
| workflow_scope | 适用工作流 |
| topic | 主题标签 |
| risk_level | low / medium / high |
| review_status | pending / approved / rejected |
| last_reviewed | 最近人工审核日期 |

## 9. AI 搜索任务模板

当需要 AI 搜索资料时，使用以下任务模板：

```text
请搜索与【主题】相关的权威公开资料。

要求：
1. 优先官方专业协会、政府或公共医疗机构、大学咨询中心资料。
2. 不使用论坛、社交媒体、营销文章或无来源资料。
3. 每个候选来源生成资料卡。
4. 不直接写入正式 RAG。
5. 对版权、适用地区、发布日期和专业边界做备注。

主题：
- 

输出：
- 候选来源列表
- 每个来源的资料卡
- 推荐是否进入人工审核
```

## 10. 人工审核清单

资料进入正式 RAG 前，至少检查：

| 检查项 | 通过标准 |
|---|---|
| 来源可靠性 | 来源来自官方协会、公共机构、大学或其他可信机构 |
| 适用性 | 内容适用于咨询师端辅助，而不是来访者自助治疗 |
| 地域与法律语境 | 不把特定地区法律要求误用为通用规则 |
| 风险安全 | 不淡化自伤、自杀、他伤、虐待等风险 |
| 版权 | 不复制大段受版权保护内容 |
| 与 v0.1 相关性 | 能服务初访、个案整理或 session 记录 |
| 表述清晰度 | 能被 Agent 检索并稳定使用 |

审核结果：

- approved：进入正式 RAG
- pending：保留资料卡，暂不入库
- rejected：放入 rejected-sources，并记录原因

## 11. v0.1 最小资料清单

第一轮建库建议只做最小闭环：

### 11.1 ethics-risk

至少准备：

- 保密原则与保密例外
- 知情同意
- 自伤 / 自杀风险识别
- 他伤风险识别
- 虐待或不安全环境识别
- 转介与危机服务边界

### 11.2 intake-assessment

至少准备：

- 初访基本信息字段
- 来访原因与咨询期待
- 当前困扰评估
- 生活背景与支持资源
- 初访风险筛查
- 来访者预填写表语言原则

### 11.3 case-recording

至少准备：

- 事实与推测区分
- 主诉、观察、判断的区分
- 敏感信息最小必要原则
- 信息缺口标注

### 11.4 session-notes

至少准备：

- 普通咨询记录结构
- SOAP 记录结构
- DAP 记录结构
- BIRP 记录结构
- 风险变化记录原则

### 11.5 forms-fields

至少准备：

- 初访表 JSON Schema 字段规范
- sensitive 字段标注规则
- risk_signal 字段标注规则

## 12. 与 workflow 的绑定

| Workflow | 默认检索分区 |
|---|---|
| Workflow 1：初访信息收集表生成 | intake-assessment、ethics-risk、forms-fields |
| Workflow 2：个案信息整理 | case-recording、ethics-risk、intake-assessment |
| Workflow 3：Session 总结与咨询记录生成 | session-notes、case-recording、ethics-risk |

## 13. 后续执行顺序

建议按以下顺序推进：

1. 建立 `rag/` 目录结构。
2. 先人工确定 5 到 10 个权威来源。
3. 让 AI 为每个来源生成资料卡。
4. 人工审核资料卡。
5. 将 approved 资料切成正式 RAG chunk。
6. 用 v0.1 测试用例验证 Agent 是否正确调用资料。
7. 根据测试结果调整 chunk、metadata 和系统提示词。
