import fs from "node:fs";
import path from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { CallToolRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";
import { ToolMetrics, instrumentToolCalls, type Metric } from "../src/mcp/tool-metrics.js";
import { createMcpServer } from "../src/mcp/server.js";
import { Workspace } from "../src/workspace/manager.js";
import { Logger } from "../src/logger/index.js";
import { makeTmpDir, cleanup, write } from "./helpers.js";

const dirs: string[] = [];
const originalState = process.env.C2C_STATE_DIR;
const tmp = () => { const dir = makeTmpDir("metrics"); dirs.push(dir); return dir; };
afterEach(() => {
  vi.restoreAllMocks();
  if (originalState === undefined) delete process.env.C2C_STATE_DIR;
  else process.env.C2C_STATE_DIR = originalState;
  dirs.splice(0).forEach(cleanup);
});
const row = (durationMs = 1, timestamp = new Date().toISOString()): Metric => ({ timestamp, tool: "workspace_info", durationMs, outcome: "success", errorKind: "none" });
const report = (store: ToolMetrics) => store.report(undefined, new Date(Date.now() + 1000).toISOString(), new Date(Date.now() + 1000));
async function connect(server: McpServer, scopes?: string[]) {
  const client = new Client({ name: "metrics-test", version: "1" });
  const [a, b] = InMemoryTransport.createLinkedPair();
  if (scopes) {
    const send = a.send.bind(a);
    a.send = (message, options) => send(message, { ...options, authInfo: { token: "secret-token", clientId: "secret-client", scopes } });
  }
  await server.connect(b);
  await client.connect(a);
  return client;
}

describe("MCP metrics dispatch boundary", () => {
  it("counts original SDK scope denial without persisting authentication metadata", async () => {
    const state = tmp(); process.env.C2C_STATE_DIR = state;
    const server = createMcpServer({ workspace: new Workspace(tmp()), logger: new Logger({ quiet: true }) });
    const client = await connect(server, ["workspace.read"]);
    const store = new ToolMetrics(path.join(state, "call-metrics"));
    try {
      const denied = await client.callTool({ name: "git_diff", arguments: {} });
      expect(denied.isError).toBe(true);
      expect(report(store).perTool.git_diff).toMatchObject({ count: 1, error: 1, success: 0 });
      const raw = fs.readdirSync(store.directory).map(file => fs.readFileSync(path.join(store.directory, file), "utf8")).join("");
      expect(raw).not.toContain("secret");
      expect(raw).not.toContain("INSUFFICIENT_SCOPE");
    } finally { await client.close(); await server.close(); }
  });

  it("records actual bridge calls, invalid input, scope/business errors and unknown names without recording initialization/list or secrets", async () => {
    const state = tmp(); process.env.C2C_STATE_DIR = state;
    const root = tmp(); write(root, "hello.txt", "secret-result");
    const server = createMcpServer({ workspace: new Workspace(root), logger: new Logger({ quiet: true }) });
    const client = await connect(server);
    const store = new ToolMetrics(path.join(state, "call-metrics"));
    try {
      await client.listTools();
      expect(report(store).overall.count).toBe(0);
      expect((await client.callTool({ name: "workspace_info", arguments: {} })).isError).not.toBe(true);
      expect((await client.callTool({ name: "read_file", arguments: { path: 123 } })).isError).toBe(true);
      expect((await client.callTool({ name: "read_file", arguments: { path: "missing-secret-path" } })).isError).toBe(true);
      expect((await client.callTool({ name: "secret-token-name", arguments: { secret: "secret-argument" } })).isError).toBe(true);
      const result = report(store);
      expect(result.overall).toMatchObject({ count: 4, success: 1, error: 3, successRate: .25 });
      expect(result.perTool.unknown.error).toBe(1);
      const raw = fs.readdirSync(store.directory).map(file => fs.readFileSync(path.join(store.directory, file), "utf8")).join("");
      for (const secret of ["secret-token-name", "secret-argument", "missing-secret-path", "secret-result", root]) expect(raw).not.toContain(secret);
      // Invalid basic protocol shape is rejected before the decorated callback.
      await expect(client.request({ method: "tools/call", params: { name: 123 } } as never, z.any())).rejects.toThrow();
      expect(report(store).overall.count).toBe(4);
    } finally { await client.close(); await server.close(); }
  });

  it("preserves result and rejection identity and classifies cancellation only using the abort signal", async () => {
    const store = new ToolMetrics(tmp());
    const server = new McpServer({ name: "test", version: "1" }, { capabilities: { tools: {} } });
    let handler: (request: any, extra: any) => Promise<any>;
    vi.spyOn(server.server, "setRequestHandler").mockImplementation((_schema, callback) => { handler = callback as typeof handler; });
    instrumentToolCalls(server, store);
    const result = { content: [], isError: true };
    server.server.setRequestHandler(CallToolRequestSchema, () => result);
    const controller = new AbortController();
    expect(await handler!({ params: { name: "read_file", arguments: { secret: "hidden" } } }, { signal: controller.signal })).toBe(result);
    const error = new Error("secret-error-text");
    server.server.setRequestHandler(CallToolRequestSchema, () => { throw error; });
    await expect(handler!({ params: { name: "secret-name" } }, { signal: controller.signal })).rejects.toBe(error);
    controller.abort();
    await expect(handler!({ params: { name: "read_file" } }, { signal: controller.signal })).rejects.toBe(error);
    expect(report(store).overall).toMatchObject({ count: 3, error: 2, cancelled: 1 });
    const rows = fs.readdirSync(store.directory).flatMap(file => fs.readFileSync(path.join(store.directory, file), "utf8").trim().split("\n").map(line => JSON.parse(line)));
    expect(rows.map(r => r.errorKind)).toEqual(["returned_error", "thrown_error", "aborted"]);
    expect(JSON.stringify(rows)).not.toContain("secret");
    vi.spyOn(store, "record").mockImplementation(() => { throw new Error("disk failure"); });
    await expect(handler!({ params: { name: "read_file" } }, { signal: controller.signal })).rejects.toBe(error);
  });

  it("records concurrent actual requests exactly once and SDK cancellation after callback settlement", async () => {
    const store = new ToolMetrics(tmp());
    const server = new McpServer({ name: "test", version: "1" });
    instrumentToolCalls(server, store);
    let started!: () => void;
    const ready = new Promise<void>(resolve => { started = resolve; });
    server.registerTool("workspace_info", { inputSchema: { wait: z.boolean().optional() } }, async (args, extra) => {
      if (args.wait) {
        started();
        await new Promise<void>(resolve => extra.signal.addEventListener("abort", () => resolve(), { once: true }));
      }
      return { content: [] };
    });
    const client = await connect(server);
    try {
      await Promise.all(Array.from({ length: 40 }, () => client.callTool({ name: "workspace_info", arguments: {} })));
      expect(report(store).overall.count).toBe(40);
      const controller = new AbortController();
      const pending = client.callTool({ name: "workspace_info", arguments: { wait: true } }, undefined, { signal: controller.signal });
      const rejection = expect(pending).rejects.toThrow();
      await ready; controller.abort(); await rejection;
      await vi.waitFor(() => expect(report(store).overall.cancelled).toBe(1));
      expect(report(store).overall.count).toBe(41);
    } finally { await client.close(); await server.close(); }
  });
});

describe("bounded metrics storage and reports", () => {
  it("returns null for empty reports; computes nearest-rank percentiles and UTC half-open filtering", () => {
    const store = new ToolMetrics(tmp());
    expect(report(store).overall).toMatchObject({ count: 0, successRate: null, averageMs: null, p50Ms: null, p95Ms: null });
    const now = new Date("2026-10-08T12:00:00.000Z");
    for (let i = 1; i <= 20; i++) store.record(row(i, `2026-10-08T00:00:${String(i).padStart(2, "0")}.000Z`));
    expect(store.report(undefined, undefined, now).overall).toMatchObject({ count: 20, averageMs: 10.5, p50Ms: 10, p95Ms: 19 });
    expect(store.report("2026-10-08T00:00:10Z", "2026-10-08T00:00:12Z", now).overall).toMatchObject({ count: 2, averageMs: 10.5 });
    expect(() => store.report("yesterday")).toThrow();
    expect(() => store.report("2026-10-09T00:00:00Z", "2026-10-08T00:00:00Z")).toThrow();
  });

  it("ignores corrupt/partial/privacy-invalid records and repairs an interrupted append", () => {
    const dir = tmp(); const store = new ToolMetrics(dir);
    const file = path.join(dir, `${new Date().toISOString().slice(0, 10)}-00000.jsonl`);
    fs.writeFileSync(file, `not-json\n${JSON.stringify({ ...row(), arguments: "secret" })}\n{"partial":`);
    expect(report(store).coverage.ignoredRecords).toBe(3);
    store.record(row());
    expect(report(store).overall.count).toBe(1);
    expect(report(store).coverage.ignoredRecords).toBe(3);
    store.record({ ...row(), tool: "arbitrary-secret" } as Metric);
    expect(report(store).overall.count).toBe(1);
  });

  it("prunes old days and oldest segments to keep data below 30 MiB; old rows never appear as all-time totals", () => {
    const dir = tmp(); const store = new ToolMetrics(dir);
    fs.writeFileSync(path.join(dir, "2020-01-01-00000.jsonl"), JSON.stringify(row(1, "2020-01-01T00:00:00.000Z")) + "\n");
    const today = new Date().toISOString().slice(0, 10);
    for (let i = 0; i < 31; i++) fs.writeFileSync(path.join(dir, `${today}-${String(i).padStart(5, "0")}.jsonl`), Buffer.alloc(1024 * 1024, 32));
    store.record(row());
    expect(fs.existsSync(path.join(dir, "2020-01-01-00000.jsonl"))).toBe(false);
    const total = fs.readdirSync(dir).reduce((sum, file) => sum + fs.statSync(path.join(dir, file)).size, 0);
    expect(total).toBeLessThanOrEqual(30 * 1024 * 1024);
    expect(report(store).overall.count).toBe(1);
    expect(report(store).coverage.complete).toBe(false);
  });

  it("fails open for disk errors and competing writers, and reports unreadable storage honestly", () => {
    const dir = tmp(); const store = new ToolMetrics(dir);
    fs.mkdirSync(path.join(dir, ".writer-lock"));
    expect(() => store.record(row())).not.toThrow();
    expect(report(store).overall.count).toBe(0);
    fs.rmdirSync(path.join(dir, ".writer-lock"));
    vi.spyOn(fs, "appendFileSync").mockImplementation(() => { throw new Error("disk full"); });
    expect(() => store.record(row())).not.toThrow();
    expect(fs.existsSync(path.join(dir, ".writer-lock"))).toBe(false);
    vi.spyOn(fs, "readdirSync").mockImplementation(() => { throw new Error("denied"); });
    expect(report(store).available).toBe(false);
  });
});
