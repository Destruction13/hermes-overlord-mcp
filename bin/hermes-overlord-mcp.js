#!/usr/bin/env node

import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import { createServer } from "node:http";
import os from "node:os";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { z } from "zod";

const PACKAGE_ROOT = path.resolve(path.join(path.dirname(fileURLToPath(import.meta.url)), ".."));
const NPM_PACKAGE_NAME = "@destruction13/hermes-overlord-mcp";
const SERVER_ID = "hermes-overlord";
const DISPLAY_NAME = "Hermes Overlord";
const VERSION = "1.1.0";

const ROOT = PACKAGE_ROOT;

function packageRefFromNpxLock() {
  const lockPath = path.join(PACKAGE_ROOT, "..", "..", ".package-lock.json");
  if (!fs.existsSync(lockPath)) return null;
  try {
    const lock = JSON.parse(fs.readFileSync(lockPath, "utf8"));
    const entry = lock.packages?.[`node_modules/${NPM_PACKAGE_NAME}`];
    const resolved = entry?.resolved;
    if (typeof resolved !== "string") return null;
    const match = resolved.match(/^git\+(?:ssh:\/\/git@|https:\/\/)github\.com[/:]([^/]+)\/([^#]+?)(?:\.git)?(?:#(.+))?$/i);
    if (!match) return null;
    const [, owner, repo] = match;
    return `github:${owner}/${repo}`;
  } catch {
    return null;
  }
}

const PACKAGE_NAME = process.env.HERMES_MCP_PACKAGE_NAME || process.env.npm_config_package || packageRefFromNpxLock() || NPM_PACKAGE_NAME;

function defaultHermesHome() {
  if (process.env.HERMES_HOME) return process.env.HERMES_HOME;
  if (process.platform === "win32" && process.env.LOCALAPPDATA) {
    return path.join(process.env.LOCALAPPDATA, "hermes");
  }
  return path.join(os.homedir(), ".hermes");
}

function baseEnv(extra = {}) {
  return {
    ...process.env,
    PYTHONUTF8: process.env.PYTHONUTF8 || "1",
    PYTHONIOENCODING: process.env.PYTHONIOENCODING || "utf-8",
    HERMES_HOME: defaultHermesHome(),
    HERMES_OVERLORD_ROOT: process.env.HERMES_OVERLORD_ROOT || ROOT,
    HERMES_BRIDGE_ROOT: process.env.HERMES_BRIDGE_ROOT || ROOT,
    HERMES_BRIDGE_PROFILE: process.env.HERMES_BRIDGE_PROFILE || "overlord",
    HERMES_BRIDGE_BOARD: process.env.HERMES_BRIDGE_BOARD || "overlord",
    HERMES_BRIDGE_CLIENT: process.env.HERMES_BRIDGE_CLIENT || "npx/mcp-client",
    ...extra,
  };
}

function findPython() {
  const explicit = process.env.HERMES_PYTHON;
  const candidates = [];
  if (explicit) candidates.push({ command: explicit, args: [] });
  if (process.platform === "win32") candidates.push({ command: "py", args: ["-3"] });
  candidates.push({ command: "python", args: [] });
  candidates.push({ command: "python3", args: [] });
  for (const candidate of candidates) {
    const check = spawnSync(candidate.command, [...candidate.args, "--version"], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "pipe"],
    });
    if (check.status === 0) return candidate;
  }
  return null;
}

function runPython(args, options = {}) {
  const python = findPython();
  if (!python) {
    throw new Error("Python 3 was not found. Install Python 3 or set HERMES_PYTHON.");
  }
  return spawn(python.command, [...python.args, ...args], {
    cwd: ROOT,
    env: baseEnv(options.env || {}),
    stdio: options.stdio || "inherit",
  });
}

function runPythonSync(args) {
  const python = findPython();
  if (!python) {
    return { status: 1, stdout: "", stderr: "Python 3 was not found. Install Python 3 or set HERMES_PYTHON." };
  }
  return spawnSync(python.command, [...python.args, ...args], {
    cwd: ROOT,
    env: baseEnv(),
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
}

function parseJsonOutput(result) {
  if (result.status !== 0) {
    const message = [result.stderr, result.stdout].filter(Boolean).join("\n").trim();
    throw new Error(message || `Hermes command failed with exit code ${result.status}`);
  }
  const text = (result.stdout || "").trim();
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch (error) {
    return { ok: true, text };
  }
}

function bridgeCliArgs(command, params = {}) {
  const board = params.board || process.env.HERMES_BRIDGE_BOARD || "overlord";
  const args = ["-m", "bridge.cli", "--root", ROOT, "--board", board, command];
  switch (command) {
    case "submit":
      args.push(params.goal || "");
      if (params.workspace) args.push("--workspace", params.workspace);
      if (params.assignee) args.push("--assignee", params.assignee);
      if (params.mode) args.push("--mode", params.mode);
      if (Number.isInteger(params.priority)) args.push("--priority", String(params.priority));
      if (params.idempotency_key) args.push("--idempotency-key", params.idempotency_key);
      if (params.max_runtime) args.push("--max-runtime", params.max_runtime);
      if (params.dispatch) args.push("--dispatch");
      if (params.include_micro_reports === false) args.push("--no-micro-reports");
      if (params.dry_run) args.push("--dry-run");
      break;
    case "status":
    case "report":
    case "events":
    case "heartbeat-prompt":
    case "log":
    case "comment":
      args.push("--task-id", params.task_id || "");
      if (command === "report") {
        if (Number.isInteger(params.max_children)) args.push("--max-children", String(params.max_children));
        if (Number.isInteger(params.log_tail_bytes)) args.push("--log-tail-bytes", String(params.log_tail_bytes));
      }
      if (command === "events" && Number.isInteger(params.max_children)) args.push("--max-children", String(params.max_children));
      if (command === "log" && Number.isInteger(params.tail_bytes)) args.push("--tail-bytes", String(params.tail_bytes));
      if (command === "comment") args.push("--comment", params.comment || "");
      break;
    case "list":
      if (params.status) args.push("--status", params.status);
      if (params.assignee) args.push("--assignee", params.assignee);
      if (Number.isInteger(params.limit)) args.push("--limit", String(params.limit));
      break;
    case "direct-ask":
      args.push(params.query || "");
      if (Number.isInteger(params.timeout_seconds)) args.push("--timeout-seconds", String(params.timeout_seconds));
      if (params.toolsets) args.push("--toolsets", params.toolsets);
      for (const skill of params.skills || []) args.push("--skill", skill);
      if (params.ignore_rules) args.push("--ignore-rules");
      break;
    case "autocheck":
      if (params.deep) args.push("--deep");
      break;
    default:
      break;
  }
  return args;
}

async function runBridge(command, params = {}) {
  const result = runPythonSync(bridgeCliArgs(command, params));
  return parseJsonOutput(result);
}

function textResponse(data) {
  return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] };
}

function registerTools(server) {
  server.registerTool(
    "hermes_submit_task",
    {
      title: "Submit Hermes task",
      description: "Submit exactly one durable root handoff to Hermes Overlord.",
      inputSchema: {
        goal: z.string().min(1),
        workspace: z.string().optional(),
        board: z.string().optional(),
        assignee: z.string().optional(),
        mode: z.enum(["task", "triage"]).default("task"),
        include_micro_reports: z.boolean().default(true),
        priority: z.number().int().default(0),
        idempotency_key: z.string().optional(),
        max_runtime: z.string().optional(),
        dispatch: z.boolean().default(false),
        dry_run: z.boolean().default(false),
      },
    },
    async (params) => textResponse(await runBridge("submit", params)),
  );

  server.registerTool(
    "hermes_task_status",
    { title: "Hermes task status", description: "Return one Hermes Kanban task status.", inputSchema: { task_id: z.string(), board: z.string().optional() } },
    async (params) => textResponse(await runBridge("status", params)),
  );

  server.registerTool(
    "hermes_task_report",
    {
      title: "Hermes task report",
      description: "Return a curator-friendly report for a Hermes task family.",
      inputSchema: { task_id: z.string(), board: z.string().optional(), log_tail_bytes: z.number().int().optional(), max_children: z.number().int().optional() },
    },
    async (params) => textResponse(await runBridge("report", params)),
  );

  server.registerTool(
    "hermes_task_events",
    { title: "Hermes task events", description: "Return structured bridge and Kanban events.", inputSchema: { task_id: z.string(), board: z.string().optional(), max_children: z.number().int().optional() } },
    async (params) => textResponse(await runBridge("events", params)),
  );

  server.registerTool(
    "hermes_heartbeat_prompt",
    { title: "Hermes heartbeat prompt", description: "Generate a client heartbeat prompt for an exact Hermes task id.", inputSchema: { task_id: z.string(), board: z.string().optional() } },
    async (params) => textResponse(await runBridge("heartbeat-prompt", params)),
  );

  server.registerTool(
    "hermes_task_list",
    {
      title: "Hermes task list",
      description: "List Hermes Kanban tasks.",
      inputSchema: { board: z.string().optional(), status: z.string().optional(), assignee: z.string().optional(), limit: z.number().int().optional() },
    },
    async (params) => textResponse(await runBridge("list", params)),
  );

  server.registerTool(
    "hermes_task_comment",
    { title: "Hermes task comment", description: "Append a curator comment to a Hermes task.", inputSchema: { task_id: z.string(), comment: z.string(), board: z.string().optional() } },
    async (params) => textResponse(await runBridge("comment", params)),
  );

  server.registerTool(
    "hermes_task_log",
    { title: "Hermes task log", description: "Return the tail of a Hermes worker log.", inputSchema: { task_id: z.string(), board: z.string().optional(), tail_bytes: z.number().int().optional() } },
    async (params) => textResponse(await runBridge("log", params)),
  );

  server.registerTool(
    "hermes_dispatch_once",
    { title: "Hermes dispatch once", description: "Run one Hermes Kanban dispatcher pass.", inputSchema: { board: z.string().optional() } },
    async (params) => textResponse(await runBridge("dispatch", params)),
  );

  server.registerTool(
    "hermes_gateway_status",
    { title: "Hermes gateway status", description: "Return Hermes gateway process status.", inputSchema: {} },
    async () => textResponse(await runBridge("gateway-status", {})),
  );

  server.registerTool(
    "hermes_autocheck",
    { title: "Hermes autocheck", description: "Return quiet bridge, gateway, and Kanban health summary.", inputSchema: { board: z.string().optional(), deep: z.boolean().default(false) } },
    async (params) => textResponse(await runBridge("autocheck", params)),
  );

  server.registerTool(
    "hermes_direct_ask",
    {
      title: "Hermes direct ask",
      description: "Ask Hermes Overlord synchronously for explicit short questions.",
      inputSchema: { query: z.string(), timeout_seconds: z.number().int().optional(), toolsets: z.string().optional(), skills: z.array(z.string()).optional(), ignore_rules: z.boolean().default(false) },
    },
    async (params) => textResponse(await runBridge("direct-ask", params)),
  );
}

function createMcpServer() {
  const server = new McpServer(
    { name: SERVER_ID, title: DISPLAY_NAME, version: VERSION },
    {
      instructions:
        "Hermes Overlord is a client-neutral MCP gateway. Submit one durable root task, then read report/status/events; Hermes owns routing, specialists, tools, review, and synthesis.",
    },
  );
  registerTools(server);
  return server;
}

async function startStdio() {
  const server = createMcpServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

async function startHttp(argv) {
  const host = valueAfter(argv, "--host") || process.env.HERMES_OVERLORD_MCP_HOST || "127.0.0.1";
  const port = Number(valueAfter(argv, "--port") || process.env.HERMES_OVERLORD_MCP_PORT || 8765);
  const mcpPath = valueAfter(argv, "--path") || process.env.HERMES_OVERLORD_MCP_PATH || "/mcp";
  const httpServer = createServer(async (req, res) => {
    if (!req.url?.startsWith(mcpPath)) {
      res.writeHead(404).end("not found");
      return;
    }
    if (req.method !== "POST") {
      res.writeHead(405, { "content-type": "application/json" }).end(
        JSON.stringify({ jsonrpc: "2.0", error: { code: -32000, message: "Method not allowed." }, id: null }),
      );
      return;
    }
    const server = createMcpServer();
    const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined });
    try {
      await server.connect(transport);
      await transport.handleRequest(req, res, await readJsonBody(req));
      res.on("close", () => {
        transport.close();
        server.close();
      });
    } catch (error) {
      console.error(error?.stack || error?.message || String(error));
      if (!res.headersSent) res.writeHead(500, { "content-type": "application/json" });
      res.end(JSON.stringify({ jsonrpc: "2.0", error: { code: -32603, message: "Internal server error" }, id: null }));
    }
  });
  httpServer.listen(port, host, () => {
    console.error(`${DISPLAY_NAME} MCP HTTP listening at http://${host}:${port}${mcpPath}`);
  });
}

function readJsonBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", (chunk) => chunks.push(chunk));
    req.on("error", reject);
    req.on("end", () => {
      const text = Buffer.concat(chunks).toString("utf8");
      if (!text.trim()) return resolve(undefined);
      try {
        resolve(JSON.parse(text));
      } catch (error) {
        reject(error);
      }
    });
  });
}

function valueAfter(argv, flag) {
  const index = argv.indexOf(flag);
  if (index >= 0 && index + 1 < argv.length) return argv[index + 1];
  return undefined;
}

function printHelp() {
  console.log(`Hermes Overlord MCP\n\nUsage:\n  hermes-overlord-mcp                 Start MCP over stdio\n  hermes-overlord-mcp mcp             Start MCP over stdio\n  hermes-overlord-mcp start-http      Start MCP over Streamable HTTP\n  hermes-overlord-mcp init            Initialize HERMES_HOME and write a config snippet\n  hermes-overlord-mcp install         Print install guide/snippets for MCP clients\n  hermes-overlord-mcp config          Print an MCP config snippet\n  hermes-overlord-mcp doctor          Check local readiness\n  hermes-overlord-mcp package         Build dist/hermes-portable\n  hermes-overlord-mcp clean-audit     Audit/quarantine local artifacts\n\nExamples:\n  npx -y ${PACKAGE_NAME} install\n  npx -y ${PACKAGE_NAME} install --client claude-code\n  npx -y ${PACKAGE_NAME} init --client generic\n  npx -y ${PACKAGE_NAME} config --client vscode\n  npx -y ${PACKAGE_NAME} config --client kiro --format add-mcp\n  npx -y ${PACKAGE_NAME} doctor`);
}

function runHermesCtl(args) {
  const child = runPython([path.join(ROOT, "hermesctl.py"), ...args]);
  child.on("exit", (code) => process.exit(code ?? 1));
}

async function main() {
  const argv = process.argv.slice(2);
  const command = argv[0];
  if (!command || command === "mcp" || command === "stdio") {
    await startStdio();
    return;
  }
  if (command === "start-http" || command === "http") {
    await startHttp(argv.slice(1));
    return;
  }
  if (command === "help" || command === "--help" || command === "-h") {
    printHelp();
    return;
  }
  if (command === "doctor") return runHermesCtl(["doctor", ...argv.slice(1)]);
  if (command === "package") return runHermesCtl(["package", ...argv.slice(1)]);
  if (command === "clean-audit") return runHermesCtl(["clean-audit", ...argv.slice(1)]);
  if (command === "config" || command === "mcp-config") return runHermesCtl(["mcp-config", "--package-name", PACKAGE_NAME, ...argv.slice(1)]);
  if (command === "init") return runHermesCtl(["init", "--package-name", PACKAGE_NAME, ...argv.slice(1)]);
  if (command === "install") return runHermesCtl(["install", "--package-name", PACKAGE_NAME, ...argv.slice(1)]);
  console.error(`Unknown command: ${command}`);
  printHelp();
  process.exit(2);
}

main().catch((error) => {
  console.error(error?.stack || error?.message || String(error));
  process.exit(1);
});
