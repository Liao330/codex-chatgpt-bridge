---
name: chatgpt-pro-analysis
description: Route a bounded analysis, architecture review, code review, or reverse-challenge task to ChatGPT Web Pro through the review-only CCW orchestrator. Use when Codex needs an independent Pro-level review while retaining all local tools and final judgment.
---

# ChatGPT Pro Analysis

Use this skill only with mode `chat-pro`.

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
- No MCP connector to the local machine.
- No tunnel.
- No file writes by ChatGPT.
- No automatic acceptance of the Pro verdict.
