# Chicogong Codex Bridge

**中文** | [English](README.md)

一个只读型 Codex 插件，用于把 ChatGPT Web 的 **Chat + Pro** 和 **Deep Research** 接入 Codex，作为外部分析和审查能力。

本项目以 `chicogong/codex-chatgpt-web-orchestrator` 作为固定版本的编排底座。项目不实现浏览器控制器；首选 adapter 是 Codex 原生 Browser / ChatGPT thread bridge。

## 永久策略

**ChatGPT Work 被永久禁止。**

路由解析、adapter 清单校验、状态机、测试和 verifier 都会拒绝 Work。仅支持两种模式：

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
- 提供编排、Pro 分析、Deep Research 和结果压缩的 Codex skills。
- 离线测试不会打开浏览器，也不会调用 ChatGPT 账号。

## 仓库结构

```text
.codex-plugin/       Codex 插件清单
adapters/            Adapter 能力清单
references/          Bridge、生命周期、输出和只读策略
schemas/             来自 upstream 的公共 receipt schema
skills/              Codex skills
src/ccw/             本地 Python 编排包
tests/               离线单元测试和 CLI 测试
vendor/              固定版本的 upstream 编排底座
scripts/             Windows 启动和校验脚本
```

## 快速开始

运行离线测试：

```powershell
.\scripts\test.ps1
```

校验插件清单：

```powershell
.\scripts\validate-plugin.ps1
```

在不读取凭据的情况下检测原生 adapter 是否存在：

```powershell
.\ccw.cmd adapter detect --inventory .\examples\inventory.example.json
```

规划一条路由：

```powershell
.\ccw.cmd route plan `
  --task-kind review `
  --mode chat-pro `
  --capabilities .\examples\capabilities.native.json
```

尝试 Work 形状的任务会直接失败：

```powershell
.\ccw.cmd route plan `
  --task-kind artifact `
  --capabilities .\examples\capabilities.native.json
# exit code 3: ChatGPT Work is permanently disabled in this bridge
```

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

# 3. 记录原生浏览器的只读 preflight 证据。
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

当 run 断线或状态不明确时：

```powershell
.\ccw.cmd run recover <run_id> --observation .\recovery.json
```

恢复优先使用同一 conversation identity。如果身份丢失且没有保存的捕获结果，run 会进入 `unknown`，不会静默重跑。

## Adapter 契约

必需能力：

- `send`
- `observe`
- `capture`
- `stable_identity`

路由能力：

- `chat_pro`
- `deep_research`

Adapter 不得暴露 Work。

参见 [Bridge contract](references/bridge-contract.md) 和 [Native Codex Browser adapter](references/native-codex-browser.md)。具体可用的 `agent-browser` adapter 示例位于 `adapters/agent-browser.example.json`。

## Live smoke

真实浏览器和账号验收与离线测试分开。只有在明确授权使用已登录 ChatGPT 账号后，才按 [docs/live-smoke.md](docs/live-smoke.md) 执行。

## 私有数据

运行时状态位于 `CCW_HOME`，默认是 `~/.ccw/runs/<run_id>`。`private.json` 和 `receipt.private.json` 包含原始 conversation identity，绝不能提交或共享。公共 receipt 只包含 commitment。

## Upstream

参见 [UPSTREAM.md](UPSTREAM.md) 和 [THIRD_PARTY.md](THIRD_PARTY.md)。
