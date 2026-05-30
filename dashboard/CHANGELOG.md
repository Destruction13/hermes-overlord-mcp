# Hermes Dashboard Changelog

## 2026-05-25 — Live project execution graph

- Added `Проекты` mode to the real dashboard site with isolated active projects from the local Overlord board.
- Added `dashboard/serve-dashboard.py` and `hermes-site.ps1` for local live APIs over Kanban tasks and worker logs.
- Rendered active processes as graph nodes with running/blocked state, active handoff edges, MCP/tool signal pills, project rail, mobile list, and inspector drill-down.
- Added realtime per-task log polling in the inspector, plus run/event summaries for analysis.
- Tightened live-project detection to require real liveness evidence: fresh heartbeat, unexpired claim, alive worker PID, or recent run start.
- Stopped stale `running`, old `ready`, and old `blocked` tasks from being presented as active projects while still showing freshly launched pending tasks before dispatch.
- Preserved project rail and log scroll positions during polling; logs now fetch up to 2 MB by default, include a full-file option, and no longer trim to the last 180 lines.

## Verification

- `node --check dashboard/app.js`
- `python -m py_compile dashboard/serve-dashboard.py`
- API smoke: `/api/live/health`, `/api/live/projects?board=overlord`, `/api/live/log?board=overlord&task_id=<task-id>`
- Playwright smoke: Projects desktop/mobile, node inspector, realtime log, no console errors.

## 2026-05-25 — Workflow clarity v4

- Split layout persistence by view so moving a profile in Flow no longer moves it in MCP maps.
- Remember pan/zoom separately for Flow and MCP views.
- Repaired dark, graphite, light, and warm themes with consistent tokens, contrast, and mobile overflow handling.
- Added semantic workflow line colors, animated selected paths, arrowheads, and visible node input/output ports.
- Improved MCP map, catalog, and matrix with health/link summary tiles, clearer catalog cards, and readable matrix headers.
- Localized constructor controls and the theme/edge drawers.

## Verification

- `node --check dashboard/app.js`
- `node --check dashboard/dist/app.js`
- Playwright screenshots: Flow light, MCP dark, Catalog dark, Matrix dark, mobile.

## 2026-05-25 — Premium Constructor v3

- Reworked the visual system to the Iceberg & Citrine palette with semantic edge colors, brand focus states, density modes, dark/sepia/graphite themes, and reduced-motion support.
- Added top-level app modes: View, Constructor, Presentation.
- Added constructor toolbar with undo, redo, auto-layout reset, lock, snap, density, theme drawer, import, export, and presets.
- Added `hermes.user.v1` localStorage state with versioned defaults for theme, density, hidden nodes, node overrides, edge overrides, MCP view, tags, and layout preferences.
- Added draggable node handles in Constructor mode with grid snap, lane bounds, persisted positions, and minimap updates.
- Added edge editing popover in Constructor mode with label, color, style, and hide controls.
- Reworked MCP mode into three views: connection map, 14 x 33 matrix, and catalog with filters, tag chips, health icons, avatar initials, and MCP detail drawer.
- Added tags to generated profile and MCP data, plus sidebar tag filters with counters.
- Redesigned header statuses, search, sidebar grouping, inspector actions, and responsive drawer behavior.
- Updated generated data date to the current generation date.

## Verification

- `node --check dashboard/app.js`
- Playwright smoke: Flow, Constructor, MCP Matrix, MCP Catalog, overflow scan.
