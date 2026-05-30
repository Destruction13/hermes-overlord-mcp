# Hermes Control Constellation

Static dashboard for the Hermes agent family. It runs with plain `index.html`, `styles.css`, `data.js`, and `app.js`; no bundler or framework is required.

## Live Projects

The `Проекты` mode reads the local Overlord Kanban board and renders active work as a live execution graph: project chips, task/process nodes, active handoff edges, MCP/tool signals, run/event history, and realtime worker logs in the inspector.

Current means a task is either actually live (non-expired claim, fresh heartbeat, alive worker PID, or very recent run start) or freshly launched and still pending dispatch. Old `ready`, `blocked`, and stale `running` rows stay visible in diagnostics counters but are not shown as active projects.

By default `/api/live/projects` shows Hermes Kanban project families only. Codex
session reconstruction is opt-in with `include_codex_sessions=1`, so mentioning a
Hermes task id in a Codex chat does not hide or replace the native Hermes root
project in the main dashboard.

Start the local site server when you need live project data:

```powershell
C:\AI\Hermes\hermes-site.ps1
```

Then open `http://127.0.0.1:8787/` and switch to `Проекты`. Opening `index.html` directly still works for the static Flow/MCP views; live project mode uses the local API from `dashboard/serve-dashboard.py`:

- `/api/live/projects?board=overlord`
- `/api/live/log?board=overlord&task_id=<task-id>`

Realtime logs fetch up to 2 MB by default, include a full-file option, keep the user's scroll position during polling, and only auto-follow the bottom while the log is already near the bottom.

## Constructor

The dashboard now has three app modes in the header:

- `Просмотр`: normal map navigation and inspection.
- `Конструктор`: enables node handles, edge editing, theme controls, import/export, density, snap, lock, undo/redo, and presets.
- `Презентация`: hides side panels and keeps the map focused for walkthroughs.

Constructor changes are stored locally in `localStorage` under `hermes.user.v1`. The generated `data.js` remains the source of truth; user changes are layered on top and can be exported as JSON.

Layout edits are scoped per view: moving a node in Flow no longer changes the MCP map, matrix, or catalog view state. Zoom/pan state is also remembered separately for Flow and each MCP view.

Useful shortcuts:

- `F`: fit map
- `+`, `-`, `0`: zoom in, zoom out, reset
- `/`: focus search
- `M`: switch Flow/Projects/MCP
- `E`: switch View/Constructor
- `G`: show or hide grid
- `A`: auto-layout reset
- `L`: lock layout
- `Ctrl/Cmd+Z`, `Shift+Ctrl/Cmd+Z`: undo/redo
- `Ctrl/Cmd+E`: export config
- `Delete`: hide selected node in Constructor
- `Esc`: close drawers/popovers or leave Presentation

## MCP Views

MCP mode has three views:

- `Карта связей`: focused agent-to-MCP map.
- `Матрица`: agents by MCP coverage table.
- `Каталог`: searchable MCP cards with category, health, and tag filters.

MCP cards include health icons, category, transport hints, tags, agent initials, and a detail drawer. Matrix/catalog views include summary tiles for health and agent-MCP link coverage.

## Data

Run this to regenerate `data.js` from local Hermes profiles:

```powershell
python C:\AI\Hermes\dashboard\generate-dashboard-data.py
```

The generator adds optional `tags` to profiles and MCP records while preserving the previous data shape.
