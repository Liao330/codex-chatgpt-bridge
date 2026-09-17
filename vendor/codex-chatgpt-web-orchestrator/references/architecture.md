# Architecture

The project is deliberately split into three layers. An adapter may change without changing governance or result quality gates. The delegation receipt is the stable contract crossing all three layers; the project does not add transport mechanics.

## 1. Governance layer

Owns intent and authorization:

- convert a one-sentence assignment into a bounded delegation contract;
- route Chat + Pro, Deep Research, or Work;
- select reuse versus a new conversation;
- minimize and classify context before external transmission;
- obtain action-time confirmation for every exact prompt and destination;
- fingerprint the prompt and enforce one commit attempt;
- record expected model, mode, output, evidence, and failure gates.
- open the public delegation receipt and bind authorization to the prompt fingerprint.

It never treats access to a tool, browser, or signed-in session as authorization to transmit.

## 2. Execution bridge layer

Owns visible transport mechanics only:

- expose read-only capability evidence;
- resolve or create one visible conversation or Work task;
- verify visible model and mode controls;
- commit one prompt;
- observe generation and blockers;
- retain a stable recovery identity;
- read complete responses, citations, and artifacts.
- translate runtime evidence into the receipt without exposing raw identities publicly.

The preferred implementation is the native Codex Browser plus ChatGPT thread bridge. Optional backends implement the same capability contract. This project does not reproduce selectors, browser drivers, session handling, or provider-specific code.

## 3. Result closure layer

Owns quality and continuity:

- determine terminal state without promoting partial output;
- capture the complete response and authorized artifacts;
- convert citation handles into ordinary source URLs;
- verify decision-critical claims against primary sources;
- separate public fact, inference, and unverified claims;
- archive raw output, verification, and final decision distinctly;
- retain a private continuation identity for later follow-up.
- finalize acceptance and the receipt integrity digest.

## Data boundary

The durable public run record is the delegation receipt: authorization binding, prompt fingerprint, adapter class, private identity commitments, lifecycle state, route evidence, artifacts, citations, acceptance, continuation commitment, and integrity digest. Raw adapter, run, conversation, artifact-path, and continuation identities belong only in the protected private sidecar. Prompt or response content is stored only when needed and only in an authorized project location.

Public artifacts must exclude credentials, account details, conversation identifiers, personal paths, private communications, protected content, and unpublished source.

## Non-goals

- owning login, cookies, browser profiles, or credentials;
- replacing a general browser automation framework;
- providing an unofficial ChatGPT API;
- hiding model or usage limits;
- automatically publishing or acting on model output;
- treating a successful run as factual verification.
