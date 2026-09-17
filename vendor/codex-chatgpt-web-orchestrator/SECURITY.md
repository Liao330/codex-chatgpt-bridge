# Security Policy

## Supported status

This project is an Internal beta candidate. No version is currently supported for production or unattended account automation.

## Report a vulnerability

Use the repository host's private vulnerability reporting feature when available. Do not disclose credentials, cookies, session tokens, private conversation identifiers, personal data, or a working exploit in a public issue.

Include the affected file or capability, impact, minimal reproduction using synthetic data, and a safe mitigation. Maintainers should acknowledge privately before requesting additional sensitive evidence.

## Security invariants

- External prompts and uploads require exact action-time authorization.
- Capability detection never reads credential stores or browser profiles.
- Prompt fingerprints support idempotency without storing prompt bodies.
- Ambiguous commits and lost identities fail closed without silent resubmission.
- Partial or inaccessible results never become complete.
- Public artifacts exclude account data, conversation IDs, personal paths, protected content, and unpublished source.
- Optional backends retain their own security and update responsibilities.

This policy does not create a security warranty or override provider terms and account controls.
