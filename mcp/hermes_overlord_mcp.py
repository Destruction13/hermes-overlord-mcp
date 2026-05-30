"""Focused MCP adapter for the canonical Hermes bridge.

MCP is intentionally an adapter, not the source of truth. The durable contract
lives in ``bridge.core.HermesBridge`` and is shared with the CLI wrapper.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP


DEFAULT_ROOT = Path(os.environ.get("HERMES_OVERLORD_ROOT", Path(__file__).resolve().parents[1]))
if str(DEFAULT_ROOT) not in sys.path:
    sys.path.insert(0, str(DEFAULT_ROOT))

from bridge.core import BridgeError, HermesBridge  # noqa: E402


DEFAULT_BOARD = os.environ.get("HERMES_OVERLORD_BOARD", "overlord")
DEFAULT_WORKSPACE = os.environ.get("HERMES_OVERLORD_WORKSPACE", os.environ.get("HERMES_BRIDGE_WORKSPACE", f"dir:{Path.home()}"))
DEFAULT_ASSIGNEE = os.environ.get("HERMES_OVERLORD_ASSIGNEE", "overlord")
MCP_HOST = os.environ.get("HERMES_OVERLORD_MCP_HOST", "127.0.0.1")
MCP_PORT = int(os.environ.get("HERMES_OVERLORD_MCP_PORT", "8765"))
MCP_PATH = os.environ.get("HERMES_OVERLORD_MCP_PATH", "/mcp")


mcp = FastMCP(
    "hermes-overlord",
    instructions=(
        "Submit exactly one durable root task to Hermes Overlord, then poll the "
        "canonical bridge report/status/events. The calling MCP client remains "
        "the external gateway/curator; Hermes owns decomposition, workers, skills, MCP/tools, "
        "watchdog/reviewer/synth, and execution."
    ),
    host=MCP_HOST,
    port=MCP_PORT,
    streamable_http_path=MCP_PATH,
)


def _bridge(board: str | None = None, workspace: str | None = None, assignee: str | None = None) -> HermesBridge:
    return HermesBridge(
        root=DEFAULT_ROOT,
        board=board or DEFAULT_BOARD,
        workspace=workspace or DEFAULT_WORKSPACE,
        assignee=assignee or DEFAULT_ASSIGNEE,
    )


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _format_completed(bridge: HermesBridge, completed: Any) -> str:
    stdout = (getattr(completed, "stdout", "") or "").strip()
    stderr = (getattr(completed, "stderr", "") or "").strip()
    if stdout:
        try:
            return _json(json.loads(stdout))
        except json.JSONDecodeError:
            pass
    payload: dict[str, Any] = {"stdout": stdout}
    if stderr:
        payload["stderr"] = bridge.redact(stderr[-2000:])
    return _json(payload)


def _error_payload(exc: Exception) -> str:
    return _json({"schema_version": 1, "ok": False, "error": str(exc)})


@mcp.tool()
def hermes_submit_task(
    goal: str,
    workspace: str = DEFAULT_WORKSPACE,
    board: str = DEFAULT_BOARD,
    assignee: str = DEFAULT_ASSIGNEE,
    mode: Literal["triage", "task"] = "task",
    include_micro_reports: bool = True,
    priority: int = 0,
    idempotency_key: str | None = None,
    max_runtime: str | None = "4h",
    dispatch: bool = False,
) -> str:
    """Submit exactly one durable root handoff to Hermes Overlord.

    This tool does not create a client-side swarm/council. Hermes Overlord decides
    whether the goal needs direct work, council, specialists, delegate_task,
    skills, MCP/tools, watchdog/reviewer/synth gates, or no subagents.
    """
    try:
        bridge = _bridge(board=board, workspace=workspace, assignee=assignee)
        return _json(
            bridge.submit(
                goal,
                workspace=workspace,
                board=board,
                assignee=assignee,
                mode=mode,
                priority=priority,
                idempotency_key=idempotency_key,
                max_runtime=max_runtime,
                dispatch=dispatch,
                include_micro_reports=include_micro_reports,
            )
        )
    except Exception as exc:
        return _error_payload(exc)


@mcp.tool()
def hermes_task_status(task_id: str, board: str = DEFAULT_BOARD) -> str:
    """Return one Hermes Kanban task through the canonical bridge status contract."""
    try:
        return _json(_bridge(board=board).status(task_id, board=board))
    except Exception as exc:
        return _error_payload(exc)


@mcp.tool()
def hermes_task_report(
    task_id: str,
    board: str = DEFAULT_BOARD,
    log_tail_bytes: int = 40000,
    max_children: int = 80,
) -> str:
    """Return a curator-friendly report grounded in exact task evidence."""
    try:
        return _json(_bridge(board=board).report(task_id, board=board, log_tail_bytes=log_tail_bytes, max_children=max_children))
    except Exception as exc:
        return _error_payload(exc)


@mcp.tool()
def hermes_task_events(task_id: str, board: str = DEFAULT_BOARD, max_children: int = 80) -> str:
    """Return structured bridge events and recent Kanban events for a task family."""
    try:
        return _json(_bridge(board=board).events(task_id, board=board, max_children=max_children))
    except Exception as exc:
        return _error_payload(exc)


@mcp.tool()
def hermes_heartbeat_prompt(task_id: str, board: str = DEFAULT_BOARD) -> str:
    """Generate a heartbeat prompt for an exact Hermes task id."""
    try:
        return _json(_bridge(board=board).heartbeat_prompt(task_id, board=board))
    except Exception as exc:
        return _error_payload(exc)


@mcp.tool()
def hermes_task_list(
    board: str = DEFAULT_BOARD,
    status: Literal["archived", "blocked", "done", "ready", "review", "running", "scheduled", "todo", "triage"] | None = None,
    assignee: str | None = None,
    limit: int = 20,
) -> str:
    """List Hermes Kanban tasks, optionally filtered by status or assignee."""
    try:
        return _json(_bridge(board=board).task_list(board=board, status=status, assignee=assignee, limit=limit))
    except Exception as exc:
        return _error_payload(exc)


@mcp.tool()
def hermes_task_comment(task_id: str, comment: str, board: str = DEFAULT_BOARD) -> str:
    """Append a curator comment to a Hermes Kanban task."""
    try:
        return _json(_bridge(board=board).task_comment(task_id, comment, board=board))
    except Exception as exc:
        return _error_payload(exc)


@mcp.tool()
def hermes_task_log(task_id: str, board: str = DEFAULT_BOARD, tail_bytes: int = 12000) -> str:
    """Return the tail of a Hermes worker log for a task."""
    try:
        return _json(_bridge(board=board).task_log(task_id, board=board, tail_bytes=tail_bytes))
    except Exception as exc:
        return _error_payload(exc)


@mcp.tool()
def hermes_dispatch_once(board: str = DEFAULT_BOARD) -> str:
    """Run one Hermes Kanban dispatcher pass for diagnostics/manual recovery."""
    bridge = _bridge(board=board)
    try:
        return _json(bridge.dispatch_once(board=board))
    except Exception as exc:
        return _error_payload(exc)


@mcp.tool()
def hermes_gateway_status() -> str:
    """Return Hermes gateway process status for the current profile."""
    try:
        return _json(_bridge().gateway_status())
    except Exception as exc:
        return _error_payload(exc)


@mcp.tool()
def hermes_autocheck(board: str = DEFAULT_BOARD, deep: bool = False, timeout_seconds: int = 90) -> str:
    """Quiet client -> Hermes bridge health summary."""
    try:
        return _json(_bridge(board=board).autocheck(board=board, deep=deep))
    except Exception as exc:
        return _error_payload(exc)


@mcp.tool()
def hermes_direct_ask(
    query: str,
    timeout_seconds: int = 600,
    toolsets: str | None = None,
    skills: list[str] | None = None,
    ignore_rules: bool = False,
) -> str:
    """Ask the Overlord profile synchronously; use only for explicit short asks."""
    try:
        return _json(_bridge().direct_ask(query, timeout_seconds=timeout_seconds, toolsets=toolsets, skills=skills, ignore_rules=ignore_rules))
    except Exception as exc:
        return _error_payload(exc)


if __name__ == "__main__":
    transport = os.environ.get("HERMES_OVERLORD_MCP_TRANSPORT", "stdio")
    if transport not in {"stdio", "sse", "streamable-http"}:
        raise SystemExit(f"Unsupported HERMES_OVERLORD_MCP_TRANSPORT={transport!r}")
    mcp.run(transport=transport)  # type: ignore[arg-type]
