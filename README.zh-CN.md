# Codex ChatGPT Bridge

**中文** | [English](README.md)

一个双平面桥接项目：ChatGPT Web 负责规划、审查和研究，Codex 保留执行权与最终判断。

项目组合两个固定版本的 MIT 上游底座：

- `chicogong/codex-chatgpt-web-orchestrator`：路由、receipt、生命周期、恢复和治理。
- `codex-with-chatgpt`：C2C 控制协议、只读 workspace MCP、OAuth 2.1、配对、Cloudflare Tunnel、执行记录和会话恢复。

控制面优先使用 Codex In-app Browser。headed 系统浏览器仅作为 fallback，并且必须获得用户明确同意。

## 永久策略

**ChatGPT Work 被永久禁止。**

路由解析、adapter 清单校验、状态机、测试、MCP 策略和 verifier 都会拒绝 Work。仅支持：

- `chat-pro`：架构分析、代码审查、反向质询、综合判断。
- `deep-research`：带引用的资料调研和长任务恢复。

## 已实现能力

- 基于 receipt 的授权与 prompt 指纹。
- `submission.count <= 1`，并有明确的 `committing` 和 `committed` 状态。
- 断线后恢复同一 conversation，而不是盲目重发。
- 明确区分 `generating`、`complete`、`partial`、`incomplete`、`blocked` 和 `unknown`。
- 原始回复、压缩工作视图、核验记录三者分离。
- 代码 review 的 file/line 结构校验。
- Deep Research 的 HTTPS citation 校验与语义核验交接。
- 只读 workspace MCP：代码、搜索、git、测试和脱敏执行记录。
- `INIT -> PLAN -> EXECUTING -> EXECUTED -> REVIEW -> DONE/BLOCKED` 治理状态。
- 脱敏执行记录和 HANDOFF。
- 外部生产数据只读契约，包含行数、字节数和超时限制。
- 离线测试不会打开浏览器，也不会调用 ChatGPT 账号。

## 仓库结构

```text
.codex-plugin/       Codex 插件清单
adapters/            Adapter 能力清单
docs/                部署（中继 + 开机自启）、Live smoke、Vendor 补丁
examples/            示例清单和 observation
references/          Bridge、数据面、生命周期和输出契约
schemas/             Receipt、核验和只读数据源 schema
skills/              Codex skills
src/ccw/             本地 Python 治理与集成包
tests/               离线单元测试和 CLI 测试
vendor/              固定版本的治理底座与 C2C Bridge
scripts/             Windows 启动、测试和依赖脚本
```

## 快速开始

运行本地治理测试：

```powershell
.\scripts\test.ps1
```

运行 vendored C2C Bridge 测试：

```powershell
.\scripts\test-c2c.ps1
```

校验插件：

```powershell
.\scripts\validate-plugin.ps1
```

检查 C2C 环境并构建 bridge：

```powershell
.\ccw.cmd c2c detect
.\ccw.cmd c2c build
```

用中继把它暴露给 ChatGPT：[docs/deployment.md](docs/deployment.md)。

## 集成后的 C2C 闭环

控制面通过 In-app Browser 发送小于 1 KB 的 `[C2C]` 状态消息。数据面通过只读 workspace MCP 暴露代码、diff、搜索、git、测试和脱敏执行记录，让 ChatGPT 自己读取需要的事实。

```powershell
.\ccw.cmd c2c exec -- start --tunnel
.\ccw.cmd c2c exec -- doctor
```

本地同步治理状态：

```powershell
.\ccw.cmd cycle set <run_id> --state INIT --iteration 0 --task-id <task_id>
.\ccw.cmd cycle set <run_id> --state PLAN --iteration 1
.\ccw.cmd cycle set <run_id> --state EXECUTING --iteration 1
.\ccw.cmd cycle record-execution <run_id> `
  --iteration 1 `
  --changed-file src/a.ts `
  --tests "27 passed" `
  --exit-status ok `
  --command "pnpm test" `
  --output-file .\test.log
.\ccw.cmd cycle set <run_id> --state EXECUTED --iteration 1
```

控制消息不包含文件正文、diff 或日志。详细输出保存在本地，经过脱敏后只通过只读数据面暴露。

## Pro Review 生命周期

```powershell
# 1. 使用精确 prompt 创建 run。
.\ccw.cmd run init `
  --mode chat-pro `
  --task-kind review `
  --workspace E:\path\to\repo `
  --adapter-manifest .\adapters\native-codex-browser.example.json `
  --prompt-file .\prompt.md

# 2. 授权精确 prompt。
.\ccw.cmd run authorize <run_id>

# 3. 记录 In-app Browser 的只读 preflight 证据。
.\ccw.cmd run preflight <run_id> --observation .\observation.json

# 4. 记录单次提交意图和 acknowledgement。
.\ccw.cmd run begin-submit <run_id>
.\ccw.cmd run confirm-submit <run_id> --conversation-identity <private-id>

# 5. 捕获、压缩、核验并生成 receipt。
.\ccw.cmd run capture <run_id> --raw-file .\response.md --terminal-signal
.\ccw.cmd run compress <run_id>
.\ccw.cmd run verify <run_id>
.\ccw.cmd run finalize <run_id>
```

ChatGPT 原始回复是权威来源。`compressed.json` 只是有界的工作视图。Codex 必须逐条验证 findings 和 decisions。

## Deep Research 生命周期

使用 `--mode deep-research --task-kind source-research` 或 `research-report`。

Deep Research 遵循同样的 receipt 和单次提交规则。运行时间可以很长，但超时不代表可以重新提交。压缩前必须捕获完整报告和普通 HTTPS citations。

## 恢复

```powershell
.\ccw.cmd run recover <run_id> --observation .\recovery.json
```

恢复优先使用同一 conversation identity。如果身份丢失且没有保存的捕获结果，run 会进入 `unknown`，不会静默重跑。

## 只读数据面

workspace MCP 是主要数据面。可选生产数据源必须满足 [references/data-plane.md](references/data-plane.md)：

- 只读视图或副本。
- 远程 endpoint 使用 OAuth 2.1。
- 强制行数、字节数和超时上限。
- 敏感字段脱敏和访问审计。
- 不提供写入、Shell、commit、部署或管理工具。

校验外部数据源契约：

```powershell
.\ccw.cmd data validate --manifest .\examples\readonly-data-source.sqlite.json
```

## Adapter 契约

必需能力：

- `send`
- `observe`
- `capture`
- `stable_identity`

路由能力：

- `chat_pro`
- `deep_research`

Adapter 不得暴露 Work。参见 [references/bridge-contract.md](references/bridge-contract.md)。

## 部署

bridge 只监听本机回环地址。用中继把它暴露出去（地址永久固定、本机不开任何入站端口）：[docs/deployment.md](docs/deployment.md)。

```powershell
# 在要跑 bridge 的机器上（中继就绪后）
powershell -ExecutionPolicy Bypass -File deploy\install.ps1 -WorkspacePath <工作区根目录>
```

- `deploy/relay-setup.sh`：准备中继机（Tailscale Funnel）。
- `deploy/install.ps1`：一条命令完成客户端 + Codex 插件安装。
- `deploy/install-client.ps1`：准备一台要跑 bridge 的机器。
- `scripts/startup.ps1`：开机守护，同时保活 **bridge 和反向隧道**，重启后无需手动操作。

一个工作区可以覆盖多个仓库（bridge 根目录设为父目录即可）：`workspace_info` 会返回仓库列表，`git_status`/`git_diff` 用 `repo` 参数选择仓库。详见 [docs/deployment.md](docs/deployment.md)。

访问 ChatGPT 页面一律使用 In-app Browser，不要启动 headed 系统浏览器。

## Live smoke

真实浏览器和账号验收与离线测试分开。只有在明确授权使用已登录 ChatGPT 账号后，才按 [docs/live-smoke.md](docs/live-smoke.md) 执行。

## 私有数据

运行时状态位于 `CCW_HOME`，默认是 `~/.ccw/runs/<run_id>`。`private.json` 和 `receipt.private.json` 包含原始 conversation identity，绝不能提交或共享。公共 receipt 只包含 commitment。

## Upstream

参见 [UPSTREAM.md](UPSTREAM.md) 和 [THIRD_PARTY.md](THIRD_PARTY.md)。
