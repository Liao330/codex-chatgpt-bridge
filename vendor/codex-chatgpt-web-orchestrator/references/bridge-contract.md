# Execution Bridge Contract

An adapter is eligible only when it can prove the required capabilities at run time. Project name, installation, or a successful import is not enough.

## Required operations

| Operation | Required result |
|---|---|
| Detect | Read-only inventory and visible capability evidence |
| Resolve | Stable identity for a referenced or new conversation/task |
| Configure | Observable mode and exact model label when applicable |
| Stabilize | Same bound identity, expected surface, and interactive composer across two consecutive read-only observations |
| Submit | One commit attempt with an observable acknowledgement |
| Observe | Generating, terminal, and blocker signals on the same identity |
| Reattach | Reopen the same run after tab, bridge, or local wait interruption |
| Capture | Complete assistant body, ordinary citation URLs, and required artifacts |
| Continue | Reuse the same private identity for an authorized follow-up |

## Capability manifest

The policy helper accepts a non-sensitive manifest. An automated route requires:

- `send`
- `observe`
- `capture`
- `stable_identity`
- one of `chat_pro`, `deep_research`, or `work`

Missing capability produces no backend. A manual handoff qualifies only when the user agrees to operate the surface and return equivalent evidence.

## Evidence object

Before submission, the bridge should provide:

- observed surface: Chat or Work;
- observed mode: Chat Pro, Deep Research, or Work;
- exact visible model label when the route specifies one;
- verification source: visible control, backend report with postcondition check, or user-operated evidence;
- stable conversation or task identity;
- timestamp and timezone.

If the surface hides a model label, record that limitation. Do not invent or infer a model from answer style.

## Preflight contract

Run preflight once before filling the prompt and again immediately before Send. Read-only evidence must establish all of the following on the same bound tab or task identity:

- the bridge is connected and the tab binding is live;
- the identity is stable and has a defined reopen path;
- the observed Chat or Work surface matches the intended route;
- the intended mode and exact model label are verified;
- the composer is visible and interactive;
- two consecutive observations agree after the most recent acquire, reopen, or route change.

A surviving Pro label is not a liveness signal for the surrounding surface. Any acquire, reopen, bridge reconnect, Chat/Work transition, or composer loss resets the stable-read count. Do not fill the prompt until preflight returns `ready_to_fill_prompt`. A filled draft requires the same gate again before `ready_to_submit_once`.

## Failure contract

Return a structured stop reason for login, CAPTCHA, permission, unavailable mode, unavailable model, disconnected bridge, invalid tab binding, unstable surface, non-interactive composer, ambiguous Send state, lost identity, inaccessible tail, or artifact failure. The governance layer decides whether to reacquire, reopen, Hold, ask the user, or propose a different route.

Adapters must not install dependencies, switch to a paid API, copy a browser profile, read credentials, or silently create a replacement conversation.
