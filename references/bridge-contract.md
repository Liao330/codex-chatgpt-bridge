# Bridge Contract

## Opt-in independent HTTP transport

The `web-http` adapter executes text `chat-pro` runs through HTTP without a
browser controller. It must retain the authorization, private identity,
single-attempt submission and raw-output contracts below. See
`docs/http-text-review.md` for setup, commands and live acceptance.

HTTP preflight checks account and model availability. Final mode/model evidence
comes from the server's exact response branch, alongside matching read-only MCP
tool provenance. It must not fabricate visible-page evidence. Project/context
wire parameters and HTTP Deep Research remain unsupported. Existing browser
defaults change only after actual model, MCP and interruption-recovery evidence.

The remaining visible-transport requirements apply to browser adapters.

The adapter is responsible for visible transport only. It must expose:

- `send`: activate Send or Start exactly once.
- `observe`: determine whether generation is active, blocked, or terminal.
- `capture`: read the complete final response and citations.
- `stable_identity`: retain a conversation, thread, or tab identity for recovery.

For this repository the adapter must additionally expose the selected route capability:

- `chat_pro`
- `deep_research`

`work` is not an allowed capability.

## Preflight

Before filling the prompt and again immediately before Send, verify:

- the bridge is connected;
- the intended tab or thread is bound;
- the identity is stable and reopenable;
- the observed surface matches the expected surface;
- the visible mode and model match the exact approved route;
- the composer is interactive;
- the same state is observed on at least two consecutive reads;
- the submission count is still zero.

A visible model label is not sufficient when the tab, composer, or thread binding is unstable.

## Failure behavior

- Missing capability: fail closed before transmission.
- Unstable page or composer: hold without sending.
- Ambiguous post-click state: mark `unknown` and reconnect to the same identity.
- Timeout after a possible send: never resend.
- Lost identity with no saved capture: mark `unknown`.
