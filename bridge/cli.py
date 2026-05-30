from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .core import BridgeError, HermesBridge


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def emit(data: Any, human: bool = False) -> None:
    if human:
        print(humanize(data))
        return
    print(json.dumps(data, ensure_ascii=False, indent=2))


def humanize(data: Any) -> str:
    if not isinstance(data, dict):
        return str(data)
    action = data.get("action")
    if action == "submit":
        if data.get("dry_run"):
            return "Bridge submit dry run: OK"
        return f"Передал в Hermes: {data.get('task_id')} ({data.get('status') or 'unknown'})"
    if action == "autocheck":
        lines = [f"Hermes bridge autocheck: {'OK' if data.get('ok') else 'FAIL'}"]
        for check in data.get("checks") or []:
            lines.append(f"- {check.get('name')}: {'OK' if check.get('ok') else 'FAIL'} {check.get('summary') or ''}".rstrip())
        return "\n".join(lines)
    if action == "report":
        handoff = data.get("handoff") or {}
        delegation = data.get("delegation") or {}
        lines = [
            f"Task: {handoff.get('task_id') or data.get('task_id')} [{handoff.get('status')}] {handoff.get('title') or ''}".rstrip(),
            f"Outcome: {data.get('outcome')} | Next: {data.get('next')}",
            f"Profiles: {', '.join(delegation.get('profiles_seen') or []) or '-'}",
            f"Children: {delegation.get('child_task_count', 0)} {delegation.get('child_status_rollup') or {}}",
        ]
        blockers = data.get("blockers") or []
        if blockers:
            lines.append("Blockers: " + " | ".join(str(item)[:180] for item in blockers[:3]))
        return "\n".join(lines)
    if action == "events":
        lines = [f"Bridge events for {data.get('task_id')}: {len(data.get('bridge_events') or [])}"]
        for event in (data.get("bridge_events") or [])[-10:]:
            lines.append(f"- {event.get('type')}: {event.get('profile') or event.get('source') or '-'} {event.get('summary') or ''}".rstrip())
        return "\n".join(lines)
    if action == "dispatch":
        stdout = str(data.get("stdout") or "").strip()
        return f"Hermes dispatch: {'OK' if data.get('ok') else 'FAIL'}" + (f"\n{stdout}" if stdout else "")
    if action == "heartbeat_prompt":
        return str(data.get("prompt") or "")
    if action == "status":
        task = data.get("task") or {}
        return f"Task: {task.get('id') or data.get('task_id')} [{task.get('status')}] {task.get('title') or ''}".rstrip()
    return json.dumps(data, ensure_ascii=False, indent=2)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Canonical CLI bridge between MCP clients and Hermes Overlord")
    parser.add_argument("--root", help="Hermes bridge root, defaults to CWD/repository root")
    parser.add_argument("--board", default=None, help="Kanban board slug, default overlord")
    parser.add_argument("--human", action="store_true", help="Print a compact human summary instead of JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--root", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
        subparser.add_argument("--board", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
        subparser.add_argument("--human", action="store_true", help=argparse.SUPPRESS)

    submit = sub.add_parser("submit", help="Submit one durable root handoff to Hermes")
    add_common(submit)
    submit.add_argument("goal")
    submit.add_argument("--workspace", default=None)
    submit.add_argument("--assignee", default=None)
    submit.add_argument("--mode", choices=["triage", "task"], default="task")
    submit.add_argument("--priority", type=int, default=0)
    submit.add_argument("--idempotency-key")
    submit.add_argument("--max-runtime", default="4h")
    submit.add_argument("--dispatch", action="store_true")
    submit.add_argument("--no-micro-reports", action="store_true")
    submit.add_argument("--dry-run", action="store_true")

    status = sub.add_parser("status", help="Show raw task status")
    add_common(status)
    status.add_argument("--task-id", required=True)

    report = sub.add_parser("report", help="Show curator-friendly task report")
    add_common(report)
    report.add_argument("--task-id", required=True)
    report.add_argument("--max-children", type=int, default=80)
    report.add_argument("--log-tail-bytes", type=int, default=40000)

    events = sub.add_parser("events", help="Show bridge/kanban events for a task family")
    add_common(events)
    events.add_argument("--task-id", required=True)
    events.add_argument("--max-children", type=int, default=80)

    dispatch = sub.add_parser("dispatch", help="Run one Hermes Kanban dispatcher pass")
    add_common(dispatch)

    task_list = sub.add_parser("list", help="List Hermes Kanban tasks")
    add_common(task_list)
    task_list.add_argument("--status", choices=["archived", "blocked", "done", "ready", "review", "running", "scheduled", "todo", "triage"])
    task_list.add_argument("--assignee")
    task_list.add_argument("--limit", type=int, default=20)

    comment = sub.add_parser("comment", help="Append a curator comment to a Hermes task")
    add_common(comment)
    comment.add_argument("--task-id", required=True)
    comment.add_argument("--comment", required=True)

    log = sub.add_parser("log", help="Show the tail of a Hermes worker log")
    add_common(log)
    log.add_argument("--task-id", required=True)
    log.add_argument("--tail-bytes", type=int, default=12000)

    gateway_status = sub.add_parser("gateway-status", help="Show Hermes gateway process status")
    add_common(gateway_status)

    direct_ask = sub.add_parser("direct-ask", help="Ask Hermes Overlord synchronously")
    add_common(direct_ask)
    direct_ask.add_argument("query")
    direct_ask.add_argument("--timeout-seconds", type=int, default=600)
    direct_ask.add_argument("--toolsets")
    direct_ask.add_argument("--skill", dest="skills", action="append", default=[])
    direct_ask.add_argument("--ignore-rules", action="store_true")

    heartbeat_prompt = sub.add_parser("heartbeat-prompt", help="Generate a client heartbeat prompt for a task")
    add_common(heartbeat_prompt)
    heartbeat_prompt.add_argument("--task-id", required=True)

    autocheck = sub.add_parser("autocheck", help="Check bridge, Kanban, gateway, and optional MCP port")
    add_common(autocheck)
    autocheck.add_argument("--deep", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    bridge = HermesBridge(root=getattr(args, "root", None), board=getattr(args, "board", None))
    try:
        if args.command == "submit":
            data = bridge.submit(
                args.goal,
                workspace=args.workspace,
                assignee=args.assignee,
                mode=args.mode,
                priority=args.priority,
                idempotency_key=args.idempotency_key,
                max_runtime=args.max_runtime,
                dispatch=args.dispatch,
                include_micro_reports=not args.no_micro_reports,
                dry_run=args.dry_run,
            )
        elif args.command == "status":
            data = bridge.status(args.task_id, board=args.board)
        elif args.command == "report":
            data = bridge.report(args.task_id, board=args.board, max_children=args.max_children, log_tail_bytes=args.log_tail_bytes)
        elif args.command == "events":
            data = bridge.events(args.task_id, board=args.board, max_children=args.max_children)
        elif args.command == "dispatch":
            data = bridge.dispatch_once(board=args.board)
        elif args.command == "list":
            data = bridge.task_list(board=args.board, status=args.status, assignee=args.assignee, limit=args.limit)
        elif args.command == "comment":
            data = bridge.task_comment(args.task_id, args.comment, board=args.board)
        elif args.command == "log":
            data = bridge.task_log(args.task_id, board=args.board, tail_bytes=args.tail_bytes)
        elif args.command == "gateway-status":
            data = bridge.gateway_status()
        elif args.command == "direct-ask":
            data = bridge.direct_ask(
                args.query,
                timeout_seconds=args.timeout_seconds,
                toolsets=args.toolsets,
                skills=args.skills,
                ignore_rules=args.ignore_rules,
            )
        elif args.command == "heartbeat-prompt":
            data = bridge.heartbeat_prompt(args.task_id, board=args.board)
        elif args.command == "autocheck":
            data = bridge.autocheck(board=args.board, deep=args.deep)
        else:
            parser.error(f"unknown command {args.command}")
            return 2
        emit(data, human=args.human)
        return 0
    except BridgeError as exc:
        emit({"schema_version": 1, "ok": False, "error": str(exc)}, human=False)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
