# 咨询师助理 Agent

当前产品由两个表面组成：`ios-app/` 是面向咨询师的原生 iOS 客户端，也是唯一 App Store 应用根目录；`web-workbench/` 与 `scripts/web_workbench.py` 组成保留的独立托管 Web/API 产品。产品阶段为 `App Store Release Candidate`，首个公开版本为 `1.0.0 (1)`。Web 服务及其服务端能力不会进入 iOS 包。

文件名、路径、schema 或 API 中的 `v0.1` / `0.1.0` / `MVP` 仅为历史兼容标识，不代表当前产品阶段或能力版本。版本与目录边界以 [`docs/product-editions-and-directory-contract.md`](docs/product-editions-and-directory-contract.md) 为准，当前迭代状态以 [`docs/product-loop-state.md`](docs/product-loop-state.md) 为准。

> 安全提示：仅使用去标识化材料；所有模型输出都必须由具备相应资质的专业人员人工复核，不能替代诊断、风险评估、危机处置或临床决策。

## 产品目录

| 目录 | 定位 | 是否进入 App Store 包 |
|---|---|---|
| `ios-app/` | 原生 SwiftUI 主产品、iOS 测试与上架元数据 | 是，且仅限该 target 声明的资源 |
| `scripts/` | 共享后端、Agent、RAG、评测与独立 Web/API host | 否 |
| `web-workbench/` | 保留的托管 Web 产品前端 | 否 |
| `render.yaml` | 独立 Web 服务的 Render 部署定义 | 否 |
| `rag/`、`eval-*` | 服务端知识与工程评测 | 否 |

## 本地 Web 运行

从 `.env.example` 复制创建本地 `.env`，至少配置 `DEEPSEEK_API_KEY`；不要提交 `.env`。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run-web-workbench.ps1
```

默认地址：`http://127.0.0.1:8765`

## Native iOS App

iOS 工程、XcodeGen 生成方式、签名占位配置与完整移动端 API 合同见 [`ios-app/README.md`](ios-app/README.md)。本地可先运行包边界检查：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ios-app\scripts\validate-package-boundary.ps1
```

原生客户端通过 `/api/mobile/v1` 使用 bearer session 调用登录、会话、个案、Agent 运行、历史重开和受控产物下载接口；workspace token 存储在 iOS Keychain，模型供应商密钥始终留在服务端。

真正的 App Store readiness 必须在 macOS/Xcode 环境完成生成、编译、单元/UI 测试、模拟器与设备验收、签名归档、TestFlight 和 App Store Connect 校验。

## W1–W6 完成度

`workflow-completion.json` 是 W1–W6 五道验收门的机器可读事实源；可读矩阵位于 [`docs/product-loop-state.md`](docs/product-loop-state.md#w1-w6-unified-completion-matrix)。运行以下命令检查状态文件和进度文档是否一致：

```powershell
python scripts/workflow_completion.py --check
```

## Render Web

Render 只部署一个服务：`counselor-agent-web`。

规范生产地址：`https://counselor-agent-web.onrender.com`

启动命令：

```text
python scripts/web_workbench.py --host 0.0.0.0 --port $PORT
```

健康检查：`/health`

托管 smoke 依次检查 `/health`、`/api/session` 和认证；未使用 `--skip-run` 时还会检查可选的 `/api/run` 模型调用。先把凭据放入环境变量，再运行不触发模型调用的产品接口检查：

```powershell
python scripts/hosted_smoke.py --base-url https://counselor-agent-web.onrender.com --username $env:WORKBENCH_USER --password $env:WORKBENCH_PASSWORD --skip-run
```

需要验证真实 Agent 运行时，再显式执行：

```powershell
python scripts/hosted_smoke.py --base-url https://counselor-agent-web.onrender.com --username $env:WORKBENCH_USER --password $env:WORKBENCH_PASSWORD --workflow AUTO --real-run
```

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
- `counselor-agent-v0.1-system-prompt.md` 用于兼容离线评测和三个基础工作流 prompt；完整能力由运行时组装，文件名中的 `v0.1` 仅为兼容标识。

## 工程证据

来源追溯、安全边界、评测依据和关键产品决策保存在 [`docs/evidence/`](docs/evidence/README.md)。这些文件不进入运行时 prompt。
