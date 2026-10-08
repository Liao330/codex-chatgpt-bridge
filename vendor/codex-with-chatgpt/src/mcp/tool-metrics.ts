import fs from "node:fs";
import path from "node:path";
import { performance } from "node:perf_hooks";
import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { CallToolRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import { getStateDir } from "../config/paths.js";

export const TOOL_NAMES = ["workspace_info", "list_directory", "read_file", "search_workspace", "git_status", "git_diff", "test_status", "execution_summary", "execution_output", "unknown"] as const;
export type Metric = { timestamp: string; tool: typeof TOOL_NAMES[number]; durationMs: number; outcome: "success" | "error" | "cancelled"; errorKind: "none" | "returned_error" | "thrown_error" | "aborted" };
const DAY = 86_400_000;
const MAX_BYTES = 30 * 1024 * 1024;
const SEGMENT_BYTES = 1024 * 1024;
const FILE_PATTERN = /^\d{4}-\d{2}-\d{2}-\d{5}\.jsonl$/;

function valid(value: unknown): value is Metric {
  if (!value || typeof value !== "object") return false;
  const m = value as Metric;
  return Object.keys(m).sort().join(",") === "durationMs,errorKind,outcome,timestamp,tool" &&
    typeof m.timestamp === "string" && new Date(m.timestamp).toISOString() === m.timestamp &&
    TOOL_NAMES.includes(m.tool) && Number.isFinite(m.durationMs) && m.durationMs >= 0 &&
    ((m.outcome === "success" && m.errorKind === "none") ||
      (m.outcome === "cancelled" && m.errorKind === "aborted") ||
      (m.outcome === "error" && ["returned_error", "thrown_error"].includes(m.errorKind)));
}

/** Dedicated, bounded local telemetry. Never write request/result data. */
export class ToolMetrics {
  constructor(readonly directory = path.join(getStateDir(), "call-metrics")) {}

  private files(): { name: string; bytes: number }[] {
    return fs.readdirSync(this.directory).filter(name => FILE_PATTERN.test(name)).sort()
      .map(name => ({ name, bytes: fs.statSync(path.join(this.directory, name)).size }));
  }

  record(metric: Metric): void {
    let locked = false;
    const lock = path.join(this.directory, ".writer-lock");
    try {
      if (!valid(metric)) return;
      fs.mkdirSync(this.directory, { recursive: true, mode: 0o700 });
      // No waiting in the MCP callback. Another process or a failed writer may
      // cause a telemetry gap; it must never affect tool results.
      fs.mkdirSync(lock);
      locked = true;
      const today = metric.timestamp.slice(0, 10);
      const cutoff = new Date(Date.parse(metric.timestamp) - 30 * DAY).toISOString().slice(0, 10);
      let files = this.files();
      for (const file of files.filter(f => f.name.slice(0, 10) <= cutoff)) fs.unlinkSync(path.join(this.directory, file.name));
      files = this.files();
      const line = JSON.stringify(metric) + "\n";
      const bytes = Buffer.byteLength(line);
      let total = files.reduce((sum, f) => sum + f.bytes, 0);
      while (files.length && total + bytes + 1 > MAX_BYTES) {
        const oldest = files.shift()!;
        fs.unlinkSync(path.join(this.directory, oldest.name));
        total -= oldest.bytes;
      }
      const latest = files.filter(f => f.name.startsWith(today)).at(-1);
      let name = latest?.name;
      let prefix = "";
      if (latest && latest.bytes + bytes + 1 <= SEGMENT_BYTES) {
        if (latest.bytes) {
          const fd = fs.openSync(path.join(this.directory, latest.name), "r");
          try {
            const tail = Buffer.alloc(1);
            fs.readSync(fd, tail, 0, 1, latest.bytes - 1);
            if (tail[0] !== 10) prefix = "\n";
          } finally { fs.closeSync(fd); }
        }
      } else {
        const index = latest ? Number(latest.name.slice(11, 16)) + 1 : 0;
        if (index > 99999) return;
        name = `${today}-${String(index).padStart(5, "0")}.jsonl`;
      }
      fs.appendFileSync(path.join(this.directory, name!), prefix + line, { mode: 0o600 });
    } catch { /* Telemetry is fail-open, including retention/disk/lock failures. */ }
    finally {
      if (locked) { try { fs.rmdirSync(lock); } catch { /* fail-open */ } }
    }
  }

  report(from?: string, to?: string, now = new Date()) {
    const parse = (value: string | undefined, fallback: number): number => {
      if (value === undefined) return fallback;
      if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$/.test(value) || !Number.isFinite(Date.parse(value))) throw new Error("Date bounds must be UTC ISO timestamps (ending Z)");
      return Date.parse(value);
    };
    const retentionStart = now.getTime() - 30 * DAY;
    const start = parse(from, retentionStart), end = parse(to, now.getTime());
    if (start > end) throw new Error("from must not be after to");
    const rows: Metric[] = [];
    let ignoredRecords = 0;
    let available = true;
    try {
      for (const file of this.files()) {
        const raw = fs.readFileSync(path.join(this.directory, file.name), "utf8");
        const lines = raw.split("\n");
        const partial = lines.pop();
        if (partial) ignoredRecords++;
        for (const line of lines) {
          try {
            const row: unknown = JSON.parse(line);
            if (!valid(row)) { ignoredRecords++; continue; }
            if (Date.parse(row.timestamp) >= retentionStart && Date.parse(row.timestamp) <= now.getTime()) rows.push(row);
          } catch { ignoredRecords++; }
        }
      }
    } catch (error) {
      // A never-created store is empty; permission and other I/O failures are
      // unavailable, rather than an invented empty history.
      available = (error as NodeJS.ErrnoException).code === "ENOENT" && !fs.existsSync(this.directory);
    }
    rows.sort((a, b) => a.timestamp.localeCompare(b.timestamp));
    const selected = rows.filter(row => Date.parse(row.timestamp) >= start && Date.parse(row.timestamp) < end);
    const aggregate = (items: Metric[]) => {
      const durations = items.map(row => row.durationMs).sort((a, b) => a - b);
      const count = items.length;
      const success = items.filter(row => row.outcome === "success").length;
      return { count, success, error: items.filter(row => row.outcome === "error").length,
        cancelled: items.filter(row => row.outcome === "cancelled").length,
        successRate: count ? success / count : null,
        averageMs: count ? durations.reduce((a, b) => a + b, 0) / count : null,
        p50Ms: count ? durations[Math.ceil(count * .5) - 1] : null,
        p95Ms: count ? durations[Math.ceil(count * .95) - 1] : null };
    };
    return { available, window: { from: new Date(start).toISOString(), to: new Date(end).toISOString(), endExclusive: true },
      coverage: { retentionDays: 30, maxBytes: MAX_BYTES, firstRetained: rows[0]?.timestamp ?? null, lastRetained: rows.at(-1)?.timestamp ?? null,
        ignoredRecords, complete: false, denominator: "completed tools/call dispatcher entries; excludes pre-dispatch protocol rejection; storage failures may cause gaps" },
      overall: aggregate(selected), perTool: Object.fromEntries(TOOL_NAMES.map(tool => [tool, aggregate(selected.filter(row => row.tool === tool))])) };
  }
}

/** Decorate only the public registration API, retaining SDK schemas/validation. */
export function instrumentToolCalls(server: McpServer, metrics = new ToolMetrics()): void {
  const original: typeof server.server.setRequestHandler = server.server.setRequestHandler.bind(server.server);
  const decorated: typeof server.server.setRequestHandler = (schema, callback) => {
    if ((schema as unknown) !== CallToolRequestSchema) return original(schema, callback);
    original(schema, async (request, extra) => {
      const start = performance.now();
      let outcome: Metric["outcome"] = "success";
      let errorKind: Metric["errorKind"] = "none";
      try {
        const result = await callback(request, extra);
        if ((result as { isError?: boolean }).isError === true) { outcome = "error"; errorKind = "returned_error"; }
        return result;
      } catch (error) {
        outcome = "error"; errorKind = "thrown_error";
        throw error;
      } finally {
        if (extra.signal.aborted) { outcome = "cancelled"; errorKind = "aborted"; }
        const name = (request as { params?: { name?: unknown } }).params?.name;
        try {
          metrics.record({ timestamp: new Date().toISOString(), tool: TOOL_NAMES.includes(name as Metric["tool"]) ? name as Metric["tool"] : "unknown",
            durationMs: Math.max(0, performance.now() - start), outcome, errorKind });
        } catch { /* Injected or future recorders must also remain fail-open. */ }
      }
    });
  };
  server.server.setRequestHandler = decorated;
}
