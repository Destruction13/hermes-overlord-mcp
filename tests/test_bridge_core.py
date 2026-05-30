from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from bridge.cli import build_parser
from bridge.core import BRIDGE_EVENT_PREFIX, HermesBridge


class BridgeCoreTests(unittest.TestCase):
    def test_submit_dry_run_is_root_only(self) -> None:
        bridge = HermesBridge(root="C:/AI/Hermes")
        payload = bridge.submit("Do the thing", dry_run=True)
        args = payload["command_args"]
        self.assertIn("create", args)
        self.assertNotIn("swarm", args)
        self.assertNotIn("--triage", args)
        self.assertIn("--created-by", args)
        self.assertIn("hermes-bridge", args)

    def test_bridge_event_comment_roundtrip(self) -> None:
        bridge = HermesBridge(root="C:/AI/Hermes")
        line = bridge.bridge_event("task_accepted", "t_123", profile="overlord", summary="accepted")
        self.assertTrue(line.startswith(BRIDGE_EVENT_PREFIX))
        events = bridge.parse_bridge_events([{"id": 7, "body": line, "created_at": 1}], [])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["type"], "task_accepted")
        self.assertEqual(events[0]["task_id"], "t_123")
        self.assertEqual(events[0]["profile"], "overlord")
        self.assertEqual(events[0]["evidence"], "task_comment")

    def test_parse_bridge_event_payload_from_task_event(self) -> None:
        bridge = HermesBridge(root="C:/AI/Hermes")
        events = bridge.parse_bridge_events(
            [],
            [
                {
                    "id": 3,
                    "kind": "bridge.final",
                    "payload": json.dumps({"type": "final", "task_id": "t_123"}),
                    "created_at": 2,
                }
            ],
        )
        self.assertEqual(events[0]["type"], "final")
        self.assertEqual(events[0]["evidence"], "task_event")

    def test_next_action_terminal(self) -> None:
        bridge = HermesBridge(root="C:/AI/Hermes")
        self.assertEqual(bridge.next_action("done", [], [], []), "finalize_to_user_and_pause_heartbeat")

    def test_next_action_waits_for_active_child(self) -> None:
        bridge = HermesBridge(root="C:/AI/Hermes")
        action = bridge.next_action("running", [{"status": "running"}], [], [])
        self.assertEqual(action, "wait_for_next_material_event")

    def test_heartbeat_prompt_mentions_exact_task(self) -> None:
        bridge = HermesBridge(root="C:/AI/Hermes")
        payload = bridge.heartbeat_prompt("t_123", board="overlord")
        self.assertEqual(payload["action"], "heartbeat_prompt")
        self.assertIn("t_123", payload["prompt"])
        self.assertIn("python -m bridge.cli report", payload["prompt"])

    def test_report_aggregates_child_tool_evidence_without_body_claims(self) -> None:
        bridge = HermesBridge(root="C:/AI/Hermes")
        snapshots = {
            "t_root": {
                "task": {"id": "t_root", "title": "root", "assignee": "overlord", "status": "running"},
                "children": [{"id": "t_child"}],
                "comments": [{"id": 1, "body": "prompt text mentions mcp_fake_prompt_only", "created_at": 1}],
                "events": [],
                "runs": [],
            },
            "t_child": {
                "task": {"id": "t_child", "title": "frontend", "assignee": "olfrontend", "status": "done"},
                "comments": [
                    {
                        "id": 2,
                        "body": '[worker:evidence] {"profile":"olfrontend","tools_or_mcp":["mcp_playwright_browser_navigate","kanban_show"],"artifact_path":"C:/AI/site/index.html","did":"Verified the route."}',
                        "created_at": 2,
                    }
                ],
                "events": [],
                "runs": [{"id": 9, "profile": "olfrontend", "status": "completed", "outcome": "completed"}],
            },
        }

        def fake_json_run(args, timeout=None, default=None):  # type: ignore[no-untyped-def]
            return snapshots[args[4]]

        def fake_log(task_id: str, board: str, tail_bytes: int = 40000) -> dict[str, object]:
            if task_id == "t_child":
                return {
                    "mcp_servers": {},
                    "mcp_tools_seen": ["mcp_shadcn_get_component"],
                    "tool_calls_seen": ["terminal"],
                    "material_log_lines": ["Tool call: terminal"],
                }
            return {"mcp_servers": {}, "mcp_tools_seen": [], "tool_calls_seen": [], "material_log_lines": []}

        bridge.json_run = fake_json_run  # type: ignore[method-assign]
        bridge.descendants_from_db = lambda *args, **kwargs: []  # type: ignore[method-assign]
        bridge.summarize_log = fake_log  # type: ignore[method-assign]
        report = bridge.report("t_root", board="overlord")

        child_signal = report["child_mcp_and_tools"][0]
        self.assertEqual(child_signal["task_id"], "t_child")
        self.assertIn("mcp_playwright_browser_navigate", child_signal["mcp_tools_seen"])
        self.assertIn("mcp_shadcn_get_component", child_signal["mcp_tools_seen"])
        self.assertIn("C:/AI/site/index.html", report["final_artifacts"])
        self.assertNotIn("mcp_fake_prompt_only", report["mcp_and_tools"]["mcp_tools_seen"])

    def test_report_recovers_child_ids_from_bridge_event_graph(self) -> None:
        bridge = HermesBridge(root="C:/AI/Hermes")
        snapshots = {
            "t_root": {
                "task": {"id": "t_root", "title": "root", "assignee": "overlord", "status": "running"},
                "children": [],
                "comments": [
                    {
                        "id": 1,
                        "body": BRIDGE_EVENT_PREFIX
                        + json.dumps(
                            {
                                "type": "child_created",
                                "task_id": "t_root",
                                "children": ["t_product", "t_frontend"],
                                "summary": "Created graph with t_product and t_frontend.",
                            }
                        ),
                        "created_at": 1,
                    }
                ],
                "events": [],
                "runs": [],
            },
            "t_product": {
                "task": {"id": "t_product", "title": "product", "assignee": "olproduct", "status": "done"},
                "comments": [],
                "events": [],
                "runs": [],
            },
            "t_frontend": {
                "task": {"id": "t_frontend", "title": "frontend", "assignee": "olfrontend", "status": "running"},
                "comments": [],
                "events": [],
                "runs": [],
            },
        }

        def fake_json_run(args, timeout=None, default=None):  # type: ignore[no-untyped-def]
            return snapshots[args[4]]

        bridge.json_run = fake_json_run  # type: ignore[method-assign]
        bridge.descendants_from_db = lambda *args, **kwargs: []  # type: ignore[method-assign]
        bridge.summarize_log = lambda *args, **kwargs: {"mcp_servers": {}, "mcp_tools_seen": [], "tool_calls_seen": [], "material_log_lines": []}  # type: ignore[method-assign]

        report = bridge.report("t_root", board="overlord")

        self.assertEqual(report["delegation"]["child_task_count"], 2)
        self.assertIn("olfrontend", report["delegation"]["profiles_seen"])
        self.assertEqual({child["id"] for child in report["delegation"]["children"]}, {"t_product", "t_frontend"})

    def test_board_flag_works_after_subcommand_for_powershell_wrapper(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["report", "--task-id", "t_123", "--board", "overlord"])
        self.assertEqual(args.board, "overlord")

    def test_dispatch_subcommand_exists_for_cli_fallback(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["dispatch", "--board", "overlord"])
        self.assertEqual(args.command, "dispatch")
        self.assertEqual(args.board, "overlord")

    def test_base_command_uses_explicit_cross_platform_python(self) -> None:
        with patch.dict(os.environ, {"HERMES_PYTHON": "/opt/hermes/bin/python", "HERMES_BRIDGE_PROFILE": "overlord"}, clear=False):
            bridge = HermesBridge(root="/opt/hermes")

            command = bridge.base_command()

            self.assertEqual(Path(command[0]).as_posix().replace("//", "/"), "/opt/hermes/bin/python")
            self.assertEqual(command[1:4], ["-m", "hermes_cli.main", "-p"])
            self.assertEqual(command[4], "overlord")

    def test_env_defaults_to_home_hermes_on_non_windows(self) -> None:
        with patch("platform.system", return_value="Linux"):
            with patch.dict(os.environ, {"HOME": "/home/tester", "USERPROFILE": "C:/Users/tester"}, clear=True):
                bridge = HermesBridge(root="/opt/hermes")

                self.assertTrue(bridge.env()["HERMES_HOME"].endswith(".hermes"))


if __name__ == "__main__":
    unittest.main()
