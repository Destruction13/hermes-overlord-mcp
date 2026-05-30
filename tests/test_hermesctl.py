from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import hermesctl


class HermesCtlTests(unittest.TestCase):
    def test_redact_text_hides_secret_assignments(self) -> None:
        text = "api_key: sk-test-value\nAuthorization: Bearer abcdefghijklmnop\nnormal: value\n"

        redacted = hermesctl.redact_text(text)

        self.assertNotIn("sk-test-value", redacted)
        self.assertNotIn("abcdefghijklmnop", redacted)
        self.assertIn("normal: value", redacted)

    def test_mcp_config_shapes(self) -> None:
        root = Path("/opt/hermes")

        claude = hermesctl.build_mcp_config("claude-code", root=root, hermes_home_path=Path("/home/user/.hermes"))
        codex = hermesctl.build_mcp_config("codex", root=root, hermes_home_path=Path("/home/user/.hermes"))
        antigravity = hermesctl.build_mcp_config("antigravity", root=root, hermes_home_path=Path("/home/user/.hermes"))
        vscode = hermesctl.build_mcp_config("vscode", root=root, hermes_home_path=Path("/home/user/.hermes"))
        cursor = hermesctl.build_mcp_config("cursor", root=root, hermes_home_path=Path("/home/user/.hermes"))
        opencode = hermesctl.build_mcp_config("opencode", root=root, hermes_home_path=Path("/home/user/.hermes"))
        gemini = hermesctl.build_mcp_config("gemini", root=root, hermes_home_path=Path("/home/user/.hermes"))
        zed = hermesctl.build_mcp_config("zed", root=root, hermes_home_path=Path("/home/user/.hermes"))
        generic_http = hermesctl.build_mcp_config("generic", root=root, transport="streamable-http")

        self.assertIn("hermes-overlord", claude["mcpServers"])
        self.assertIn("hermes-overlord", codex["mcpServers"])
        self.assertIn("servers", antigravity)
        self.assertIn("hermes-overlord", antigravity["servers"])
        self.assertEqual(antigravity["servers"]["hermes-overlord"]["command"], "npx")
        self.assertIn("servers", vscode)
        self.assertIn("servers", cursor["mcp"])
        self.assertIn("mcp", opencode)
        self.assertEqual(opencode["mcp"]["hermes-overlord"]["command"][:2], ["npx", "-y"])
        self.assertEqual(gemini["mcpServers"]["hermes-overlord"]["env"]["HERMES_BRIDGE_CLIENT"], "gemini-cli")
        self.assertIn("context_servers", zed)
        self.assertEqual(zed["context_servers"]["hermes-overlord"]["command"]["path"], "npx")
        self.assertIn("streamable_http", generic_http)
        self.assertIn("serverUrl", generic_http["streamable_http"])

    def test_npx_configs_do_not_pin_package_cache_root(self) -> None:
        config = hermesctl.build_mcp_config("generic", root=Path("/opt/hermes"), package_name="github:Destruction13/hermes-overlord-mcp")
        env = config["mcpServers"]["hermes-overlord"]["env"]

        self.assertNotIn("HERMES_OVERLORD_ROOT", env)
        self.assertNotIn("HERMES_BRIDGE_ROOT", env)
        self.assertEqual(config["mcpServers"]["hermes-overlord"]["args"], ["-y", "github:Destruction13/hermes-overlord-mcp"])

    def test_add_mcp_shape_and_package_override(self) -> None:
        root = Path("/opt/hermes")

        add_mcp = hermesctl.build_add_mcp_config(
            "kiro",
            root=root,
            hermes_home_path=Path("/home/user/.hermes"),
            package_name="github:Destruction13/hermes-overlord-mcp",
        )

        self.assertEqual(add_mcp["name"], "hermes-overlord")
        self.assertEqual(add_mcp["command"], "npx")
        self.assertEqual(add_mcp["args"], ["-y", "github:Destruction13/hermes-overlord-mcp"])
        self.assertEqual(add_mcp["env"]["HERMES_BRIDGE_CLIENT"], "kiro")

    def test_install_guide_has_standard_and_client_specific_snippets(self) -> None:
        data = hermesctl.install_guide_data(client="all", package_name="github:Destruction13/hermes-overlord-mcp")
        markdown = hermesctl.install_guide_markdown(data)
        by_client = {item["client"]: item for item in data["clients"]}

        self.assertIn("mcpServers", data["standard_config"])
        self.assertIn("claude-code", by_client)
        self.assertIn("codex", by_client)
        self.assertIn("zed", by_client)
        self.assertIn("claude mcp add hermes-overlord", by_client["claude-code"]["primary"]["command"])
        self.assertIn("codex mcp add hermes-overlord", by_client["codex"]["primary"]["command"])
        self.assertIn("context_servers", by_client["zed"]["config"])
        self.assertIn("<summary>Claude Code</summary>", markdown)
        self.assertIn("## Requirements", markdown)

    def test_default_package_name_uses_npx_package_reference(self) -> None:
        with mock.patch.dict(os.environ, {"npm_config_package": "github:Destruction13/hermes-overlord-mcp"}, clear=False):
            self.assertEqual(hermesctl.default_package_name(), "github:Destruction13/hermes-overlord-mcp")

    def test_package_ref_from_npx_lock_detects_git_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "node_modules" / "@destruction13" / "hermes-overlord-mcp"
            root.mkdir(parents=True)
            lock = root.parent.parent / ".package-lock.json"
            lock.write_text(
                json.dumps(
                    {
                        "packages": {
                            "node_modules/@destruction13/hermes-overlord-mcp": {
                                "resolved": "git+ssh://git@github.com/Destruction13/hermes-overlord-mcp.git#abc123"
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                hermesctl.package_ref_from_npx_lock(root),
                "github:Destruction13/hermes-overlord-mcp",
            )

    def test_init_install_writes_home_templates_and_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            root = temp_path / "root"
            profile = root / "dist" / "hermes-portable" / "runtime" / "profiles" / "overlord"
            profile.mkdir(parents=True)
            (profile / "SOUL.md").write_text("portable soul\n", encoding="utf-8")
            home = temp_path / "home"

            result = hermesctl.init_install(client="generic", home=home, root=root)

            self.assertTrue((home / "profiles" / "overlord" / "SOUL.md").exists())
            self.assertTrue(Path(result["config_file"]).exists())
            self.assertEqual(result["display_name"], "Hermes Overlord")
            self.assertIn("mcpServers", result["config"])

    def test_cleanup_classification(self) -> None:
        root = Path("C:/repo")

        self.assertEqual(hermesctl.classify_cleanup_path(root / "node_modules", root)[0], "local-dependency-cache")
        self.assertEqual(hermesctl.classify_cleanup_path(root / "scratch" / "smoke", root)[0], "temporary-workspace")
        self.assertEqual(hermesctl.classify_cleanup_path(root / "bridge" / "__pycache__" / "core.pyc", root)[0], "generated-cache")
        self.assertIsNone(hermesctl.classify_cleanup_path(root / "bridge" / "core.py", root))

    def test_parse_mcp_inventory(self) -> None:
        inventory = hermesctl.parse_mcp_inventory(
            """
mcp_servers:
  github:
    command: npx
    args: []
    enabled: true
  notion:
    url: https://mcp.notion.com/mcp
    headers:
      Authorization: Bearer ${NOTION_TOKEN}
"""
        )

        by_name = {item["name"]: item for item in inventory}
        self.assertEqual(by_name["github"]["transport"], "stdio")
        self.assertEqual(by_name["notion"]["transport"], "streamable_http")
        self.assertEqual(by_name["notion"]["env"], ["NOTION_TOKEN"])

    def test_package_sanitizes_profiles_and_excludes_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            fake_home = temp_path / "home"
            profile = fake_home / "profiles" / "overlord"
            profile.mkdir(parents=True)
            (fake_home / ".env").write_text("OMNIROUTE_API_KEY=super-secret\n", encoding="utf-8")
            (profile / ".env").write_text("GITHUB_TOKEN=another-secret\n", encoding="utf-8")
            (profile / "SOUL.md").write_text("Use tools honestly.\n", encoding="utf-8")
            (profile / "config.yaml").write_text(
                """
providers:
  x:
    api_key: should-not-ship
mcp_servers:
  github:
    command: npx
    headers:
      Authorization: Bearer ${GITHUB_TOKEN}
""",
                encoding="utf-8",
            )
            out = temp_path / "portable"

            manifest = hermesctl.package(out, home=fake_home)
            findings = hermesctl.scan_package_for_secret_risk(out)
            config_text = (out / "runtime" / "profiles" / "overlord" / "config.template.yaml").read_text(encoding="utf-8")
            env_keys = (out / "runtime" / "profiles" / "overlord" / "ENV_KEYS.txt").read_text(encoding="utf-8")

            self.assertIn("overlord", manifest["included"]["profiles"])
            self.assertNotIn("should-not-ship", config_text)
            self.assertNotIn("super-secret", env_keys)
            self.assertIn("OMNIROUTE_API_KEY", env_keys)
            self.assertEqual(findings, [])
            json.loads((out / "client-configs" / "antigravity.stdio.json").read_text(encoding="utf-8"))
            generic_config = json.loads((out / "client-configs" / "generic.stdio.json").read_text(encoding="utf-8"))
            add_mcp = json.loads((out / "client-configs" / "kiro.add-mcp.json").read_text(encoding="utf-8"))
            install_doc = (out / "client-configs" / "INSTALL.md").read_text(encoding="utf-8")
            self.assertEqual(generic_config["mcpServers"]["hermes-overlord"]["args"], ["-y", "github:Destruction13/hermes-overlord-mcp"])
            self.assertEqual(add_mcp["name"], "hermes-overlord")
            self.assertEqual(add_mcp["command"], "npx")
            self.assertIn("Client-specific configuration", install_doc)


if __name__ == "__main__":
    unittest.main()
