# 咨询师助理 Agent

当前产品阶段统一为“市场验证版”。文件名、路径、schema 或 API 中的 `v0.1` / `0.1.0` 仅为兼容标识，不代表当前产品阶段或能力版本。

> 安全提示：仅使用去标识化材料；所有模型输出都必须由具备相应资质的专业人员人工复核，不能替代诊断、风险评估、危机处置或临床决策。

## 本地运行

从 `.env.example` 复制创建本地 `.env`，至少配置 `DEEPSEEK_API_KEY`；不要提交 `.env`。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-web-workbench.ps1
```

默认地址：`http://127.0.0.1:8765`

## Render Web

启动命令：

```text
python scripts/web_workbench.py --host 0.0.0.0 --port $PORT
```

健康检查：`/health`

公开部署必要变量：

- `DEEPSEEK_API_KEY`
- `WORKBENCH_USER`
- `WORKBENCH_PASSWORD`

按需变量：

- `WORKBENCH_ALLOW_SIGNUP`
- `WORKBENCH_SIGNUP_INVITE_CODE`
- `WORKBENCH_MAX_UPLOAD_BYTES`
- `WORKBENCH_RETENTION_DAYS`
- `DEEPSEEK_BASE_URL`
- `DEEPSEEK_MODEL`
- `DEEPSEEK_TIMEOUT_SECONDS`

## 运行时 Prompt 清单

- `scripts/run_agent.py` 内置的角色、安全边界、Workflow 固定输出合同与工作流补充指令。
- `rag/**/*.md` 中带非空 `chunk_id` 的检索片段，由 retrieval map 按工作流装配。
- 当前用户输入；启用结构化输出时同时装配对应 schema 合同。
- `counselor-agent-v0.1-system-prompt.md` 是模型配置参考；文件名中的 `v0.1` 仅为兼容标识。
