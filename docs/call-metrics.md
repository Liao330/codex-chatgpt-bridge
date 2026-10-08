# Local connector call metrics

After enabling the reviewed bridge build, `c2c metrics` reports retained local
MCP tool calls. `c2c metrics --json` emits the same report as JSON.
Use `--from 2026-10-08T00:00:00Z --to 2026-10-09T00:00:00Z` for a UTC
window: start inclusive, end exclusive. Both flags require ISO UTC timestamps
ending in `Z`. Defaults cover the preceding 30 days through the current time.

Overall and each fixed tool bucket show count, success/error/cancelled counts,
success rate (success divided by all completed measured calls), average duration,
P50 and P95 in milliseconds. Percentiles use the nearest rank in sorted observed
durations. Empty values are JSON `null` or human-readable `n/a`. Unknown tool
names are always grouped as `unknown`.

The boundary is the public SDK registration of the `tools/call` dispatcher,
installed before the first tool registration. Original SDK schemas, input/output
validation, results and thrown errors are preserved. Timing uses a monotonic
clock around the original dispatcher callback and ends on settlement. Returned
`isError` is an error; a rejection is a thrown error. Cancellation is counted
only when the SDK abort signal is aborted at settlement, including callbacks
that settle after cancellation. Initialize/list requests and malformed JSON or
invalid basic protocol shapes rejected before dispatcher entry are excluded.
Tool input validation, missing/unknown tools, scope denials and business errors
that reach the dispatcher are included. SDK 1.30.0 returns unknown tool and
input validation failures as `isError`; error text is never parsed or recorded.
These are bridge processing durations, not round-trip/network latency.

Records are local to `<C2C state directory>/call-metrics`. Each contains exactly
UTC completion timestamp, a fixed tool-name bucket, nonnegative duration,
outcome, and categorical error kind. Arguments/results/error messages, paths,
request IDs, session/account/client IDs and secrets are excluded. Existing
historical calls are not reconstructed. No new MCP tool, endpoint or scope is
introduced. Reports cover this machine's retained observations, not all-time
usage or a complete account history.

Storage rotates 1 MiB JSONL segments and prunes oldest segments before appending
to stay within 30 MiB of record data. Old daily segments are pruned on the next
write; reports exclude rows older than 30 days even when no new call arrives.
The entire UTC day containing the 30-day cutoff is pruned conservatively on
write, so whole-segment pruning can shorten available history. The report includes first
and last retained timestamps, ignored malformed/partial row count and the
configured limits. A partial final line is ignored; the next append starts a new
line. Corrupt rows are skipped, not treated as successful calls.

Same-process completions write synchronously in order. An exclusive directory
lock prevents overlapping writers in different bridge processes. Contention,
disk/permission errors and other storage failures skip telemetry without
changing the original tool outcome. Therefore coverage may have gaps and the
report explicitly marks completeness false. An interrupted writer can leave
`.writer-lock`; after confirming all bridge writers are stopped, remove only
that metrics lock to resume capture. An unreadable store fails the CLI report
instead of claiming an empty successful history. Owner-only file/directory
permissions are requested where supported; Windows relies on inherited ACLs.

Build and deploy using the parent bridge workflow. A source-only/staged build
does not establish production capture; verify an actual connector call creates
a new row after enabling the build. Code rollback preserves existing auth and
session state and need not restore any metrics.
