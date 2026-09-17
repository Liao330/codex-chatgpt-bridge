---
name: chatgpt-deep-research
description: Route a source-heavy investigation to ChatGPT Web Deep Research through the review-only CCW orchestrator, preserve citations and long-run recovery identity, and return a compressed evidence report for Codex verification. ChatGPT Work is forbidden.
---

# ChatGPT Deep Research

Use mode `deep-research` for public-source investigations, standards surveys, ecosystem comparisons, policy research, and evidence-heavy technical questions.

## Lifecycle differences from Pro analysis

- Expect a long-running task.
- Reuse the same conversation or task identity after a timeout.
- Never resend merely because the local wait expired.
- Capture the complete report before compressing.
- Preserve ordinary HTTPS citation URLs.
- Distinguish public facts, inference, and unverified claims.

## Required output

Request a response with:

```json
{
  "summary": [],
  "key_points": [],
  "citations": ["https://..."],
  "uncertainties": [],
  "methodology": ""
}
```

The local compressor may fall back to extractive headings and citations if the response is not valid JSON, but the raw response remains authoritative.

## Verification

Codex must verify decision-critical claims against primary sources. Citations prove that a source was cited, not that the claim is true.

## Hard limits

- No ChatGPT Work.
- No local MCP connector.
- No workspace mutation.
- No silent model or route downgrade.
