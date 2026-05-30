# Codex Hermes Bridge

## Purpose

This bridge is the canonical boundary between Codex clients and Hermes Overlord.
It keeps the responsibilities strict:

- Codex submits one durable root task and later curates status.
- Hermes Overlord owns decomposition, specialist profiles, skills, MCP/tools,
  reviewer/watchdog/synth gates, and execution.
- Dashboard and heartbeat jobs are read-only observers after submit.

## Commands

```powershell
C:\AI\Hermes\bridge.ps1 submit "Build X" -Workspace "dir:C:\AI" -Human
C:\AI\Hermes\bridge.ps1 status -TaskId t_xxx
C:\AI\Hermes\bridge.ps1 report -TaskId t_xxx
C:\AI\Hermes\bridge.ps1 events -TaskId t_xxx
C:\AI\Hermes\bridge.ps1 dispatch -Human
C:\AI\Hermes\bridge.ps1 heartbeat-prompt -TaskId t_xxx -Human
C:\AI\Hermes\bridge.ps1 autocheck -Human
```

`submit` supports only root handoffs: `-Mode task` (default) or `-Mode triage`.
It does not create a swarm. If a task needs council, workers, review, or
synthesis, Overlord decides that inside Hermes. The default is `task` because it
puts the root handoff directly into the dispatcher path; `triage` is reserved
for setups where the Hermes triage decomposer is known to be actively consuming
triage cards.

## JSON Contract

Every command returns JSON by default:

- `schema_version`: currently `1`.
- `ok`: boolean success flag.
- `action`: `submit`, `status`, `report`, `events`, `dispatch`,
  `heartbeat_prompt`, or `autocheck`.
- `task_id`: present for task-bound commands.

`submit` returns the created root task id plus ready-to-run status/report
commands. `report` returns a curator snapshot with:

- `handoff`: root task state.
- `delegation`: real child tasks and profiles found from Kanban evidence.
- `bridge_events`: structured bridge comments/events.
- `visibility`: recent comments, events, and runs.
- `mcp_and_tools`: root task MCP/tool evidence from actual logs and structured
  comments/events only.
- `child_mcp_and_tools`: descendant task MCP/tool evidence, artifacts, and
  compact structured evidence by task id/profile.
- `final_artifacts`: artifact paths/URLs reported by root or child structured
  evidence.
- `next`: suggested Codex heartbeat action.

The bridge must not count task prompt/body text as tool use. MCP and tool claims
come only from worker logs, task events, or structured worker comments.

`heartbeat-prompt` generates the exact prompt text Codex Desktop should store in
the thread heartbeat automation for a submitted task.

## Verified Smoke

The current canonical path was live-smoked on May 29, 2026 with task
`t_e2780a02` after switching default submit mode to dispatcher-ready `task`.

- Submit path: MCP HTTP `hermes_submit_task`, backed by `bridge.core`.
- Heartbeat: Codex Desktop heartbeat `hermes-bridge-smoke-t-e2780a02`, every
  seven minutes, then paused after terminal completion.
- Result: `bridge.ps1 report -TaskId t_e2780a02 -Board overlord` returns
  `terminal: true`, `outcome: done`, `next: finalize_to_user_and_pause_heartbeat`.
- Hermes execution: Overlord executed directly; no child tasks were needed.
- Artifacts:
  `C:\AI\Hermes\scratch\codex-hermes-bridge-smoke-20260529-taskmode\README.md`
  and `index.html`.
- Dashboard evidence:
  `/api/live/projects?board=overlord&view=archive&project_id=root:t_e2780a02`
  resolves to the native Hermes root project, not a reconstructed Codex session.

Automated coverage lives in `tests/test_bridge_core.py` and
`tests/test_dashboard_projects.py`.

## Structured Events

The bridge writes one accepted event after submit and asks Hermes workers to use
the same comment format for material state changes:

```text
BRIDGE_EVENT v1 {"type":"child_created|handoff|tool_used|blocked|review_result|final","task_id":"t_xxx","profile":"olfrontend","summary":"..."}
```

These comments are not instructions to Codex; they are telemetry evidence. The
dashboard may read them, but it must not mutate Hermes state.

## Codex Slash Flow

For `/hermes <goal>`:

1. Run `bridge.ps1 submit <goal>` or call the MCP adapter once it wraps this
   same core.
2. Reply: `Передал в Hermes: <task_id> (<status>)`.
3. Create a Codex Desktop heartbeat every 5-10 minutes for the exact task id.
4. Heartbeat runs `bridge.ps1 report -TaskId <task_id>` and reports only
   material changes, blockers, final results, or user-visible risk.
5. When `report.terminal` is true, summarize the result and pause/delete the
   heartbeat.

For the native end-to-end live test procedure, see
`docs/CODEX_HERMES_NATIVE_LIVE_TEST.md`.

## Adapter Rule

MCP is an adapter, not the source of truth. Future MCP tools should call
`bridge.core.HermesBridge` instead of duplicating submit/report logic.
