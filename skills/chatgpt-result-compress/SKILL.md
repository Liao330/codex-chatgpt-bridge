---
name: chatgpt-result-compress
description: Compress a captured ChatGPT Web response into a bounded JSON working view without replacing the raw source, losing citations, or promoting unverified claims. Use after the CCW run reaches a terminal state.
---

# Compress a ChatGPT Result

Run compression only after the raw response is captured:

```powershell
.\ccw.cmd run compress <run_id>
.\ccw.cmd run verify <run_id>
```

## Rules

- Keep the raw response as the canonical source.
- Preserve file paths, line numbers, commands, warnings, and citation URLs.
- Do not strengthen uncertainty into certainty.
- Do not delete contrary evidence.
- Do not issue another ChatGPT request to summarize the first request.
- Return the compressed JSON plus `raw_ref` and `raw_sha256`.

For code review, Codex must check every file/line reference and potentially apply a fix. For Deep Research, Codex must verify decision-critical claims against primary sources.
