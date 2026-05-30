# Changelog

## 2026-05-30 - Public MCP install surface

- Added `hermes-overlord-mcp install` for a screenshot-style install guide with
  standard MCP JSON, requirements, and client-specific setup snippets.
- Added generated config presets for Claude Code, Gemini CLI, Cline, Roo Code,
  Continue, and Zed, while keeping Codex, VS Code, Cursor, Windsurf, OpenCode,
  Kilo, Kiro, and Antigravity support.
- Stopped pinning npx-generated configs to a local package cache root, so public
  GitHub installs stay portable across machines.

## 2026-05-25 — Workflow clarity and theme repair

- Split constructor node positions by view so Flow layout edits no longer move the same profile inside MCP maps.
- Added per-view pan/zoom memory for Flow and MCP views.
- Reworked light, dark, graphite, and warm themes with readable tokens, better contrast, and mobile overflow fixes.
- Rebuilt workflow lines with semantic colors, animated selected paths, arrowheads, and visible node input/output ports.
- Upgraded MCP map, catalog, and matrix with summary metrics, clearer cards, category/health context, and less cramped matrix headers.
- Localized and tightened constructor controls, theme drawer options, and edge style controls.

## 2026-05-24 — Hermes Control Constellation audit pass

- Synced the task-flow graph with profile ownership: `olproduct`, `olresearcher`, `overlord`, workers, reviewer, risk, UX, and synth now expose the missing edges from the audit.
- Replaced `olsynth.receivesFrom = "all specialists"` with concrete profile ids and added the missing `olrisk -> olautomation` risk-gate path.
- Added Russian `humanNote` descriptions for every MCP and Russian summaries for system nodes.
- Reworked MCP categories into core/memory, docs/research, workspace, frontend/UX, backend/risk, and platform/runtime.
- Improved graph rendering: selected-edge labels are on by default, zoom hides labels below 55%, arrows use stronger colors, and incoming edge offsets reduce line stacking.
- Added MCP hover tooltips, grouped connection chips in the inspector, keyboard shortcuts, focus handling for SOUL modal, and a compact legend.
- Polished the visual layer with calmer premium tokens, 12px radii, lighter borders, clearer focus rings, and a mobile list mode.
