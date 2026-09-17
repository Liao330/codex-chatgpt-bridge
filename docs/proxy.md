# agent-browser Proxy Setup (Fallback Only)

Use this only when the In-app Browser cannot reach ChatGPT. If the In-app Browser works, do not run `agent-browser --headed`; that command launches a separate system Chrome window.

The In-app Browser is managed by the Codex host and does not expose a per-tab proxy setting. Use the `agent-browser` adapter only as an explicitly approved fallback when the host must reach ChatGPT through a local proxy.

Validated Windows configuration:

```powershell
agent-browser --headed `
  --proxy http://127.0.0.1:7897 `
  --proxy-bypass "localhost,127.0.0.1,::1" `
  open https://chatgpt.com/
```

The proxy bypass is required. Without it, the agent-browser local control channel is also sent through the proxy and fails with a connection-refused error.

Verify proxy egress separately:

```powershell
agent-browser --proxy http://127.0.0.1:7897 `
  --proxy-bypass "localhost,127.0.0.1,::1" `
  open https://httpbin.org/ip
agent-browser --proxy http://127.0.0.1:7897 `
  --proxy-bypass "localhost,127.0.0.1,::1" `
  get text body
```

Use a visible browser when Cloudflare or login requires user interaction. Codex must not solve CAPTCHAs or enter user credentials.
