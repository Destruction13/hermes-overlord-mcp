# Codex Hermes Native Live Test Protocol

Дата: 2026-05-29.

This protocol verifies native Codex -> Hermes behavior. It is not a prompt
template for normal work and must not be hardcoded into agents.

## Test Prompt

Use a fresh Codex chat and send this exact prompt:

```text
/hermes Сделай мне красивый сайт, который будет стоит очень много денег, у меня есть вот такой, но он старый и плохой http://trener.egor.tilda.ws/page69301633.html
```

Do not rewrite the prompt. Do not add role routing, worker requirements, or
implementation notes from Codex.

## Expected Native Flow

- Codex submits exactly one Hermes root handoff through `hermes_submit_task` or
  `C:\AI\Hermes\bridge.ps1 submit ... -Workspace "dir:C:\AI"`.
- Codex replies only with `Передал в Hermes: <task_id> (<status>)` and creates a
  thread heartbeat every 5-10 minutes for that exact task id.
- Hermes Overlord classifies the task, writes acceptance criteria, and creates a
  reviewable Kanban graph because this is a non-trivial website request.
- The graph includes `olfrontend` unless that profile is unavailable. For vague
  premium-quality website tasks, `olproduct` and/or `olux` should normally shape
  scope/UX before frontend implementation.
- Workers follow their SOUL.md, health-check required MCPs, load relevant skills,
  and record actual MCP/tool/skill evidence only after use.
- Reviewer verifies output with build/browser evidence where practical, and synth
  returns the final user-facing result with artifacts, verification, task ids,
  profiles, and residual risks.

## Failure Handling

- If the flow fails, do not fix the produced website manually.
- Diagnose the systemic cause first: Codex routing, heartbeat, bridge, Kanban,
  Overlord decomposition, profile/SOUL following, MCP/skill availability,
  reviewer/synth gates, or evidence reporting.
- Archive or otherwise remove the failed task family from active Kanban after
  preserving evidence and a DB backup when direct DB cleanup is needed.
- Rerun only in another fresh Codex chat after the foundation fix.

## Evidence To Capture

- Root task id, child task ids, assignees, statuses, and task links.
- Heartbeat automation id and exact task id in its prompt.
- `bridge.ps1 report -TaskId <task_id> -Board overlord` output.
- Worker logs or structured comments showing SOUL/MCP/skill/tool evidence.
- Output artifact paths/URLs, build/test/browser checks, screenshots when useful,
  reviewer pass/block, and synth final summary.
