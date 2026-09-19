import { describe, it, expect, beforeAll, afterAll } from "vitest";
import fs from "node:fs";
import path from "node:path";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";
import { startBridge, type Bridge } from "../src/bridge/server.js";
import { cleanup, isolateStateDir, makeTmpDir, makeGitRepo, write, git } from "./helpers.js";

let parentRoot: string;
let bridge: Bridge;
let client: Client;
let stateDir: string;

function jsonOf<T = Record<string, unknown>>(result: { content?: unknown }): T {
  const content = result.content as { type: string; text: string }[];
  return JSON.parse(content?.[0]?.text ?? "{}") as T;
}

beforeAll(async () => {
  stateDir = isolateStateDir();
  parentRoot = makeTmpDir("multi-repo-root");

  // Two independent repositories under one workspace root.
  for (const name of ["alpha", "beta"]) {
    const repo = path.join(parentRoot, name);
    fs.mkdirSync(repo, { recursive: true });
    makeGitRepo(repo);
    write(repo, "file.txt", `${name} original\n`);
    git(repo, "add", ".");
    git(repo, "commit", "-m", "add file");
    write(repo, "file.txt", `${name} changed\n`);
  }

  bridge = await startBridge({
    workspaceRoot: parentRoot,
    port: 0,
    persistRuntime: false,
    authStoreFile: path.join(makeTmpDir("auth"), "store.json"),
  });
  const tokens = bridge.authStore.issueTokens({
    clientId: "multi-repo-client",
    scopes: ["workspace.read", "workspace.search", "git.read", "execution.read"],
  });

  client = new Client({ name: "c2c-multi-repo-client", version: "1.0.0" });
  const transport = new StreamableHTTPClientTransport(new URL(`${bridge.localBaseUrl()}/mcp`), {
    requestInit: { headers: { authorization: `Bearer ${tokens.accessToken}` } },
  });
  await client.connect(transport);
});

afterAll(async () => {
  await client.close();
  await bridge.close();
  cleanup(parentRoot);
});

describe("multi-repo workspace root", () => {
  it("reports the repositories under the root", async () => {
    const info = jsonOf<{ repos: string[]; git: { isRepo: boolean } }>(
      await client.callTool({ name: "workspace_info", arguments: {} })
    );
    expect(info.repos).toEqual(expect.arrayContaining(["alpha", "beta"]));
    // Whether the *root itself* counts as a repo depends on where the temp dir lives
    // (test temp dirs sit inside this project), so only the discovery list is asserted.
  });

  it("scopes git_status to the selected repository", async () => {
    const status = jsonOf<{ isRepo: boolean; branch: string | null; unstaged: { path: string }[] }>(
      await client.callTool({ name: "git_status", arguments: { repo: "alpha" } })
    );
    expect(status.isRepo).toBe(true);
    expect(status.branch).toBe("main");
    expect(status.unstaged.map((c) => c.path)).toContain("file.txt");
  });

  it("scopes git_diff to the selected repository", async () => {
    const diff = jsonOf<{ isRepo: boolean; diff: string }>(
      await client.callTool({ name: "git_diff", arguments: { repo: "beta", mode: "unstaged" } })
    );
    expect(diff.isRepo).toBe(true);
    expect(diff.diff).toContain("beta changed");
    expect(diff.diff).not.toContain("alpha changed");
  });

  it("scopes a diff by path inside the selected repository", async () => {
    const diff = jsonOf<{ diff: string }>(
      await client.callTool({ name: "git_diff", arguments: { repo: "alpha", path: "file.txt" } })
    );
    expect(diff.diff).toContain("alpha changed");
  });

  it("reads files across repositories", async () => {
    const file = jsonOf<{ content: string }>(
      await client.callTool({ name: "read_file", arguments: { path: "beta/file.txt" } })
    );
    expect(file.content).toContain("beta changed");
  });

  it("still refuses paths outside the workspace", async () => {
    const result = await client.callTool({ name: "git_status", arguments: { repo: "../outside" } });
    const payload = jsonOf<{ error?: string }>(result);
    expect(payload.error).toBe("PATH_OUTSIDE_WORKSPACE");
  });
});
