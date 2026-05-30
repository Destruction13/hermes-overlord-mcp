from __future__ import annotations

import json
import os
import platform
import re
import shlex
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from collections import Counter, deque
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
BRIDGE_EVENT_PREFIX = "BRIDGE_EVENT v1 "
TERMINAL_STATUSES = {"done", "archived", "blocked"}
SUCCESS_STATUSES = {"done", "archived"}
ACTIVE_STATUSES = {"triage", "todo", "ready", "running", "review", "scheduled"}
SECRET_KEY_TOKENS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "COOKIE")
STRUCTURED_EVIDENCE_PREFIXES = (
    BRIDGE_EVENT_PREFIX,
    "[worker:evidence] ",
    "[swarm:evidence] ",
    "[completion:metadata] ",
    "[swarm:blackboard] ",
)
TOOL_EVIDENCE_KEYS = {
    "tool_calls_seen",
    "tool_mcp_name",
    "tools",
    "tools_or_mcp",
    "tools_or_mcp_used",
}
MCP_EVIDENCE_KEYS = {
    "mcp",
    "mcp_tools",
    "mcp_tools_seen",
}
ARTIFACT_EVIDENCE_KEYS = {
    "artifact",
    "artifact_path",
    "artifacts",
    "changed_files",
    "files_changed",
    "notion_url",
    "obsidian_artifact_path",
    "output_path",
    "preview_url",
    "result_path",
    "screenshot_path",
    "url",
}


class BridgeError(RuntimeError):
    pass


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _compact_text(value: Any, limit: int = 500) -> str:
    text = "" if value is None else str(value)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + "..."


def _safe_json_loads(value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    text = str(value).strip()
    if not text:
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default


class HermesBridge:
    def __init__(
        self,
        root: str | Path | None = None,
        board: str | None = None,
        workspace: str | None = None,
        assignee: str | None = None,
    ) -> None:
        self.root = Path(root or os.environ.get("HERMES_BRIDGE_ROOT") or Path(__file__).resolve().parents[1])
        self.board = board or os.environ.get("HERMES_BRIDGE_BOARD", "overlord")
        self.workspace = workspace or os.environ.get("HERMES_BRIDGE_WORKSPACE", f"dir:{Path.home()}")
        self.assignee = assignee or os.environ.get("HERMES_BRIDGE_ASSIGNEE", "overlord")
        self.profile = os.environ.get("HERMES_BRIDGE_PROFILE") or os.environ.get("HERMES_OVERLORD_PROFILE") or "overlord"
        self.client_name = os.environ.get("HERMES_BRIDGE_CLIENT", "client/agent")
        self.created_by = os.environ.get("HERMES_BRIDGE_CREATED_BY", "hermes-bridge")
        self.event_source = os.environ.get("HERMES_BRIDGE_EVENT_SOURCE", self.created_by)
        self.timeout = int(os.environ.get("HERMES_BRIDGE_TIMEOUT", "180"))

    def env(self) -> dict[str, str]:
        env = dict(os.environ)
        env.setdefault("PYTHONUTF8", "1")
        env.setdefault("PYTHONIOENCODING", "utf-8")
        env.setdefault("HERMES_QUIET", "1")
        env.setdefault("HERMES_REDACT_SECRETS", "true")
        if "HERMES_HOME" not in env:
            if platform.system().lower().startswith("win"):
                local_app_data = env.get("LOCALAPPDATA")
                if local_app_data:
                    env["HERMES_HOME"] = str(Path(local_app_data) / "hermes")
            else:
                env["HERMES_HOME"] = str(Path.home() / ".hermes")
        return env

    def hermes_python_candidates(self) -> list[Path]:
        env = self.env()
        candidates: list[Path] = []
        if env.get("HERMES_PYTHON"):
            candidates.append(Path(env["HERMES_PYTHON"]).expanduser())
        hermes_home = Path(env.get("HERMES_HOME", Path.home() / ".hermes")).expanduser()
        if platform.system().lower().startswith("win"):
            candidates.append(hermes_home / "hermes-agent" / "venv" / "Scripts" / "python.exe")
        else:
            candidates.append(hermes_home / "hermes-agent" / "venv" / "bin" / "python")
        return candidates

    def redact(self, text: str) -> str:
        redacted = text or ""
        for key, value in self.env().items():
            if value and any(token in key.upper() for token in SECRET_KEY_TOKENS):
                redacted = redacted.replace(value, "<redacted>")
        redacted = re.sub(r"(?i)(api[_-]?key|token|secret|password|cookie)\s*[:=]\s*[^\s,;]+", r"\1=<redacted>", redacted)
        return redacted

    def base_command(self) -> list[str]:
        explicit = os.environ.get("HERMES_BRIDGE_COMMAND") or os.environ.get("HERMES_OVERLORD_COMMAND")
        if explicit:
            return shlex.split(explicit)
        for python in self.hermes_python_candidates():
            if os.environ.get("HERMES_PYTHON") or python.exists():
                return [str(python), "-m", "hermes_cli.main", "-p", self.profile]
        script = self.root / "overlord.ps1"
        if platform.system().lower().startswith("win"):
            return ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)]
        return ["pwsh", "-NoProfile", "-File", str(script)]

    def run(self, args: list[str], timeout: int | None = None) -> subprocess.CompletedProcess[str]:
        command = [*self.base_command(), *args]
        stdout_path = ""
        stderr_path = ""
        try:
            with tempfile.NamedTemporaryFile(delete=False) as stdout_file, tempfile.NamedTemporaryFile(delete=False) as stderr_file:
                stdout_path = stdout_file.name
                stderr_path = stderr_file.name
                completed = subprocess.run(
                    command,
                    cwd=str(self.root),
                    env=self.env(),
                    stdin=subprocess.DEVNULL,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    timeout=timeout or self.timeout,
                    check=False,
                )
        except FileNotFoundError as exc:
            raise BridgeError("Hermes command was not found. Check HERMES_BRIDGE_ROOT or HERMES_BRIDGE_COMMAND.") from exc
        except subprocess.TimeoutExpired as exc:
            raise BridgeError(f"Hermes command timed out after {timeout or self.timeout}s: {exc}") from exc

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
            raise BridgeError(
                json.dumps(
                    {
                        "error": "Hermes command failed",
                        "exit_code": result.returncode,
                        "command": command[:6] + ["..."],
                        "stdout": self.redact((result.stdout or "").strip())[-4000:],
                        "stderr": self.redact((result.stderr or "").strip())[-4000:],
                    },
                    ensure_ascii=False,
                )
            )
        return result

    def json_run(self, args: list[str], timeout: int | None = None, default: Any = None) -> Any:
        result = self.run(args, timeout=timeout)
        stdout = (result.stdout or "").strip()
        if not stdout:
            return default
        try:
            return json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise BridgeError(f"Hermes command did not return JSON: {self.redact(stdout[:1000])}") from exc

    def task_body(self, goal: str, workspace: str, include_micro_reports: bool = True) -> str:
        reporting = (
            "Post concise BRIDGE_EVENT v1 JSON comments for material decisions, child handoffs, blockers, "
            "verification results, tool/MCP evidence, and final synthesis."
            if include_micro_reports
            else "Post only blockers and final BRIDGE_EVENT v1 JSON comments."
        )
        return f"""
Goal: {goal}

Workspace: {workspace}

Canonical Hermes bridge contract:
- The calling MCP client or agent IDE is the external gateway and curator only.
- Hermes Overlord is the execution and orchestration owner.
- {self.client_name} submitted exactly one durable root task. Do not assume the client created a swarm or chose worker routing.
- Preserve Hermes internals: Kanban decomposition, specialist profiles/souls, delegate_task, skills, MCP/tools, watchdog/reviewer/synth gates.
- Start by reading this task with Kanban context/show and derive pragmatic acceptance criteria from the goal, workspace, and available evidence. Ask the user only when missing input makes safe execution impossible.
- For non-trivial creation/build/design tasks, create a reviewable Kanban graph with product/UX or architecture planning as needed, the domain implementer profile for the task type, reviewer, and final synth.
- Website, web app, landing page, dashboard, and browser UI tasks should include olfrontend when that profile is available.
- For non-trivial build/design tasks, Overlord coordinates after the graph exists; it must not substitute itself for product/UX/frontend/backend implementation deliverables or manually complete those worker cards with Overlord-authored artifacts. If a specialist stalls, diagnose, reassign, retry, or split the task; do not silently replace the specialist.
- Manual `reclaim` + `complete` is allowed only for reviewer/synth/evidence-only gate cards after their required evidence already exists and the closure metadata states the original worker evidence. It must never be used to make a product, UX, frontend, backend, or implementation worker appear to have completed Overlord's direct work.
- First-level child cards should be linked to this root task when the tool surface supports it; otherwise post a `child_created` BRIDGE_EVENT with complete `children` and `graph` fields before dispatching workers.
- Web/UI worker briefs should require checking Magic/shadcn or equivalent configured design/component MCPs when available. The worker should use a healthy fitting tool or record the concrete unavailable/not-applicable reason; do not claim MCP use from prompt text.
- Worker task briefs must tell workers to read/follow their active profile SOUL.md (prefer `$HERMES_HOME/profiles/<profile>/SOUL.md` or the injected profile prompt; do not treat old diagnostic snapshots as primary runtime instructions), check required MCP health, load/report relevant skills, provide evidence only for tools actually used, state acceptance criteria, and stop on blockers or unsafe/destructive operations.
- Create child tasks only when the goal benefits from them; Overlord chooses council/direct/specialist execution.
- Use olwatchdog for long-running/stale-risk work, olreviewer for verification, and olsynth for final synthesis when useful.
- Root lifecycle is part of the deliverable. If a reviewer/synth gate produces a terminal PASS/BLOCK final handoff for this root, the root owner or final synth must immediately mark this root task terminal with `kanban complete` or `kanban block`. Do not leave a client bridge root running after all child gates are terminal.
- Name actual MCP/tools/skills in comments only after they are used or deliberately assigned.
- {reporting}
- Required bridge event comment format: {BRIDGE_EVENT_PREFIX}{{"type":"child_created|handoff|tool_used|blocked|review_result|final","task_id":"...","profile":"...","summary":"..."}}
- For `child_created` bridge events, include machine-readable `children:[...]` and preferably `graph:{{"task_id":{{"profile":"...","parents":[...]}}}}` so external clients can track the whole task family without inferring from prose.
- Do not leak secrets. Avoid destructive commands unless the user explicitly asked for them.
- For local preview servers, use an actually free non-reserved port. Treat Hermes/client gateway service ports 8765, 8787, and 9119 as reserved unless the task is explicitly about those services.
- Reviewer must block user-facing UI completion when browser/screenshot evidence shows blank hidden sections, broken reveal animations, missing responsive content, or only a partial hero instead of the promised complete experience.
- Final output must include outcome, task/subagent evidence, verification, changed files if any, remaining risks, and a terminal root Kanban status.
""".strip()

    def bridge_event(self, event_type: str, task_id: str, **fields: Any) -> str:
        payload = {
            "type": event_type,
            "task_id": task_id,
            "source": self.event_source,
            "created_at": _now_iso(),
            **{k: v for k, v in fields.items() if v is not None},
        }
        return BRIDGE_EVENT_PREFIX + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    def task_from_payload(self, payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            task = payload.get("task") if isinstance(payload.get("task"), dict) else payload
            return task if isinstance(task, dict) else {}
        return {}

    def submit(
        self,
        goal: str,
        workspace: str | None = None,
        board: str | None = None,
        assignee: str | None = None,
        mode: str = "task",
        priority: int = 0,
        idempotency_key: str | None = None,
        max_runtime: str | None = "4h",
        dispatch: bool = False,
        include_micro_reports: bool = True,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        selected_board = board or self.board
        selected_workspace = workspace or self.workspace
        selected_assignee = assignee or self.assignee
        if mode not in {"triage", "task"}:
            raise BridgeError("bridge submit supports only root modes: triage or task")

        title_goal = " ".join(goal.split())[:120]
        args = [
            "kanban",
            "--board",
            selected_board,
            "create",
            f"Hermes bridge handoff: {title_goal}",
            "--body",
            self.task_body(goal, selected_workspace, include_micro_reports=include_micro_reports),
            "--assignee",
            selected_assignee,
            "--workspace",
            selected_workspace,
            "--priority",
            str(priority),
            "--created-by",
            self.created_by,
            "--skill",
            "kanban-orchestrator",
            "--json",
        ]
        if mode == "triage":
            args.append("--triage")
        if idempotency_key:
            args.extend(["--idempotency-key", idempotency_key])
        if max_runtime:
            args.extend(["--max-runtime", max_runtime])

        if dry_run:
            return {
                "schema_version": SCHEMA_VERSION,
                "ok": True,
                "action": "submit",
                "dry_run": True,
                "board": selected_board,
                "command_args": args,
            }

        payload = self.json_run(args)
        task = self.task_from_payload(payload)
        task_id = task.get("id") or payload.get("id") if isinstance(payload, dict) else None
        if not task_id:
            raise BridgeError(f"submit did not return a task id: {payload!r}")

        accepted_comment = self.bridge_event(
            "task_accepted",
            str(task_id),
            board=selected_board,
            workspace=selected_workspace,
            assignee=selected_assignee,
            status=task.get("status"),
        )
        try:
            self.run(["kanban", "--board", selected_board, "comment", str(task_id), accepted_comment], timeout=60)
        except Exception as exc:
            payload = {"submit": payload, "bridge_event_warning": self.redact(str(exc))[:1000]}

        dispatch_warning = None
        if dispatch:
            try:
                self.run(["kanban", "--board", selected_board, "dispatch"], timeout=60)
            except Exception as exc:
                dispatch_warning = self.redact(str(exc))[:1000]

        return {
            "schema_version": SCHEMA_VERSION,
            "ok": True,
            "action": "submit",
            "task_id": str(task_id),
            "status": task.get("status"),
            "board": selected_board,
            "workspace": selected_workspace,
            "assignee": selected_assignee,
            "created_by": task.get("created_by") or self.created_by,
            "submitted_at": _now_iso(),
            "raw": payload,
            "dispatch_warning": dispatch_warning,
            "next": {
                "status_cmd": f"python -m bridge.cli status --task-id {task_id} --board {selected_board}",
                "report_cmd": f"python -m bridge.cli report --task-id {task_id} --board {selected_board}",
            },
        }

    def status(self, task_id: str, board: str | None = None) -> dict[str, Any]:
        selected_board = board or self.board
        snapshot = self.json_run(["kanban", "--board", selected_board, "show", task_id, "--json"], default={}) or {}
        task = snapshot.get("task") if isinstance(snapshot, dict) and isinstance(snapshot.get("task"), dict) else snapshot
        return {
            "schema_version": SCHEMA_VERSION,
            "ok": True,
            "action": "status",
            "board": selected_board,
            "task_id": task_id,
            "task": task,
            "raw": snapshot,
        }

    def board_db_path(self, board: str | None = None) -> Path | None:
        env = self.env()
        home = Path(env.get("HERMES_HOME", Path.home() / ".hermes"))
        selected_board = board or self.board
        candidates = [
            home / "kanban" / "boards" / selected_board / "kanban.db",
            home / "kanban.db",
        ]
        for path in candidates:
            if path.exists():
                return path
        return None

    def descendants_from_db(self, task_id: str, board: str | None = None, max_nodes: int = 200) -> list[str]:
        db_path = self.board_db_path(board)
        if not db_path:
            return []
        try:
            con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            con.row_factory = sqlite3.Row
        except sqlite3.Error:
            return []
        try:
            seen: set[str] = set()
            ordered: list[str] = []
            queue: deque[str] = deque([task_id])
            while queue and len(ordered) < max_nodes:
                parent = queue.popleft()
                for row in con.execute("select child_id from task_links where parent_id = ? order by child_id", (parent,)):
                    child = str(row["child_id"])
                    if child in seen:
                        continue
                    seen.add(child)
                    ordered.append(child)
                    queue.append(child)
            return ordered
        except sqlite3.Error:
            return []
        finally:
            con.close()

    def _extract_child_ids(self, snapshot: dict[str, Any], task_id: str, board: str, max_children: int) -> list[str]:
        child_ids: list[str] = []
        children = snapshot.get("children") if isinstance(snapshot, dict) else []
        if isinstance(children, list):
            for item in children:
                if isinstance(item, str):
                    child_ids.append(item)
                elif isinstance(item, dict):
                    source = item.get("task") if isinstance(item.get("task"), dict) else item
                    child_id = source.get("id") if isinstance(source, dict) else None
                    if child_id:
                        child_ids.append(str(child_id))
        for child_id in self.descendants_from_db(task_id, board=board, max_nodes=max_children):
            if child_id not in child_ids:
                child_ids.append(child_id)
        return child_ids[: max(1, min(max_children, 200))]

    def child_ids_from_bridge_events(self, bridge_events: list[dict[str, Any]], root_task_id: str) -> list[str]:
        """Recover task-family ids from bridge telemetry when Kanban links are dependency-only."""
        ids: list[str] = []

        def add(value: Any) -> None:
            if not value:
                return
            text = str(value)
            if re.fullmatch(r"t_[A-Za-z0-9]+", text) and text != root_task_id and text not in ids:
                ids.append(text)

        def walk(value: Any) -> None:
            if isinstance(value, dict):
                for key, child_value in value.items():
                    if key in {"children", "child_ids", "tasks", "task_ids", "graph", "dependencies"}:
                        walk(child_value)
                    elif key in {"task_id", "child_id", "id"}:
                        add(child_value)
                    else:
                        walk(child_value)
                return
            if isinstance(value, (list, tuple, set)):
                for item in value:
                    walk(item)
                return
            for match in re.findall(r"\bt_[A-Za-z0-9]+\b", str(value or "")):
                add(match)

        for event in bridge_events:
            if not isinstance(event, dict):
                continue
            event_type = str(event.get("type") or "")
            if event_type not in {"child_created", "handoff", "review_result", "final", "tool_used"}:
                continue
            walk(event)
        return ids

    def parse_bridge_events(self, comments: list[Any], task_events: list[Any]) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for comment in comments:
            body = comment.get("body") if isinstance(comment, dict) else str(comment)
            text = str(body or "")
            idx = text.find(BRIDGE_EVENT_PREFIX)
            if idx < 0:
                continue
            payload_text = text[idx + len(BRIDGE_EVENT_PREFIX) :].strip()
            payload = _safe_json_loads(payload_text)
            if isinstance(payload, dict):
                payload.setdefault("evidence", "task_comment")
                if isinstance(comment, dict):
                    payload.setdefault("comment_id", comment.get("id"))
                    payload.setdefault("created_at_raw", comment.get("created_at"))
                events.append(payload)
        for event in task_events:
            if not isinstance(event, dict):
                continue
            payload = _safe_json_loads(event.get("payload"), {})
            if not isinstance(payload, dict):
                payload = {"payload": event.get("payload")}
            kind = str(event.get("kind") or "")
            if kind.startswith("bridge") or payload.get("type") in {"task_accepted", "child_created", "handoff", "tool_used", "blocked", "review_result", "final"}:
                payload.setdefault("type", kind or "task_event")
                payload.setdefault("evidence", "task_event")
                payload.setdefault("event_id", event.get("id"))
                payload.setdefault("created_at_raw", event.get("created_at"))
                events.append(payload)
        return events

    def compact_task(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        task = snapshot.get("task") if isinstance(snapshot.get("task"), dict) else snapshot
        runs = snapshot.get("runs") if isinstance(snapshot.get("runs"), list) else []
        latest_run = runs[-1] if runs and isinstance(runs[-1], dict) else {}
        return {
            "id": task.get("id"),
            "title": task.get("title"),
            "assignee": task.get("assignee"),
            "status": task.get("status"),
            "priority": task.get("priority"),
            "created_by": task.get("created_by"),
            "workspace": task.get("workspace_path"),
            "skills": task.get("skills"),
            "latest_summary": snapshot.get("latest_summary"),
            "latest_run": {
                "id": latest_run.get("id"),
                "profile": latest_run.get("profile"),
                "status": latest_run.get("status"),
                "outcome": latest_run.get("outcome"),
                "summary": _compact_text(latest_run.get("summary"), 500),
                "error": _compact_text(latest_run.get("error"), 500),
            }
            if latest_run
            else None,
        }

    def _split_evidence_values(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, dict):
            values: list[str] = []
            for item in value.values():
                values.extend(self._split_evidence_values(item))
            return values
        if isinstance(value, (list, tuple, set)):
            values = []
            for item in value:
                values.extend(self._split_evidence_values(item))
            return values
        text = str(value).strip()
        if not text:
            return []
        parts = re.split(r"[;,]\s*|\s+\|\s+", text)
        return [part.strip() for part in parts if part.strip()]

    def _structured_comment_payloads(self, comments: list[Any]) -> list[dict[str, Any]]:
        payloads: list[dict[str, Any]] = []
        for comment in comments:
            body = comment.get("body") if isinstance(comment, dict) else str(comment)
            text = str(body or "")
            for prefix in STRUCTURED_EVIDENCE_PREFIXES:
                idx = text.find(prefix)
                if idx < 0:
                    continue
                payload_text = text[idx + len(prefix) :].strip()
                payload = _safe_json_loads(payload_text)
                if isinstance(payload, dict):
                    payloads.append(payload)
                break
        return payloads

    def _payload_evidence_sources(self, payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
        sources: list[dict[str, Any]] = []
        for payload in payloads:
            sources.append(payload)
            value = payload.get("value")
            if isinstance(value, dict):
                sources.append(value)
        return sources

    def summarize_structured_evidence(self, comments: list[Any]) -> dict[str, Any]:
        mcp_tools: set[str] = set()
        tool_calls: set[str] = set()
        artifacts: set[str] = set()
        structured_evidence: list[dict[str, Any]] = []
        payloads = self._structured_comment_payloads(comments)
        for payload in self._payload_evidence_sources(payloads):
            for key, value in payload.items():
                if key in MCP_EVIDENCE_KEYS:
                    mcp_tools.update(self._split_evidence_values(value))
                elif key in TOOL_EVIDENCE_KEYS:
                    values = self._split_evidence_values(value)
                    tool_calls.update(item for item in values if not item.startswith("mcp_"))
                    mcp_tools.update(item for item in values if item.startswith("mcp_"))
                elif key in ARTIFACT_EVIDENCE_KEYS:
                    artifacts.update(self._split_evidence_values(value))
            summary = payload.get("summary") or payload.get("did") or payload.get("outcome") or payload.get("handoff")
            if summary:
                structured_evidence.append(
                    {
                        "type": payload.get("type") or payload.get("key") or "structured_comment",
                        "profile": payload.get("profile"),
                        "summary": _compact_text(summary, 500),
                    }
                )
        return {
            "mcp_tools_seen": sorted(mcp_tools),
            "tool_calls_seen": sorted(tool_calls),
            "artifacts": sorted(artifacts),
            "structured_evidence": structured_evidence[-20:],
        }

    def merge_evidence_summaries(self, *summaries: dict[str, Any]) -> dict[str, Any]:
        mcp_servers: dict[str, dict[str, Any]] = {}
        mcp_tools: set[str] = set()
        tool_calls: set[str] = set()
        artifacts: set[str] = set()
        material_lines: list[str] = []
        structured_evidence: list[dict[str, Any]] = []
        log_unavailable: list[str] = []
        for summary in summaries:
            if not isinstance(summary, dict):
                continue
            for name, server in (summary.get("mcp_servers") or {}).items():
                if isinstance(server, dict):
                    mcp_servers[str(name)] = server
            mcp_tools.update(str(item) for item in summary.get("mcp_tools_seen") or [] if item)
            tool_calls.update(str(item) for item in summary.get("tool_calls_seen") or [] if item)
            artifacts.update(str(item) for item in summary.get("artifacts") or [] if item)
            material_lines.extend(str(item) for item in summary.get("material_log_lines") or [] if item)
            structured_evidence.extend(item for item in summary.get("structured_evidence") or [] if isinstance(item, dict))
            if summary.get("log_unavailable"):
                log_unavailable.append(str(summary.get("log_unavailable")))
        merged: dict[str, Any] = {
            "mcp_servers": mcp_servers,
            "mcp_tools_seen": sorted(mcp_tools),
            "tool_calls_seen": sorted(tool_calls),
            "artifacts": sorted(artifacts),
            "material_log_lines": material_lines[-30:],
            "structured_evidence": structured_evidence[-20:],
        }
        if log_unavailable:
            merged["log_unavailable"] = log_unavailable[-5:]
        return merged

    def summarize_log(self, task_id: str, board: str, tail_bytes: int = 40000) -> dict[str, Any]:
        try:
            result = self.run(["kanban", "--board", board, "log", task_id, "--tail", str(max(1000, min(tail_bytes, 200000)))], timeout=60)
            text = result.stdout or ""
        except Exception as exc:
            return {"log_unavailable": self.redact(str(exc))[:1000]}

        tool_calls: set[str] = set()
        mcp_tools: set[str] = set()
        mcp_servers: dict[str, dict[str, Any]] = {}
        material_lines: list[str] = []
        server_re = re.compile(r"MCP server '([^']+)'.*registered (\d+) tool\(s\):\s*(.*)")
        tool_patterns = (
            re.compile(r"Tool call:\s*([A-Za-z0-9_\-.]+)"),
            re.compile(r"Processing tool call[^:]*:\s*([A-Za-z0-9_\-.]+)"),
            re.compile(r"\bpreparing\s+([A-Za-z0-9_\-.]+)"),
        )
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            lower = line.lower()
            execution_line = any(token in lower for token in ("tool call", "processing tool", "preparing", " mcp_", "⚡ mcp_", "mcp server"))
            server_match = server_re.search(line)
            if server_match:
                name, count, tools_blob = server_match.groups()
                tools = [part.strip() for part in tools_blob.split(",") if part.strip()]
                mcp_servers[name] = {"tool_count": int(count), "tools": tools[:30]}
                mcp_tools.update(tools)
            if execution_line:
                mcp_tools.update(re.findall(r"\bmcp_[A-Za-z0-9_]+", line))
            for pattern in tool_patterns:
                match = pattern.search(line)
                if match:
                    name = match.group(1)
                    if name.startswith("mcp_"):
                        mcp_tools.add(name)
                    elif execution_line:
                        tool_calls.add(name)
            if any(token in lower for token in ("tool call", "mcp server", "delegate", "delegat", "spawn", "kanban", "blocked", "complete", "error", "traceback", "review", "synth")):
                material_lines.append(self.redact(line))
        return {
            "mcp_servers": mcp_servers,
            "mcp_tools_seen": sorted(mcp_tools),
            "tool_calls_seen": sorted(tool_calls),
            "material_log_lines": material_lines[-30:],
        }

    def report(self, task_id: str, board: str | None = None, max_children: int = 80, log_tail_bytes: int = 40000) -> dict[str, Any]:
        selected_board = board or self.board
        snapshot = self.json_run(["kanban", "--board", selected_board, "show", task_id, "--json"], default={}) or {}
        task = snapshot.get("task") if isinstance(snapshot.get("task"), dict) else snapshot
        runs = snapshot.get("runs") if isinstance(snapshot.get("runs"), list) else []
        comments = snapshot.get("comments") if isinstance(snapshot.get("comments"), list) else []
        events = snapshot.get("events") if isinstance(snapshot.get("events"), list) else []
        root_bridge_events = self.parse_bridge_events(comments, events)
        child_ids = self._extract_child_ids(snapshot, task_id, selected_board, max_children=max_children)
        for event_child_id in self.child_ids_from_bridge_events(root_bridge_events, task_id):
            if event_child_id not in child_ids:
                child_ids.append(event_child_id)
        child_ids = child_ids[: max(1, min(max_children, 200))]

        children: list[dict[str, Any]] = []
        child_bridge_events: list[dict[str, Any]] = []
        child_evidence: list[dict[str, Any]] = []
        for child_id in child_ids:
            try:
                child_snapshot = self.json_run(["kanban", "--board", selected_board, "show", child_id, "--json"], timeout=60, default={}) or {}
                compact_child = self.compact_task(child_snapshot)
                children.append(compact_child)
                child_comments = child_snapshot.get("comments") if isinstance(child_snapshot.get("comments"), list) else []
                child_events = child_snapshot.get("events") if isinstance(child_snapshot.get("events"), list) else []
                child_bridge_events.extend(self.parse_bridge_events(child_comments, child_events))
                child_summary = self.merge_evidence_summaries(
                    self.summarize_log(child_id, selected_board, tail_bytes=min(log_tail_bytes, 60000)),
                    self.summarize_structured_evidence(child_comments),
                )
                if any(child_summary.get(key) for key in ("mcp_servers", "mcp_tools_seen", "tool_calls_seen", "artifacts", "material_log_lines", "structured_evidence")):
                    child_evidence.append(
                        {
                            "task_id": child_id,
                            "assignee": compact_child.get("assignee"),
                            "status": compact_child.get("status"),
                            **child_summary,
                        }
                    )
            except Exception as exc:
                children.append({"id": child_id, "error": self.redact(str(exc))[:500]})

        root_status = str(task.get("status") or "unknown")
        child_status_rollup = Counter(str(child.get("status") or "unknown") for child in children)
        profiles = {str(task.get("assignee"))} if task.get("assignee") else set()
        profiles.update(str(child.get("assignee")) for child in children if child.get("assignee"))
        profiles.update(str(run.get("profile")) for run in runs if isinstance(run, dict) and run.get("profile"))
        profiles.update(str((child.get("latest_run") or {}).get("profile")) for child in children if isinstance(child.get("latest_run"), dict) and (child.get("latest_run") or {}).get("profile"))

        blockers: list[str] = []
        for comment in comments[-30:]:
            body = str(comment.get("body") if isinstance(comment, dict) else comment)
            idx = body.find(BRIDGE_EVENT_PREFIX)
            if idx >= 0:
                event_payload = _safe_json_loads(body[idx + len(BRIDGE_EVENT_PREFIX) :].strip(), {})
                if isinstance(event_payload, dict) and event_payload.get("type") == "blocked":
                    blockers.append(_compact_text(body, 500))
                continue
            if re.search(r"block|blocked|блок|ошиб|error|fail|risk", body, re.I):
                blockers.append(_compact_text(body, 500))
        for child in children:
            latest_run = child.get("latest_run") if isinstance(child.get("latest_run"), dict) else {}
            if child.get("status") == "blocked" or latest_run.get("error"):
                blockers.append(_compact_text(json.dumps(child, ensure_ascii=False), 500))

        bridge_events = root_bridge_events + child_bridge_events
        active_children = [child for child in children if str(child.get("status")) in ACTIVE_STATUSES]
        has_final_event = any(event.get("type") == "final" for event in bridge_events)
        has_block_event = any(event.get("type") == "blocked" for event in bridge_events)
        terminal_child_graph = bool(children) and not active_children
        effective_terminal = root_status in TERMINAL_STATUSES and terminal_child_graph
        final_event_ready = has_final_event and terminal_child_graph
        is_terminal = effective_terminal or final_event_ready
        if root_status == "blocked" or has_block_event:
            outcome = "blocked"
        elif root_status in SUCCESS_STATUSES or final_event_ready:
            outcome = "done"
        else:
            outcome = "active"
        if final_event_ready and root_status not in TERMINAL_STATUSES:
            blockers.append(
                "root_lifecycle: final bridge event exists and all child tasks are terminal, but the root Kanban task is still "
                f"{root_status}; the root owner/final synth should mark it terminal."
            )
        root_evidence = self.merge_evidence_summaries(
            self.summarize_log(task_id, selected_board, tail_bytes=log_tail_bytes),
            self.summarize_structured_evidence(comments),
        )
        final_artifacts = sorted(
            set(root_evidence.get("artifacts") or [])
            | {
                artifact
                for child_summary in child_evidence
                for artifact in (child_summary.get("artifacts") or [])
            }
        )
        reviewer_tasks = [child for child in children if str(child.get("assignee") or "").lower() == "olreviewer"]
        synth_tasks = [child for child in children if str(child.get("assignee") or "").lower() == "olsynth"]

        return {
            "schema_version": SCHEMA_VERSION,
            "ok": True,
            "action": "report",
            "checked_at": _now_iso(),
            "board": selected_board,
            "task_id": task_id,
            "outcome": outcome,
            "terminal": is_terminal,
            "handoff": {
                "task_id": task.get("id") or task_id,
                "title": task.get("title"),
                "assignee": task.get("assignee"),
                "status": root_status,
                "workspace": task.get("workspace_path"),
                "created_by": task.get("created_by"),
                "result": _compact_text(task.get("result"), 1200),
                "latest_summary": snapshot.get("latest_summary"),
            },
            "delegation": {
                "profiles_seen": sorted(p for p in profiles if p and p != "None"),
                "child_task_count": len(children),
                "child_status_rollup": dict(sorted(child_status_rollup.items())),
                "children": children,
                "reviewer_tasks": reviewer_tasks,
                "synth_tasks": synth_tasks,
            },
            "bridge_events": bridge_events[-80:],
            "visibility": {
                "recent_comments": comments[-10:],
                "recent_events": events[-20:],
                "runs": [self._compact_run(run) for run in runs[-30:] if isinstance(run, dict)],
            },
            "mcp_and_tools": root_evidence,
            "child_mcp_and_tools": child_evidence[:80],
            "final_artifacts": final_artifacts[:50],
            "blockers": blockers[:10],
            "next": self.next_action(root_status, children, blockers, bridge_events),
        }

    def _compact_run(self, run: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": run.get("id"),
            "profile": run.get("profile"),
            "status": run.get("status"),
            "outcome": run.get("outcome"),
            "worker_pid": run.get("worker_pid"),
            "summary": _compact_text(run.get("summary"), 500),
            "error": _compact_text(run.get("error"), 500),
        }

    def next_action(self, root_status: str, children: list[dict[str, Any]], blockers: list[str], bridge_events: list[dict[str, Any]]) -> str:
        active_children = [child for child in children if str(child.get("status")) in ACTIVE_STATUSES]
        has_final_event = any(event.get("type") == "final" for event in bridge_events)
        if has_final_event and not active_children and root_status not in TERMINAL_STATUSES:
            return "final_available_but_root_needs_terminal_close"
        if root_status in SUCCESS_STATUSES and not active_children:
            return "finalize_to_user_and_pause_heartbeat"
        if root_status == "blocked" or blockers:
            return "surface_blocker"
        if any(str(child.get("status")) in {"running", "review"} for child in children) or root_status in {"running", "review"}:
            return "wait_for_next_material_event"
        if any(str(child.get("status")) in {"triage", "todo", "ready", "scheduled"} for child in children) or root_status in {"triage", "todo", "ready", "scheduled"}:
            return "wait_or_dispatch_if_gateway_stale"
        if has_final_event:
            return "finalize_to_user_and_pause_heartbeat"
        return "inspect_report"

    def events(self, task_id: str, board: str | None = None, max_children: int = 80) -> dict[str, Any]:
        report = self.report(task_id, board=board, max_children=max_children, log_tail_bytes=5000)
        return {
            "schema_version": SCHEMA_VERSION,
            "ok": True,
            "action": "events",
            "board": report["board"],
            "task_id": task_id,
            "bridge_events": report.get("bridge_events", []),
            "recent_events": report.get("visibility", {}).get("recent_events", []),
        }

    def dispatch_once(self, board: str | None = None) -> dict[str, Any]:
        selected_board = board or self.board
        completed = self.run(["kanban", "--board", selected_board, "dispatch"], timeout=60)
        return {
            "schema_version": SCHEMA_VERSION,
            "ok": True,
            "action": "dispatch",
            "board": selected_board,
            "stdout": self.redact((completed.stdout or "").strip())[-2000:],
            "stderr": self.redact((completed.stderr or "").strip())[-2000:],
        }

    def task_list(self, board: str | None = None, status: str | None = None, assignee: str | None = None, limit: int = 20) -> dict[str, Any]:
        selected_board = board or self.board
        args = ["kanban", "--board", selected_board, "list", "--json", "--sort", "updated"]
        if status:
            args.extend(["--status", status])
        if assignee:
            args.extend(["--assignee", assignee])
        data = self.json_run(args, timeout=60, default=[])
        if isinstance(data, list):
            data = data[: max(1, min(limit, 100))]
        return {"schema_version": SCHEMA_VERSION, "ok": True, "action": "list", "board": selected_board, "tasks": data}

    def task_comment(self, task_id: str, comment: str, board: str | None = None) -> dict[str, Any]:
        selected_board = board or self.board
        completed = self.run(["kanban", "--board", selected_board, "comment", task_id, comment], timeout=60)
        return {
            "schema_version": SCHEMA_VERSION,
            "ok": True,
            "action": "comment",
            "board": selected_board,
            "task_id": task_id,
            "stdout": self.redact((completed.stdout or "").strip())[-2000:],
            "stderr": self.redact((completed.stderr or "").strip())[-2000:],
        }

    def task_log(self, task_id: str, board: str | None = None, tail_bytes: int = 12000) -> dict[str, Any]:
        selected_board = board or self.board
        tail = str(max(1000, min(tail_bytes, 200000)))
        completed = self.run(["kanban", "--board", selected_board, "log", task_id, "--tail", tail], timeout=60)
        return {
            "schema_version": SCHEMA_VERSION,
            "ok": True,
            "action": "log",
            "board": selected_board,
            "task_id": task_id,
            "stdout": self.redact((completed.stdout or "").strip())[-max(1000, min(tail_bytes, 200000)) :],
            "stderr": self.redact((completed.stderr or "").strip())[-2000:],
        }

    def gateway_status(self) -> dict[str, Any]:
        completed = self.run(["gateway", "status"], timeout=60)
        return {
            "schema_version": SCHEMA_VERSION,
            "ok": True,
            "action": "gateway-status",
            "stdout": self.redact((completed.stdout or "").strip())[-4000:],
            "stderr": self.redact((completed.stderr or "").strip())[-2000:],
        }

    def direct_ask(
        self,
        query: str,
        timeout_seconds: int = 600,
        toolsets: str | None = None,
        skills: list[str] | None = None,
        ignore_rules: bool = False,
    ) -> dict[str, Any]:
        args = ["chat", "-Q", "--source", "tool"]
        if ignore_rules:
            args.append("--ignore-rules")
        if toolsets:
            args.extend(["--toolsets", toolsets])
        for skill in skills or []:
            if skill:
                args.extend(["--skills", skill])
        args.extend(["-q", query])
        completed = self.run(args, timeout=max(30, min(timeout_seconds, 3600)))
        return {
            "schema_version": SCHEMA_VERSION,
            "ok": True,
            "action": "direct-ask",
            "stdout": self.redact((completed.stdout or "").strip())[-12000:],
            "stderr": self.redact((completed.stderr or "").strip())[-2000:],
        }

    def heartbeat_prompt(self, task_id: str, board: str | None = None) -> dict[str, Any]:
        selected_board = board or self.board
        prompt = f"""
Check Hermes task `{task_id}` through the canonical bridge, using this exact command when shell access is available:

`python -m bridge.cli report --task-id {task_id} --board {selected_board}`

On Windows with the bundled wrapper, this equivalent command is also acceptable:

`bridge.ps1 report -TaskId {task_id} -Board {selected_board}`

If the MCP adapter is available and wraps the same bridge core, `hermes_task_report(task_id={task_id}, board={selected_board})` is also acceptable.

Report only material changes to the current thread: status transitions, new child tasks/profiles, blockers, review/synthesis movement, final result, or user-visible risk. Do not repeat unchanged progress. Do not infer agents, MCPs, tools, or completion from prompt text; use only report/kanban/log/event evidence for this exact task id.

When the report says `next: final_available_but_root_needs_terminal_close`, report the final result once, explicitly note that Hermes produced final evidence while the root still needs terminal closure, and pause/delete this heartbeat after the root is cleaned up or rerun. When the report says `terminal: true` or `next: finalize_to_user_and_pause_heartbeat`, give a concise final summary with outcome, participating task ids/profiles, verification evidence, changed files if any, and remaining risks, then pause or delete this heartbeat automation.
""".strip()
        return {
            "schema_version": SCHEMA_VERSION,
            "ok": True,
            "action": "heartbeat_prompt",
            "board": selected_board,
            "task_id": task_id,
            "recommended_rrule": "FREQ=MINUTELY;INTERVAL=7",
            "prompt": prompt,
        }

    def port_open(self, host: str, port: int, timeout: float = 0.7) -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            return False

    def autocheck(self, board: str | None = None, deep: bool = False) -> dict[str, Any]:
        selected_board = board or self.board
        checks: list[dict[str, Any]] = []

        def add(name: str, ok: bool, summary: str = "", data: Any = None) -> None:
            checks.append({"name": name, "ok": bool(ok), "summary": self.redact(str(summary))[:500], "data": data})

        add("root", self.root.exists(), str(self.root))
        add("overlord_ps1", (self.root / "overlord.ps1").exists(), str(self.root / "overlord.ps1"))
        for file_path in (self.root / "bridge" / "core.py", self.root / "bridge" / "cli.py"):
            if not file_path.exists():
                add(f"syntax:{file_path.name}", False, "missing")
                continue
            try:
                compile(file_path.read_text(encoding="utf-8", errors="replace"), str(file_path), "exec")
                add(f"syntax:{file_path.name}", True, "ok")
            except SyntaxError as exc:
                add(f"syntax:{file_path.name}", False, str(exc))

        try:
            stats = self.json_run(["kanban", "--board", selected_board, "stats", "--json"], timeout=60, default={})
            add("kanban_stats", True, "stats ok", stats)
        except Exception as exc:
            add("kanban_stats", False, str(exc))

        try:
            diagnostics = self.json_run(["kanban", "--board", selected_board, "diagnostics", "--json"], timeout=60, default=[])
            severe = []
            if isinstance(diagnostics, list):
                severe = [d for d in diagnostics if str(d.get("severity", "")).lower() in {"error", "critical"}]
            add("kanban_diagnostics", len(severe) == 0, f"diagnostics={len(diagnostics) if isinstance(diagnostics, list) else '?'} severe={len(severe)}", severe[:10])
        except Exception as exc:
            add("kanban_diagnostics", False, str(exc))

        try:
            gateway = self.run(["gateway", "status"], timeout=60)
            stdout = (gateway.stdout or "").strip()
            add("gateway_status", "Gateway process running" in stdout, stdout[-500:])
        except Exception as exc:
            add("gateway_status", False, str(exc))

        add("mcp_http_port_8765", self.port_open("127.0.0.1", 8765), "127.0.0.1:8765")

        if deep:
            try:
                listed = self.json_run(["kanban", "--board", selected_board, "list", "--json", "--sort", "updated"], timeout=60, default=[])
                add("kanban_list", isinstance(listed, list), f"tasks={len(listed) if isinstance(listed, list) else '?'}")
            except Exception as exc:
                add("kanban_list", False, str(exc))

        return {
            "schema_version": SCHEMA_VERSION,
            "ok": all(check["ok"] for check in checks),
            "action": "autocheck",
            "checked_at": _now_iso(),
            "board": selected_board,
            "checks": checks,
        }
