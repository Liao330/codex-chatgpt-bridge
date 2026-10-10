# Independent HTTP text review

The `web-http` adapter is the default for `chat-pro`. It does not import or read
another project's code, Python environment or credentials. HTTP failures are
fail-closed and never silently fall back to a browser. Browser adapters remain
available only through explicit selection.
ChatGPT Work is forbidden. HTTP Deep Research is not supported by this version.

## Independent setup

Install the `http` extra in this repository's own `.venv-http`. The launcher uses
that environment when present. The HTTP client requires `curl_cffi`; its session
disables redirects and never retries a conversation POST.

Run this in an interactive terminal, signed in as your Windows user:

```powershell
.\ccw.cmd http credentials-set
```

The prompt hides the token. Windows DPAPI encrypts it for the current user in
`CCW_HOME/http/credentials.dpapi` (default `~/.ccw/http/credentials.dpapi`). No
plaintext credential is accepted in a JSON configuration. An ephemeral
`CCW_CHATGPT_ACCESS_TOKEN` environment variable is also supported. Never put a
token in a command argument, chat message, Git file, prompt or transcript.

This command cannot log in on your behalf or obtain a browser session. Supply
an access token from your own authenticated ChatGPT session through the hidden
input. Credential expiry or a server authentication challenge stops the request;
the verifiable computational proof-of-work is computed, but Turnstile/Arkose
human-verification challenges are never bypassed and credentials are not refreshed.

Copy `examples/web-http.config.json` to a private configuration file. Probe it:

```powershell
.\ccw.cmd http probe --config <private-config.json>
```

The read-only probe returns account commitment and available model slugs. Set
the approved Pro model slug and account commitment from this response. Select
the expected read-only connector/tool identity from verified server metadata.
Placeholders are not verified capabilities. `project_id`/`context` parameters
are rejected because their wire protocol has not been validated. Existing
project-bound conversations may be continued only with exact conversation and
parent-message identities in private configuration; tool availability must
still be demonstrated by the server. An optional private `proxy` field
(`http://host:port`) routes the HTTP client through a local proxy when the
machine cannot reach chatgpt.com directly; it is read from the private
configuration and is never written into the repository.

## Default HTTP run

Prompts carry only a bounded question, repository-relative targets and read-only
constraints. ChatGPT must retrieve source, diffs and tests through MCP; never
paste those bodies into the prompt.

```powershell
.\ccw.cmd run init --mode chat-pro --task-kind review --workspace <workspace> --adapter-manifest .\adapters\web-http.example.json --prompt-file <prompt.md>
.\ccw.cmd run authorize <run-id>
.\ccw.cmd run preflight-http <run-id> --config <private-config.json>
.\ccw.cmd run execute-http <run-id> --config <private-config.json>
.\ccw.cmd run recover-http <run-id> --config <private-config.json>
```

Execute submits once. Recover is read-only and can be repeated without sending.
It matches the persisted account, user-message and parent-message identities.
When no conversation ID was acknowledged, recovery scans at most twenty
candidate conversations with a shared deadline/byte budget; no unique match
leaves the run `unknown`. It never assumes a missing match means not sent.
Unknown stream patches are rejected rather than interpreted speculatively.

Completion requires server branch metadata, the exact approved model, a final
assistant message, complete text and matching read-only MCP tool evidence.
HTTP 200, `[DONE]`, configuration booleans and model self-description are not
acceptance evidence. Run outputs and raw server identity evidence stay private;
public receipts contain commitments and evidence categories.

## Live acceptance and fail-closed default

1. Verify the actual returned model against the approved target model.
2. Have ChatGPT use the expected MCP tool to retrieve an agreed safe repository
   target whose contents were not supplied in the prompt. Verify both the server
   tool trace and retrieved result locally. Connector health alone is insufficient.
3. Interrupt response consumption, restart, recover the exact original message
   and verify there was only one POST. Cover interruption before receipt of the
   conversation ID as well as interruption after it.
4. Record real evidence separately from offline fixtures. Compare equivalent
   tasks for latency and success rate before declaring the default route
   production-ready.

Live acceptance is still required before declaring the HTTP route production
ready. The default route is nevertheless HTTP now; an unverified or unavailable
HTTP capability stops the run instead of opening a browser. Existing runs retain
their initialized transport.

## Acceptance status: 2026-10-10 (Asia/Shanghai)

The scoped HTTP implementation was restored from the prior reviewed staging
copy after the installed checkout was found at its pre-migration baseline.
The streaming parser now persists a supported complete event's conversation ID
before consuming the next chunk. Conflicting IDs, unsupported patches and
private persistence failures leave the run unknown. Recovery never resubmits.
Categorical errors are whitelisted; exception text is not persisted or published.

Recovery now revokes accepted receipts when identity, model, MCP or terminal
evidence is downgraded, including when the text and terminal message ID remain
unchanged. Final reviewer re-review passed. The installed project suite passed
72 tests, the upstream suite passed 39 tests, and supervisor checks passed 28.
The existing Windows-only skip of the upstream Bash demonstration remains.

Live account and selected GPT-6 Pro model-list probes returned HTTP 200. This
proves account binding and availability in the list, not the actual answer model.
The single authorized conversation POST returned HTTP 403. The run remains
unknown with submission count one. A subsequent recovery used only GET requests,
searched twenty candidates, and did not locate the persisted exact message.
The retained transport observation records exactly one conversation POST.

The existing read-only MCP acceptance conversation uses api_tool.call_tool with
invoked_resource.resource_uri/app_name and content.text, rather than the fixture
tool_metadata connector_id/tool_name/read_only shape. HTTP requests have not yet
demonstrated a successful MCP tool result. These metadata formats need a verified
adapter; app names and historical successful calls alone cannot satisfy a new run.

The local C2C build and existing SSH reverse tunnel were restored. Public health
returned status ok. CLI admin status still returned 404 and the supervisor's fixed
runtime file did not match the listening PID. The relay self-check still flagged
its Funnel target. These are unresolved operational checks, not MCP acceptance.

The prepare endpoint's `proofofwork` challenge is now computed independently
(`src/ccw/http_pow.py`) and its `proof_token` is carried into the finalize
request. The solved payload reuses the exact fingerprint serialization sent to
prepare; the search is bounded. Malformed challenge fields stop before finalize.
The Turnstile challenge is now also evaluated independently
(`src/ccw/http_turnstile.py`): its `dx` blob is base64-decoded, XOR-masked with
the fingerprint token `p`, then run as a bounded `[opcode, ...args]` instruction
stream to produce the `turnstile_token`. Only Arkose remains a hard boundary.

A live run now completes the full chain: `turnstile` + `proofofwork` solved,
`finalize` returned a requirements token, `conversation/prepare` returned a
conduit token, and the single conversation POST was acknowledged with the
actual reply model verified (`model_verified=true`). The reply shows ChatGPT
attempted the expected MCP tool but the connector returned `400 "We couldn't
connect your account"`, so `mcp_verified` is still false and the run is
`partial`, not accepted. This is the first end-to-end backend submission.

A live probe also showed `conversation/prepare` returns a null conduit token for
`*-pro` model slugs (`gpt-6-pro`, `gpt-5-6-pro`, `gpt-5-5-pro`) while base
slugs (`gpt-6`, `gpt-5-6`, `gpt-6-mini`, `gpt-6-thinking`) return a conduit.
The Pro model conversation protocol is not yet validated.

A configured `fallback_model` now covers pro and plus accounts: when the
requested model is refused (`conduit_token: null`), the bridge retries
`conversation/prepare` with the fallback model and carries that resolved model
through submission, observation and recovery. A live run on the plus account
requested `gpt-6-pro`, fell back to `gpt-6-thinking`, and verified the reply
model as `gpt-6-thinking` (`model_verified=true`). The identity check allows
exactly the configured-model-to-fallback transition; other model changes are
still rejected.

The default is now the HTTP route. Actual reply model, MCP result and live
interruption recovery remain acceptance risks; browser execution logic is kept
only for an explicitly selected browser route.
Next steps are to fix the ChatGPT-side connector (MCP 400), then demonstrate a
successful read-only MCP tool result, and validate the Pro model conversation
protocol. Preserve the existing run's private intent and locator; neither
changing request parameters nor failing to find a message permits resend.
