"""Codex-facing CLI fallback for explicit /hermes routing.

This script is intentionally separate from the MCP server so Codex can still
submit, inspect, and health-check Hermes when the MCP namespace is absent or a
Codex Desktop session has not hot-reloaded the latest MCP config.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import socket
import subprocess
import sys
import tempfile
import textwrap
import time
from collections import Counter
from pathlib import Path
from typing import Any


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(os.environ.get("HERMES_OVERLORD_ROOT", Path(__file__).resolve().parents[1]))
BOARD_DEFAULT = os.environ.get("HERMES_OVERLORD_BOARD", "overlord")
WORKSPACE_DEFAULT = os.environ.get("HERMES_OVERLORD_WORKSPACE", r"dir:C:\AI")
ASSIGNEE_DEFAULT = os.environ.get("HERMES_OVERLORD_ASSIGNEE", "overlord")
TIMEOUT_DEFAULT = int(os.environ.get("HERMES_OVERLORD_TIMEOUT", "180"))
MCP_HOST = os.environ.get("HERMES_OVERLORD_MCP_HOST", "127.0.0.1")
MCP_PORT = int(os.environ.get("HERMES_OVERLORD_MCP_PORT", "8765"))

SECRET_KEY_TOKENS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "COOKIE")

def _base_command() -> list[str]:
    explicit = os.environ.get("HERMES_OVERLORD_COMMAND")
    if explicit:
        import shlex

        return shlex.split(explicit)
    script = ROOT / "overlord.ps1"
    if platform.system().lower().startswith("win"):
        return ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)]
    return ["pwsh", "-NoProfile", "-File", str(script)]


def _env() -> dict[str, str]:
    env = dict(os.environ)
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("HERMES_QUIET", "1")
    env.setdefault("HERMES_REDACT_SECRETS", "true")
    if "HERMES_HOME" not in env and platform.system().lower().startswith("win"):
        local_app_data = env.get("LOCALAPPDATA")
        if local_app_data:
            env["HERMES_HOME"] = str(Path(local_app_data) / "hermes")
    return env


def _redact(text: str) -> str:
    redacted = text or ""
    for key, value in _env().items():
        if value and any(token in key.upper() for token in SECRET_KEY_TOKENS):
            redacted = redacted.replace(value, "<redacted>")
    # Coarse fallback for common literal token-looking fragments in command output.
    redacted = re.sub(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+", r"\1=<redacted>", redacted)
    return redacted


def _run(args: list[str], timeout: int = TIMEOUT_DEFAULT) -> subprocess.CompletedProcess[str]:
    command = [*_base_command(), *args]
    stdout_path = ""
    stderr_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False) as stdout_file, tempfile.NamedTemporaryFile(delete=False) as stderr_file:
            stdout_path = stdout_file.name
            stderr_path = stderr_file.name
            completed = subprocess.run(
                command,
                cwd=str(ROOT),
                env=_env(),
                stdin=subprocess.DEVNULL,
                stdout=stdout_file,
                stderr=stderr_file,
                timeout=timeout,
                check=False,
            )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Hermes Overlord command was not found. Set HERMES_OVERLORD_ROOT "
            "or HERMES_OVERLORD_COMMAND for this host."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Hermes Overlord command timed out after {timeout}s: {exc}") from exc

    stdout = Path(stdout_path).read_text(encoding="utf-8", errors="replace") if stdout_path else ""
    stderr = Path(stderr_path).read_text(encoding="utf-8", errors="replace") if stderr_path else ""
    for path in (stdout_path, stderr_path):
        if path:
            try:
                Path(path).unlink()
            except OSError:
                pass

    result = subprocess.CompletedProcess(command, completed.returncode, stdout=stdout, stderr=stderr)
    if result.returncode != 0:
        raise RuntimeError(
            json.dumps(
                {
                    "error": "Hermes Overlord command failed",
                    "exit_code": result.returncode,
                    "command": command[:6] + ["..."],
                    "stdout": _redact(result.stdout.strip())[-4000:],
                    "stderr": _redact(result.stderr.strip())[-4000:],
                },
                ensure_ascii=False,
            )
        )
    return result


def _json_stdout(result: subprocess.CompletedProcess[str], default: Any = None) -> Any:
    stdout = (result.stdout or "").strip()
    if not stdout:
        return default
    return json.loads(stdout)


def _emit(data: Any, human: bool = False) -> None:
    if human and isinstance(data, dict):
        print(_humanize(data))
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))


def _humanize(data: dict[str, Any]) -> str:
    if "handoff" in data and "delegation" in data:
        handoff = data.get("handoff") or {}
        delegation = data.get("delegation") or {}
        lines = [
            f"Задача: {handoff.get('task_id')} — {handoff.get('status')} — {handoff.get('title')}",
            f"Исполнитель: {handoff.get('assignee')}; summary: {handoff.get('latest_summary') or '—'}",
            f"Делегация: children={delegation.get('child_task_count', 0)}, profiles={', '.join(delegation.get('profiles_seen') or []) or '—'}",
        ]
        rollup = delegation.get("child_status_rollup") or {}
        if rollup:
            lines.append("Статусы детей: " + ", ".join(f"{k}={v}" for k, v in sorted(rollup.items())))
        tools = data.get("mcp_and_tools") or {}
        tool_names = tools.get("tool_calls_seen") or tools.get("mcp_tools_seen") or []
        if tool_names:
            lines.append("Tools/MCP: " + ", ".join(tool_names[:20]))
        blockers = data.get("blockers") or []
        if blockers:
            lines.append("Блокеры: " + " | ".join(str(b)[:160] for b in blockers[:3]))
        return "\n".join(lines)
    if "checks" in data:
        status = "OK" if data.get("ok") else "FAIL"
        checks = data.get("checks") or []
        lines = [f"Hermes autocheck: {status}"]
        for check in checks:
            lines.append(f"- {check.get('name')}: {'OK' if check.get('ok') else 'FAIL'} {check.get('summary') or ''}")
        return "\n".join(lines)
    return json.dumps(data, ensure_ascii=False, indent=2)


def _task_body(goal: str, workspace: str, include_micro_reports: bool = True) -> str:
    reporting = (
        "Post concise Kanban comments for material decisions, blocker changes, "
        "subtask handoffs, verification results, MCP/tool evidence, and final user-visible risks."
        if include_micro_reports
        else "Post only blockers and the final result."
    )
    return textwrap.dedent(
        f"""
        Goal: {goal}

        Workspace: {workspace}

        Explicit /hermes handoff contract:
        - Codex is only the external gateway/curator. Hermes Overlord is the executor and orchestration owner.
        - Codex submitted exactly one root handoff. Hermes decides whether this goal needs direct work, council, specialist workers, delegate_task, watchdog/reviewer/synth gates, or no subagents at all.
        - Preserve Hermes internals: Kanban decomposition, specialist profiles/souls, delegate_task, skills, MCP/tools, watchdog/reviewer/synth gates.
        - Start by reading this task with kanban_show/context.
        - Derive pragmatic acceptance criteria from the goal, workspace, and available evidence. Ask the user only when missing input makes safe execution impossible.
        - For non-trivial creation/build/design tasks, create a reviewable Kanban graph with product/UX or architecture planning as needed, the domain implementer profile for the task type, reviewer, and final synth.
        - Website, web app, landing page, dashboard, and browser UI tasks should include olfrontend when that profile is available.
        - For non-trivial `/hermes` build/design tasks, Overlord coordinates after the graph exists; it must not substitute itself for product/UX/frontend/backend implementation deliverables or manually complete those worker cards with Overlord-authored artifacts. If a specialist stalls, diagnose, reassign, retry, or split the task; do not silently replace the specialist.
        - Manual `reclaim` + `complete` is allowed only for reviewer/synth/evidence-only gate cards after their required evidence already exists and the closure metadata states the original worker evidence. It must never be used to make a product, UX, frontend, backend, or implementation worker appear to have completed Overlord's direct work.
        - First-level child cards should be linked to this root task when the tool surface supports it; otherwise post a `child_created` BRIDGE_EVENT with complete `children` and `graph` fields before dispatching workers.
        - Web/UI worker briefs should require checking Magic/shadcn or equivalent configured design/component MCPs when available. The worker should use a healthy fitting tool or record the concrete unavailable/not-applicable reason; do not claim MCP use from prompt text.
        - Use council profiles when useful: olarchitect, olresearcher, olproduct, olrisk, olux.
        - Create execution workers only when the task benefits from them; use specialist profiles when useful: olfrontend, olbackend, olautomation, olreviewer, olwatchdog, olsynth.
        - Worker task briefs must tell workers to read/follow their active profile SOUL.md (prefer `%LOCALAPPDATA%\\hermes\\profiles\\<profile>\\SOUL.md` or the injected profile prompt; do not treat docs/external-handoff snapshots as primary runtime instructions), check required MCP health, load/report relevant skills, provide evidence only for tools actually used, state acceptance criteria, and stop on blockers or unsafe/destructive operations.
        - Include olwatchdog for long-running work, olreviewer for verification, and olsynth for final synthesis.
        - Root lifecycle is part of the deliverable. If a reviewer/synth gate produces a terminal PASS/BLOCK final handoff for this root, the root owner or final synth must immediately mark this root task terminal with `kanban complete` or `kanban block`. Do not leave a Codex bridge root running after all child gates are terminal.
        - Name relevant MCPs/tools/skills in child task bodies and concise comments when they matter.
        - When posting child graph telemetry for Codex, include machine-readable children:[...] and preferably graph:{{task_id:{{profile,parents}}}} fields, not prose-only task ids.
        - {reporting}
        - Do not leak secrets. Avoid destructive commands unless the user explicitly asked for them.
        - For local preview servers, use an actually free non-reserved port. Treat Hermes/Codex service ports 8765, 8787, and 9119 as reserved unless the task is explicitly about those services.
        - Reviewer must block user-facing UI completion when browser/screenshot evidence shows blank hidden sections, broken reveal animations, missing responsive content, or only a partial hero instead of the promised complete experience.
        - Final output must include outcome, task/subagent evidence, verification, changed files if any, remaining risks, and a terminal root Kanban status.
        """
    ).strip()


def _status_task(task_id: str, board: str) -> dict[str, Any]:
    return _json_stdout(_run(["kanban", "--board", board, "show", task_id, "--json"]), {}) or {}


def _read_log(task_id: str, board: str, tail_bytes: int) -> str:
    try:
        result = _run(["kanban", "--board", board, "log", task_id, "--tail", str(max(1000, min(tail_bytes, 200000)))], timeout=60)
        return result.stdout or ""
    except Exception:
        return ""


def _summarize_log(log_text: str, max_lines: int = 24) -> dict[str, Any]:
    mcp_servers: dict[str, dict[str, Any]] = {}
    mcp_tools: set[str] = set()
    tool_calls: set[str] = set()
    material_lines: list[str] = []
    server_re = re.compile(r"MCP server '([^']+)'.*registered (\d+) tool\(s\):\s*(.*)")
    tool_call_res = (
        re.compile(r"Tool call:\s*([A-Za-z0-9_\-.]+)"),
        re.compile(r"Processing tool call[^:]*:\s*([A-Za-z0-9_\-.]+)"),
        re.compile(r"\b(functions\.[A-Za-z0-9_\-.]+)"),
    )
    for raw_line in log_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        server_match = server_re.search(line)
        if server_match:
            name, count, tools_blob = server_match.groups()
            tools = [part.strip() for part in tools_blob.split(",") if part.strip()]
            mcp_servers[name] = {"tool_count": int(count), "tools": tools[:30]}
            mcp_tools.update(tools)
        mcp_tools.update(re.findall(r"\bmcp_[A-Za-z0-9_]+", line))
        for pattern in tool_call_res:
            match = pattern.search(line)
            if match:
                tool_calls.add(match.group(1))
        lower = line.lower()
        if any(token in lower for token in ("mcp server", "tool call", "delegate", "delegat", "spawn", "kanban", "blocked", "complete", "error", "traceback", "review", "synth")):
            material_lines.append(_redact(line))
    return {
        "mcp_servers": mcp_servers,
        "mcp_tools_seen": sorted(mcp_tools),
        "tool_calls_seen": sorted(tool_calls),
        "material_log_lines": material_lines[-max_lines:],
    }


def _compact_task_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    task = snapshot.get("task") if isinstance(snapshot, dict) else {}
    task = task if isinstance(task, dict) else {}
    runs = snapshot.get("runs") if isinstance(snapshot, dict) else []
    runs = runs if isinstance(runs, list) else []
    latest_run = runs[-1] if runs and isinstance(runs[-1], dict) else {}
    return {
        "id": task.get("id"),
        "title": task.get("title"),
        "assignee": task.get("assignee"),
        "status": task.get("status"),
        "skills": task.get("skills"),
        "latest_summary": snapshot.get("latest_summary"),
        "latest_run": {
            "profile": latest_run.get("profile"),
            "status": latest_run.get("status"),
            "outcome": latest_run.get("outcome"),
            "summary": latest_run.get("summary"),
            "error": latest_run.get("error"),
        }
        if latest_run
        else None,
    }


def _report(task_id: str, board: str, tail_bytes: int, max_children: int = 50) -> dict[str, Any]:
    snapshot = _status_task(task_id, board)
    task = snapshot.get("task") if isinstance(snapshot, dict) else {}
    task = task if isinstance(task, dict) else {}
    child_ids_raw = snapshot.get("children") if isinstance(snapshot, dict) else []
    child_ids: list[str] = []
    child_details: list[dict[str, Any]] = []
    for item in child_ids_raw if isinstance(child_ids_raw, list) else []:
        if isinstance(item, str):
            child_ids.append(item)
        elif isinstance(item, dict):
            task_obj = item.get("task") if isinstance(item.get("task"), dict) else {}
            child_id = item.get("id") or task_obj.get("id")
            if child_id:
                child_ids.append(str(child_id))
            child_details.append(item)
    resolved_children: list[dict[str, Any]] = []
    child_log_signals: list[dict[str, Any]] = []
    for child_id in child_ids[:max_children]:
        try:
            child_snapshot = _status_task(child_id, board)
            compact = _compact_task_snapshot(child_snapshot)
            resolved_children.append(compact)
            log_summary = _summarize_log(_read_log(child_id, board, min(tail_bytes, 60000)), max_lines=8)
            if log_summary.get("mcp_servers") or log_summary.get("mcp_tools_seen") or log_summary.get("tool_calls_seen") or log_summary.get("material_log_lines"):
                child_log_signals.append({"task_id": child_id, **log_summary})
        except Exception as exc:
            resolved_children.append({"id": child_id, "error": _redact(str(exc))[:500]})
    # Include any already-detailed child dicts only if no resolved details were available.
    if not resolved_children and child_details:
        for item in child_details[:max_children]:
            source = item.get("task") if isinstance(item.get("task"), dict) else item
            resolved_children.append({
                "id": source.get("id"),
                "title": source.get("title"),
                "assignee": source.get("assignee"),
                "status": source.get("status"),
                "skills": source.get("skills"),
            })

    runs = snapshot.get("runs") if isinstance(snapshot, dict) else []
    runs = runs if isinstance(runs, list) else []
    events = snapshot.get("events") if isinstance(snapshot, dict) else []
    events = events if isinstance(events, list) else []
    comments = snapshot.get("comments") if isinstance(snapshot, dict) else []
    comments = comments if isinstance(comments, list) else []
    profiles = {str(task.get("assignee"))} if task.get("assignee") else set()
    profiles.update(str(c.get("assignee")) for c in resolved_children if c.get("assignee"))
    profiles.update(str(r.get("profile")) for r in runs if isinstance(r, dict) and r.get("profile"))
    statuses = Counter(str(c.get("status") or "unknown") for c in resolved_children)
    root_log_summary = _summarize_log(_read_log(task_id, board, tail_bytes))
    blockers: list[str] = []
    for comment in comments[-20:]:
        body = str(comment.get("body") if isinstance(comment, dict) else comment)
        if re.search(r"block|blocked|блок|ошиб|error|fail|risk", body, re.I):
            blockers.append(body[:500])
    for child in resolved_children:
        if child.get("status") == "blocked" or (child.get("latest_run") or {}).get("error"):
            blockers.append(json.dumps(child, ensure_ascii=False)[:500])

    return {
        "handoff": {
            "task_id": task.get("id") or task_id,
            "title": task.get("title"),
            "assignee": task.get("assignee"),
            "status": task.get("status"),
            "workspace": task.get("workspace_path"),
            "created_by": task.get("created_by"),
            "result": task.get("result"),
            "latest_summary": snapshot.get("latest_summary") if isinstance(snapshot, dict) else None,
        },
        "delegation": {
            "profiles_seen": sorted(p for p in profiles if p and p != "None"),
            "child_task_count": len(child_ids_raw) if isinstance(child_ids_raw, list) else len(resolved_children),
            "child_status_rollup": dict(sorted(statuses.items())),
            "children": resolved_children,
            "runs": [
                {
                    "id": r.get("id"),
                    "profile": r.get("profile"),
                    "status": r.get("status"),
                    "outcome": r.get("outcome"),
                    "summary": r.get("summary"),
                    "error": r.get("error"),
                }
                for r in runs[:50]
                if isinstance(r, dict)
            ],
        },
        "visibility": {
            "recent_comments": comments[-10:],
            "recent_events": events[-20:],
        },
        "mcp_and_tools": root_log_summary,
        "child_mcp_and_tool_signals": child_log_signals[:20],
        "blockers": blockers[:10],
    }


def _parse_slash(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if not stripped.startswith("/hermes"):
        return {"route": "codex", "action": "none", "reason": "no explicit /hermes opt-in"}
    rest = stripped[len("/hermes") :].strip()
    if not rest:
        return {"route": "hermes", "action": "help"}
    parts = rest.split(maxsplit=1)
    head = parts[0].lower()
    tail = parts[1].strip() if len(parts) > 1 else ""
    if head in {"status", "report", "log"} and tail:
        return {"route": "hermes", "action": head, "task_id": tail.split()[0]}
    if head in {"dispatch", "autocheck"}:
        return {"route": "hermes", "action": head}
    if head in {"ask"} and tail:
        return {"route": "hermes", "action": "ask", "query": tail}
    return {"route": "hermes", "action": "submit", "goal": rest}


def cmd_submit(args: argparse.Namespace) -> None:
    title_goal = " ".join(args.goal.split())[:120]
    cmd = [
        "kanban",
        "--board",
        args.board,
        "create",
        f"Codex /hermes handoff: {title_goal}",
        "--body",
        _task_body(args.goal, args.workspace, include_micro_reports=not args.no_micro_reports),
        "--assignee",
        args.assignee,
        "--workspace",
        args.workspace,
        "--priority",
        str(args.priority),
        "--created-by",
        "codex-wrapper",
        "--skill",
        "kanban-orchestrator",
        "--json",
    ]
    if args.mode == "triage":
        cmd.append("--triage")
    if args.idempotency_key:
        cmd.extend(["--idempotency-key", args.idempotency_key])
    if args.max_runtime:
        cmd.extend(["--max-runtime", args.max_runtime])
    data = _json_stdout(_run(cmd, timeout=max(args.timeout, 180)), {}) or {}
    if args.dispatch:
        try:
            _run(["kanban", "--board", args.board, "dispatch"], timeout=60)
        except Exception as exc:
            data = {"submit": data, "dispatch_warning": _redact(str(exc))[:1000]}
    _emit(data, args.human)


def cmd_status(args: argparse.Namespace) -> None:
    _emit(_status_task(args.task_id, args.board), args.human)


def cmd_report(args: argparse.Namespace) -> None:
    _emit(_report(args.task_id, args.board, args.tail_bytes, args.max_children), args.human)


def cmd_dispatch(args: argparse.Namespace) -> None:
    result = _run(["kanban", "--board", args.board, "dispatch"], timeout=60)
    payload = {"ok": True, "stdout": (result.stdout or "").strip(), "stderr": _redact((result.stderr or "").strip())}
    _emit(payload, args.human)


def _add_check(checks: list[dict[str, Any]], name: str, ok: bool, summary: str = "", data: Any = None) -> None:
    checks.append({"name": name, "ok": bool(ok), "summary": summary[:500], "data": data})


def _port_open(host: str, port: int, timeout: float = 0.7) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def cmd_autocheck(args: argparse.Namespace) -> None:
    checks: list[dict[str, Any]] = []
    _add_check(checks, "root", ROOT.exists(), str(ROOT))
    python_files = [ROOT / "mcp" / "hermes_overlord_mcp.py", ROOT / "mcp" / "codex_hermes_cli.py"]
    for file_path in python_files:
        if not file_path.exists():
            _add_check(checks, f"py_compile:{file_path.name}", False, "file missing")
            continue
        proc = subprocess.run([sys.executable, "-m", "py_compile", str(file_path)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        _add_check(checks, f"py_compile:{file_path.name}", proc.returncode == 0, _redact((proc.stderr or proc.stdout or "ok").strip()))

    _add_check(checks, "mcp_http_port", _port_open(MCP_HOST, MCP_PORT), f"{MCP_HOST}:{MCP_PORT}")

    if args.deep:
        preflight = ROOT / "mcp" / "codex-hermes-preflight.ps1"
        if preflight.exists():
            proc = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(preflight), "-Quiet", "-TimeoutSeconds", str(args.timeout)],
                cwd=str(ROOT),
                env=_env(),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=max(args.timeout + 10, 60),
            )
            _add_check(checks, "mcp_preflight", proc.returncode == 0, _redact((proc.stderr or proc.stdout or "ok").strip())[-500:])
        else:
            _add_check(checks, "mcp_preflight", False, "preflight script missing")

    try:
        gateway = _run(["gateway", "status"], timeout=60)
        stdout = gateway.stdout.strip()
        _add_check(checks, "gateway_status", "Gateway process running" in stdout, stdout[-500:])
    except Exception as exc:
        _add_check(checks, "gateway_status", False, _redact(str(exc))[:500])

    try:
        stats = _json_stdout(_run(["kanban", "--board", args.board, "stats", "--json"], timeout=60), {})
        _add_check(checks, "kanban_stats", True, "stats ok", stats)
    except Exception as exc:
        _add_check(checks, "kanban_stats", False, _redact(str(exc))[:500])

    try:
        diagnostics = _json_stdout(_run(["kanban", "--board", args.board, "diagnostics", "--json"], timeout=60), [])
        diag_count = len(diagnostics) if isinstance(diagnostics, list) else 0
        severe = []
        if isinstance(diagnostics, list):
            severe = [d for d in diagnostics if str(d.get("severity", "")).lower() in {"error", "critical"}]
        _add_check(checks, "kanban_diagnostics", len(severe) == 0, f"diagnostics={diag_count}, severe={len(severe)}", severe[:10])
    except Exception as exc:
        _add_check(checks, "kanban_diagnostics", False, _redact(str(exc))[:500])

    try:
        mcp_list = _run(["mcp", "list"], timeout=90)
        text = mcp_list.stdout.strip()
        _add_check(checks, "hermes_profile_mcp_list", True, "mcp list ok", text[-1500:])
    except Exception as exc:
        _add_check(checks, "hermes_profile_mcp_list", False, _redact(str(exc))[:500])

    payload = {
        "ok": all(check.get("ok") for check in checks),
        "checked_at": int(time.time()),
        "board": args.board,
        "checks": checks,
    }
    _emit(payload, args.human)


def cmd_parse(args: argparse.Namespace) -> None:
    _emit(_parse_slash(args.text), args.human)


def cmd_slash(args: argparse.Namespace) -> None:
    parsed = _parse_slash(args.text)
    if parsed.get("route") != "hermes":
        _emit(parsed, args.human)
        return
    action = parsed.get("action")
    if action == "submit":
        ns = argparse.Namespace(
            goal=parsed.get("goal") or "",
            board=args.board,
            workspace=args.workspace,
            assignee=ASSIGNEE_DEFAULT,
            mode=args.mode,
            idempotency_key=args.idempotency_key,
            max_runtime="4h",
            priority=0,
            timeout=args.timeout,
            dispatch=args.dispatch,
            no_micro_reports=False,
            human=args.human,
        )
        cmd_submit(ns)
    elif action == "status":
        cmd_status(argparse.Namespace(task_id=parsed.get("task_id"), board=args.board, human=args.human))
    elif action == "report":
        cmd_report(argparse.Namespace(task_id=parsed.get("task_id"), board=args.board, tail_bytes=40000, max_children=50, human=args.human))
    elif action == "dispatch":
        cmd_dispatch(argparse.Namespace(board=args.board, human=args.human))
    elif action == "autocheck":
        cmd_autocheck(argparse.Namespace(board=args.board, timeout=args.timeout, deep=args.deep, human=args.human))
    else:
        _emit(parsed, args.human)


def _normalize_argv(argv: list[str]) -> list[str]:
    aliases = {
        "-TaskId": "--task-id",
        "-Board": "--board",
        "-Workspace": "--workspace",
        "-Assignee": "--assignee",
        "-Mode": "--mode",
        "-IdempotencyKey": "--idempotency-key",
        "-MaxRuntime": "--max-runtime",
        "-Priority": "--priority",
        "-Timeout": "--timeout",
        "-TimeoutSeconds": "--timeout",
        "-TailBytes": "--tail-bytes",
        "-MaxChildren": "--max-children",
        "-Json": "--json",
        "-Human": "--human",
        "-Dispatch": "--dispatch",
        "-NoDispatch": "--no-dispatch",
        "-Deep": "--deep",
        "-NoMicroReports": "--no-micro-reports",
    }
    normalized: list[str] = []
    for arg in argv:
        normalized.append(aliases.get(arg, arg))
    return normalized


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Codex fallback wrapper for explicit /hermes routing")
    sub = parser.add_subparsers(dest="command", required=True)

    submit = sub.add_parser("submit", help="Submit a durable task to Hermes Overlord")
    submit.add_argument("goal")
    submit.add_argument("--board", default=BOARD_DEFAULT)
    submit.add_argument("--workspace", default=WORKSPACE_DEFAULT)
    submit.add_argument("--assignee", default=ASSIGNEE_DEFAULT)
    submit.add_argument("--mode", choices=["triage", "task"], default="task")
    submit.add_argument("--idempotency-key")
    submit.add_argument("--max-runtime", default="4h")
    submit.add_argument("--priority", type=int, default=0)
    submit.add_argument("--timeout", type=int, default=TIMEOUT_DEFAULT)
    submit.add_argument("--dispatch", action="store_true")
    submit.add_argument("--no-dispatch", dest="dispatch", action="store_false")
    submit.add_argument("--no-micro-reports", action="store_true")
    submit.add_argument("--human", action="store_true")
    submit.add_argument("--json", action="store_true", help="accepted for PowerShell symmetry; JSON is default")
    submit.set_defaults(func=cmd_submit)

    status = sub.add_parser("status", help="Show raw Kanban task status")
    status.add_argument("--task-id", required=True)
    status.add_argument("--board", default=BOARD_DEFAULT)
    status.add_argument("--human", action="store_true")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_status)

    report = sub.add_parser("report", help="Show curator-friendly task summary")
    report.add_argument("--task-id", required=True)
    report.add_argument("--board", default=BOARD_DEFAULT)
    report.add_argument("--tail-bytes", type=int, default=40000)
    report.add_argument("--max-children", type=int, default=50)
    report.add_argument("--human", action="store_true")
    report.add_argument("--json", action="store_true")
    report.set_defaults(func=cmd_report)

    dispatch = sub.add_parser("dispatch", help="Run one Kanban dispatcher pass")
    dispatch.add_argument("--board", default=BOARD_DEFAULT)
    dispatch.add_argument("--human", action="store_true")
    dispatch.add_argument("--json", action="store_true")
    dispatch.set_defaults(func=cmd_dispatch)

    autocheck = sub.add_parser("autocheck", help="Quiet health summary for Codex -> Hermes routing")
    autocheck.add_argument("--board", default=BOARD_DEFAULT)
    autocheck.add_argument("--timeout", type=int, default=90)
    autocheck.add_argument("--deep", action="store_true", help="also run MCP preflight")
    autocheck.add_argument("--human", action="store_true")
    autocheck.add_argument("--json", action="store_true")
    autocheck.set_defaults(func=cmd_autocheck)

    parse = sub.add_parser("parse", help="Parse a /hermes message without executing it")
    parse.add_argument("text")
    parse.add_argument("--human", action="store_true")
    parse.add_argument("--json", action="store_true")
    parse.set_defaults(func=cmd_parse)

    slash = sub.add_parser("slash", help="Execute a /hermes message through the CLI fallback")
    slash.add_argument("text")
    slash.add_argument("--board", default=BOARD_DEFAULT)
    slash.add_argument("--workspace", default=WORKSPACE_DEFAULT)
    slash.add_argument("--mode", choices=["triage", "task"], default="task")
    slash.add_argument("--idempotency-key")
    slash.add_argument("--timeout", type=int, default=TIMEOUT_DEFAULT)
    slash.add_argument("--dispatch", action="store_true")
    slash.add_argument("--deep", action="store_true")
    slash.add_argument("--human", action="store_true")
    slash.add_argument("--json", action="store_true")
    slash.set_defaults(func=cmd_slash)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(_normalize_argv(list(sys.argv[1:] if argv is None else argv)))
    try:
        args.func(args)
        return 0
    except Exception as exc:
        payload = {"ok": False, "error": _redact(str(exc))[:5000]}
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
