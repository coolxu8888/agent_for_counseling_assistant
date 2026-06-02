# 咨询师助理 Agent v0.1

这是一个面向心理咨询师端的咨询助理 Agent MVP。v0.1 阶段聚焦三个基础能力：

1. 初访信息收集表生成
2. 个案信息整理
3. Session 总结与咨询记录生成

v0.1 的核心原则是：先建立统一、流派无关的基础信息抓取系统。CPS/中国本地伦理与法律资料作为伦理、风险、记录规范和专业边界的主要参考；境外专业资料只作为补充参考，并需标注地域限制。CBT、人本、精神动力、家庭系统等流派框架留到后续个案概念化和咨询方案设计中使用。

当前 RAG 已完成第一批正式 chunk 切分：共 18 个 approved chunk，覆盖伦理风险、个案记录、session 记录、初访评估和表单字段。

## 文件说明

| 文件 | 用途 |
|---|---|
| `agent-capacity-map.md` | Agent 能力地图，说明整体产品能力边界 |
| `mvp-v0.1-scope.md` | MVP v0.1 范围，说明第一阶段做什么、不做什么 |
| `mvp-v0.1-workflows.md` | 三个 P0 能力的详细工作流 |
| `counselor-agent-v0.1-system-prompt.md` | 可直接用于模型配置的系统提示词草案 |
| `counselor-agent-v0.1-test-cases.md` | 用于验证 Agent 行为的测试用例 |
| `model-eval-v0.1.md` | 人工模型评测记录，用于粘贴模型输出并评分 |
| `model-eval-workflow-regression-v0.1.md` | 三个 P0 workflow 的典型输入回归测试记录 |
| `model-eval-crisis-level-v0.1.md` | 危机等级候选判断的人工模型评测记录 |
| `crisis-level-rubric-v0.1.md` | 基于用户训练数据整理的危机等级候选判断 rubric |
| `counselor-agent-v0.1-rag-build-plan.md` | RAG 资料库建设计划，定义资料来源、审核、切块和 metadata 规则 |
| `agent-runtime-architecture.md` | Agent 运行时架构，说明路由、RAG 检索、提示词组装和输出检查 |
| `eval-data/crisis-level-cases.v0.1.json` | 从用户 Excel 导入的危机等级题目、标答和数据质量标记 |
| `rag/CHUNK_TEMPLATE.md` | 正式 RAG chunk 模板 |
| `rag/CHUNK_INDEX.md` | 已切分正式 RAG chunk 的索引和 workflow 检索建议 |
| `rag/RAG_TEST_RUN_2026-05-30.md` | 第一批 RAG chunk 的结构性测试记录 |
| `rag/RAG_RUNTIME_SMOKE_TEST_2026-05-30.md` | 最小 retrieval runner 的冒烟测试记录 |
| `rag/SOURCE_CARD_REVIEW_GUIDE.md` | 资料卡人工审核指南 |
| `rag/RAG_RETRIEVAL_MAP.md` | workflow 与 RAG 分区/topic 的检索映射表 |
| `rag/retrieval-map.v0.1.json` | workflow 检索策略的机器可读配置 |
| `scripts/validate-rag.ps1` | RAG chunk 元数据和检索配置校验脚本 |
| `scripts/run-retrieval.ps1` | 最小 RAG retrieval runner，用于路由、取 chunk 和组装 prompt context |
| `scripts/build-crisis-eval-prompt.ps1` | 从危机等级评测数据生成单题 prompt package |
| `scripts/build-workflow-eval-prompts.ps1` | 生成三个 P0 workflow 的典型回归测试 prompt 文件 |
| `scripts/run-deepseek-workflow-evals.ps1` | 通过外部 Edge 自动发送 workflow eval prompt 并保存 raw output |
| `scripts/clean-eval-outputs.ps1` | 清洗 raw output，提取最终回答，并生成自动规则检查与分维度 rubric 汇总 |
| `eval-prompts/` | 三个 P0 workflow 的回归测试 prompt 文件 |
| `eval-results/` | DeepSeek Web 回归测试的 raw output、clean output 和检查汇总 |
| `counseling-agent-mvp.md` | 初访信息收集表三版本的早期 MVP 内容 |

## 推荐接入顺序

1. 使用 `counselor-agent-v0.1-system-prompt.md` 作为系统提示词。
2. 将 CPS/中国本地伦理、精神卫生法风险边界、记录规范、初访评估规范、咨询记录模板等资料放入 RAG。
3. 用 `mvp-v0.1-workflows.md` 校验路由和输出结构。
4. 用 `counselor-agent-v0.1-test-cases.md` 做首轮测试。
5. 按 `counselor-agent-v0.1-rag-build-plan.md` 建立最小 RAG 资料库。
6. 按 `rag/SOURCE_CARD_REVIEW_GUIDE.md` 审核资料卡。
7. 用 `rag/CHUNK_TEMPLATE.md` 将 approved 资料切成正式 RAG chunk。
8. 用 `rag/RAG_RETRIEVAL_MAP.md` 配置每个 workflow 的检索策略。
9. 用 `rag/RAG_TEST_RUN_2026-05-30.md` 检查第一批 chunk 的结构性测试结果。
10. 用 `rag/retrieval-map.v0.1.json` 作为程序读取的检索配置。
11. 运行 `scripts/validate-rag.ps1` 校验 chunk 元数据和检索配置。
12. 运行 `scripts/run-retrieval.ps1` 做本地路由、取 chunk 和 prompt context 组装测试。
13. 用 `model-eval-v0.1.md` 记录人工模型评测结果。
14. 用 `scripts/build-workflow-eval-prompts.ps1` 生成 workflow 回归测试 prompt。
15. 用 `scripts/run-deepseek-workflow-evals.ps1` 或人工复制方式跑模型输出。
16. 用 `scripts/clean-eval-outputs.ps1` 清洗 raw output，生成基础规则检查和分维度 rubric 汇总。
17. 参考 `agent-runtime-architecture.md` 接入路由、检索、提示词组装和输出检查。
18. 根据测试结果微调系统提示词、RAG 文档和输出模板。

## 本地运行命令

校验 RAG 资料库：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\validate-rag.ps1
```

测试最小检索链路：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-retrieval.ps1 -Query "帮我生成一个初访信息收集表" -SummaryOnly
```

输出完整 prompt context：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-retrieval.ps1 -Query "帮我生成本次咨询记录：来访者提到不想醒来，但没有具体计划。"
```

生成危机等级候选判断评测 prompt：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build-crisis-eval-prompt.ps1 -CaseId crisis-level-001
```

生成评测 prompt 并显示标答：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build-crisis-eval-prompt.ps1 -CaseId crisis-level-001 -IncludeGold
```

生成 workflow 回归测试 prompt：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build-workflow-eval-prompts.ps1
```

通过外部 Edge 的 DeepSeek Web 自动跑指定 workflow eval：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-deepseek-workflow-evals.ps1 -Ids W1-001,W2-003
```

清洗 raw output，并生成自动规则检查与分维度 rubric 汇总：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\clean-eval-outputs.ps1
```

清洗后的最终回答位于：

```text
eval-results/clean/
```

自动检查汇总位于：

```text
eval-results/eval-clean-summary.v0.1.md
eval-results/eval-clean-summary.v0.1.json
eval-results/eval-rubric-summary.v0.1.md
eval-results/eval-rubric-summary.v0.1.json
```

`eval-rubric-summary.v0.1.md` 会按以下维度给每条 eval 评分，并在 WARN / FAIL 时生成“问题、原因、修正建议”：

```text
路由正确、结构正确、RAG 使用合理、无诊断、无编造、风险处理、边界清晰、隐私最小化、v0.1 范围
```

## v0.1 不做的事

- 不做自动诊断
- 不替代咨询师做治疗决策
- 不做最终风险分级
- 真实个案中不做最终危机等级分级；训练/评测语境可输出候选等级和依据
- 不直接面向来访者提供咨询
- 不按流派切换基础信息收集模板
- 不生成完整咨询 Road Map

## 后续版本方向

v0.2 可以继续扩展：

- 个案概念化
- 按 CBT、人本、精神动力、家庭系统等流派生成概念化假设
- 咨询方案设计
- 访谈问题提纲
- 阶段性 Road Map
- 报告生成与机构模板适配
