param(
    [string]$Board = "overlord",
    [int]$Interval = 5,
    [int]$Events = 18,
    [switch]$Once,
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

function Invoke-HermesSnapshot {
    $env:HERMES_MONITOR_BOARD = $Board
    $env:HERMES_MONITOR_EVENTS = [string]$Events

@'
import ctypes
import datetime as dt
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

LOCALAPPDATA = Path(os.environ.get("LOCALAPPDATA", ""))
BOARD = os.environ.get("HERMES_MONITOR_BOARD", "overlord")
EVENTS = int(os.environ.get("HERMES_MONITOR_EVENTS", "18"))
ROOT = LOCALAPPDATA / "hermes"
DB = ROOT / "kanban" / "boards" / BOARD / "kanban.db"
PROFILES = ROOT / "profiles"


def ts(value):
    if value in (None, "", 0):
        return "-"
    try:
        return dt.datetime.fromtimestamp(float(value)).strftime("%H:%M:%S")
    except Exception:
        return str(value)


def age(value):
    if value in (None, "", 0):
        return "-"
    try:
        sec = max(0, int(time.time() - float(value)))
    except Exception:
        return "-"
    if sec < 90:
        return f"{sec}s"
    if sec < 5400:
        return f"{sec // 60}m"
    return f"{sec // 3600}h{(sec % 3600) // 60:02d}m"


def short(text, limit=92):
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[: max(0, limit - 1)] + "..."


def pid_alive(pid):
    if not pid:
        return False
    try:
        pid = int(pid)
    except Exception:
        return False
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return False
    try:
        code = ctypes.c_ulong()
        if ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return code.value == 259
        return True
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def notion_enabled(profile_dir):
    cfg = profile_dir / "config.yaml"
    if not cfg.exists():
        return False
    text = cfg.read_text(encoding="utf-8", errors="replace").splitlines()
    in_block = False
    for line in text:
        if re.match(r"^  notion:\s*$", line):
            in_block = True
            continue
        if in_block and re.match(r"^  [A-Za-z0-9_.-]+:\s*$", line):
            return False
        if in_block:
            m = re.match(r"^    enabled:\s*(\w+)", line)
            if m:
                return m.group(1).lower() == "true"
    return False


def print_row(cols, widths):
    parts = []
    for col, width in zip(cols, widths):
        s = short(col, abs(width))
        parts.append(s.rjust(width) if width < 0 else s.ljust(width))
    print("  ".join(parts).rstrip())


print(f"Hermes live monitor | board={BOARD} | {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 100)

state = read_json(PROFILES / "overlord" / "gateway_state.json") or {}
gw_pid = state.get("pid")
platforms = state.get("platforms") or {}
telegram = (platforms.get("telegram") or {}).get("state", "-")
print(f"Gateway: {state.get('gateway_state', '-')} | pid={gw_pid or '-'} alive={pid_alive(gw_pid)} | telegram={telegram}")
print(f"DB: {DB}")

if not DB.exists():
    print("Kanban DB not found.")
    raise SystemExit(0)

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
con.row_factory = sqlite3.Row

counts = {r["status"]: r["c"] for r in con.execute("select status,count(*) c from tasks group by status")}
run_counts = {r["status"]: r["c"] for r in con.execute("select status,count(*) c from task_runs group by status")}
print("Tasks:", " | ".join(f"{k}={counts[k]}" for k in sorted(counts)))
print("Runs: ", " | ".join(f"{k}={run_counts[k]}" for k in sorted(run_counts)))

print("\nLatest intake")
root = con.execute(
    "select * from tasks where title like 'Overlord intake:%' order by created_at desc limit 1"
).fetchone()
if root:
    print(f"  {root['id']} [{root['status']}] assignee={root['assignee']} created={ts(root['created_at'])} age={age(root['created_at'])}")
    print(f"  {short(root['title'], 150)}")
    related = con.execute(
        """
        select distinct t.id,t.assignee,t.status,t.worker_pid,t.current_run_id,
               t.consecutive_failures,t.last_failure_error,t.created_at,t.title,
               case when l.child_id = ? then 'feeds-root' else 'from-root' end rel
          from task_links l
          join tasks t on t.id = case when l.child_id = ? then l.parent_id else l.child_id end
         where l.child_id = ? or l.parent_id = ?
         order by t.created_at, t.id
        """,
        (root["id"], root["id"], root["id"], root["id"]),
    ).fetchall()
    if related:
        print("\nCurrent graph / dependencies")
        print_row(["rel", "task", "agent", "status", "run", "pid", "alive", "fail", "title"], [10, 11, 12, 9, 6, 7, 6, 5, 74])
        for r in related:
            print_row([
                r["rel"], r["id"], r["assignee"], r["status"], r["current_run_id"] or "-",
                r["worker_pid"] or "-", str(pid_alive(r["worker_pid"])), r["consecutive_failures"] or 0,
                r["title"],
            ], [10, 11, 12, 9, 6, 7, 6, 5, 74])
else:
    print("  No intake tasks found.")

print("\nRunning / ready / blocked")
rows = con.execute(
    """
    select id,assignee,status,current_run_id,worker_pid,created_at,last_failure_error,title
      from tasks
     where status in ('running','ready','blocked','scheduled')
     order by case status when 'running' then 0 when 'ready' then 1 else 2 end, created_at desc
     limit 24
    """
).fetchall()
if rows:
    print_row(["task", "agent", "status", "run", "pid", "alive", "age", "last error / title"], [11, 12, 9, 6, 7, 6, 6, 92])
    for r in rows:
        detail = r["last_failure_error"] or r["title"]
        print_row([r["id"], r["assignee"], r["status"], r["current_run_id"] or "-", r["worker_pid"] or "-", str(pid_alive(r["worker_pid"])), age(r["created_at"]), detail], [11, 12, 9, 6, 7, 6, 6, 92])
else:
    print("  none")

cut = int(time.time()) - 20 * 60
print("\nCrashes in last 20m")
crashes = con.execute(
    """
    select profile,count(*) c,max(error) sample
      from task_runs
     where started_at >= ? and status='crashed'
     group by profile order by c desc
    """,
    (cut,),
).fetchall()
if crashes:
    for r in crashes:
        print(f"  {r['profile']}: {r['c']} | {short(r['sample'], 90)}")
else:
    print("  none")

print(f"\nLatest events ({EVENTS})")
events = con.execute(
    """
    select e.id,e.task_id,e.run_id,e.kind,e.payload,e.created_at,t.assignee,t.title
      from task_events e left join tasks t on t.id=e.task_id
     order by e.id desc limit ?
    """,
    (EVENTS,),
).fetchall()
print_row(["id", "time", "kind", "task", "run", "agent", "payload / title"], [-5, 8, 10, 11, 6, 12, 88])
for r in events:
    payload = r["payload"] or r["title"] or ""
    print_row([r["id"], ts(r["created_at"]), r["kind"], r["task_id"] or "-", r["run_id"] or "-", r["assignee"] or "-", payload], [-5, 8, 10, 11, 6, 12, 88])

print("\nNotion MCP state")
print_row(["profile", "enabled", "token", "expires", "client"], [13, 8, 10, 10, 18])
for profile in sorted(p.name for p in PROFILES.iterdir() if p.is_dir()):
    pdir = PROFILES / profile
    enabled = notion_enabled(pdir)
    token = read_json(pdir / "mcp-tokens" / "notion.json")
    client = read_json(pdir / "mcp-tokens" / "notion.client.json")
    if token and token.get("expires_at"):
        left = int(float(token["expires_at"]) - time.time())
        token_state = "valid" if left > 0 else "expired"
        exp = (f"{left // 60}m" if left > 0 else f"-{abs(left) // 3600}h")
    elif token:
        token_state = "cached"
        exp = "?"
    else:
        token_state = "missing"
        exp = "-"
    client_id = (client or {}).get("client_id", "-")
    if enabled or token_state != "missing":
        print_row([profile, str(enabled), token_state, exp, client_id], [13, 8, 10, 10, 18])

print("\nUseful commands")
print(f"  hermes kanban --board {BOARD} watch")
print(f"  hermes kanban --board {BOARD} show <task_id>")
print(f"  hermes kanban --board {BOARD} runs <task_id>")
print(f"  hermes kanban --board {BOARD} log <task_id>")
print(f"  logs: {ROOT / 'kanban' / 'boards' / BOARD / 'logs'}")
'@ | & $Python -
}

do {
    Clear-Host
    Invoke-HermesSnapshot
    if ($Once) { break }
    Start-Sleep -Seconds $Interval
} while ($true)
