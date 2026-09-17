# Bridge Contract

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
