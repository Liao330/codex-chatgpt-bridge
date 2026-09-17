# Codex ChatGPT Web Orchestrator

简体中文 | [English](README_EN.md)

让 **Codex 当项目经理**，把适合的工作交给你已经登录的 ChatGPT 网页版 Pro、Deep Research 或 Work；任务完成后，再由 Codex 取回结果、核对证据并继续当前项目。

> **当前状态：Public beta。** 40 项自动化测试与 Chat Pro、Deep Research、Work 三条真实网页链路均已通过。仓库已公开，但仍需更多独立用户验证后再创建正式 Release。

## 它解决什么问题

你可能同时在 Codex 中开发项目，又拥有 ChatGPT 网页版中的高级模型和研究、文件、浏览器等能力。普通做法需要反复复制 Prompt、盯着长任务、复制答案回来，还容易重复发送、拿错模型或把未完成结果当成最终答案。

这个 Skill 把过程闭环成：

```text
你给 Codex 一个目标
        ↓
Codex 选择 Chat Pro / Deep Research / Work
        ↓
Codex 整理最小必要上下文，并在发送前确认
        ↓
ChatGPT 网页版执行任务
        ↓
Codex 等待或重新连接同一次运行
        ↓
取回完整结果、引用和文件
        ↓
核验关键事实，回到原项目继续工作
```

它不会绕过登录、订阅、配额或产品限制，也不承诺“免费”或“无限”。它利用的是用户当前账户真实可见、可用的 ChatGPT 网页能力。

## 可以做什么

| 需求 | 推荐模式 | 典型交付 |
|---|---|---|
| 复杂方案、架构评审、反方审查、长文润色 | Chat + 可见的 Pro 模型 | 评审结论、方案比较、草稿 |
| 市场、竞品、技术标准、政策等公开资料调研 | Deep Research | 带引用的研究报告、证据表 |
| 多步骤浏览器或文件工作、制作完整文档 | Work | Markdown、表格、演示稿等成品 |
| 继续已有 ChatGPT 会话 | 原会话 | 基于原上下文继续分析或修改 |

几个实际例子：

- 让 Pro 对产品战略做一次支持方与反方同时存在的决策评审。
- 让 Deep Research 只使用一手公开来源调研某个市场或技术标准。
- 让 Work 制作一份完整发布清单、报告或其他文件型交付。
- 把 ChatGPT 的结果拿回来，由 Codex 对照官方来源复核后写入当前项目。
- 长任务中断后重新连接原会话，不盲目再次发送同一个任务。

## 它具体提供什么

- 自动判断更适合 Chat Pro、Deep Research 还是 Work。
- 保留用户指定的模型和模式；不可用时不会偷偷降级。
- 发送前检查网页模式、模型标签、会话绑定和输入框状态。
- 对 Prompt 生成指纹，默认只提交一次。
- 区分 `generating`、`partial`、`incomplete`、`complete`、`blocked` 和 `unknown`。
- 超时或断线时优先恢复同一次运行，而不是重复消耗额度。
- 捕获完整正文、普通引用链接和授权生成的文件。
- 把公开收据与私有会话身份分开，避免把会话地址或运行标识发布出去。
- 将模型输出视为待核验材料，而不是自动当成事实。

## 使用条件

1. 已安装 Codex 桌面版，并能使用其 Browser 或 ChatGPT 会话桥接能力。
2. 浏览器中的 ChatGPT 已由用户本人登录。
3. 你的账户当前确实显示所请求的 Pro、Deep Research 或 Work 模式。

这个仓库不包含 ChatGPT 账号、不保存 Cookie，也不会替你安装或登录第三方浏览器控制器。

## 安装

直接克隆到 Codex Skills 目录：

```bash
export CODEX_SKILLS_DIR="${CODEX_HOME:-${HOME}/.codex}/skills"
mkdir -p "$CODEX_SKILLS_DIR"
git clone https://github.com/chicogong/codex-chatgpt-web-orchestrator.git \
  "$CODEX_SKILLS_DIR/codex-chatgpt-web-orchestrator"
```

然后新建一个 Codex 任务，让 Skill 发现列表刷新。

如需先检查源码：

```bash
git clone https://github.com/chicogong/codex-chatgpt-web-orchestrator.git
cd codex-chatgpt-web-orchestrator
python3 scripts/check_candidate.py
```

Skill 本身只使用 Python 标准库，不要求安装第三方 Python 包。

## 怎么用

在 Codex 中直接说需求即可；也可以明确写出 `$codex-chatgpt-web-orchestrator`。

### 1. 使用 Chat Pro 做复杂分析

```text
使用 $codex-chatgpt-web-orchestrator，把下面的问题交给 ChatGPT 网页版当前可见的 Pro 模型：
比较这两个产品定价方案，列出假设、最强反方证据和最终建议。
发送前把准确 Prompt 给我确认，拿回答案后再由你做事实核验。
```

### 2. 使用 Deep Research 做带来源调研

```text
使用 $codex-chatgpt-web-orchestrator，让 Deep Research 调研 iOS 独立开发者最值得关注的三个细分机会。
只采用公开一手来源，区分事实、推断和待验证；完成后把引用和结论带回当前任务。
```

### 3. 使用 Work 制作成品

```text
使用 $codex-chatgpt-web-orchestrator，让 ChatGPT Work 制作一份完整的 Markdown 发布检查清单。
必须包含负责人、可观察证据、通过条件和回滚步骤；不要执行发布。
```

### 4. 继续你标记的 ChatGPT 会话

```text
读取我刚刚 @ 的 ChatGPT 会话，确认它是否真正完成。
如果已经完成，提取完整报告并核验关键来源；如果仍在生成，就继续等待同一次运行，不要重发。
```

## 一次任务会发生什么

1. Codex 把目标整理成有边界的任务书。
2. 选择模式，并确认网页上实际可见的模型和模式。
3. 只发送完成任务所需的最少信息。
4. 如果这次发送尚未被当前消息明确授权，Codex 会在发送前展示准确 Prompt。
5. 提交后绑定原会话并等待；超时不会自动重发。
6. 只有终态、正文完整且所需文件齐全时才标记 `complete`。
7. Codex 复核关键事实，输出可继续使用的结论或文件。

## 关于“发送前确认”

把 Prompt 发给 ChatGPT 网页版属于一次外部传输。如果当前指令已经明确授权了准确任务和目标，Codex 可以直接执行；否则会在发送前请求确认。文件、私人数据、未公开代码或其他敏感上下文不会因为安装了本 Skill 就自动获得上传权限。

## 本地 CLI 是做什么的

仓库中的 CLI 只用于无副作用地检查路由和恢复决策，**不会打开浏览器或发送 Prompt**：

```bash
python3 scripts/orchestrator_cli.py plan \
  --request tests/fixtures/requests/deep-research.json \
  --capabilities tests/fixtures/capabilities/native-all.json
```

运行全部本地门禁：

```bash
python3 scripts/check_candidate.py
```

## 安全边界

- 不读取 Cookie、Token、浏览器配置或凭据。
- 不绕过登录、验证码、权限或配额。
- 不因等待超时而偷偷重复提交。
- 不把未完成、截断或缺失文件的结果写成完成。
- 不自动发布、付费、发消息、部署或修改公开可见性。
- 不把私人会话 URL、运行 ID 或受保护路径写入公开收据。

详细设计见：

- [Skill 主指令](SKILL.md)
- [架构](references/architecture.md)
- [委派收据协议](references/delegation-receipt.md)
- [运行生命周期与断线恢复](references/run-lifecycle.md)
- [结果捕获与核验](references/result-loop.md)
- [支持矩阵](references/backends.md)
- [真实 Smoke 证据](smoke/EVIDENCE.md)

## 当前验证结果

- 40/40 自动化测试通过。
- `quick_validate` 通过。
- Chat Pro：终态正文捕获通过。
- Deep Research：带公开来源的终态报告捕获通过。
- Work：完整 Markdown 文件捕获通过。
- 私有运行记录位于 Git 忽略目录，没有进入公开仓库。

这些结果证明三条链路曾成功运行，不代表所有账户、地区或未来网页版本都始终兼容。ChatGPT 页面、模型名称和模式入口变化时，Skill 会优先停止并要求重新确认，而不是猜测。

## 项目定位

这是一个独立、非官方的互操作项目，不隶属于 OpenAI，也不包含或复制 Oracle、Agentify Desktop、codex-chatgpt-control 等可选项目的代码。第三方边界与许可证说明见 [THIRD_PARTY.md](THIRD_PARTY.md)。

采用 [MIT License](LICENSE)。当前为公开 Beta；正式 GitHub Release 将在独立用户安装与复用验证完成后再决定。
