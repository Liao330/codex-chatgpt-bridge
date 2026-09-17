# Live Smoke Evidence

Status: **All three live smokes passed**
Completed: 2026-08-30, Asia/Singapore
Authorization: the owner confirmed the original exact three prompts and separately authorized the Deep Research rerun immediately before execution.

No prompt was resubmitted. No file was uploaded. No private project context was added. Conversation URLs are excluded from public files and retained only in `smoke/output/private-run-record.json`, which is gitignored and excluded from the public scanner.

## Result summary

| Run | Result | Mode/model evidence | Single-submit | Terminal and capture evidence |
|---|---|---|---|---|
| Chat Pro | Passed | Chat selected; Pro visible before and after Send | One user turn | Stop control observed then disappeared; one complete assistant response captured: 8,881 characters, 89 lines, SHA-256 `d899ff312db4a75f3c3484d13950150da7a234255889872b613064ea56666949` |
| Deep Research | Passed | Deep Research selected; Report tab selected; Pro visible | One committed user turn | Stop control observed then disappeared; one complete 11,226-character report captured with 21 citation links and independently checked against W3C |
| Work | Passed | Work selected; 5.6 Sol with Light effort visible | One task start | Stop control observed then disappeared; one completion message plus a downloaded and read-back Markdown artifact: 205 lines, 14,308 bytes, SHA-256 `c304e5455ccff16402981d2eba102b2cc5dc9082dfb266fddff528806775f1f8` |

## Deep Research rerun

The owner separately authorized a new run of the same public W3C-only prompt. Two stable preflight observations verified the same blank Chat surface, visible Pro label, Deep Research selection, Report tab, interactive composer, and zero prior submissions before prompt fill.

- A semantic Send click and Enter produced no user turn, conversation URL, stop control, or cleared composer. Readback therefore proved `submission_count=0`; neither action created a duplicate.
- The visible send control committed exactly one user turn. The conversation gained a stable URL, the composer cleared, and the stop control appeared.
- The same run progressed through public-source search and report writing without cancellation, follow-up, or retry.
- Terminal evidence: stop control disappeared; one assistant message was captured; report length was 11,226 characters; 21 citation links were present.
- The normalized report hashes to SHA-256 `c853c8d96ffa23c6abb2cde7cc24915a525c170dfc08e9c4adc21b082a798d93`.
- Independent primary-source checks confirmed the WCAG 2.2 Recommendation date, the normative/informative distinction, and the cited levels and wording for 2.4.7, 2.4.11, 2.4.12, and 2.4.13.

## Recovered outputs

- Chat Pro complete response, normalized to public Markdown: [chat-pro-response.md](evidence/chat-pro-response.md)
- Deep Research complete cited report: [deep-research-wcag-focus.md](evidence/deep-research-wcag-focus.md)
- Work artifact: [lantern-cli-launch-checklist.md](evidence/artifacts/lantern-cli-launch-checklist.md)

## Release ruling

**Live-smoke gate passed.** Chat Pro, Deep Research, and Work each reached a terminal result with complete captured output and the intended route evidence. This removes the prior Deep Research blocker. Public repository creation, terms review, independent-user validation, and release remain separate decisions; no live-smoke result authorizes publication by itself.
