# 移除 Coze 并统一独立 Web 服务设计

日期：2026-08-14

## 目标

项目停止维护 Coze 兼容路线，只保留以下独立 Web 产品入口：

`https://counselor-agent-web.onrender.com`

完成后，仓库内不再包含 Coze 功能、服务、路由、密钥配置、接口规范、测试、部署项或历史文字。现有 Web、移动 API、iOS 和评测成果必须保留。

这里的“仓库内”指当前主工作树中受版本控制或准备纳入版本控制的产品文件，不包含 `.git/` 提交历史、其他分支或 `.worktrees/` 中的独立工作树。本任务不改写 Git 历史。

本设计说明是实施前审阅所需的过渡文件，因为它必须列出待删除对象，所以也会在最终全仓清理步骤中删除；最终验收以实施后的工作树搜索结果为准。

## 当前问题

当前 Coze 适配器同时代理了部分 Web 和移动 API，相关测试也混在 Coze 测试文件中。因此直接删除适配器会造成移动端或 Web 回归覆盖丢失。

当前工作树还包含尚未提交的 iOS、共享 API、评测修复和产品文档。所谓“清理工作树”不是丢弃这些修改，而是安全整理、验证并提交本次应保留的成果，使 Git 状态最终清晰。

## 目标架构

### 单一服务

`scripts/web_workbench.py` 是唯一产品 Web 服务入口，负责：

- 提供 `web-workbench/` 静态页面；
- Web 登录、个案、运行、模板和文件下载 API；
- `/api/mobile/v1` 移动 API；
- `/health` 健康检查；
- 调用共享 Agent、RAG、校验和文档生成能力。

Render Blueprint 只保留 `counselor-agent-web` 服务。iOS、部署文档和冒烟测试统一使用 `https://counselor-agent-web.onrender.com`。

### 删除的兼容面

以下能力不再存在：

- Coze 专用 HTTP 服务和启动脚本；
- `/coze/*` 路由；
- `/service-info` 和 Coze OpenAPI 输出；
- Coze API Key 鉴权；
- Coze 插件导入规范及 Render 服务；
- 所有仅用于该兼容面的测试与文档。

## 迁移顺序

1. 建立可恢复的 Git 工作分支，保留当前所有非临时修改；不执行 `git reset --hard` 或 `git clean -fdx`。
2. 将 Coze 测试文件中仍属于 Web/mobile API 的回归用例迁入对应 Web 或移动 API 测试文件。
3. 确认 `web_workbench.py` 独立提供所有 Web、移动 API 和文件下载能力。
4. 将 iOS 配置、冒烟测试、README 和部署说明切换到独立 Web 地址。
5. 从 `render.yaml` 删除 Coze 服务，从环境变量示例删除 Coze 密钥。
6. 删除 Coze 服务端、启动脚本、接口规范、专用测试和专用文档。
7. 删除或重写现行文档与历史记录中的全部 Coze 文字，使全仓大小写不敏感搜索结果为零。
8. 运行完整验证，整理提交，使当前工作树不再混杂未解释的修改。

## 文件处理范围

### 整文件删除

- `scripts/coze_api_server.py`
- `scripts/run-coze-api.ps1`
- `scripts/test_coze_api_server.py`
- `docs/coze-demo-integration-plan.md`
- `docs/coze-render-deployment.md`
- `docs/coze-openapi.json`
- `docs/coze-openapi.coze-min.json`
- `docs/coze-openapi.swagger2.json`

### 修改并保留

- `render.yaml`
- `.env.example`
- `README.md`
- `scripts/web_workbench.py`
- `scripts/test_web_workbench.py`
- `scripts/test_mobile_api_contract.py`
- `scripts/hosted_smoke.py`
- `scripts/test_hosted_smoke.py`
- `ios-app/Config/Debug.xcconfig`
- `ios-app/Config/Release.xcconfig`
- `ios-app/README.md`
- `ios-app/scripts/validate-package-boundary.ps1`
- `docs/product-editions-and-directory-contract.md`
- `docs/product-loop-state.md`
- 其他被全仓搜索发现仍含 Coze 文字的计划、设计或配置文件

历史计划不享有例外。若其唯一价值是记录已终止的兼容路线，则删除；若同时记录仍有效的产品决策，则只删除或改写相关段落。

## 数据流

```text
浏览器或 iOS
  -> counselor-agent-web.onrender.com
  -> scripts/web_workbench.py
  -> 登录与工作空间鉴权
  -> Agent 路由 / RAG / 模型调用 / 校验 / Word 生成
  -> Web 或移动 API 响应与受鉴权文件下载
```

不保留第二个兼容入口或代理层。

## 工作树安全策略

- 保留当前非 Coze 的 tracked 和 untracked 成果，包括 iOS 工程、移动 API、评测修复及产品文档。
- `.superpowers/brainstorm/` 中的端口、令牌、PID 和临时预览属于工具临时状态，不纳入产品提交；确认无用后删除或忽略。
- 不删除 `.worktrees/` 中的其他工作树或分支。
- 在同步远端前先确保当前修改可恢复，避免本地分支落后远端导致覆盖或大范围冲突。
- “工作树干净”的验收含义是：所有应保留的成果均已明确提交，临时文件已清除，`git status` 无未解释修改；不等于还原并丢弃用户工作。

## 错误和部署处理

- 独立 Web Render 服务必须配置 `DEEPSEEK_API_KEY`；未配置时不得把迁移视为完成。
- 删除仓库中的 Render Blueprint 服务不会自动删除 Render 平台上的旧服务。仓库验证完成后，需在 Render 控制台单独停用旧服务，并删除不再使用的相关密钥。
- 若迁移后 Web 或移动 API 测试失败，先修复共享服务，不恢复兼容层。
- 文件下载必须继续使用 Web 会话或移动 Bearer Token 的现有授权方式，不引入第二套共享密钥。

## 验证

至少完成以下检查：

1. 在排除 `.git/` 和 `.worktrees/` 后，对当前主工作树执行大小写不敏感搜索 `coze`、旧服务名及旧环境变量名；实施完成并删除本过渡说明后结果为零。
2. Python 语法检查通过。
3. Web、移动 API、Agent、模板、文档生成及评测清理相关单元测试通过。
4. JavaScript 语法检查通过。
5. 本地 Web 主线通过：登录、个案、Agent 运行、历史重开和 Word 下载。
6. iOS 配置与 API 合同只指向独立 Web 服务。
7. `render.yaml` 只声明 `counselor-agent-web`。
8. 独立 Web Render 环境变量齐全后，运行健康检查、登录、真实 Agent 和文件下载冒烟测试。
9. 最终 `git status` 只允许存在明确向用户说明且暂不提交的内容；目标状态为空。

## 非目标

- 不重写 Counselor Assistant 的 Agent 能力。
- 不借本次清理重构全部 Web 前端。
- 不删除 iOS、RAG、评测、运行器或文档生成能力。
- 不保留已弃用兼容层、重定向页或占位说明。

## 完成标准

- 仓库中不存在任何 Coze 相关内容或字样。
- 唯一 Render 产品服务和文档入口是 `counselor-agent-web.onrender.com`。
- Web 与移动 API 仍可独立运行，相关回归覆盖没有随适配器一起丢失。
- 非 Coze 的现有工作成果得到保留。
- 本地与线上验证通过，工作树状态清晰。
