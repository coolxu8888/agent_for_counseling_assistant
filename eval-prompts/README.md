# Workflow Eval Prompts

本目录存放 v0.1 三个 workflow 的典型回归测试 prompt。

## 使用方式

### 手工方式

1. 打开目标模型聊天窗口。
2. 逐个打开本目录下的 `.txt` 文件。
3. 将文件全文复制给模型。
4. 将模型回复粘贴回 `model-eval-workflow-regression-v0.1.md` 对应条目。
5. 按评分表打分。

### DeepSeek Web 自动化方式

先在外部 Edge 登录 DeepSeek，并进入可发送消息的聊天页，然后运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-deepseek-workflow-evals.ps1 -Ids W1-001,W2-003
```

跑完后清洗 raw output：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\clean-eval-outputs.ps1
```

输出位置：

```text
eval-results/*-deepseek-raw.txt
eval-results/clean/*-clean.md
eval-results/eval-clean-summary.v0.1.md
eval-results/eval-clean-summary.v0.1.json
```

## 当前测试集

| Eval ID | 文件 | 场景 |
|---|---|---|
| W1-001 | `W1-001-intake-counselor-interview.txt` | 默认咨询师访谈版初访表 |
| W1-002 | `W1-002-json-schema-sensitive-fields.txt` | 系统字段 JSON Schema + 敏感信息 |
| W1-003 | `W1-003-intake-gap-check-from-notes.txt` | 基于已有笔记生成补充询问表 |
| W2-001 | `W2-001-case-summary-basic.txt` | 普通个案背景整理 |
| W2-002 | `W2-002-student-crisis-case.txt` | 学生危机个案整理 |
| W2-003 | `W2-003-deidentified-supervision-summary.txt` | 外部分享/督导用去识别摘要 |
| W3-001 | `W3-001-session-note-basic.txt` | 普通 session 记录 |
| W3-003 | `W3-003-session-note-soap.txt` | SOAP 格式记录 |

## 重新生成

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build-workflow-eval-prompts.ps1
```
