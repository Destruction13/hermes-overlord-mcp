from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_PATH = ROOT / "dashboard" / "serve-dashboard.py"


def load_dashboard_module():
    spec = importlib.util.spec_from_file_location("hermes_dashboard_server", DASHBOARD_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("dashboard module could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DashboardProjectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.hermes_root = self.root / "hermes"
        self.codex_home = self.root / "codex"
        self.board_dir = self.hermes_root / "kanban" / "boards" / "overlord"
        self.board_dir.mkdir(parents=True)
        self.codex_home.mkdir(parents=True)

        self.old_codex_home = os.environ.get("CODEX_HOME")
        os.environ["CODEX_HOME"] = str(self.codex_home)

        self.dashboard = load_dashboard_module()
        self.old_hermes_root = self.dashboard.HERMES_ROOT
        self.dashboard.HERMES_ROOT = self.hermes_root
        self.now = int(time.time())
        self.task_id = "t_12345678"
        self._create_db()
        self._create_codex_session()

    def tearDown(self) -> None:
        self.dashboard.HERMES_ROOT = self.old_hermes_root
        if self.old_codex_home is None:
            os.environ.pop("CODEX_HOME", None)
        else:
            os.environ["CODEX_HOME"] = self.old_codex_home
        self.temp.cleanup()

    def _create_db(self) -> None:
        conn = sqlite3.connect(self.board_dir / "kanban.db")
        try:
            conn.executescript(
                """
                CREATE TABLE tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    body TEXT,
                    status TEXT,
                    assignee TEXT,
                    session_id TEXT,
                    created_at INTEGER,
                    started_at INTEGER,
                    completed_at INTEGER,
                    claim_expires INTEGER,
                    last_heartbeat_at INTEGER,
                    current_run_id INTEGER,
                    worker_pid INTEGER,
                    claim_lock TEXT,
                    result TEXT,
                    workspace_path TEXT,
                    skills TEXT,
                    created_by TEXT,
                    idempotency_key TEXT,
                    priority INTEGER
                );
                CREATE TABLE task_links (parent_id TEXT, child_id TEXT);
                CREATE TABLE task_comments (id INTEGER PRIMARY KEY, task_id TEXT, author TEXT, body TEXT, created_at INTEGER);
                CREATE TABLE task_events (id INTEGER PRIMARY KEY, task_id TEXT, kind TEXT, payload TEXT, created_at INTEGER, run_id INTEGER);
                CREATE TABLE task_runs (
                    id INTEGER PRIMARY KEY,
                    task_id TEXT,
                    profile TEXT,
                    status TEXT,
                    outcome TEXT,
                    started_at INTEGER,
                    ended_at INTEGER,
                    last_heartbeat_at INTEGER,
                    claim_expires INTEGER,
                    claim_lock TEXT,
                    worker_pid INTEGER,
                    summary TEXT,
                    error TEXT,
                    metadata TEXT
                );
                """
            )
            conn.execute(
                """
                INSERT INTO tasks (
                    id, title, body, status, assignee, session_id, created_at, started_at,
                    completed_at, claim_expires, last_heartbeat_at, current_run_id,
                    worker_pid, claim_lock, result, workspace_path, skills, created_by,
                    idempotency_key, priority
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.task_id,
                    "Codex bridge handoff: dashboard regression",
                    "One native Hermes root task.",
                    "ready",
                    "overlord",
                    None,
                    self.now,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    "",
                    "C:\\AI\\Hermes",
                    json.dumps(["kanban-orchestrator"]),
                    "codex-bridge",
                    None,
                    0,
                ),
            )
            conn.execute(
                "INSERT INTO task_comments (task_id, author, body, created_at) VALUES (?, ?, ?, ?)",
                (self.task_id, "overlord", "BRIDGE_EVENT v1 {\"type\":\"task_accepted\"}", self.now),
            )
            conn.commit()
        finally:
            conn.close()

    def _create_codex_session(self) -> None:
        session_dir = self.codex_home / "sessions" / "2026" / "05" / "29"
        session_dir.mkdir(parents=True)
        session_id = "11111111-2222-3333-4444-555555555555"
        path = session_dir / f"rollout-{session_id}.jsonl"
        rows = [
            {
                "type": "session_meta",
                "timestamp": "2026-05-29T00:00:00Z",
                "payload": {"timestamp": "2026-05-29T00:00:00Z", "cwd": str(ROOT)},
            },
            {
                "type": "event",
                "timestamp": "2026-05-29T00:00:01Z",
                "payload": {"type": "user_message", "content": f"/hermes check {self.task_id}"},
            },
        ]
        path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
        os.utime(path, (self.now, self.now))

    def test_codex_sessions_are_opt_in(self) -> None:
        payload = self.dashboard.project_graph("overlord", view="active")

        self.assertEqual(payload["live_filter"]["codex_sessions"], 0)
        self.assertEqual(payload["project"]["id"], f"root:{self.task_id}")
        self.assertTrue(all(not item["id"].startswith("codex-session:") for item in payload["projects"]))

    def test_explicit_root_request_prefers_native_project(self) -> None:
        payload = self.dashboard.project_graph(
            "overlord",
            project_id=f"root:{self.task_id}",
            view="active",
            include_codex_sessions=True,
        )

        self.assertEqual(payload["project"]["id"], f"root:{self.task_id}")
        self.assertEqual(payload["nodes"][0]["task_id"], self.task_id)

    def test_tool_evidence_ignores_prompt_prose(self) -> None:
        text = "Use MCP and github later if needed.\nTool call: shell_command\nNo tool call happened for notion."

        evidence = self.dashboard._tool_evidence_text(text)

        self.assertIn("Tool call: shell_command", evidence)
        self.assertNotIn("Use MCP", evidence)
        self.assertNotIn("No tool call happened", evidence)


if __name__ == "__main__":
    unittest.main()
