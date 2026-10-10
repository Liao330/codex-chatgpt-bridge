---
name: chatgpt-pro-analysis
description: Route a bounded analysis, architecture review, code review, or reverse-challenge task to ChatGPT Web Pro through the review-only CCW orchestrator. Use when Codex needs an independent Pro-level review while retaining all local tools and final judgment.
---

# ChatGPT Pro Analysis

Use this skill only with mode `chat-pro`.

The default transport is the repository's independent `web-http` executor and
has no GUI. Use an In-app Browser only when the caller explicitly selects a
browser adapter; HTTP failure must stop the run rather than trigger a browser
fallback.

Use it when the user explicitly requests a web GPT review, plan, reverse challenge, or independent second opinion. For architecture, cross-module refactors, migrations, and security work, use it before implementation. After a substantive feature is completed, Codex may automatically run this read-only review once the route and connector are verified.

ChatGPT is read-only. Codex retains file edits, command execution, and final judgment.

## Suitable work

- Architecture and API design critique.
- Independent code review of a bounded diff.
- Reverse-challenge of a Codex plan.
- Failure-mode and regression analysis.
- Comparison of competing designs.

## Prompt contract

The prompt must include:

1. Objective and question.
2. Repository-relative files or diff.
3. Constraints and invariants.
4. Explicit exclusions.
5. Required response fields.
6. A statement that ChatGPT has no local tools and must not ask for them.

If the route exposes a verified read-only workspace MCP, ChatGPT may use it to inspect the requested repository facts. It must not write files, execute shell commands, commit changes, or access unapproved paths.

For review, request JSON with:

```json
{
  "verdict": "approve | request_changes",
  "summary": [],
  "findings": [
    {
      "severity": "critical | high | medium | low",
      "file": "src/example.py",
      "line": 42,
      "claim": "",
      "evidence": "",
      "recommendation": ""
    }
  ],
  "tests": [],
  "uncertainties": []
}
```

Codex must verify every finding locally. A Pro finding is a hypothesis, not a patch command.

## Hard limits

- No ChatGPT Work.
- No unverified MCP connector or tunnel.
- No write, shell, commit, or mutation MCP tools.
- No file writes by ChatGPT.
- No automatic acceptance of the Pro verdict.
- Every finding, path, line number, and conclusion remains a hypothesis until Codex verifies it locally.
