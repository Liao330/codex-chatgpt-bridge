#!/usr/bin/env node
import { createHash, randomBytes } from "node:crypto";
import { Client } from "../vendor/codex-with-chatgpt/node_modules/@modelcontextprotocol/sdk/dist/esm/client/index.js";
import { StreamableHTTPClientTransport } from "../vendor/codex-with-chatgpt/node_modules/@modelcontextprotocol/sdk/dist/esm/client/streamableHttp.js";

const [base, pairingCode, expectedWorkspace] = process.argv.slice(2);
if (!base || !pairingCode) {
  console.error("usage: node scripts/c2c-data-plane-smoke.mjs <baseUrl> <pairingCode> [workspaceName]");
  process.exit(1);
}

const redirectUri = "http://127.0.0.1:19877/callback";
const prm = await (await fetch(`${base}/.well-known/oauth-protected-resource/mcp`)).json();
const authServer = prm.authorization_servers[0];
const asMeta = await (await fetch(`${authServer}/.well-known/oauth-authorization-server`)).json();
const registration = await (await fetch(asMeta.registration_endpoint, {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ client_name: "C2C Data Plane Smoke", redirect_uris: [redirectUri] }),
})).json();
const verifier = randomBytes(32).toString("base64url");
const challenge = createHash("sha256").update(verifier).digest("base64url");
const authorizeUrl = new URL(asMeta.authorization_endpoint);
authorizeUrl.searchParams.set("client_id", registration.client_id);
authorizeUrl.searchParams.set("redirect_uri", redirectUri);
authorizeUrl.searchParams.set("response_type", "code");
authorizeUrl.searchParams.set("state", randomBytes(8).toString("hex"));
authorizeUrl.searchParams.set("code_challenge", challenge);
authorizeUrl.searchParams.set("code_challenge_method", "S256");
authorizeUrl.searchParams.set("scope", asMeta.scopes_supported.join(" "));
const page = await fetch(authorizeUrl, { redirect: "manual" });
const html = await page.text();
const requestId = html.match(/name="request_id" value="([a-f0-9]+)"/)?.[1];
if (!requestId) throw new Error("authorization page did not expose request_id");
const submit = await fetch(asMeta.authorization_endpoint, {
  method: "POST",
  headers: { "content-type": "application/x-www-form-urlencoded" },
  body: new URLSearchParams({ request_id: requestId, pairing_code: pairingCode }),
  redirect: "manual",
});
if (submit.status !== 302) throw new Error(`pairing failed with status ${submit.status}`);
const code = new URL(submit.headers.get("location")).searchParams.get("code");
const tokenResponse = await fetch(asMeta.token_endpoint, {
  method: "POST",
  headers: { "content-type": "application/x-www-form-urlencoded" },
  body: new URLSearchParams({ grant_type: "authorization_code", code, code_verifier: verifier, client_id: registration.client_id, redirect_uri: redirectUri }),
});
const tokens = await tokenResponse.json();
if (!tokens.access_token) throw new Error("token exchange failed");

const client = new Client({ name: "c2c-data-plane-smoke", version: "1.0.0" });
await client.connect(new StreamableHTTPClientTransport(new URL(`${base}/mcp`), {
  requestInit: { headers: { authorization: `Bearer ${tokens.access_token}` } },
}));
const call = async (name, args = {}) => {
  const result = await client.callTool({ name, arguments: args });
  return { result, value: JSON.parse(result.content[0].text) };
};

const tools = (await client.listTools()).tools.map((tool) => tool.name);
const info = await call("workspace_info");
if (expectedWorkspace && info.value.workspaceName !== expectedWorkspace) throw new Error(`wrong workspace: ${info.value.workspaceName}`);
const source = await call("read_file", { path: "sample.py" });
if (!String(source.value.content).includes("return a + b")) throw new Error("fixed source was not visible through read_file");
const secret = await call("read_file", { path: ".env" });
if (secret.result.isError !== true) throw new Error(".env was not denied");
const status = await call("git_status");
const diff = await call("git_diff", { mode: "unstaged" });
const tests = await call("test_status");
const executions = await call("execution_summary", { limit: 5 });
const outputs = await call("execution_output", { action: "list", limit: 5 });
let outputText = null;
const readable = outputs.value.items?.find((item) => item.readable);
if (readable) outputText = (await call("execution_output", { action: "read", id: readable.id })).value.text;
await client.close();

const summary = {
  tools,
  workspace: info.value.workspaceName,
  branch: status.value.branch,
  diffContainsFix: JSON.stringify(diff.value).includes("return a + b"),
  tests: tests.value,
  executions: executions.value.records?.length ?? 0,
  readableOutputs: outputs.value.items?.filter((item) => item.readable).length ?? 0,
  outputContainsPassed: outputText ? /OK|passed|Ran 1 test/i.test(outputText) : false,
  envDenied: true,
};
console.log(JSON.stringify(summary, null, 2));
if (!summary.diffContainsFix || !summary.tests.available || summary.executions < 1 || !summary.envDenied) {
  throw new Error("data-plane assertions failed");
}
console.log("C2C DATA PLANE SMOKE PASSED");
