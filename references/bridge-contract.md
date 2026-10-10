# Bridge Contract

## Default independent HTTP transport

The `web-http` adapter is the default for text `chat-pro` runs and executes them through HTTP without a
browser controller. It must retain the authorization, private identity,
single-attempt submission and raw-output contracts below. See
`docs/http-text-review.md` for setup, commands and live acceptance.

HTTP preflight checks account and model availability. Final mode/model evidence
comes from the server's exact response branch, alongside matching read-only MCP
tool provenance. It must not fabricate visible-page evidence. Project/context
wire parameters and HTTP Deep Research remain unsupported. Browser execution is
explicit and is never selected as a silent fallback. Actual model, MCP and
interruption-recovery evidence remains required for acceptance.

The remaining visible-transport requirements apply to browser adapters.

The adapter is responsible for its selected transport. Browser adapters must
expose visible transport capabilities; the HTTP adapter exposes equivalent
server-side evidence without a visible page. The required capability contract
is transport-neutral:

- `send`: perform the single authorized submission exactly once.
- `observe`: determine whether processing is active, blocked, or terminal.
- `capture`: read the complete final response and citations from the selected transport.
- `stable_identity`: retain a conversation, thread, or tab identity for recovery.

For this repository the adapter must additionally expose the selected route capability:

- `chat_pro`
- `deep_research`

`work` is not an allowed capability.

## Preflight

For browser adapters, before filling the prompt and again immediately before
Send, verify:

- the bridge is connected;
- the intended tab or thread is bound;
- the identity is stable and reopenable;
- the observed surface matches the expected surface;
- the visible mode and model match the exact approved route;
- the composer is interactive;
- the same state is observed on at least two consecutive reads;
- the submission count is still zero.

A visible model label is not sufficient when the tab, composer, or thread binding is unstable.

For the default HTTP adapter, use `run preflight-http` and verify account
binding, target model availability, expected MCP binding, exact prompt
authorization, and zero prior submissions. Do not manufacture visible-page
evidence for an HTTP run.

## Failure behavior

- Missing capability: fail closed before transmission.
- Unstable page or composer: hold without sending.
- Ambiguous post-click state: mark `unknown` and reconnect to the same identity.
- Timeout after a possible send: never resend.
- Lost identity with no saved capture: mark `unknown`.
