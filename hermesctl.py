from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PACKAGE_DIR = ROOT / "dist" / "hermes-portable"
DEFAULT_BOARD = "overlord"
DEFAULT_PROFILE = "overlord"
DEFAULT_HTTP_URL = "http://127.0.0.1:8765/mcp"
MCP_SERVER_ID = "hermes-overlord"
MCP_DISPLAY_NAME = "Hermes Overlord"
NPM_PACKAGE_NAME = "@destruction13/hermes-overlord-mcp"
SUPPORTED_CLIENTS = ("generic", "vscode", "cursor", "kilo", "kiro", "windsurf", "opencode", "codex", "antigravity")
ADD_MCP_CLIENTS = {"vscode", "cursor", "kiro", "antigravity"}
TOP_LEVEL_SERVERS_CLIENTS = {"kiro", "antigravity"}
PROFILE_EXPORT_RE = re.compile(r"^(overlord|ol[A-Za-z0-9_-]+)$")
SECRET_KEY_RE = re.compile(r"(?i)(api[_-]?key|token|secret|password|cookie|authorization|client[_-]?secret|refresh[_-]?token)")
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?im)^(?P<prefix>\s*[-\w.]*?(?:api[_-]?key|token|secret|password|cookie|authorization|client[_-]?secret|refresh[_-]?token)[-\w.]*\s*[:=]\s*)(?P<value>.+?)\s*$"
)
ENV_REF_RE = re.compile(r"\$\{([A-Z0-9_]+)\}")

SOURCE_FILES = [
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "package.json",
    "package-lock.json",
    "hermesctl.ps1",
    "hermesctl.sh",
    "bridge.ps1",
    "codex-hermes.ps1",
    "overlord.ps1",
    "overlord-dashboard.ps1",
    "overlord-kanban-create.ps1",
    "hermes-site.ps1",
    "watch-hermes.ps1",
    "ensure-obsidian.ps1",
    "storybook-enable.ps1",
    "telegram-connect.ps1",
]

SOURCE_DIRS = [
    "bin",
    "bridge",
    "mcp",
    "tests",
]

DASHBOARD_FILES = [
    "README.md",
    "CHANGELOG.md",
    "index.html",
    "styles.css",
    "app.js",
    "data.js",
    "generate-dashboard-data.py",
    "serve-dashboard.py",
    "hermes-preset-defaults.json",
]

DOC_FILES = [
    "HERMES_USER_GUIDE.md",
    "HERMES_MCP_HEALTH.md",
    "CODEX_HERMES_BRIDGE.md",
    "CODEX_HERMES_NATIVE_LIVE_TEST.md",
]

KEEP_SKILLS = [
    "acquire-codebase-knowledge",
    "audit-integrity",
    "mcp-builder",
]

HIDDEN_SKILL_MIRRORS = {
    ".adal",
    ".agents",
    ".aider-desk",
    ".augment",
    ".bob",
    ".claude",
    ".codeartsdoer",
    ".codebuddy",
    ".codemaker",
    ".codestudio",
    ".commandcode",
    ".continue",
    ".cortex",
    ".crush",
    ".devin",
    ".factory",
    ".forge",
    ".goose",
    ".hermes",
    ".iflow",
    ".junie",
    ".kilocode",
    ".kiro",
    ".kode",
    ".mcpjam",
    ".mux",
    ".neovate",
    ".openhands",
    ".pi",
    ".pochi",
    ".qoder",
    ".qwen",
    ".roo",
    ".rovodev",
    ".tabnine",
    ".trae",
    ".vibe",
    ".windsurf",
    ".zencoder",
}


def hermes_home() -> Path:
    explicit = os.environ.get("HERMES_HOME")
    if explicit:
        return Path(explicit).expanduser()
    if platform.system().lower().startswith("win") and os.environ.get("LOCALAPPDATA"):
        return Path(os.environ["LOCALAPPDATA"]) / "hermes"
    return Path.home() / ".hermes"


def rel(path: Path, root: Path = ROOT) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def copy_tree_filtered(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    for item in src.rglob("*"):
        if item.is_dir():
            continue
        parts = set(item.relative_to(src).parts)
        if "__pycache__" in parts or item.suffix == ".pyc":
            continue
        if item.name.startswith(".") and item.name not in {".gitkeep"}:
            continue
        copy_file(item, dst / item.relative_to(src))


def redact_text(text: str) -> str:
    redacted = text
    for key, value in os.environ.items():
        if value and SECRET_KEY_RE.search(key):
            redacted = redacted.replace(value, "<redacted>")
    redacted = SECRET_ASSIGNMENT_RE.sub(lambda m: f"{m.group('prefix')}<set via environment>", redacted)
    redacted = re.sub(r"Bearer\s+[A-Za-z0-9._\-+/=]+", "Bearer <set via environment>", redacted)
    redacted = re.sub(r"Token\s+[A-Za-z0-9._\-+/=]+", "Token <set via environment>", redacted)
    redacted = re.sub(re.escape(str(hermes_home())), "${HERMES_HOME}", redacted, flags=re.IGNORECASE)
    if os.environ.get("USERPROFILE"):
        redacted = re.sub(re.escape(os.environ["USERPROFILE"]), "${USER_HOME}", redacted, flags=re.IGNORECASE)
    redacted = redacted.replace("C:\\AI", "${HERMES_WORKSPACE_ROOT}")
    redacted = redacted.replace("C:/AI", "${HERMES_WORKSPACE_ROOT}")
    redacted = re.sub(r"https://[^\s'\"]*tail[0-9a-z.-]*/v1", "${HERMES_MODEL_BASE_URL}", redacted, flags=re.IGNORECASE)
    return redacted


def env_keys_from_file(path: Path) -> list[str]:
    if not path.exists():
        return []
    keys: list[str] = []
    for line in read_text(path).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key = stripped.split("=", 1)[0].strip()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            keys.append(key)
    return sorted(set(keys))


def env_refs_from_text(text: str) -> list[str]:
    return sorted(set(ENV_REF_RE.findall(text)))


def profile_dirs(home: Path | None = None) -> list[Path]:
    base = (home or hermes_home()) / "profiles"
    if not base.exists():
        return []
    return sorted(path for path in base.iterdir() if path.is_dir() and PROFILE_EXPORT_RE.match(path.name))


def parse_mcp_inventory(config_text: str) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    in_block = False
    current: dict[str, Any] | None = None
    for line in config_text.splitlines():
        if line.startswith("mcp_servers:"):
            in_block = True
            continue
        if in_block and line and not line.startswith(" "):
            break
        if not in_block:
            continue
        match = re.match(r"^\s{2}([A-Za-z0-9_.-]+):\s*$", line)
        if match:
            current = {"name": match.group(1), "transport": "unknown", "enabled": True, "env": []}
            inventory.append(current)
            continue
        if current is None:
            continue
        stripped = line.strip()
        if stripped.startswith("url:"):
            current["transport"] = "streamable_http"
        elif stripped.startswith("command:"):
            current["transport"] = "stdio"
        elif stripped.startswith("enabled:"):
            current["enabled"] = stripped.split(":", 1)[1].strip().lower() != "false"
        for key in env_refs_from_text(line):
            if key not in current["env"]:
                current["env"].append(key)
    for item in inventory:
        item["env"] = sorted(item["env"])
    return inventory


def export_profiles(out_dir: Path, home: Path | None = None) -> list[dict[str, Any]]:
    exported: list[dict[str, Any]] = []
    global_env_keys = env_keys_from_file((home or hermes_home()) / ".env")
    for profile in profile_dirs(home):
        profile_out = out_dir / "runtime" / "profiles" / profile.name
        profile_out.mkdir(parents=True, exist_ok=True)
        env_keys = sorted(set(global_env_keys + env_keys_from_file(profile / ".env")))
        inventory: list[dict[str, Any]] = []
        for file_name in ("SOUL.md", "profile.yaml", "shell-hooks-allowlist.json"):
            src = profile / file_name
            if src.exists():
                write_text(profile_out / file_name, redact_text(read_text(src)))
        config = profile / "config.yaml"
        if config.exists():
            config_text = read_text(config)
            write_text(profile_out / "config.template.yaml", redact_text(config_text))
            inventory = parse_mcp_inventory(config_text)
            for item in inventory:
                env_keys.extend(item.get("env") or [])
        write_text(profile_out / "ENV_KEYS.txt", "\n".join(sorted(set(env_keys))) + ("\n" if env_keys else ""))
        exported.append(
            {
                "profile": profile.name,
                "files": sorted(path.name for path in profile_out.iterdir() if path.is_file()),
                "env_keys": sorted(set(env_keys)),
                "mcp_servers": inventory,
            }
        )
    return exported


def python_executable_for_config() -> str:
    return os.environ.get("HERMES_PYTHON") or "python"


def default_package_name() -> str:
    explicit = os.environ.get("HERMES_MCP_PACKAGE_NAME")
    if explicit:
        return explicit
    npx_package = os.environ.get("npm_config_package")
    if npx_package:
        return npx_package
    return NPM_PACKAGE_NAME


def default_workspace() -> str:
    return f"dir:{Path.home()}"


def server_env(client: str = "generic", hermes_home_path: Path | None = None, workspace: str | None = None, root: Path = ROOT) -> dict[str, str]:
    return {
        "HERMES_HOME": str(hermes_home_path or hermes_home()),
        "HERMES_OVERLORD_ROOT": str(root),
        "HERMES_BRIDGE_ROOT": str(root),
        "HERMES_BRIDGE_PROFILE": DEFAULT_PROFILE,
        "HERMES_BRIDGE_BOARD": DEFAULT_BOARD,
        "HERMES_BRIDGE_WORKSPACE": workspace or default_workspace(),
        "HERMES_BRIDGE_CLIENT": client,
    }


def stdio_server_config(
    root: Path = ROOT,
    client: str = "generic",
    package_name: str = NPM_PACKAGE_NAME,
    launcher: str = "npx",
    hermes_home_path: Path | None = None,
    workspace: str | None = None,
) -> dict[str, Any]:
    env = server_env(client=client, hermes_home_path=hermes_home_path, workspace=workspace, root=root)
    if launcher == "python":
        return {
            "command": python_executable_for_config(),
            "args": [str(root / "mcp" / "hermes_overlord_mcp.py")],
            "env": {**env, "HERMES_OVERLORD_MCP_TRANSPORT": "stdio"},
        }
    if launcher == "node":
        return {"command": "node", "args": [str(root / "bin" / "hermes-overlord-mcp.js")], "env": env}
    return {"command": "npx", "args": ["-y", package_name], "env": env}


def http_server_config(http_url: str = DEFAULT_HTTP_URL, client: str = "generic", hermes_home_path: Path | None = None, workspace: str | None = None, root: Path = ROOT) -> dict[str, Any]:
    return {"serverUrl": http_url, "url": http_url, "env": server_env(client=client, hermes_home_path=hermes_home_path, workspace=workspace, root=root)}


def build_mcp_config(
    client: str,
    root: Path = ROOT,
    transport: str = "stdio",
    http_url: str = DEFAULT_HTTP_URL,
    package_name: str = NPM_PACKAGE_NAME,
    launcher: str = "npx",
    hermes_home_path: Path | None = None,
    workspace: str | None = None,
) -> dict[str, Any]:
    if client not in SUPPORTED_CLIENTS:
        raise ValueError(f"unsupported client: {client}")
    env = {
        "HERMES_OVERLORD_ROOT": str(root),
        "HERMES_BRIDGE_ROOT": str(root),
        "HERMES_BRIDGE_PROFILE": DEFAULT_PROFILE,
        "HERMES_BRIDGE_BOARD": DEFAULT_BOARD,
        "HERMES_BRIDGE_WORKSPACE": workspace or default_workspace(),
    }
    stdio = stdio_server_config(root=root, client=client, package_name=package_name, launcher=launcher, hermes_home_path=hermes_home_path, workspace=workspace)
    http = http_server_config(http_url=http_url, client=client, hermes_home_path=hermes_home_path, workspace=workspace, root=root)
    if transport in {"http", "streamable-http", "streamable_http"}:
        server = http
    else:
        server = stdio
    if client == "generic":
        return {
            "name": MCP_SERVER_ID,
            "displayName": MCP_DISPLAY_NAME,
            "mcpServers": {MCP_SERVER_ID: server},
            "stdio": stdio,
            "streamable_http": http,
        }
    if client == "vscode":
        vscode_server = {"type": "stdio", **server} if transport == "stdio" else {"type": "http", "url": http_url, "env": http["env"]}
        return {"servers": {MCP_SERVER_ID: vscode_server}}
    if client == "cursor":
        return {"mcp": {"servers": {MCP_SERVER_ID: server}}}
    if client == "opencode":
        if transport == "stdio":
            return {
                "mcp": {
                    MCP_SERVER_ID: {
                        "type": "local",
                        "command": [server["command"], *server.get("args", [])],
                        "environment": server.get("env", {}),
                        "enabled": True,
                    }
                }
            }
        return {"mcp": {MCP_SERVER_ID: {"type": "remote", "url": http_url, "enabled": True}}}
    if client in TOP_LEVEL_SERVERS_CLIENTS:
        return {"servers": {MCP_SERVER_ID: server}}
    return {"mcpServers": {MCP_SERVER_ID: server}}


def build_add_mcp_config(
    client: str,
    root: Path = ROOT,
    transport: str = "stdio",
    http_url: str = DEFAULT_HTTP_URL,
    package_name: str = NPM_PACKAGE_NAME,
    launcher: str = "npx",
    hermes_home_path: Path | None = None,
    workspace: str | None = None,
) -> dict[str, Any]:
    if transport in {"http", "streamable-http", "streamable_http"}:
        http = http_server_config(http_url=http_url, client=client, hermes_home_path=hermes_home_path, workspace=workspace, root=root)
        return {"name": MCP_SERVER_ID, "serverUrl": http["serverUrl"], "env": http["env"]}
    stdio = stdio_server_config(root=root, client=client, package_name=package_name, launcher=launcher, hermes_home_path=hermes_home_path, workspace=workspace)
    return {"name": MCP_SERVER_ID, **stdio}


def write_client_configs(out_dir: Path, root: Path) -> None:
    config_dir = out_dir / "client-configs"
    for client in SUPPORTED_CLIENTS:
        write_text(
            config_dir / f"{client}.stdio.json",
            json.dumps(
                build_mcp_config(client, root=root, hermes_home_path=Path("${HERMES_HOME}"), workspace="dir:${HERMES_WORKSPACE_ROOT}"),
                ensure_ascii=False,
                indent=2,
            ),
        )
        if client in ADD_MCP_CLIENTS:
            write_text(
                config_dir / f"{client}.add-mcp.json",
                json.dumps(
                    build_add_mcp_config(client, root=root, hermes_home_path=Path("${HERMES_HOME}"), workspace="dir:${HERMES_WORKSPACE_ROOT}"),
                    ensure_ascii=False,
                    indent=2,
                ),
            )
        write_text(
            config_dir / f"{client}.http.json",
            json.dumps(
                build_mcp_config(
                    client,
                    root=root,
                    transport="streamable-http",
                    hermes_home_path=Path("${HERMES_HOME}"),
                    workspace="dir:${HERMES_WORKSPACE_ROOT}",
                ),
                ensure_ascii=False,
                indent=2,
            ),
        )
    plugin_dir = config_dir / "antigravity-plugin"
    write_text(
        plugin_dir / "plugin.json",
        json.dumps(
            {
                "name": MCP_SERVER_ID,
                "displayName": MCP_DISPLAY_NAME,
                "description": "Portable Hermes Overlord MCP bridge for any MCP-compatible client.",
                "version": "0.1.0",
            },
            ensure_ascii=False,
            indent=2,
        ),
    )
    write_text(
        plugin_dir / "mcp_config.json",
        json.dumps(
            build_mcp_config("antigravity", root=root, hermes_home_path=Path("${HERMES_HOME}"), workspace="dir:${HERMES_WORKSPACE_ROOT}"),
            ensure_ascii=False,
            indent=2,
        ),
    )
    write_text(
        plugin_dir / "AGENT.md",
        "Use `hermes_submit_task` for durable Hermes execution and `hermes_task_report` for progress. "
        "The MCP client is only the gateway; Hermes owns routing, specialists, tools, review, and synthesis.\n",
    )


def package(out_dir: Path = PACKAGE_DIR, home: Path | None = None) -> dict[str, Any]:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    source_out = out_dir / "source"
    for file_name in SOURCE_FILES:
        src = ROOT / file_name
        if src.exists():
            copy_file(src, source_out / file_name)
    copy_file(ROOT / "hermesctl.py", source_out / "hermesctl.py")
    for dir_name in SOURCE_DIRS:
        copy_tree_filtered(ROOT / dir_name, source_out / dir_name)
    dashboard_out = source_out / "dashboard"
    for file_name in DASHBOARD_FILES:
        src = ROOT / "dashboard" / file_name
        if src.exists():
            copy_file(src, dashboard_out / file_name)
    docs_out = out_dir / "docs"
    for file_name in DOC_FILES:
        src = ROOT / "docs" / file_name
        if src.exists():
            copy_file(src, docs_out / file_name)
    if (ROOT / "docs" / "distribution").exists():
        copy_tree_filtered(ROOT / "docs" / "distribution", docs_out / "distribution")
    if (ROOT / "docs" / "codebase").exists():
        copy_tree_filtered(ROOT / "docs" / "codebase", docs_out / "codebase")
    skills_out = out_dir / "skills"
    for skill in KEEP_SKILLS:
        src = ROOT / "skills" / skill
        if src.exists():
            copy_tree_filtered(src, skills_out / skill)

    profiles = export_profiles(out_dir, home=home)
    write_client_configs(out_dir, root=Path("${HERMES_ROOT}"))

    manifest = {
        "schema_version": 1,
        "created_at": int(time.time()),
        "package": "hermes-portable-clean-template",
        "source_root": str(ROOT),
        "included": {
            "source_files": SOURCE_FILES + ["hermesctl.py"],
            "source_dirs": SOURCE_DIRS,
            "dashboard_files": DASHBOARD_FILES,
            "docs": DOC_FILES + ["docs/distribution", "docs/codebase"],
            "skills": KEEP_SKILLS,
            "profiles": [item["profile"] for item in profiles],
        },
        "excluded": [
            ".env/auth/token files",
            "Kanban databases/history/log tails",
            "sessions and local memories",
            "node_modules and tool virtualenvs",
            "scratch workspaces and smoke-test artifacts",
            "__pycache__, *.pyc, backups, generated screenshots, old external handoff snapshots",
        ],
        "profiles": profiles,
    }
    write_text(out_dir / "MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return manifest


def copy_template_tree(src: Path, dst: Path, force: bool = False) -> list[str]:
    copied: list[str] = []
    if not src.exists():
        return copied
    for item in src.rglob("*"):
        if item.is_dir():
            continue
        target = dst / item.relative_to(src)
        if target.exists() and not force:
            continue
        copy_file(item, target)
        copied.append(rel(target, dst))
    return copied


def portable_template_root(root: Path = ROOT) -> Path:
    direct = root / "dist" / "hermes-portable"
    if direct.exists():
        return direct
    parent = root.parent
    if parent.name == "source" and (parent.parent / "runtime").exists():
        return parent.parent
    return direct


def init_install(
    client: str = "generic",
    home: Path | None = None,
    root: Path = ROOT,
    force: bool = False,
    transport: str = "stdio",
    package_name: str = NPM_PACKAGE_NAME,
    launcher: str = "npx",
    workspace: str | None = None,
    http_url: str = DEFAULT_HTTP_URL,
    out: Path | None = None,
) -> dict[str, Any]:
    if client not in SUPPORTED_CLIENTS:
        raise ValueError(f"unsupported client: {client}")
    target_home = (home or hermes_home()).expanduser()
    target_home.mkdir(parents=True, exist_ok=True)
    template = portable_template_root(root)
    copied_profiles = copy_template_tree(template / "runtime" / "profiles", target_home / "profiles", force=force)
    copied_skills = copy_template_tree(template / "skills", target_home / "skills", force=force)
    config = build_mcp_config(
        client,
        root=root,
        transport=transport,
        http_url=http_url,
        package_name=package_name,
        launcher=launcher,
        hermes_home_path=target_home,
        workspace=workspace,
    )
    config_dir = target_home / "client-configs"
    config_file = out or config_dir / f"{client}.{transport}.json"
    write_text(config_file, json.dumps(config, ensure_ascii=False, indent=2))
    return {
        "schema_version": 1,
        "ok": True,
        "action": "init",
        "client": client,
        "server_id": MCP_SERVER_ID,
        "display_name": MCP_DISPLAY_NAME,
        "hermes_home": str(target_home),
        "template_root": str(template),
        "config_file": str(config_file),
        "copied": {"profiles": len(copied_profiles), "skills": len(copied_skills)},
        "config": config,
        "next": [
            f"Add {config_file} to your MCP-compatible client, or copy the JSON snippet from this output.",
            f"Run: npx -y {package_name} doctor",
        ],
    }


def path_size(path: Path) -> int:
    if path.is_file() or path.is_symlink():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    total = 0
    for child in path.rglob("*"):
        if child.is_file():
            try:
                total += child.stat().st_size
            except OSError:
                pass
    return total


def classify_cleanup_path(path: Path, root: Path = ROOT) -> tuple[str, str] | None:
    name = path.name
    relative = rel(path, root)
    parts = set(Path(relative).parts)
    if name == "dist":
        return None
    if "__pycache__" in parts or name.endswith(".pyc"):
        return "generated-cache", "Python bytecode/cache"
    if name in {"node_modules", ".tools", ".codegraph", ".codegraphcontext"}:
        return "local-dependency-cache", "Local dependency/tool cache, reproducible or non-shareable"
    if name == "scratch" or relative.startswith("scratch/"):
        return "temporary-workspace", "Scratch and smoke-test workspaces are not part of the portable template"
    if name in {".oauth-refresh", ".playwright-mcp"} or relative.startswith(".oauth-refresh/") or relative.startswith(".playwright-mcp/"):
        return "local-log-cache", "OAuth refresh or Playwright MCP logs"
    if name == ".codex" or relative.startswith(".codex/"):
        return "local-client-artifact", "Local Codex screenshots/session-adjacent artifacts"
    if name in HIDDEN_SKILL_MIRRORS:
        return "duplicate-skill-mirror", "Duplicated agent skill mirror; canonical skills are exported from skills/"
    if name in {"docs/external-handoff", "external-handoff"} or relative.startswith("docs/external-handoff/"):
        return "old-diagnostic-handoff", "Old diagnostic handoff snapshot replaced by docs/distribution"
    if re.search(r"\.(bak|backup)(?:[-.].*)?$", name, re.IGNORECASE):
        return "backup-file", "Backup files are not part of the clean template"
    if name.endswith((".tgz", ".zip", ".7z")):
        return "archive-artifact", "Generated or downloaded archive artifact"
    if name == "NUL":
        return "invalid-temp-file", "Windows NUL artifact"
    if path.suffix.lower() in {".log", ".tmp", ".temp"}:
        return "log-or-temp-file", "Log/temp file"
    if path.parent.name == "screenshots" and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
        return "generated-screenshot", "Generated dashboard/test screenshot"
    if path.parent == root / "dashboard" and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".json"} and name != "hermes-preset-defaults.json":
        return "generated-dashboard-artifact", "Dashboard preview/smoke artifact"
    return None


def cleanup_candidates(root: Path = ROOT) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for current, dirs, files in os.walk(root):
        current_path = Path(current)
        if current_path == root / "dist":
            dirs[:] = []
            continue

        kept_dirs: list[str] = []
        for dirname in dirs:
            path = current_path / dirname
            classification = classify_cleanup_path(path, root)
            if classification:
                category, reason = classification
                candidates.append({"path": rel(path, root), "category": category, "reason": reason, "size_bytes": path_size(path), "action": "quarantine"})
            else:
                kept_dirs.append(dirname)
        dirs[:] = kept_dirs

        for filename in files:
            path = current_path / filename
            classification = classify_cleanup_path(path, root)
            if classification:
                category, reason = classification
                candidates.append({"path": rel(path, root), "category": category, "reason": reason, "size_bytes": path_size(path), "action": "quarantine"})
    return sorted(candidates, key=lambda item: item["path"])


def quarantine_history(root: Path = ROOT) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    for qdir in sorted(root.parent.glob("Hermes-quarantine-*")):
        if not qdir.is_dir():
            continue
        for current, dirs, files in os.walk(qdir):
            current_path = Path(current)
            kept_dirs: list[str] = []
            for dirname in dirs:
                path = current_path / dirname
                relative = path.relative_to(qdir)
                classification = classify_cleanup_path(root / relative, root)
                if classification:
                    category, reason = classification
                    history.append(
                        {
                            "path": relative.as_posix(),
                            "category": category,
                            "reason": reason,
                            "size_bytes": path_size(path),
                            "action": "quarantined",
                            "quarantine_dir": str(qdir),
                            "quarantine_path": str(path),
                        }
                    )
                else:
                    kept_dirs.append(dirname)
            dirs[:] = kept_dirs
            for filename in files:
                if filename == "cleanup-manifest.json":
                    continue
                path = current_path / filename
                relative = path.relative_to(qdir)
                classification = classify_cleanup_path(root / relative, root)
                if not classification:
                    continue
                category, reason = classification
                history.append(
                    {
                        "path": relative.as_posix(),
                        "category": category,
                        "reason": reason,
                        "size_bytes": path_size(path),
                        "action": "quarantined",
                        "quarantine_dir": str(qdir),
                        "quarantine_path": str(path),
                    }
                )
    deduped: dict[tuple[str, str], dict[str, Any]] = {}
    for item in history:
        deduped[(item["quarantine_path"], item["path"])] = item
    return sorted(deduped.values(), key=lambda item: (item["quarantine_dir"], item["path"]))


def verify_target_within(path: Path, base: Path) -> Path:
    resolved = path.resolve()
    base_resolved = base.resolve()
    if resolved != base_resolved and base_resolved not in resolved.parents:
        raise ValueError(f"target {resolved} is outside {base_resolved}")
    return resolved


def move_path_to_quarantine(src: Path, dst: Path) -> dict[str, Any]:
    if dst.exists():
        dst = dst.with_name(f"{dst.name}.{int(time.time())}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        try:
            src.rename(dst)
            return {"result": "moved", "quarantine_path": str(dst)}
        except OSError as rename_error:
            skipped: list[str] = []
            moved = 0
            dst.mkdir(parents=True, exist_ok=True)
            for child in src.iterdir():
                if child.name.upper() == "NUL":
                    skipped.append(str(child))
                    continue
                child_result = move_path_to_quarantine(child, dst / child.name)
                if child_result.get("result") in {"moved", "partial"}:
                    moved += 1
                skipped.extend(child_result.get("skipped", []))
            try:
                src.rmdir()
            except OSError:
                pass
            if skipped:
                return {
                    "result": "partial",
                    "quarantine_path": str(dst),
                    "warning": f"directory rename failed ({rename_error}); skipped invalid Windows device path(s)",
                    "skipped": skipped,
                    "moved_children": moved,
                }
            if src.exists():
                return {
                    "result": "partial",
                    "quarantine_path": str(dst),
                    "warning": f"directory rename failed ({rename_error}); moved children but source directory is still locked or not empty",
                    "moved_children": moved,
                }
            return {"result": "moved", "quarantine_path": str(dst), "warning": f"directory rename failed ({rename_error}); moved children"}
    shutil.move(str(src), str(dst))
    return {"result": "moved", "quarantine_path": str(dst)}


def clean_audit(quarantine: bool = False, quarantine_dir: Path | None = None, root: Path = ROOT) -> dict[str, Any]:
    candidates = cleanup_candidates(root)
    qdir = quarantine_dir or root.parent / f"Hermes-quarantine-{time.strftime('%Y%m%d-%H%M%S')}"
    manifest = {
        "schema_version": 1,
        "created_at": int(time.time()),
        "root": str(root),
        "mode": "quarantine" if quarantine else "audit",
        "quarantine_dir": str(qdir),
        "items": candidates,
        "total_bytes": sum(item["size_bytes"] for item in candidates),
    }
    if quarantine:
        verify_target_within(qdir, root.parent)
        qdir.mkdir(parents=True, exist_ok=True)
        for item in candidates:
            src = root / item["path"]
            if not src.exists():
                item["result"] = "missing"
                continue
            dst = qdir / item["path"]
            item.update(move_path_to_quarantine(src, dst))
    manifest["quarantine_history"] = quarantine_history(root)
    write_text(root / "cleanup-manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    if quarantine:
        write_text(qdir / "cleanup-manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return manifest


def scan_package_for_secret_risk(package_dir: Path) -> list[str]:
    findings: list[str] = []
    forbidden_names = {".env", "auth.json", "google_token.json", "google_client_secret.json"}
    for path in package_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.name in forbidden_names or "mcp-tokens" in path.parts or "sessions" in path.parts or "logs" in path.parts:
            findings.append(rel(path, package_dir))
            continue
        if path.suffix.lower() in {".json", ".yaml", ".yml", ".md", ".txt", ".toml", ".ps1", ".py"}:
            text = read_text(path)[:200_000]
            for line in text.splitlines():
                match = SECRET_ASSIGNMENT_RE.match(line)
                if not match:
                    continue
                value = match.group("value").strip().strip("'\"")
                safe_markers = ("<set via environment>", "<redacted>", "${", "ENV_KEYS")
                if not value or any(marker in value for marker in safe_markers):
                    continue
                if value.lower() in {"true", "false", "none", "null", "redacted", "placeholder"}:
                    continue
                if re.search(r"\s", value):
                    continue
                if re.fullmatch(r"[A-Z][A-Z0-9_]+", value):
                    continue
                compact = re.sub(r"\s+", "", value)
                known_prefix = re.match(r"(?i)^(sk-|ghp_|github_pat_|xox[baprs]-|ya29\.|eyJ)", compact)
                high_entropy = len(compact) >= 24 and bool(re.search(r"[A-Za-z]", compact)) and bool(re.search(r"[0-9]", compact))
                if known_prefix or high_entropy:
                    findings.append(rel(path, package_dir))
                    break
    return sorted(set(findings))


def doctor(root: Path = ROOT, package_dir: Path = PACKAGE_DIR) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add(name: str, ok: bool, summary: str = "") -> None:
        checks.append({"name": name, "ok": bool(ok), "summary": summary})

    add("root", root.exists(), str(root))
    for file_name in ("bridge/core.py", "bridge/cli.py", "mcp/hermes_overlord_mcp.py", "hermesctl.py"):
        path = root / file_name
        if not path.exists():
            add(f"exists:{file_name}", False, "missing")
            continue
        try:
            compile(read_text(path), str(path), "exec")
            add(f"syntax:{file_name}", True, "ok")
        except SyntaxError as exc:
            add(f"syntax:{file_name}", False, str(exc))
    live_profiles = profile_dirs()
    template_profiles = sorted((package_dir / "runtime" / "profiles").glob("*")) if (package_dir / "runtime" / "profiles").exists() else []
    add(
        "profiles_available",
        bool(live_profiles or template_profiles),
        f"live_profiles={len(live_profiles)} template_profiles={len(template_profiles)}",
    )
    if package_dir.exists():
        findings = scan_package_for_secret_risk(package_dir)
        add("package_secret_scan", not findings, ", ".join(findings[:5]) if findings else "ok")
        add("package_templates", bool(template_profiles), str(package_dir / "runtime" / "profiles"))
        if (package_dir / "MANIFEST.json").exists():
            add("package_manifest", True, str(package_dir / "MANIFEST.json"))
    else:
        add("package_exists", False, str(package_dir))
    return {"schema_version": 1, "ok": all(item["ok"] for item in checks), "checked_at": int(time.time()), "checks": checks}


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hermes portable distribution and MCP configuration utility")
    sub = parser.add_subparsers(dest="command", required=True)

    package_cmd = sub.add_parser("package", help="Build dist/hermes-portable clean template")
    package_cmd.add_argument("--out", default=str(PACKAGE_DIR))
    package_cmd.add_argument("--hermes-home", default=None)

    config_cmd = sub.add_parser("mcp-config", aliases=["config"], help="Generate MCP client config")
    config_cmd.add_argument("--client", choices=list(SUPPORTED_CLIENTS), required=True)
    config_cmd.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    config_cmd.add_argument("--root", default=str(ROOT))
    config_cmd.add_argument("--http-url", default=DEFAULT_HTTP_URL)
    config_cmd.add_argument("--package-name", default=default_package_name())
    config_cmd.add_argument("--launcher", choices=["npx", "node", "python"], default="npx")
    config_cmd.add_argument("--hermes-home", default=None)
    config_cmd.add_argument("--workspace", default=None)
    config_cmd.add_argument("--format", choices=["config", "add-mcp"], default="config")
    config_cmd.add_argument("--out", default=None)

    init_cmd = sub.add_parser("init", help="Initialize a user-local Hermes MCP home and config snippet")
    init_cmd.add_argument("--client", choices=list(SUPPORTED_CLIENTS), default="generic")
    init_cmd.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    init_cmd.add_argument("--root", default=str(ROOT))
    init_cmd.add_argument("--http-url", default=DEFAULT_HTTP_URL)
    init_cmd.add_argument("--package-name", default=default_package_name())
    init_cmd.add_argument("--launcher", choices=["npx", "node", "python"], default="npx")
    init_cmd.add_argument("--hermes-home", default=None)
    init_cmd.add_argument("--workspace", default=None)
    init_cmd.add_argument("--out", default=None)
    init_cmd.add_argument("--force", action="store_true")

    clean_cmd = sub.add_parser("clean-audit", help="Audit or quarantine non-shareable local artifacts")
    clean_cmd.add_argument("--quarantine", action="store_true")
    clean_cmd.add_argument("--quarantine-dir", default=None)

    doctor_cmd = sub.add_parser("doctor", help="Check local portable readiness")
    doctor_cmd.add_argument("--package-dir", default=str(PACKAGE_DIR))

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "package":
            home = Path(args.hermes_home).expanduser() if args.hermes_home else None
            print_json(package(Path(args.out), home=home))
        elif args.command in {"mcp-config", "config"}:
            home = Path(args.hermes_home).expanduser() if args.hermes_home else None
            builder = build_add_mcp_config if args.format == "add-mcp" else build_mcp_config
            data = builder(
                args.client,
                root=Path(args.root),
                transport=args.transport,
                http_url=args.http_url,
                package_name=args.package_name,
                launcher=args.launcher,
                hermes_home_path=home,
                workspace=args.workspace,
            )
            if args.out:
                write_text(Path(args.out), json.dumps(data, ensure_ascii=False, indent=2))
            print_json(data)
        elif args.command == "init":
            home = Path(args.hermes_home).expanduser() if args.hermes_home else None
            out = Path(args.out).expanduser() if args.out else None
            print_json(
                init_install(
                    client=args.client,
                    home=home,
                    root=Path(args.root),
                    force=args.force,
                    transport=args.transport,
                    package_name=args.package_name,
                    launcher=args.launcher,
                    workspace=args.workspace,
                    http_url=args.http_url,
                    out=out,
                )
            )
        elif args.command == "clean-audit":
            qdir = Path(args.quarantine_dir).expanduser() if args.quarantine_dir else None
            print_json(clean_audit(quarantine=args.quarantine, quarantine_dir=qdir))
        elif args.command == "doctor":
            print_json(doctor(package_dir=Path(args.package_dir)))
        else:
            parser.error(f"unknown command: {args.command}")
            return 2
        return 0
    except Exception as exc:
        print_json({"ok": False, "error": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
