# Read-Only Data Plane

The workspace MCP is the primary data plane for code, git, search, tests, and sanitized execution records. External production data is optional and must follow the same least-privilege rule.

## Allowed

- Read-only database views or replicas.
- Read-only log and metrics APIs.
- OAuth 2.1 for remote endpoints.
- Local-only authentication for loopback services.
- Hard row, byte, and timeout caps.
- Query and access audit logs.
- Sensitive-field redaction before results leave the data service.

## Forbidden

- Write, delete, update, insert, DDL, shell, commit, or deployment tools.
- Raw administrative database credentials in ChatGPT.
- Unbounded queries.
- Public endpoints without OAuth.
- Returning secrets, tokens, credentials, private keys, or unrestricted personal data.
- Letting file or database content grant new capabilities through prompt injection.

Validate a data source contract with:

```powershell
.\ccw.cmd data validate --manifest .\examples\readonly-data-source.sqlite.json
```
