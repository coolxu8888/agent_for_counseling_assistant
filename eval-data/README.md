# Eval Data

本目录存放咨询师助理 Agent 的本地评测数据。

## 文件

| 文件 | 用途 |
|---|---|
| `agent_eval_training_data.20260531.xlsx` | 用户提供并移入项目的原始训练/评测 Excel |
| `crisis-level-cases.v0.1.json` | 从用户提供的 Excel 导出的危机等级题目、标答和数据质量标记 |

## crisis-level-cases.v0.1.json

来源文件：

```text
eval-data\agent_eval_training_data.20260531.xlsx
```

Excel 结构：

- `Sheet1`：题目与标答。
- `Sheet2`：等级、标准、定义、备注。

字段说明：

| 字段 | 说明 |
|---|---|
| `case_id` | 项目内评测用例 ID |
| `source_row` | Excel 原始行号 |
| `question` | 题目材料 |
| `gold_answer` | 标答全文 |
| `expected_level` | 用于测试的期望等级，由 Sheet1 标答开头等级提取 |
| `answer_level_prefix` | 从标答开头提取的等级 |
| `criterion` | 从 Sheet2 合并的等级标准 |
| `definition` | 从 Sheet2 合并的等级定义 |
| `notes` | 从 Sheet2 合并的备注 |
| `data_quality_status` | 数据质量状态 |
| `data_quality_issues` | 冲突或缺失说明 |

当前导入结果：

```text
case_count: 19
standard_count: 5
issue_count: 0
```

## 使用边界

这份数据用于模型训练、人工 eval 和回归测试，不作为正式临床量表或危机处置依据。

真实个案中，Agent 只能输出候选等级和依据，并提醒咨询师进一步专业评估、按机构流程处置或转介。
