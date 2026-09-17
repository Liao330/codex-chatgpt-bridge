# Backend Selection and Capability Detection

This skill defines orchestration policy; it does not bundle automation runtimes or third-party code.

## Selection order

Choose the first backend that satisfies the task without new installation or authentication:

1. native Codex Browser and ChatGPT-thread bridge;
2. codex-chatgpt-control, when its plugin, skill, or SDK is already callable;
3. Oracle, when its CLI is already installed and browser-session handling is appropriate;
4. Agentify Desktop, when its MCP tools and user-managed tab are already available;
5. manual handoff, where the user sends the prompt and returns the answer.

The order is a safe default, not a quality ranking. A user-specified backend takes precedence when available and authorized.

An automated backend qualifies only when it exposes all four base capabilities—send, observe, capture, and stable recovery identity—plus the requested mode capability. `scripts/orchestrator_policy.py` applies this rule to already-observed capabilities and returns no backend when the gate is unmet.

Backend selection is not a per-run readiness result. Immediately before prompt fill and Send, the chosen backend must also pass the dynamic preflight in [Bridge contract](bridge-contract.md). Static capability presence and a visible model label cannot compensate for a disconnected bridge, invalid tab binding, unstable Chat/Work surface, or non-interactive composer.

The same module can classify a caller-supplied inventory of exposed tools, skills, and ordinary executable names. This is presence detection only: never promote presence into mode capability until the visible surface or backend reports and verifies that capability.

## Non-invasive detection

Capability detection must be read-only:

- inspect the tools and skills currently exposed to Codex;
- inspect whether referenced threads resolve as ChatGPT conversations;
- for a local CLI, use an ordinary executable/version check only when local command execution is allowed;
- ask the user whether the relevant visible browser tab is signed in if this cannot be established without account inspection.

Do not probe cookies, session tokens, browser profiles, credential stores, environment secrets, or private history. Do not install a missing backend during detection.

## Support matrix

| Backend | Send / observe / capture | Existing conversation | Chat / Pro | Deep Research | Work / artifacts | Durable recovery identity | Main limitation |
|---|---|---|---|---|---|---|---|
| Native Codex Browser + thread bridge | Conditional on exposed browser and thread tools plus a stable per-run preflight | When surfaced as a ChatGPT thread | Verify visible controls and interactive Chat surface | Verify visible controls | Verify visible controls and artifact access | Thread ID, URL, or browser tab | Thread synchronization may lag; a model label can outlive a usable tab binding |
| codex-chatgpt-control | Conditional on an already callable compatible bridge | Supported by its public workflow | Explicit visible controls | Verify at run time | Public upstream documents Chat and Work, including visible artifacts | Run report, thread, or tab identity | Unofficial pre-release third-party runtime |
| Oracle | Conditional on an already installed CLI or MCP route | Saved browser sessions | Browser model selection and verification | Public upstream documents browser research capture | File bundling and session artifacts; not a general desktop agent | Saved session and browser target | Third-party browser automation; API mode is a different paid transport |
| Agentify Desktop | Conditional on an already exposed MCP and user-managed tab | Stable tab key | Provider UI-dependent | Provider UI-dependent | Public upstream documents uploads and local downloads | Stable tab key | Unofficial local app supporting multiple providers, so controls vary |
| Manual handoff | User-operated | User-operated | User-operated | User-operated | User-operated | User-provided URL or transcript | No automated monitoring or capture; user must return evidence |

Feature labels and UI availability can change by account, plan, rollout, and region. Verify the visible state at run time.

## Degradation rules

- If thread tools can read but not create or monitor a run, use the native browser for those missing steps.
- If the browser can send but thread synchronization lags, treat the browser page as the live state and capture before closing the tab.
- If an optional backend is unavailable, fall back without installing it.
- If no backend can verify model, mode, submission, completion, and capture, stop before transmission or use a clearly labeled manual handoff.
- If a label remains visible while the bridge, tab, surface, or composer is unstable, discard the prior readiness evidence, reacquire or reopen, and restart preflight from zero. Never fill or send based on the label alone.
- Do not switch from browser subscription access to a paid API route without explicit approval.
- A requested backend that lacks a required capability fails closed; do not silently choose a different backend when the user required that exact one.

## Public capability references

These links document capability boundaries only; this skill contains none of their code:

- OpenAI Deep Research: <https://help.openai.com/en/articles/10500283-deep-research>
- OpenAI ChatGPT Work and Codex: <https://help.openai.com/en/articles/20001275>
- OpenAI ChatGPT model picker release notes: <https://help.openai.com/en/articles/6825453-chatgpt-release-notes>
- codex-chatgpt-control: <https://github.com/adamallcock/codex-chatgpt-control>
- Oracle browser mode: <https://github.com/steipete/oracle/blob/main/docs/browser-mode.md>
- Agentify Desktop: <https://github.com/agentify-sh/desktop>

Public capability references last reviewed 2026-08-30. They are evidence about upstream claims, not a guarantee of what a particular account or installed version exposes.
