from __future__ import annotations

import html
import json
import os
import re
import sqlite3
import time
from datetime import datetime
from functools import lru_cache
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parent
HERMES_ROOT = Path(os.environ.get("LOCALAPPDATA", "")) / "hermes"
DEFAULT_BOARD = "overlord"
DISPLAY_ACTIVE_STATUSES = {"ready", "running", "blocked", "review"}
RUNNING_STATUSES = {"running", "active", "started", "claimed"}
WATCHDOG_PROFILES = {"olwatchdog"}
LIVE_HEARTBEAT_SECONDS = 180
LIVE_START_GRACE_SECONDS = 300
RECENT_PENDING_SECONDS = 7200
CODEX_SESSION_ACTIVE_SECONDS = 3600
CODEX_SESSION_SCAN_LIMIT = 12
CODEX_SESSION_ARCHIVE_SECONDS = 7 * 24 * 3600
CODEX_SESSION_ARCHIVE_SCAN_LIMIT = 8
MAX_LOG_BYTES = 120_000
HERMES_TASK_RE = re.compile(r"\bt_[0-9a-f]{8}\b", re.IGNORECASE)

PROFILE_PHASES = {
    "overlord": "director",
    "olproduct": "council",
    "olarchitect": "council",
    "olresearcher": "council",
    "olrisk": "council",
    "olux": "council",
    "olfrontend": "execution",
    "olbackend": "execution",
    "olautomation": "execution",
    "olwatchdog": "control",
    "olreviewer": "control",
    "olsynth": "output",
    "nerood": "auxiliary",
    "diana": "auxiliary",
}

PROFILE_LABELS = {
    "overlord": "Overlord",
    "olproduct": "Product",
    "olarchitect": "Architect",
    "olresearcher": "Research",
    "olrisk": "Risk",
    "olux": "UX",
    "olfrontend": "Frontend",
    "olbackend": "Backend",
    "olautomation": "Automation",
    "olwatchdog": "Watchdog",
    "olreviewer": "Reviewer",
    "olsynth": "Synth",
    "nerood": "Nerood",
    "diana": "Diana",
}

SIGNAL_RE = re.compile(
    r"\b("
    r"mcp|filesystem|github|notion|obsidian|linear|browser|chrome|playwright|"
    r"shell|powershell|python|node|npm|git|rg|apply_patch|openai|vercel|"
    r"cloudflare|canva|tavily|exa|context7|mem0|serena|codegraph|"
    r"websocket|http|fetch|sqlite|kanban|overlord"
    r")\b",
    re.IGNORECASE,
)
SECRET_RE = re.compile(r"(?i)(api[_-]?key|token|secret|password|authorization|client_id|state|code)=([^\s&]+)")


def _now() -> int:
    return int(time.time())


def _compact(text: Any, limit: int = 180) -> str:
    value = " ".join(str(text or "").split())
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 1)].rstrip() + "…"


def _payload_text(payload: dict[str, Any]) -> str:
    if payload.get("message"):
        return str(payload.get("message") or "")
    content = payload.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("output_text") or ""))
            else:
                parts.append(str(item or ""))
        return "\n".join(part for part in parts if part)
    return ""


def _friendly_command_activity(command: str, fallback: str = "Работает с проектом") -> str:
    text = str(command or "")
    low = text.lower()
    if "overlord-intake" in low:
        return "Передает задачу в Hermes Overlord"
    if "codex-hermes-preflight" in low:
        return "Проверяет мост Codex -> Hermes"
    if "test-setupexe" in low or "isolated" in low:
        return "Проверяет установщик в изолированной среде"
    if "apply_patch" in low:
        return "Вносит правки в файлы"
    if re.search(r"\brg\b", low):
        return "Ищет нужные места в проекте"
    if "git push" in low:
        return "Публикует готовые изменения"
    if "git commit" in low:
        return "Фиксирует готовые изменения"
    if "git diff" in low or "git status" in low or "git log" in low:
        return "Сверяет изменения в репозитории"
    if "npm run" in low or "pytest" in low or "playwright" in low or "py_compile" in low:
        return "Проверяет результат"
    if "get-content" in low or "select-string" in low:
        return "Читает файлы проекта"
    return fallback


def _friendly_tool_activity(name: str, arguments: Any = "") -> str:
    tool = str(name or "tool")
    try:
        parsed = json.loads(arguments) if isinstance(arguments, str) and arguments.strip().startswith("{") else {}
    except Exception:
        parsed = {}
    command = parsed.get("command") if isinstance(parsed, dict) else ""
    if tool == "shell_command":
        return _friendly_command_activity(command or str(arguments or ""), "Выполняет проверку проекта")
    if tool == "apply_patch":
        return "Вносит правки в файлы"
    if tool == "update_plan":
        return "Обновляет план работы"
    if tool == "view_image":
        return "Смотрит приложенный скриншот"
    if "hermes" in tool.lower():
        return "Работает через Hermes"
    return "Выполняет шаг задачи"


def _friendly_tool_name(name: Any) -> str:
    value = str(name or "tool")
    low = value.lower()
    mapping = {
        "shell_command": "Terminal",
        "apply_patch": "File edits",
        "update_plan": "Plan",
        "view_image": "Screenshot",
        "multi_tool_use.parallel": "Parallel tools",
    }
    if low in mapping:
        return mapping[low]
    if "hermes" in low:
        return "Hermes MCP"
    return value.replace("_", " ").strip().title()


def _count_items(values: list[Any], limit: int = 8) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for value in values:
        name = str(value or "").strip()
        if not name:
            continue
        counts[name] = counts.get(name, 0) + 1
    return [
        {"name": name, "count": count}
        for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0].lower()))[:limit]
    ]


def _looks_like_context_message(text: str) -> bool:
    value = str(text or "").strip()
    low = value.lower()
    if not value:
        return True
    return (
        value.startswith("# AGENTS.md instructions")
        or value.startswith("# Files mentioned by the user:")
        or low.startswith("another language model started to solve this problem")
        or "<environment_context>" in low
        or "<skills_instructions>" in low
        or "<plugins_instructions>" in low
        or "<permissions instructions>" in low
        or "<app-context>" in low
        or "<collaboration_mode>" in low
        or low.startswith("knowledge cutoff:")
        or low.startswith("you are codex")
    )


def _clean_user_prompt(text: str) -> str:
    value = str(text or "").strip()
    if not value:
        return ""
    marker = "## My request for Codex:"
    if marker in value:
        value = value.split(marker, 1)[1]
    value = re.sub(r"(?is)<environment_context>.*?</environment_context>", "", value)
    value = re.sub(r"(?is)<permissions instructions>.*?</permissions instructions>", "", value)
    value = re.sub(r"(?is)<app-context>.*?</app-context>", "", value)
    value = re.sub(r"(?is)<collaboration_mode>.*?</collaboration_mode>", "", value)
    value = re.sub(r"(?is)<skills_instructions>.*?</skills_instructions>", "", value)
    value = re.sub(r"(?is)<plugins_instructions>.*?</plugins_instructions>", "", value)
    value = re.sub(r"(?im)^# Files mentioned by the user:.*$", "", value)
    value = re.sub(r"(?im)^##\s+\{[^\n]+$", "", value)
    value = re.sub(r"(?im)^##\s+[^\n]+\.png:.*$", "", value)
    parts = []
    for part in re.split(r"\n\s*\n", value):
        if not _looks_like_context_message(part):
            parts.append(part.strip())
    return "\n\n".join(part for part in parts if part).strip()


def _real_user_text(payload: dict[str, Any]) -> str:
    return _clean_user_prompt(_payload_text(payload))


def _extract_mcp_mentions(*parts: Any, limit: int = 8) -> list[dict[str, Any]]:
    names = []
    for part in parts:
        text = str(part or "")
        for signal in _extract_signals(text, limit=40):
            if signal.get("kind") == "mcp":
                names.extend([signal["name"]] * int(signal.get("count") or 1))
    return _count_items(names, limit)


def _task_text_blob(task: dict[str, Any], comments: list[dict[str, Any]], events: list[dict[str, Any]], runs: list[dict[str, Any]]) -> str:
    # Tool/MCP badges must come from evidence, not from the user's prompt or planning comments.
    parts = [task.get("result") or ""]
    parts.extend(json.dumps(event, ensure_ascii=False) for event in events[-8:])
    parts.extend(json.dumps(run, ensure_ascii=False) for run in runs[-6:])
    return "\n".join(str(part or "") for part in parts)


def _redact(text: str) -> str:
    return SECRET_RE.sub(r"\1=<redacted>", text)


def _json_loads(value: Any, fallback: Any = None) -> Any:
    if value in (None, ""):
        return fallback
    try:
        return json.loads(value)
    except Exception:
        return fallback


def _board_db_path(board: str) -> Path:
    if board == "default":
        return HERMES_ROOT / "kanban.db"
    return HERMES_ROOT / "kanban" / "boards" / board / "kanban.db"


def _board_log_path(board: str, task_id: str) -> Path:
    if board == "default":
        return HERMES_ROOT / "kanban" / "logs" / f"{task_id}.log"
    return HERMES_ROOT / "kanban" / "boards" / board / "logs" / f"{task_id}.log"


def _connect(board: str) -> sqlite3.Connection:
    path = _board_db_path(board)
    if not path.exists():
        raise FileNotFoundError(f"Kanban DB not found: {path}")
    conn = sqlite3.connect(str(path), timeout=12)
    conn.row_factory = sqlite3.Row
    return conn


def _row(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def _clock(value: Any) -> str:
    try:
        ts = int(value or 0)
    except Exception:
        ts = 0
    if ts <= 0:
        return ""
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S")


def _phase(assignee: Any) -> str:
    return PROFILE_PHASES.get(str(assignee or "").lower(), "unassigned")


def _is_watchdog_task(task: dict[str, Any]) -> bool:
    return str(task.get("assignee") or "").lower() in WATCHDOG_PROFILES


def _project_display_task_id(ids: set[str], roots: list[str], tasks: dict[str, dict[str, Any]]) -> str:
    def rank(tid: str) -> tuple[int, int, str]:
        task = tasks[tid]
        title = str(task.get("title") or "").strip().lower()
        if title.startswith("overlord intake:"):
            bucket = 0
        elif not _is_watchdog_task(task):
            bucket = 1
        else:
            bucket = 2
        return (bucket, int(task.get("created_at") or 0), tid)

    return sorted(ids or set(roots), key=rank)[0]


def _extract_signals(*parts: Any, limit: int = 12) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for part in parts:
        text = _redact(str(part or ""))
        if not text:
            continue
        for match in SIGNAL_RE.finditer(text):
            name = match.group(1).lower()
            start = max(0, match.start() - 64)
            end = min(len(text), match.end() + 96)
            item = seen.setdefault(name, {"name": name, "kind": _signal_kind(name), "count": 0, "latest_excerpt": ""})
            item["count"] += 1
            item["latest_excerpt"] = _compact(text[start:end], 180)
    return sorted(seen.values(), key=lambda item: (-item["count"], item["name"]))[:limit]


def _tool_evidence_text(text: Any) -> str:
    """Keep only log lines that are evidence of actual tool/MCP use.

    Task bodies and model prose often mention tools as instructions or negated
    scope notes. Dashboard badges should come from tool-call/log evidence, not
    prompt text.
    """
    kept: list[str] = []
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        lower = line.lower()
        if not line:
            continue
        if "tool call:" in lower or "processing tool call" in lower or "mcp server '" in lower:
            kept.append(line)
            continue
        if re.search(r"(^|\s)(\$|> )\s*(python|node|npm|git|rg|powershell|pwsh)\b", line, re.IGNORECASE):
            kept.append(line)
            continue
        if line.startswith("💻") and any(token in lower for token in ("python", "node", "npm", "git", "rg", "powershell", "pwsh")):
            kept.append(line)
    return "\n".join(kept)


def _signal_kind(name: str) -> str:
    if name in {"mcp", "filesystem", "github", "notion", "obsidian", "linear", "context7", "mem0", "serena", "codegraph"}:
        return "mcp"
    if name in {"shell", "shell_command", "powershell", "python", "node", "npm", "git", "rg", "apply_patch"}:
        return "shell"
    if name in {"browser", "chrome", "playwright", "websocket", "http", "fetch"}:
        return "browser"
    return "tool"


def _tool_phase(name: str) -> str:
    kind = _signal_kind(name)
    if kind in {"shell", "browser", "tool", "mcp"}:
        return "execution"
    return "execution"


def _read_log(board: str, task_id: str, tail: int = 120_000) -> dict[str, Any]:
    if task_id.startswith("codex-session:"):
        return _read_codex_session_log(task_id, tail)
    path = _board_log_path(board, task_id)
    if not path.exists():
        return _read_task_activity_log(board, task_id)
    size = path.stat().st_size
    requested_tail = int(tail or 0)
    tail = min(size, MAX_LOG_BYTES) if requested_tail <= 0 else max(1, min(requested_tail, MAX_LOG_BYTES))
    with path.open("rb") as handle:
        if size > tail:
            handle.seek(size - tail)
            content = handle.read().decode("utf-8", errors="replace")
            truncated = True
        else:
            content = handle.read().decode("utf-8", errors="replace")
            truncated = False
    if not content.strip():
        fallback = _read_task_activity_log(board, task_id)
        if fallback.get("content"):
            return fallback
    return {
        "task_id": task_id,
        "exists": True,
        "size_bytes": size,
        "content": _redact(content),
        "truncated": truncated,
        "updated_at": int(path.stat().st_mtime),
    }


def _read_task_activity_log(board: str, task_id: str) -> dict[str, Any]:
    try:
        with _connect(board) as conn:
            task_row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if not task_row:
                return {"task_id": task_id, "exists": False, "size_bytes": 0, "content": "", "truncated": False}
            task = _row(task_row)
            comments = [_row(row) for row in conn.execute(
                "SELECT * FROM task_comments WHERE task_id = ? ORDER BY created_at ASC, id ASC", (task_id,)
            ).fetchall()]
            events = [_row(row) for row in conn.execute(
                "SELECT * FROM task_events WHERE task_id = ? ORDER BY id ASC", (task_id,)
            ).fetchall()]
            runs = [_row(row) for row in conn.execute(
                "SELECT * FROM task_runs WHERE task_id = ? ORDER BY started_at ASC, id ASC", (task_id,)
            ).fetchall()]
    except Exception as exc:
        return {"task_id": task_id, "exists": False, "size_bytes": 0, "content": f"Журнал недоступен: {exc}", "truncated": False}

    rows: list[str] = []
    created = _clock(task.get("created_at"))
    rows.append(f"{created} Получил: {_compact(task.get('title') or task_id, 240)}".strip())
    if task.get("body"):
        rows.append(f"{created} Контекст: {_compact(task.get('body'), 360)}".strip())
    for run in runs:
        started = _clock(run.get("started_at"))
        profile = run.get("profile") or task.get("assignee") or "agent"
        rows.append(f"{started} {profile}: взял шаг в работу".strip())
        if run.get("summary"):
            rows.append(f"{_clock(run.get('ended_at'))} {profile}: {_compact(run.get('summary'), 420)}".strip())
        elif run.get("ended_at"):
            rows.append(f"{_clock(run.get('ended_at'))} {profile}: завершил шаг".strip())
    for comment in comments:
        author = comment.get("author") or task.get("assignee") or "agent"
        rows.append(f"{_clock(comment.get('created_at'))} {author}: {_compact(comment.get('body'), 520)}".strip())
    if task.get("result"):
        rows.append(f"{_clock(task.get('completed_at'))} Итог: {_compact(task.get('result'), 520)}".strip())
    if not rows and events:
        for event in events[-12:]:
            rows.append(f"{_clock(event.get('created_at'))} Событие: {event.get('kind') or 'update'}".strip())
    content = _redact("\n".join(row for row in rows if row))
    return {
        "task_id": task_id,
        "exists": bool(content),
        "size_bytes": len(content.encode("utf-8")),
        "content": content or "Журнал пока пуст.",
        "truncated": False,
        "updated_at": max(int(task.get("completed_at") or 0), int(task.get("started_at") or 0), int(task.get("created_at") or 0)),
    }


def _codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".codex")


def _session_id_from_path(path: Path) -> str:
    match = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", path.name, re.I)
    return match.group(1) if match else path.stem


def _find_codex_session_file(session_id: str) -> Path | None:
    root = _codex_home() / "sessions"
    if not root.exists():
        return None
    matches = list(root.glob(f"**/*{session_id}*.jsonl"))
    if not matches:
        return None
    return max(matches, key=lambda item: item.stat().st_mtime)


def _read_codex_session_log(task_id: str, tail: int = 120_000) -> dict[str, Any]:
    parts = task_id.split(":")
    session_id = parts[1] if len(parts) > 1 else ""
    suffix = parts[2] if len(parts) > 2 else "codex"
    path = _find_codex_session_file(session_id)
    if not path or not path.exists():
        return {"task_id": task_id, "exists": False, "size_bytes": 0, "content": "", "truncated": False}
    size = path.stat().st_size
    requested_tail = int(tail or 0)
    tail = min(size, MAX_LOG_BYTES) if requested_tail <= 0 else max(1, min(requested_tail, MAX_LOG_BYTES))
    with path.open("rb") as handle:
        if size > tail:
            handle.seek(size - tail)
            content = handle.read().decode("utf-8", errors="replace")
            truncated = True
        else:
            content = handle.read().decode("utf-8", errors="replace")
            truncated = False
    friendly = _format_codex_session_log(content, suffix)
    return {
        "task_id": task_id,
        "exists": True,
        "size_bytes": size,
        "content": friendly,
        "truncated": truncated,
        "updated_at": int(path.stat().st_mtime),
    }


def _format_codex_session_log(content: str, suffix: str = "codex") -> str:
    rows: list[str] = []
    suffix = str(suffix or "codex")
    for line in content.splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except Exception:
            continue
        payload = item.get("payload") or {}
        kind = payload.get("type") or item.get("type") or "event"
        role = payload.get("role") or ""
        stamp = str(item.get("timestamp") or "")
        clock = stamp[11:19] if len(stamp) >= 19 else ""
        prefix = f"{clock} " if clock else ""
        if kind in {"user_message"} or (kind == "message" and role == "user"):
            text = _real_user_text(payload)
            if text and suffix in {"goal", "user-result"}:
                rows.append(f"{prefix}User: {_compact(text, 260)}")
        elif kind in {"agent_message"} or (kind == "message" and role == "assistant"):
            text = _payload_text(payload)
            if text and suffix in {"codex", "codex-return", "user-result"}:
                rows.append(f"{prefix}Codex: {_compact(text, 260)}")
        elif kind == "function_call":
            activity = _friendly_tool_activity(payload.get('name') or 'tool', payload.get('arguments') or '')
            haystack = f"{payload.get('name') or ''}\n{payload.get('arguments') or ''}".lower()
            if suffix == "codex" or (suffix == "hermes" and "hermes" in haystack) or (suffix == "overlord" and "overlord" in haystack):
                rows.append(f"{prefix}Codex: {activity}")
        elif kind == "custom_tool_call":
            if suffix == "codex":
                rows.append(f"{prefix}Codex: {_friendly_tool_activity(payload.get('name') or 'tool')}")
        elif kind == "task_complete":
            if suffix in {"codex-return", "user-result"}:
                rows.append(f"{prefix}Готово: задача завершена")
    if not rows:
        return "Журнал пока пуст."
    return _redact("\n".join(rows[-240:]))


def _pid_exists(pid: Any) -> bool:
    try:
        value = int(pid or 0)
    except Exception:
        return False
    if value <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes

            handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, value)
            if not handle:
                return False
            code = ctypes.c_ulong()
            ok = ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
            ctypes.windll.kernel32.CloseHandle(handle)
            return bool(ok and code.value == 259)
        except Exception:
            return False
    try:
        os.kill(value, 0)
        return True
    except Exception:
        return False


def _claim_host(value: Any) -> str:
    text = str(value or "")
    if not text or ":" not in text:
        return ""
    return text.split(":", 1)[0].strip().lower()


@lru_cache(maxsize=1)
def _local_hostnames() -> set[str]:
    names = {"localhost", "127.0.0.1", "::1"}
    for key in ("COMPUTERNAME", "HOSTNAME"):
        value = str(os.environ.get(key) or "").strip().lower()
        if value:
            names.add(value)
    try:
        import socket

        for value in (socket.gethostname(), socket.getfqdn()):
            if value:
                names.add(str(value).strip().lower())
    except Exception:
        pass
    return names


def _local_claim_with_pid(run: dict[str, Any], task: dict[str, Any]) -> tuple[bool, Any]:
    pid = run.get("worker_pid") or task.get("worker_pid")
    if not pid:
        return False, None
    hosts = [_claim_host(run.get("claim_lock")), _claim_host(task.get("claim_lock"))]
    local_names = _local_hostnames()
    return any(host and host in local_names for host in hosts), pid


def _recent(timestamp: Any, now: int, window: int = LIVE_HEARTBEAT_SECONDS) -> bool:
    try:
        value = int(timestamp or 0)
    except Exception:
        return False
    return value > 0 and now - value <= window


def _future(timestamp: Any, now: int) -> bool:
    try:
        value = int(timestamp or 0)
    except Exception:
        return False
    return value > now


def _live_run(run: dict[str, Any], task: dict[str, Any], now: int) -> bool:
    if run.get("ended_at"):
        return False
    if str(run.get("status") or "").lower() not in RUNNING_STATUSES:
        return False
    if _recent(run.get("last_heartbeat_at"), now) or _recent(task.get("last_heartbeat_at"), now):
        return True
    if _recent(run.get("started_at"), now, LIVE_START_GRACE_SECONDS):
        return True

    # A live PID or renewed claim only proves that something still owns the task.
    # Without a heartbeat after the grace window, surface it as stale instead of live.
    has_local_pid, pid = _local_claim_with_pid(run, task)
    if has_local_pid:
        _pid_exists(pid)
        return False
    if _pid_exists(pid):
        return False
    if _future(run.get("claim_expires"), now) or _future(task.get("claim_expires"), now):
        return False
    return False


def _task_liveness(task: dict[str, Any], runs: list[dict[str, Any]], now: int) -> str:
    if any(_live_run(run, task, now) for run in runs):
        return "live"
    has_open_run = any(not run.get("ended_at") and str(run.get("status") or "").lower() in RUNNING_STATUSES for run in runs)
    if has_open_run or task.get("current_run_id") or str(task.get("status") or "").lower() == "running":
        return "stale"
    if str(task.get("status") or "").lower() in {"ready"} and _recent(
        task.get("created_at") or task.get("started_at"), now, RECENT_PENDING_SECONDS
    ):
        return "pending"
    if str(task.get("status") or "").lower() in {"ready", "review", "blocked"}:
        return "queued"
    return "idle"


def _build_projects(conn: sqlite3.Connection, include_archived: bool = False) -> dict[str, Any]:
    now = _now()
    status_clause = "" if include_archived else "WHERE status != 'archived'"
    tasks = {
        row["id"]: _row(row)
        for row in conn.execute(f"SELECT * FROM tasks {status_clause} ORDER BY created_at ASC, id ASC").fetchall()
    }
    task_ids = set(tasks.keys())
    if not task_ids:
        return {"tasks": {}, "links": [], "projects": [], "open_runs": {}, "liveness": {}}

    links = [
        {"parent_id": row["parent_id"], "child_id": row["child_id"]}
        for row in conn.execute("SELECT parent_id, child_id FROM task_links ORDER BY parent_id, child_id").fetchall()
        if row["parent_id"] in task_ids and row["child_id"] in task_ids
    ]
    existing_links = {(link["parent_id"], link["child_id"]) for link in links}
    for root_id, root_task in tasks.items():
        root_key = str(root_id or "").lower()
        if not root_key or root_task.get("session_id"):
            continue
        root_assignee = str(root_task.get("assignee") or "").lower()
        root_title = str(root_task.get("title") or "").lower()
        if root_assignee != "overlord" and not root_title.startswith("overlord intake:"):
            continue
        inferred = {
            tid for tid, task in tasks.items()
            if tid != root_id and root_key in str(task.get("idempotency_key") or "").lower()
        }
        if not inferred:
            continue
        inferred_children = {
            child for parent, child in existing_links
            if parent in inferred and child in inferred
        }
        for child_id in sorted(inferred - inferred_children, key=lambda tid: (tasks[tid].get("created_at") or 0, tid)):
            link_key = (root_id, child_id)
            if link_key not in existing_links:
                links.append({"parent_id": root_id, "child_id": child_id})
                existing_links.add(link_key)
    adjacency = {task_id: set() for task_id in task_ids}
    parents = {task_id: set() for task_id in task_ids}
    for link in links:
        parent, child = link["parent_id"], link["child_id"]
        adjacency[parent].add(child)
        adjacency[child].add(parent)
        parents[child].add(parent)

    open_runs: dict[str, list[dict[str, Any]]] = {task_id: [] for task_id in task_ids}
    for row in conn.execute("SELECT * FROM task_runs WHERE ended_at IS NULL ORDER BY started_at ASC, id ASC").fetchall():
        if row["task_id"] in task_ids:
            open_runs.setdefault(row["task_id"], []).append(_row(row))
    liveness = {task_id: _task_liveness(tasks[task_id], open_runs.get(task_id, []), now) for task_id in task_ids}

    projects: list[dict[str, Any]] = []
    seen: set[str] = set()
    for start in sorted(task_ids, key=lambda tid: (tasks[tid].get("created_at") or 0, tid)):
        if start in seen:
            continue
        stack = [start]
        component: set[str] = set()
        while stack:
            tid = stack.pop()
            if tid in component:
                continue
            component.add(tid)
            stack.extend(sorted(adjacency.get(tid, set()) - component))
        seen.update(component)

        session_ids = sorted({str(tasks[tid].get("session_id")) for tid in component if tasks[tid].get("session_id")})
        groups: list[tuple[str, set[str], list[str]]] = []
        if session_ids:
            unscoped = {tid for tid in component if not tasks[tid].get("session_id")}
            unscoped_roots = _roots(unscoped, tasks, parents) if unscoped else []
            canonical_root = next(
                (
                    tid for tid in unscoped_roots
                    if str(tasks[tid].get("assignee") or "").lower() == "overlord"
                    or str(tasks[tid].get("title") or "").lower().startswith("overlord intake:")
                ),
                None,
            )
            if canonical_root:
                groups.append((f"root:{canonical_root}", component, session_ids))
            else:
                for session_id in session_ids:
                    scoped = {tid for tid in component if str(tasks[tid].get("session_id") or "") == session_id}
                    if len(session_ids) == 1:
                        scoped |= unscoped
                    groups.append((f"session:{session_id}", scoped, [session_id]))
                if len(session_ids) > 1 and unscoped:
                    root_id = _roots(unscoped, tasks, parents)[0]
                    groups.append((f"root:{root_id}", unscoped, []))
        else:
            root_id = _roots(component, tasks, parents)[0]
            groups.append((f"root:{root_id}", component, []))

        for project_id, group_ids, group_sessions in groups:
            if not group_ids:
                continue
            roots = _roots(group_ids, tasks, parents)
            display_task_id = _project_display_task_id(group_ids, roots, tasks)
            display_task = tasks[display_task_id]
            counts: dict[str, int] = {}
            assignees: set[str] = set()
            updated_at = 0
            latest_created_at = 0
            for tid in group_ids:
                task = tasks[tid]
                status = task.get("status") or "todo"
                counts[status] = counts.get(status, 0) + 1
                if task.get("assignee"):
                    assignees.add(str(task["assignee"]))
                task_runs = open_runs.get(tid, [])
                latest_created_at = max(latest_created_at, int(task.get("created_at") or 0))
                updated_at = max(
                    updated_at,
                    int(task.get("completed_at") or 0),
                    int(task.get("started_at") or 0),
                    int(task.get("created_at") or 0),
                    int(task.get("claim_expires") or 0),
                    int(task.get("last_heartbeat_at") or 0),
                    *(int(run.get("started_at") or 0) for run in task_runs),
                    *(int(run.get("claim_expires") or 0) for run in task_runs),
                    *(int(run.get("last_heartbeat_at") or 0) for run in task_runs),
                )
            live_count = sum(1 for tid in group_ids if liveness.get(tid) == "live")
            watchdog_live_count = sum(
                1 for tid in group_ids if liveness.get(tid) == "live" and _is_watchdog_task(tasks[tid])
            )
            execution_live_count = live_count - watchdog_live_count
            stale_count = sum(1 for tid in group_ids if liveness.get(tid) == "stale")
            pending_count = sum(1 for tid in group_ids if liveness.get(tid) == "pending")
            queued_count = sum(1 for tid in group_ids if liveness.get(tid) == "queued")
            latest_comment = ""
            comment_ids = sorted(group_ids)
            if comment_ids:
                comment_placeholders = ",".join("?" for _ in comment_ids)
                row = conn.execute(
                    f"SELECT body FROM task_comments WHERE task_id IN ({comment_placeholders}) "
                    "ORDER BY created_at DESC, id DESC LIMIT 1",
                    comment_ids,
                ).fetchone()
                latest_comment = row["body"] if row else ""
            blocked_active = bool(counts.get("blocked", 0) and updated_at and now - updated_at <= RECENT_PENDING_SECONDS)
            projects.append({
                "id": project_id,
                "root_task_id": roots[0],
                "root_task_ids": roots,
                "display_task_id": display_task_id,
                "session_ids": group_sessions,
                "title": display_task.get("title") or display_task_id,
                "summary": _compact(latest_comment or display_task.get("result") or display_task.get("body") or "", 220),
                "task_ids": sorted(group_ids, key=lambda tid: (tasks[tid].get("created_at") or 0, tid)),
                "counts": counts,
                "task_count": len(group_ids),
                "active_count": execution_live_count,
                "live_count": live_count,
                "watchdog_live_count": watchdog_live_count,
                "running_count": execution_live_count,
                "pending_count": pending_count,
                "blocked_count": counts.get("blocked", 0),
                "stale_count": stale_count,
                "queued_count": queued_count,
                "done_count": counts.get("done", 0),
                "is_active": execution_live_count > 0 or pending_count > 0 or stale_count > 0 or blocked_active,
                "assignees": sorted(assignees),
                "created_at": min(int(tasks[tid].get("created_at") or 0) for tid in group_ids),
                "latest_created_at": latest_created_at,
                "updated_at": updated_at,
            })
    projects.sort(key=lambda item: (item["is_active"], item["updated_at"], item["latest_created_at"], item["active_count"]), reverse=True)
    return {"tasks": tasks, "links": links, "projects": projects, "open_runs": open_runs, "liveness": liveness}


def _roots(ids: set[str], tasks: dict[str, dict[str, Any]], parents: dict[str, set[str]]) -> list[str]:
    return sorted(
        [tid for tid in ids if not (parents.get(tid, set()) & ids)] or list(ids),
        key=lambda tid: (tasks[tid].get("created_at") or 0, tid),
    )


def _depths(ids: set[str], links: list[dict[str, str]]) -> dict[str, int]:
    parents = {tid: set() for tid in ids}
    children = {tid: set() for tid in ids}
    for link in links:
        parent, child = link["parent_id"], link["child_id"]
        if parent in ids and child in ids:
            parents[child].add(parent)
            children[parent].add(child)
    roots = [tid for tid in ids if not parents[tid]] or list(ids)
    depths = {tid: 0 for tid in roots}
    queue = list(roots)
    while queue:
        parent = queue.pop(0)
        for child in sorted(children[parent]):
            next_depth = max(depths.get(child, 0), depths[parent] + 1)
            if depths.get(child) != next_depth:
                depths[child] = next_depth
                queue.append(child)
    for tid in ids:
        depths.setdefault(tid, 0)
    return depths


def _epoch_from_iso(value: Any) -> int:
    if not value:
        return 0
    try:
        return int(datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp())
    except Exception:
        return 0


def _recent_codex_session_files(now: int, archive: bool = False) -> list[Path]:
    root = _codex_home() / "sessions"
    if not root.exists():
        return []
    window = CODEX_SESSION_ARCHIVE_SECONDS if archive else CODEX_SESSION_ACTIVE_SECONDS
    limit = CODEX_SESSION_ARCHIVE_SCAN_LIMIT if archive else CODEX_SESSION_SCAN_LIMIT
    files = [path for path in root.glob("**/*.jsonl") if now - int(path.stat().st_mtime) <= window]
    return sorted(files, key=lambda item: item.stat().st_mtime, reverse=True)[:limit]


def _session_title(first_user: str, cwd: str, session_id: str) -> str:
    if first_user:
        return _compact(first_user, 170)
    if cwd:
        return f"Codex session: {Path(cwd).name}"
    return f"Codex session: {session_id}"


def _codex_node(
    session_id: str,
    suffix: str,
    title: str,
    label: str,
    phase: str,
    depth: int,
    status: str,
    liveness: str,
    activity: str,
    signals: list[dict[str, Any]],
    created_at: int,
    updated_at: int,
    event_count: int = 0,
    runs: list[dict[str, Any]] | None = None,
    events: list[dict[str, Any]] | None = None,
    semantic_role: str = "",
    overview: str = "",
    current_action: str = "",
    outcome: str = "",
    stage_label: str = "",
    hide_tabs: list[str] | None = None,
    public_tools: list[str] | None = None,
    tools_used: list[dict[str, Any]] | None = None,
    mcp_used: list[dict[str, Any]] | None = None,
    received: str = "",
    did: str = "",
    handoff: str = "",
    log_task_id: str | None = None,
) -> dict[str, Any]:
    task_id = f"codex-session:{session_id}:{suffix}"
    return {
        "id": f"task:{task_id}",
        "task_id": task_id,
        "type": "project-task",
        "title": title,
        "label": label,
        "assignee": label,
        "phase": phase,
        "status": status,
        "liveness": liveness,
        "is_active": liveness == "live",
        "is_running": liveness == "live",
        "is_stale": liveness == "stale",
        "depth": depth,
        "subtitle": _compact(activity, 160),
        "latest_activity": activity,
        "tool_signals": signals,
        "comment_count": 0,
        "event_count": event_count,
        "runs": runs or [],
        "events": events or [],
        "log": {"task_id": log_task_id or task_id, "exists": True, "updated_at": updated_at},
        "semantic": True,
        "semantic_role": semantic_role or label,
        "overview": overview or activity,
        "current_action": current_action or activity,
        "outcome": outcome,
        "stage_label": stage_label,
        "hide_tabs": hide_tabs or [],
        "public_tools": public_tools or [],
        "tools_used": tools_used or [],
        "mcp_used": mcp_used or [],
        "received": received,
        "did": did or activity,
        "handoff": handoff,
        "created_at": created_at,
        "updated_at": updated_at,
    }


def _profile_label(profile: Any) -> str:
    value = str(profile or "").lower()
    return PROFILE_LABELS.get(value, str(profile or "unassigned"))


def _extract_hermes_task_ids(*parts: Any) -> list[str]:
    seen: set[str] = set()
    ids: list[str] = []
    for part in parts:
        for match in HERMES_TASK_RE.finditer(str(part or "")):
            task_id = match.group(0).lower()
            if task_id not in seen:
                seen.add(task_id)
                ids.append(task_id)
    return ids


def _load_hermes_family(conn: sqlite3.Connection, seed_ids: list[str], now: int) -> dict[str, Any]:
    if not seed_ids:
        return {"tasks": {}, "links": [], "comments": {}, "events": {}, "runs": {}, "liveness": {}, "ids": [], "seed_ids": []}
    try:
        tasks = {row["id"]: _row(row) for row in conn.execute("SELECT * FROM tasks ORDER BY created_at ASC, id ASC").fetchall()}
        links = [
            {"parent_id": row["parent_id"], "child_id": row["child_id"]}
            for row in conn.execute("SELECT parent_id, child_id FROM task_links ORDER BY parent_id, child_id").fetchall()
            if row["parent_id"] in tasks and row["child_id"] in tasks
        ]
    except Exception:
        return {"tasks": {}, "links": [], "comments": {}, "events": {}, "runs": {}, "liveness": {}, "ids": [], "seed_ids": []}

    valid_seeds = [task_id for task_id in seed_ids if task_id in tasks]
    adjacency = {task_id: set() for task_id in tasks}
    for link in links:
        adjacency[link["parent_id"]].add(link["child_id"])
        adjacency[link["child_id"]].add(link["parent_id"])

    family_ids: set[str] = set()
    stack = list(valid_seeds)
    while stack:
        task_id = stack.pop()
        if task_id in family_ids:
            continue
        family_ids.add(task_id)
        stack.extend(sorted(adjacency.get(task_id, set()) - family_ids))

    ordered = sorted(family_ids, key=lambda tid: (tasks[tid].get("created_at") or 0, tid))
    comments = {task_id: [] for task_id in ordered}
    events = {task_id: [] for task_id in ordered}
    runs = {task_id: [] for task_id in ordered}
    if ordered:
        placeholders = ",".join("?" for _ in ordered)
        for row in conn.execute(f"SELECT * FROM task_comments WHERE task_id IN ({placeholders}) ORDER BY created_at ASC, id ASC", ordered).fetchall():
            comments.setdefault(row["task_id"], []).append(_row(row))
        for row in conn.execute(f"SELECT * FROM task_events WHERE task_id IN ({placeholders}) ORDER BY id ASC", ordered).fetchall():
            item = _row(row)
            item["payload"] = _json_loads(item.get("payload"), None)
            events.setdefault(row["task_id"], []).append(item)
        for row in conn.execute(f"SELECT * FROM task_runs WHERE task_id IN ({placeholders}) ORDER BY started_at ASC, id ASC", ordered).fetchall():
            item = _row(row)
            item["metadata"] = _json_loads(item.get("metadata"), None)
            runs.setdefault(row["task_id"], []).append(item)

    open_runs = {task_id: [run for run in runs.get(task_id, []) if not run.get("ended_at")] for task_id in ordered}
    liveness = {task_id: _task_liveness(tasks[task_id], open_runs.get(task_id, []), now) for task_id in ordered}
    return {
        "tasks": {task_id: tasks[task_id] for task_id in ordered},
        "links": [link for link in links if link["parent_id"] in family_ids and link["child_id"] in family_ids],
        "comments": comments,
        "events": events,
        "runs": runs,
        "liveness": liveness,
        "ids": ordered,
        "seed_ids": valid_seeds,
    }


def _family_root_ids(family: dict[str, Any]) -> list[str]:
    ids = set(family.get("ids") or [])
    if not ids:
        return []
    children = {link["child_id"] for link in family.get("links") or [] if link.get("child_id") in ids}
    roots = [task_id for task_id in family.get("ids") or [] if task_id not in children]
    overlord_roots = [
        task_id for task_id in roots
        if str(family["tasks"].get(task_id, {}).get("assignee") or "").lower() == "overlord"
    ]
    return overlord_roots or roots or list(family.get("seed_ids") or [])


def _family_latest_ts(family: dict[str, Any]) -> int:
    latest = 0
    for task_id, task in family.get("tasks", {}).items():
        latest = max(
            latest,
            int(task.get("completed_at") or 0),
            int(task.get("started_at") or 0),
            int(task.get("created_at") or 0),
            int(task.get("claim_expires") or 0),
            int(task.get("last_heartbeat_at") or 0),
        )
        for run in family.get("runs", {}).get(task_id, []):
            latest = max(
                latest,
                int(run.get("ended_at") or 0),
                int(run.get("started_at") or 0),
                int(run.get("claim_expires") or 0),
                int(run.get("last_heartbeat_at") or 0),
            )
    return latest


def _select_hermes_family(conn: sqlite3.Connection, hermes_ids: list[str], now: int, view: str) -> dict[str, Any]:
    empty = {"tasks": {}, "links": [], "comments": {}, "events": {}, "runs": {}, "liveness": {}, "ids": [], "seed_ids": []}
    if not hermes_ids:
        return empty
    candidates: list[tuple[bool, int, int, dict[str, Any]]] = []
    seen: set[frozenset[str]] = set()
    for seed_id in reversed(hermes_ids[-32:]):
        family = _load_hermes_family(conn, [seed_id], now)
        ids_key = frozenset(family.get("ids") or [])
        if not ids_key or ids_key in seen:
            continue
        seen.add(ids_key)
        family["seed_ids"] = _family_root_ids(family)
        live = any(family["liveness"].get(task_id) in {"live", "pending"} for task_id in family.get("ids") or [])
        latest = _family_latest_ts(family)
        candidates.append((live, latest, len(family.get("ids") or []), family))
    if not candidates:
        return empty
    if view == "archive":
        archived = [item for item in candidates if not item[0]] or candidates
        return sorted(archived, key=lambda item: (item[1], item[2]), reverse=True)[0][3]
    active = [item for item in candidates if item[0]] or candidates
    return sorted(active, key=lambda item: (item[0], item[1], item[2]), reverse=True)[0][3]


def _task_has_work(task_id: str, family: dict[str, Any]) -> bool:
    task = family["tasks"].get(task_id, {})
    status = str(task.get("status") or "").lower()
    events = [event for event in family["events"].get(task_id, []) if event.get("kind") != "created"]
    return bool(
        family["runs"].get(task_id)
        or family["comments"].get(task_id)
        or events
        or status in {"running", "review", "done", "blocked"}
    )


def _hermes_participant_groups(family: dict[str, Any]) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    seed_ids = set(family.get("seed_ids") or [])
    for task_id in family.get("ids") or []:
        task = family["tasks"].get(task_id, {})
        assignee = str(task.get("assignee") or "").lower()
        if not assignee or assignee == "overlord" or task_id in seed_ids:
            continue
        if not _task_has_work(task_id, family):
            continue
        group = groups.setdefault(assignee, {
            "assignee": assignee,
            "task_ids": [],
            "titles": [],
            "live": False,
            "stale": False,
            "done": False,
            "latest": "",
            "received": "",
            "did": "",
            "handoff": "",
            "tools_used": [],
            "mcp_used": [],
        })
        group["task_ids"].append(task_id)
        group["titles"].append(task.get("title") or task_id)
        task_liveness = family["liveness"].get(task_id)
        live = task_liveness == "live"
        stale = task_liveness == "stale"
        group["live"] = group["live"] or live
        group["stale"] = group["stale"] or stale
        group["done"] = group["done"] or str(task.get("status") or "").lower() == "done"
        activity = _latest_activity(task, family["events"].get(task_id, []), family["runs"].get(task_id, []))
        if activity:
            group["latest"] = activity
        comments = family["comments"].get(task_id, [])
        events = family["events"].get(task_id, [])
        runs = family["runs"].get(task_id, [])
        latest_comment = next((comment.get("body") for comment in reversed(comments) if comment.get("body")), "")
        group["received"] = group["received"] or _compact(task.get("body") or task.get("title") or task_id, 420)
        group["did"] = latest_comment or task.get("result") or activity or group["did"]
        group["handoff"] = task.get("result") or latest_comment or group["handoff"]
        blob = _task_text_blob(task, comments, events, runs)
        group["mcp_used"].extend(_extract_mcp_mentions(blob, limit=8))
        group["tools_used"].extend(_count_items([_friendly_tool_name((run.get("metadata") or {}).get("tool") or run.get("profile")) for run in runs], limit=8))
    for group in groups.values():
        group["tools_used"] = _count_items(
            [item["name"] for item in group["tools_used"] for _ in range(int(item.get("count") or 1))],
            8,
        )
        group["mcp_used"] = _count_items(
            [item["name"] for item in group["mcp_used"] for _ in range(int(item.get("count") or 1))],
            8,
        )
    return sorted(groups.values(), key=lambda item: (0 if item["live"] else 1 if item["stale"] else 2, item["assignee"]))


def _overlord_summary(family: dict[str, Any], hermes_ids: list[str]) -> tuple[str, str, str]:
    if not hermes_ids:
        return "Передача в Hermes не найдена", "Codex не оставил подтвержденной карточки Hermes.", "missing"
    if not family.get("seed_ids"):
        return "Hermes-задача не найдена", "В сессии есть ссылка на Hermes, но карточка не найдена в Kanban.", "missing"
    participants = _hermes_participant_groups(family)
    if participants:
        names = ", ".join(_profile_label(item["assignee"]) for item in participants[:4])
        return f"Раздал работу: {names}", "Overlord создал рабочую линию и подключил участников Hermes family.", "running"
    seed_tasks = [family["tasks"][task_id] for task_id in family.get("seed_ids") or []]
    statuses = {str(task.get("status") or "").lower() for task in seed_tasks}
    seed_liveness = [family.get("liveness", {}).get(task_id) for task_id in family.get("seed_ids") or []]
    seed_comments = [
        str(comment.get("body") or "")
        for task_id in family.get("seed_ids") or []
        for comment in family.get("comments", {}).get(task_id, [])
    ]
    has_council_notes = any("council handoff" in body.lower() for body in seed_comments)
    if "stale" in seed_liveness and has_council_notes:
        return "Council есть только в заметках", "Overlord написал Product/UX/Architect handoff, но durable child-задачи не созданы и heartbeat устарел.", "stale"
    if "stale" in seed_liveness:
        return "Overlord без свежего heartbeat", "Hermes-задача числится running, но свежей активности и дочерних агентов не видно.", "stale"
    if statuses <= {"archived"}:
        return "Карточка закрыта без воркеров", "Hermes получил intake, но реальные дочерние агенты не запускались.", "archived"
    if has_council_notes:
        return "Council записан, воркеров нет", "Overlord оставил council handoff как комментарии, но реальные child-задачи пока не появились.", "triage"
    return "Задача в очереди Hermes", "Overlord intake создан, реальные воркеры пока не стартовали.", "triage"


def _codex_session_graph(path: Path, now: int, conn: sqlite3.Connection, view: str = "active") -> dict[str, Any] | None:
    session_id = _session_id_from_path(path)
    meta: dict[str, Any] = {}
    first_user = ""
    user_prompts: list[tuple[int, str]] = []
    latest_agent = ""
    latest_final_agent = ""
    latest_activity = ""
    latest_ts = 0
    open_calls: dict[str, dict[str, Any]] = {}
    session_texts: list[str] = []
    tool_texts: list[str] = []
    tool_names: list[str] = []
    mcp_names: list[str] = []
    tool_events: list[tuple[int, str, str]] = []
    memory_tool_used = False
    last_real_user_ts = 0
    last_final_ts = 0

    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return None

    for line in lines:
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except Exception:
            continue
        payload = item.get("payload") or {}
        ts = _epoch_from_iso(item.get("timestamp"))
        latest_ts = max(latest_ts, ts)
        kind = payload.get("type") or item.get("type") or "event"
        role = payload.get("role") or ""

        if item.get("type") == "session_meta":
            meta = payload
        if kind in {"user_message"} or (kind == "message" and role == "user"):
            text = _real_user_text(payload)
            if text:
                user_prompts.append((ts, text))
                session_texts.append(text)
                last_real_user_ts = max(last_real_user_ts, ts)
        elif kind in {"agent_message"} or (kind == "message" and role == "assistant"):
            text = _payload_text(payload)
            if text:
                latest_agent = text
                session_texts.append(text)
            if payload.get("phase") == "final_answer":
                latest_final_agent = text or latest_final_agent
                last_final_ts = max(last_final_ts, ts)

        if kind == "function_call":
            name = payload.get("name") or "tool"
            args = payload.get("arguments") or ""
            memory_tool_used = memory_tool_used or bool(re.search(r"\b(notion|obsidian)\b", str(name), re.IGNORECASE))
            tool_names.append(_friendly_tool_name(name))
            args_text = str(args or "")
            tool_events.append((ts, name, args_text))
            if "overlord-intake" in args_text.lower() or "overlord.ps1" in args_text.lower():
                mcp_names.append("Overlord Kanban")
            if "codex-hermes-preflight" in args_text.lower() or "8765/mcp" in args_text.lower():
                mcp_names.append("Hermes bridge")
            open_calls[payload.get("call_id") or f"call-{len(open_calls)}"] = {
                "id": payload.get("call_id"),
                "profile": "Codex",
                "status": "running",
                "started_at": ts,
                "ended_at": None,
                "summary": _friendly_tool_activity(name, args),
            }
            latest_activity = _friendly_tool_activity(name, args)
            session_texts.append(args)
            tool_texts.append(args)
        elif kind == "function_call_output":
            open_calls.pop(payload.get("call_id"), None)
            output = payload.get("output") or ""
            session_texts.append(output)
            tool_texts.append(output)
        elif kind == "custom_tool_call":
            name = payload.get("name") or "tool"
            memory_tool_used = memory_tool_used or bool(re.search(r"\b(notion|obsidian)\b", str(name), re.IGNORECASE))
            tool_names.append(_friendly_tool_name(name))
            tool_events.append((ts, name, ""))
            latest_activity = _friendly_tool_activity(name)
            session_texts.append(name)
        elif kind == "custom_tool_call_output":
            output = payload.get("output") or ""
            session_texts.append(output)
            tool_texts.append(output)
        elif kind == "task_complete":
            last_final_ts = max(last_final_ts, ts)

    updated_at = int(path.stat().st_mtime)
    created_at = _epoch_from_iso(meta.get("timestamp")) or latest_ts or updated_at
    cwd = meta.get("cwd") or ""
    first_user = user_prompts[-1][1] if user_prompts else ""
    completed = bool(last_final_ts and last_final_ts >= last_real_user_ts and not open_calls)

    project_id = f"codex-session:{session_id}"
    open_runs = list(open_calls.values())
    all_hermes_ids = _extract_hermes_task_ids(*session_texts)
    family = _select_hermes_family(conn, all_hermes_ids, now, view)
    hermes_ids = list(family.get("seed_ids") or all_hermes_ids[-1:])
    overlord_activity, overlord_overview, overlord_status = _overlord_summary(family, hermes_ids)
    participants = _hermes_participant_groups(family)
    family_liveness_values = [family["liveness"].get(task_id) for task_id in family.get("ids") or []]
    family_live_count = sum(1 for value in family_liveness_values if value == "live")
    family_pending_count = sum(1 for value in family_liveness_values if value == "pending")
    family_stale_count = sum(1 for value in family_liveness_values if value == "stale")
    family_queued_count = sum(1 for value in family_liveness_values if value == "queued")
    family_has_live = family_live_count > 0
    family_has_pending = family_pending_count > 0
    family_has_stale = family_stale_count > 0
    family_has_queued = family_queued_count > 0
    family_active = family_has_live or family_has_pending or family_has_stale or family_has_queued
    active = bool(open_calls) or family_active
    if view == "archive" and active:
        return None
    if view != "archive" and not active:
        return None
    liveness = (
        "live" if open_calls or family_has_live else
        "stale" if family_has_stale else
        "pending" if family_has_pending else
        "queued" if family_has_queued else
        "idle"
    )
    codex_action = latest_activity or ("Собирает ответ" if active else "Ждет следующий шаг")
    seed_id = (family.get("seed_ids") or [None])[0]
    seed_task = family["tasks"].get(seed_id, {}) if seed_id else {}
    seed_comments = family["comments"].get(seed_id, []) if seed_id else []
    seed_events = family["events"].get(seed_id, []) if seed_id else []
    seed_runs = family["runs"].get(seed_id, []) if seed_id else []
    seed_blob = _task_text_blob(seed_task, seed_comments, seed_events, seed_runs) if seed_task else ""
    seed_summary = seed_task.get("title") or seed_task.get("body") or ""
    seed_created_at = int(seed_task.get("created_at") or 0) if seed_task else 0
    if seed_created_at:
        scoped_prompts = [text for ts, text in user_prompts if ts <= seed_created_at + 180]
        if scoped_prompts:
            first_user = scoped_prompts[-1]
    title = _session_title(first_user, cwd, session_id)
    if seed_task and str(first_user or "").lstrip().startswith("<heartbeat"):
        # Heartbeat automation text is transport noise; show the actual
        # Hermes root request as the user-facing project title/context.
        first_user = seed_task.get("body") or seed_task.get("title") or first_user
        title = _compact(seed_task.get("title") or first_user, 170)
    scope_start = max(0, seed_created_at - 600) if seed_created_at else 0
    scoped_tool_events = [event for event in tool_events if not scope_start or event[0] >= scope_start] or tool_events
    scoped_tool_names = [_friendly_tool_name(event[1]) for event in scoped_tool_events]
    scoped_mcp_names: list[str] = []
    for _, name, args_text in scoped_tool_events:
        haystack = f"{name}\n{args_text}".lower()
        if "overlord-intake" in haystack or "overlord.ps1" in haystack:
            scoped_mcp_names.append("Overlord Kanban")
        if "codex-hermes-preflight" in haystack or "8765/mcp" in haystack:
            scoped_mcp_names.append("Hermes bridge")
    # Do not mine MCP names from arbitrary command arguments: those often contain the
    # user's prompt and produce false badges. Keep only concrete bridge/kanban markers.
    codex_tools = _count_items(scoped_tool_names, 10)
    codex_mcp = _count_items(scoped_mcp_names, 8)
    seed_tools = _count_items([
        _friendly_tool_name((run.get("metadata") or {}).get("tool") or run.get("profile"))
        for run in seed_runs
    ], 8)
    seed_mcp = _extract_mcp_mentions(seed_blob, limit=8)
    seed_liveness = family["liveness"].get(seed_id, "idle") if seed_id else "idle"
    seed_live = seed_liveness == "live"
    family_depths = _depths(set(family.get("ids") or []), family.get("links") or []) if family.get("ids") else {}
    participant_handoff = ", ".join(_profile_label(item["assignee"]) for item in participants[:6])
    if hermes_ids:
        codex_overview = "Принял запрос, создал передачу в Hermes и держит пользовательский чат в курсе."
        hermes_action = "Передача принята Overlord"
        hermes_status = "handoff"
    else:
        codex_overview = "Принял запрос, но подтвержденной передачи в Hermes в этой сессии не найдено."
        hermes_action = "Передача не подтверждена"
        hermes_status = "missing"

    nodes = [
        _codex_node(
            session_id,
            "goal",
            "Запрос пользователя",
            "User",
            "ingress",
            0,
            "received",
            "idle",
            "Поставил задачу",
            [],
            created_at,
            updated_at,
            semantic_role="user",
            overview=first_user or title,
            current_action="Задача передана в Codex.",
            received=first_user or title,
            did="Сформулировал задачу для Codex.",
            handoff="Codex",
            stage_label="User",
            hide_tabs=["mcp", "flow"],
        ),
        _codex_node(
            session_id,
            "codex",
            "Куратор запроса",
            "Codex",
            "director",
            1,
            "running" if active else "idle",
            liveness,
            codex_action,
            [],
            created_at,
            updated_at,
            runs=open_runs,
            semantic_role="codex",
            overview=codex_overview,
            current_action=codex_action,
            tools_used=codex_tools,
            mcp_used=codex_mcp,
            received=first_user or title,
            did=codex_overview,
            handoff="Hermes" if hermes_ids else "Нет подтвержденной передачи",
            stage_label="Codex",
            hide_tabs=["mcp", "flow"],
        ),
        _codex_node(
            session_id,
            "hermes",
            "Шлюз Hermes",
            "Hermes",
            "director",
            2,
            hermes_status,
            "idle" if hermes_ids else "stale",
            hermes_action,
            [],
            created_at,
            updated_at,
            semantic_role="hermes",
            overview="Здесь видна только смысловая передача от Codex в Hermes, без внутренних Codex-инструментов.",
            current_action=hermes_action,
            mcp_used=codex_mcp,
            received="Codex передал задачу в Hermes" if hermes_ids else "Передача не найдена",
            did=(f"Связал с Kanban: {', '.join(hermes_ids[:4])}" if hermes_ids else "Нет подтвержденной Hermes-карточки"),
            handoff="Overlord" if hermes_ids else "-",
            stage_label="Hermes",
            hide_tabs=["mcp", "flow"],
        ),
        _codex_node(
            session_id,
            "overlord",
            "Overlord",
            "Overlord",
            "director",
            3,
            "running" if seed_liveness in {"live", "stale"} else ("used" if participants else overlord_status),
            seed_liveness if seed_liveness in {"live", "stale", "pending", "queued"} else "idle",
            overlord_activity,
            [],
            created_at,
            updated_at,
            semantic_role="overlord",
            overview=overlord_overview,
            current_action=overlord_activity,
            tools_used=seed_tools,
            mcp_used=seed_mcp,
            received=_compact(seed_summary or first_user or title, 520),
            did=overlord_overview,
            handoff=participant_handoff or "Codex" if completed else participant_handoff or "Ожидает участников",
            log_task_id=seed_id,
            stage_label="Overlord",
            hide_tabs=["mcp", "flow"],
        ),
    ]

    for item in participants:
        assignee = item["assignee"]
        live = bool(item.get("live"))
        stale = bool(item.get("stale"))
        done = bool(item.get("done"))
        label = _profile_label(assignee)
        raw_depths = [family_depths.get(task_id, 1) for task_id in item.get("task_ids") or []]
        participant_depth = 3 + max(1, min(raw_depths or [1]))
        nodes.append(_codex_node(
            session_id,
            f"agent-{assignee}",
            _compact("; ".join(item.get("titles") or []), 120) or label,
            label,
            _phase(assignee),
            participant_depth,
            "running" if live or stale else "done" if done else "used",
            "live" if live else "stale" if stale else "idle",
            item.get("latest") or f"{label} участвовал в задаче",
            [],
            created_at,
            updated_at,
            semantic_role=assignee,
            overview=f"{label} реально участвовал: есть следы работы в Hermes Kanban.",
            current_action=item.get("latest") or f"{label} участвовал в задаче",
            tools_used=item.get("tools_used") or [],
            mcp_used=item.get("mcp_used") or [],
            received=item.get("received") or _compact("; ".join(item.get("titles") or []), 420),
            did=item.get("did") or item.get("latest") or f"{label} выполнил свой шаг.",
            handoff=item.get("handoff") or "Следующий участник по линии",
            log_task_id=(item.get("task_ids") or [None])[-1],
            stage_label="Family",
            hide_tabs=["mcp", "flow"],
        ))

    participant_depth_values = [node["depth"] for node in nodes if str(node.get("semantic_role") or "").startswith("ol") or node.get("semantic_role") in {"nerood", "diana"}]
    output_depth = (max(participant_depth_values) + 1) if participant_depth_values else 4
    final_activity = "Вернул результат пользователю" if completed else "Ждет проверку и синтез"
    final_answer_text = (latest_final_agent or latest_agent) if completed else ""
    memory_expected = re.search(r"\b(notion|obsidian)\b", first_user, re.IGNORECASE)
    memory_used = memory_tool_used
    nodes.append(_codex_node(
        session_id,
        "codex-return",
        "Ответ Codex",
        "Codex",
        "output",
        output_depth,
        "done" if completed else "waiting",
        "idle",
        final_activity,
        [],
        created_at,
        updated_at,
        semantic_role="codex-output",
        overview="Codex собирает понятный результат из того, что вернул Hermes и что проверено локально.",
        current_action=final_activity,
        received=participant_handoff or "Overlord",
        did=final_answer_text or final_activity,
        handoff="User",
        stage_label="Return",
        hide_tabs=["mcp", "flow"],
    ))
    nodes.append(_codex_node(
        session_id,
        "user-result",
        "Результат пользователю",
        "User",
        "output",
        output_depth + 1,
        "received" if completed else "waiting",
        "idle",
        "Получит итог в чате" if not completed else "Получил итог в чате",
        [],
        created_at,
        updated_at,
        semantic_role="user-output",
        overview=final_answer_text or "Финальный ответ еще собирается.",
        current_action="Ждет итог" if not completed else "Итог доставлен",
        received=final_answer_text or "Финальный ответ еще собирается.",
        did="Получил итог в чате" if completed else "Ждет итоговый ответ",
        handoff="Notion / Obsidian" if memory_expected or memory_used else "-",
        stage_label="User",
        hide_tabs=["mcp", "flow"],
    ))

    if memory_expected or memory_used:
        memory_action = "Запись в память подтверждена" if memory_used else "Записей в Notion/Obsidian не обнаружено"
        nodes.append(_codex_node(
            session_id,
            "memory",
            "Память",
            "Notion / Obsidian",
            "storage",
            output_depth + 1,
            "mounted" if memory_used else "missing",
            "idle",
            memory_action,
            [],
            created_at,
            updated_at,
            semantic_role="memory",
            overview=memory_action,
            current_action=memory_action,
            received="Итог задачи и заметки для памяти",
            did=memory_action,
            mcp_used=_count_items(["Notion" if memory_used else "Notion/Obsidian"]),
            stage_label="Memory",
            hide_tabs=["mcp", "flow"],
        ))

    node_by_suffix = {node["task_id"].split(":")[-1]: node for node in nodes}
    edges = []
    seen_edges: set[tuple[str, str, str]] = set()

    def add_edge(source: str, target: str, label: str, active_edge: bool = False) -> None:
        if not source or not target or source == target:
            return
        key = (source, target, label)
        if key in seen_edges:
            return
        seen_edges.add(key)
        edges.append({"from": source, "to": target, "label": label, "kind": "handoff", "active": bool(active_edge)})

    chain_suffixes = ["goal", "codex", "hermes", "overlord"]
    previous_id = None
    for suffix in chain_suffixes:
        node = node_by_suffix.get(suffix)
        if previous_id and node:
            add_edge(previous_id, node["id"], "handoff", active)
        if node:
            previous_id = node["id"]

    agent_nodes = [
        node for node in nodes
        if str(node.get("semantic_role") or "").startswith("ol") or node.get("semantic_role") in {"nerood", "diana"}
    ]
    task_to_agent_node: dict[str, dict[str, Any]] = {}
    for item in participants:
        agent_node = next((node for node in agent_nodes if node.get("semantic_role") == item.get("assignee")), None)
        if not agent_node:
            continue
        for task_id in item.get("task_ids") or []:
            task_to_agent_node[task_id] = agent_node

    agent_incoming: set[str] = set()
    agent_outgoing: set[str] = set()
    overlord_node = node_by_suffix.get("overlord")
    for link in family.get("links") or []:
        parent, child = link.get("parent_id"), link.get("child_id")
        parent_node = task_to_agent_node.get(parent)
        child_node = task_to_agent_node.get(child)
        if not parent_node and parent in set(family.get("seed_ids") or []):
            parent_node = overlord_node
        if parent_node and child_node:
            add_edge(parent_node["id"], child_node["id"], "handoff", parent_node.get("is_active") or child_node.get("is_active"))
            agent_incoming.add(child_node["id"])
            if parent_node in agent_nodes:
                agent_outgoing.add(parent_node["id"])

    if overlord_node:
        for agent_node in agent_nodes:
            if agent_node["id"] not in agent_incoming:
                add_edge(overlord_node["id"], agent_node["id"], "agent", agent_node.get("is_active", False))

    return_node = node_by_suffix.get("codex-return")
    if return_node:
        source_nodes = [node for node in agent_nodes if node["id"] not in agent_outgoing]
        if not source_nodes and agent_nodes:
            source_nodes = [max(agent_nodes, key=lambda node: node.get("depth") or 0)]
        if not source_nodes and overlord_node:
            source_nodes = [overlord_node]
        for source_node in source_nodes:
            add_edge(source_node["id"], return_node["id"], "result", source_node.get("is_active", False))
        for suffix in ["user-result", "memory"]:
            node = node_by_suffix.get(suffix)
            if node:
                add_edge(return_node["id"], node["id"], "output", completed)

    codex_live_count = 1 if open_calls else 0
    active_count = 1 if active else 0
    live_count = codex_live_count + family_live_count
    pending_count = family_pending_count
    stale_count = family_stale_count
    queued_count = family_queued_count
    counts: dict[str, int] = {}
    if live_count:
        counts["running"] = live_count
    if stale_count:
        counts["stale"] = stale_count
    if pending_count:
        counts["pending"] = pending_count
    if queued_count:
        counts["queued"] = queued_count
    if completed and not counts:
        counts["done"] = 1
    assignees = ["User", "Codex", "Hermes", "Overlord", *[_profile_label(item["assignee"]) for item in participants]]
    project = {
        "id": project_id,
        "source": "codex-session",
        "root_task_id": session_id,
        "root_task_ids": [session_id],
        "linked_hermes_task_ids": list(family.get("ids") or []),
        "display_task_id": f"codex-session:{session_id}:codex",
        "session_ids": [session_id],
        "title": title,
        "summary": _compact(overlord_activity or codex_action or first_user, 220),
        "task_ids": [node["task_id"] for node in nodes],
        "counts": counts,
        "task_count": len(nodes),
        "active_count": live_count,
        "live_count": live_count,
        "watchdog_live_count": 0,
        "running_count": live_count,
        "pending_count": pending_count,
        "blocked_count": 0,
        "stale_count": stale_count,
        "queued_count": queued_count,
        "done_count": 1 if completed else 0,
        "is_active": active,
        "assignees": assignees,
        "created_at": created_at,
        "latest_created_at": created_at,
        "updated_at": updated_at,
    }
    return {"project": project, "nodes": nodes, "edges": edges}


def _build_codex_sessions(now: int, conn: sqlite3.Connection, view: str = "active") -> dict[str, Any]:
    graphs = []
    archive = view == "archive"
    for path in _recent_codex_session_files(now, archive=archive):
        graph = _codex_session_graph(path, now, conn, view=view)
        if graph:
            graphs.append(graph)
    projects = [graph["project"] for graph in graphs]
    projects.sort(key=lambda item: item["updated_at"], reverse=True)
    return {"projects": projects, "graphs": {graph["project"]["id"]: graph for graph in graphs}}


def project_graph(board: str, project_id: str | None = None, view: str = "active", include_codex_sessions: bool = False) -> dict[str, Any]:
    view = "archive" if view == "archive" else "active"
    with _connect(board) as conn:
        now = _now()
        index = _build_projects(conn, include_archived=view == "archive")
        requested_project_id = project_id
        explicit_codex_request = bool(requested_project_id and requested_project_id.startswith("codex-session:"))
        codex_index = (
            _build_codex_sessions(now, conn, view=view)
            if include_codex_sessions or explicit_codex_request
            else {"projects": [], "graphs": {}}
        )
        requested_root_id = (
            requested_project_id.split(":", 1)[1]
            if requested_project_id and requested_project_id.startswith("root:")
            else None
        )

        def _matches_native_root_request(item: dict[str, Any], requested: str | None) -> bool:
            if not requested:
                return False
            if item.get("source") == "codex-session":
                return False
            root_ids = {str(value) for value in item.get("root_task_ids") or []}
            task_ids = {str(value) for value in item.get("task_ids") or []}
            return item.get("id") == requested or requested in root_ids or requested in task_ids

        codex_linked_task_ids = {
            task_id
            for project in codex_index["projects"]
            for task_id in project.get("linked_hermes_task_ids", [])
        }
        kanban_projects = [
            project for project in index["projects"]
            if not (set(project.get("task_ids") or []) & codex_linked_task_ids)
            or _matches_native_root_request(project, requested_root_id)
        ]
        projects = [*kanban_projects, *codex_index["projects"]]
        projects.sort(key=lambda item: (item["is_active"], item["updated_at"], item["latest_created_at"], item["active_count"]), reverse=True)
        visible = [project for project in projects if bool(project.get("is_active")) == (view == "active")]

        def _matches_requested_project(item: dict[str, Any], requested: str) -> bool:
            if item.get("id") == requested:
                return True
            root_ids = {str(value) for value in item.get("root_task_ids") or []}
            linked_ids = {str(value) for value in item.get("linked_hermes_task_ids") or []}
            task_ids = {str(value) for value in item.get("task_ids") or []}
            aliases = root_ids | linked_ids | task_ids
            if requested.startswith("root:"):
                requested_root = requested.split(":", 1)[1]
                return requested in aliases or requested_root in aliases
            return requested in aliases

        project = None
        if project_id:
            if requested_root_id:
                project = next(
                    (item for item in visible if _matches_native_root_request(item, requested_root_id)),
                    None,
                )
            if project is None:
                project = next((item for item in visible if _matches_requested_project(item, project_id)), None)
        if project is None and visible and not requested_project_id:
            project = visible[0]
        live_filter = {
            "heartbeat_seconds": LIVE_HEARTBEAT_SECONDS,
            "start_grace_seconds": LIVE_START_GRACE_SECONDS,
            "live_tasks": sum(1 for value in index["liveness"].values() if value == "live")
            + sum(project.get("live_count", 0) for project in codex_index["projects"] if project.get("is_active")),
            "pending_tasks": sum(1 for value in index["liveness"].values() if value == "pending"),
            "stale_tasks": sum(1 for value in index["liveness"].values() if value == "stale"),
            "queued_tasks": sum(1 for value in index["liveness"].values() if value == "queued"),
            "codex_sessions": len([item for item in codex_index["projects"] if item.get("is_active")]),
        }
        if project is None:
            return {
                "board": board,
                "view": view,
                "project": None,
                "projects": _public_projects(visible),
                "nodes": [],
                "edges": [],
                "live_filter": live_filter,
                "now": now,
            }

        if project.get("source") == "codex-session":
            graph = codex_index["graphs"].get(project["id"], {"nodes": [], "edges": []})
            return {
                "board": board,
                "view": view,
                "project": _public_project(project),
                "projects": _public_projects(visible),
                "nodes": graph.get("nodes", []),
                "edges": graph.get("edges", []),
                "live_filter": live_filter,
                "now": now,
            }

        task_ids = set(project["task_ids"])
        ordered = list(project["task_ids"])
        placeholders = ",".join("?" for _ in ordered)
        comments = {task_id: [] for task_id in ordered}
        events = {task_id: [] for task_id in ordered}
        runs = {task_id: [] for task_id in ordered}
        if ordered:
            for row in conn.execute(f"SELECT * FROM task_comments WHERE task_id IN ({placeholders}) ORDER BY created_at ASC, id ASC", ordered).fetchall():
                comments.setdefault(row["task_id"], []).append(_row(row))
            for row in conn.execute(f"SELECT * FROM task_events WHERE task_id IN ({placeholders}) ORDER BY id ASC", ordered).fetchall():
                item = _row(row)
                item["payload"] = _json_loads(item.get("payload"), None)
                events.setdefault(row["task_id"], []).append(item)
            for row in conn.execute(f"SELECT * FROM task_runs WHERE task_id IN ({placeholders}) ORDER BY started_at ASC, id ASC", ordered).fetchall():
                item = _row(row)
                item["metadata"] = _json_loads(item.get("metadata"), None)
                runs.setdefault(row["task_id"], []).append(item)

        depths = _depths(task_ids, index["links"])
        children_by_parent: dict[str, list[str]] = {task_id: [] for task_id in ordered}
        for link in index["links"]:
            if link["parent_id"] in task_ids and link["child_id"] in task_ids:
                children_by_parent.setdefault(link["parent_id"], []).append(link["child_id"])
        nodes = []
        for task_id in ordered:
            task = index["tasks"][task_id]
            status = task.get("status") or "todo"
            task_runs = runs.get(task_id, [])
            task_events = events.get(task_id, [])
            task_comments = comments.get(task_id, [])
            liveness = index["liveness"].get(task_id, "idle")
            log = _read_log(board, task_id, MAX_LOG_BYTES)
            signal_texts = [
                json.dumps(task_events[-8:], ensure_ascii=False),
                json.dumps(task_runs[-6:], ensure_ascii=False),
                _tool_evidence_text(log.get("content") or ""),
            ]
            latest_comment = next((comment.get("body") for comment in reversed(task_comments) if comment.get("body")), "")
            run_tool_names = [
                _friendly_tool_name((run.get("metadata") or {}).get("tool") or run.get("profile"))
                for run in task_runs
            ]
            handoff_targets = [
                _profile_label(index["tasks"].get(child_id, {}).get("assignee") or child_id)
                for child_id in children_by_parent.get(task_id, [])
            ]
            nodes.append({
                "id": f"task:{task_id}",
                "task_id": task_id,
                "type": "project-task",
                "title": task.get("title") or task_id,
                "label": task.get("assignee") or "unassigned",
                "assignee": task.get("assignee"),
                "phase": _phase(task.get("assignee")),
                "status": status,
                "liveness": liveness,
                "is_active": liveness == "live",
                "is_running": liveness == "live",
                "is_stale": liveness == "stale",
                "depth": depths.get(task_id, 0),
                "subtitle": _compact(_latest_activity(task, task_events, task_runs) or task.get("body") or "waiting", 160),
                "latest_activity": _latest_activity(task, task_events, task_runs),
                "tool_signals": _extract_signals(*signal_texts),
                "tools_used": _count_items(run_tool_names, 8),
                "mcp_used": _extract_mcp_mentions(*signal_texts, limit=8),
                "received": _compact(task.get("body") or task.get("title") or task_id, 520),
                "did": _compact(task.get("result") or latest_comment or _latest_activity(task, task_events, task_runs), 620),
                "handoff": ", ".join(dict.fromkeys(handoff_targets)) or ("Codex/User" if status == "done" else "Ожидает следующего шага"),
                "comment_count": len(task_comments),
                "event_count": len(task_events),
                "runs": task_runs[-4:],
                "events": task_events[-8:],
                "log": {k: v for k, v in log.items() if k != "content"},
                "created_at": task.get("created_at"),
                "updated_at": max(int(task.get("completed_at") or 0), int(task.get("started_at") or 0), int(task.get("created_at") or 0)),
            })

        edges = []
        for link in index["links"]:
            parent, child = link["parent_id"], link["child_id"]
            if parent not in task_ids or child not in task_ids:
                continue
            edges.append({
                "from": f"task:{parent}",
                "to": f"task:{child}",
                "label": "handoff",
                "kind": "handoff",
                "active": index["liveness"].get(child) == "live" or index["liveness"].get(parent) == "live",
            })

        return {
            "board": board,
            "view": view,
            "project": _public_project(project),
            "projects": _public_projects(visible),
            "nodes": nodes,
            "edges": edges,
            "live_filter": live_filter,
            "now": now,
        }


def _latest_activity(task: dict[str, Any], events: list[dict[str, Any]], runs: list[dict[str, Any]]) -> str:
    active_run = next((run for run in reversed(runs) if not run.get("ended_at")), None)
    if active_run:
        return f"{active_run.get('profile') or task.get('assignee') or 'worker'} выполняет задачу"
    if events:
        kind = events[-1].get("kind") or "event"
        friendly = {
            "completed": "Завершил свой шаг",
            "done": "Завершил свой шаг",
            "created": "Получил задачу",
            "claimed": "Взял задачу в работу",
            "started": "Начал работу",
            "blocked": "Ждет разблокировки",
            "archived": "Карточка закрыта",
        }.get(str(kind).lower())
        return friendly or "Обновил состояние"
    status = task.get("status") or "todo"
    if status == "running":
        return f"{task.get('assignee') or 'worker'} выполняет задачу"
    return f"Статус: {status}"


def _public_project(project: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in project.items() if key != "task_ids"}


def _public_projects(projects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_public_project(project) for project in projects]


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store" if self.path.startswith("/api/") else "no-cache")
        super().end_headers()

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/live/health":
            self._json({"ok": True, "now": _now()})
            return
        if parsed.path == "/api/live/projects":
            query = parse_qs(parsed.query)
            board = query.get("board", [DEFAULT_BOARD])[0] or DEFAULT_BOARD
            project_id = query.get("project_id", [None])[0]
            view = query.get("view", ["active"])[0]
            include_codex_sessions = (query.get("include_codex_sessions", ["0"])[0] or "0").lower() in {"1", "true", "yes"}
            try:
                self._json(project_graph(board, project_id, view=view, include_codex_sessions=include_codex_sessions))
            except Exception as exc:
                self._json({"error": html.escape(str(exc)), "board": board, "projects": [], "nodes": [], "edges": [], "now": _now()}, status=500)
            return
        if parsed.path == "/api/live/log":
            query = parse_qs(parsed.query)
            board = query.get("board", [DEFAULT_BOARD])[0] or DEFAULT_BOARD
            task_id = query.get("task_id", [""])[0]
            tail = int(query.get("tail", ["120000"])[0] or 120000)
            if not re.fullmatch(r"[A-Za-z0-9_.:-]+", task_id):
                self._json({"error": "bad task_id"}, status=400)
                return
            self._json(_read_log(board, task_id, tail))
            return
        if parsed.path == "/":
            self.path = "/index.html"
        super().do_GET()

    def _json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    host = os.environ.get("HERMES_SITE_HOST", "127.0.0.1")
    port = int(os.environ.get("HERMES_SITE_PORT", "8787"))
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"Hermes Control Constellation: http://{host}:{port}/")
    print("Live project API: /api/live/projects?board=overlord")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
