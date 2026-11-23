#!/usr/bin/env python3
"""Staff control for the Chief of Staff, on top of herdr-core (`hc`) and the Herdr app.

The chief uses it to start, watch, restart and tear down staff. Staff use it to report.

  staff.py spawn <name> [--lane omp|claude] --cwd <worktree> --brief-file <f>
  staff.py board [--all]
  staff.py respawn <name>
  staff.py teardown <name>
  staff.py report <state> "<note>" [--details <file>]     # run BY a staff worker

Design (docs/orchestration.md has the why):

* The chief does not read staff screens to learn their state. Every staff worker
  ends every turn with `staff.py report <state> ...`, which records the state on the
  worker's own hc labels (durable, survives a core restart, visible in `board`) and
  sends a one-line report to the chief's terminal. In a Claude chief it arrives as a
  new message, idle or not. hc's own status is a fallback only: `idle` can mean done,
  stuck or waiting.
* The brief lives in a file (STATE_DIR/<name>/brief.md), not only in the agent's
  first message, so a restarted worker can re-read it.
* Every long-running worker is visible in the Herdr window: one space per project,
  one tab per worker.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STATE_DIR = Path(os.environ.get("CHIEF_STATE_DIR") or Path.home() / ".chief-of-staff" / "staff")

ROLE_LABEL = "chief.role=staff"
STATES = ("progress", "waiting", "ready", "blocked", "failed")
# States that need the chief, in triage order. hc's own `blocked`/`error` count too.
NEEDS_CHIEF = ("waiting", "blocked", "failed")
NOTE_MAX = 300

# Per lane: how to start a fresh worker, how to continue its last session in the
# same folder, and the model it gets when the chief names none.
LANES = {
    "omp": {
        "start": ["omp"],
        "resume": ["omp", "--continue"],
        "model_flag": "--model",
        "default_model": None,  # omp's own default role (GLM-5.3 on this box)
    },
    "claude": {
        "start": ["claude"],
        "resume": ["claude", "--continue"],
        "model_flag": "--model",
        "default_model": None,
    },
}


class StaffError(Exception):
    pass


# --------------------------------------------------------------------------- helpers


def run(argv: list[str], check: bool = True) -> subprocess.CompletedProcess:
    # Windows: decode child output as UTF-8, never the locale codec (LESSONS.md).
    proc = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise StaffError(f"{' '.join(argv[:3])} ... exited {proc.returncode}: {detail[:400]}")
    return proc


def run_json(argv: list[str]) -> dict:
    out = run(argv).stdout
    try:
        return json.loads(out)
    except json.JSONDecodeError as exc:
        raise StaffError(f"{' '.join(argv[:3])} printed no JSON: {exc}: {out[:200]}") from exc


def hc(*args: str) -> dict:
    return run_json(["hc", *args, "--json"])


def staff_terminals(include_finished: bool = False) -> list[dict]:
    """Full records (`hc get`) of every staff terminal.

    `hc ls` filters by label but prints a summary without labels, and its `status`
    is a bare string; `hc get` has the labels and `status` as {app, state, msg}.
    """
    args = ["ls", "--label", ROLE_LABEL] + (["--all"] if include_finished else [])
    full = []
    for summary in hc(*args).get("terminals", []):
        try:
            full.append(hc("get", summary["address"]))
        except StaffError:
            continue  # removed between the two calls
    return full


def hc_state(term: dict) -> str:
    status = term.get("status")
    if isinstance(status, dict):
        return status.get("state") or "-"
    return status or "-"


def find_staff(name: str, include_finished: bool = True) -> dict | None:
    matches = [t for t in staff_terminals(include_finished) if t.get("name") == name]
    # A live one wins over finished ones; among finished, the newest.
    matches.sort(key=lambda t: (t.get("state") == "live", t.get("created_ms") or 0), reverse=True)
    return matches[0] if matches else None


def labels_of(term: dict) -> dict:
    return term.get("labels") or {}


def worker_dir(name: str) -> Path:
    path = STATE_DIR / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def repo_root_of(cwd: Path) -> Path:
    """Main checkout of the repo `cwd` belongs to (worktrees resolve to their main repo)."""
    proc = run(["git", "-C", str(cwd), "rev-parse", "--path-format=absolute", "--git-common-dir"], check=False)
    if proc.returncode == 0 and proc.stdout.strip():
        common = Path(proc.stdout.strip())
        return common.parent if common.name == ".git" else common
    return cwd


def git_branch(cwd: Path) -> str:
    proc = run(["git", "-C", str(cwd), "branch", "--show-current"], check=False)
    return proc.stdout.strip() if proc.returncode == 0 else ""


def ensure_space(name: str, folder: Path) -> str:
    """Id of the Herdr space called `name`, created (without stealing focus) if missing."""
    layout = run_json(["herdr-app", "ls"])
    for space in layout.get("spaces", []):
        if space.get("name") == name and not space.get("machine"):
            return space["id"]
    created = run_json(
        ["herdr-app", "do", "space.new", "--name", name, "--folder", str(folder), "--tab", "shell", "--focus", "false"]
    )
    if "space" not in created:
        raise StaffError(f"herdr-app space.new returned no space: {created}")
    return created["space"]


def name_tab(terminal: str, label: str, attempts: int = 10) -> bool:
    """Rename the Herdr tab that holds `terminal`. The window adds it a moment after spawn."""
    for _ in range(attempts):
        layout = run_json(["herdr-app", "ls"])
        for space in layout.get("spaces", []):
            for tab in space.get("tabs", []):
                if any(t.get("terminal") == terminal for t in tab.get("terminals", [])):
                    run(["herdr-app", "do", "tab.rename", "--id", tab["id"], "--name", label])
                    return True
        time.sleep(0.5)
    return False


# First-run dialogs that hold a fresh worker before it reads its brief. The chief never
# answers them itself (global guidelines §10): it shows the owner.
FIRST_RUN_DIALOGS = (
    ("Do you trust the files in this folder", "claude: trust this folder"),
    ("Is this a project you trust", "claude: trust this folder"),
)
SILENT_AFTER_S = 90  # no report and no hc status for this long -> the chief looks


def pending_dialog(address: str) -> str | None:
    proc = run(["hc", "read", address], check=False)
    if proc.returncode != 0:
        return None
    for needle, what in FIRST_RUN_DIALOGS:
        if needle in proc.stdout:
            return what
    return None


def chief_address() -> str:
    me = os.environ.get("HC_TERMINAL_ID")
    if not me:
        raise StaffError("HC_TERMINAL_ID is not set: run the chief inside a Herdr terminal")
    return me


# --------------------------------------------------------------------------- brief


REPORT_PROTOCOL = """\

---

## How you report (mandatory, read twice)

You are staff worker `{name}`. You report to the Chief of Staff (terminal `{chief}`).
The chief does **not** watch your screen. It only sees your reports, so a turn that ends
without one looks to it like a worker that silently stopped.

At the end of **every** turn, and immediately whenever you need a decision, run exactly one:

    python "{script}" report <state> "<one line, max {note_max} chars>" [--details <file.md>]

| state      | when                                                                       |
|------------|----------------------------------------------------------------------------|
| `progress` | a milestone, still working (optional)                                      |
| `waiting`  | you need an answer from the chief: put the exact question in the note     |
| `ready`    | DONE WHEN is met **and you verified it**: say what and where (PR, commit)  |
| `blocked`  | you cannot continue (tool missing, environment broken, access): say what   |
| `failed`   | the approach does not work: say why and what you would try instead         |

- Long content (findings, logs, a design) goes in a Markdown file; pass its path with `--details`.
- After `waiting`, stop and wait: the chief's answer arrives as your next message.
- Never report `ready` before verifying. An open PR alone is not ready.
- If you are restarted, you get a recovery note: check your folder, `git log` and
  anything outside (devices, game processes, PRs) **before** repeating an outside action.

## You are staff: what that changes

Your general instructions may assume the owner is in front of you. Here they are not: the
owner talks to the chief, and nobody watches your tab.

- **"Ask / show / tell the owner" means: report to the chief.** `waiting` with the
  question, `blocked` when only the owner can unblock it. Never stop to ask in your tab.
- **Stay in scope.** Other staff are editing other files right now. A bug, broken window
  or UI flaw outside this brief's scope (a typo in output, a wrong message, a flaky test)
  goes in your details file, not into a fix. Every `ready` report ends with
  `Out of scope: <what you noticed and left>` or `Out of scope: nothing noticed`.
- **Lessons:** propose them in a details file with a suggested scope (project or global).
  Write no `LESSONS.md` until the chief relays the owner's answer.
- **Targets:** verify for real, but only against the targets this brief names (game
  client, emulator, device, port, window). Never touch another one, not even to look.
- **Approvals only the owner gives** (a UAC Bridge `409 review_required`, a tool's own
  prompt): never accept them. Report `blocked` with the prompt text or fingerprint.
- Do not start other agents or terminals unless this brief says so.
- Kill only processes you started, by PID. Never by image name, never a process tree.
{workspace}
Your brief file (re-read it after a restart): `{brief_path}`
"""


def workspace_rules(cwd: Path) -> Path | None:
    """The shared AGENTS.md of the folder that holds the repo (e.g. D:/Projects/AGENTS.md).

    Claude loads it from parent folders by itself; omp stops at the repo, so
    the brief points every lane at it.
    """
    for folder in repo_root_of(cwd).parents:
        candidate = folder / "AGENTS.md"
        if candidate.is_file():
            return candidate
    return None


def write_brief(name: str, chief: str, body: str, cwd: Path) -> Path:
    path = worker_dir(name) / "brief.md"
    shared = workspace_rules(cwd)
    workspace = (
        f"- **Workspace rules** every agent here follows (elevated/admin actions go through the\n"
        f"  UAC Bridge, for example): read `{shared.as_posix()}` before any such action.\n"
        if shared
        else ""
    )
    protocol = REPORT_PROTOCOL.format(
        name=name,
        chief=chief,
        script=Path(__file__).resolve().as_posix(),
        note_max=NOTE_MAX,
        brief_path=path.as_posix(),
        workspace=workspace,
    )
    path.write_text(body.rstrip() + "\n" + protocol, encoding="utf-8")
    return path


def first_message(name: str, brief_path: Path) -> str:
    return (
        f"You are staff worker {name} for the Chief of Staff. Your full brief is in "
        f"{brief_path.as_posix()} . Read that whole file now and follow it exactly, "
        f"including its reporting section."
    )


def recovery_message(name: str, brief_path: Path) -> str:
    return (
        f"RECOVERY NOTE for staff worker {name}: you were restarted and your previous turn may "
        f"have been cut off mid-action. Before doing anything else: re-read your brief at "
        f"{brief_path.as_posix()} , check this folder's git status and git log, and check every "
        f"outside effect you may already have caused (PRs, pushed branches, running processes, "
        f"devices or game clients you touched, held locks). Do not repeat an outside action "
        f"that already happened. Then report with the brief's report command and continue."
    )


# --------------------------------------------------------------------------- commands


def launch(name: str, lane: str, cwd: Path, argv_tail: list[str], space: str, extra_labels: dict) -> dict:
    labels = {
        "chief.role": "staff",
        "chief.lane": lane,
        "chief.chief": chief_address(),
        "chief.cwd": str(cwd),
        "herdr.space": space,
        **extra_labels,
    }
    args = ["hc", "run", "--json", "--bg", "--outlive-parent", "--name", name, "--cwd", str(cwd)]
    for key, value in labels.items():
        args += ["--label", f"{key}={value}"]
    return run_json(args + argv_tail)


def lane_argv(lane: str, base_key: str, model: str | None) -> list[str]:
    spec = LANES[lane]
    argv = list(spec[base_key])
    chosen = model or spec["default_model"]
    if chosen:
        argv += [spec["model_flag"], chosen]
    return argv


def cmd_spawn(a: argparse.Namespace) -> int:
    cwd = Path(a.cwd).resolve()
    if not cwd.is_dir():
        raise StaffError(f"--cwd {cwd} is not a folder")
    if find_staff(a.name, include_finished=False):
        raise StaffError(f"a live staff worker is already named {a.name}")
    body = Path(a.brief_file).read_text(encoding="utf-8") if a.brief_file else a.brief
    if not body or not body.strip():
        raise StaffError("give the brief with --brief-file or --brief")

    chief = chief_address()
    brief_path = write_brief(a.name, chief, body, cwd)
    root = repo_root_of(cwd)
    space = a.space or ensure_space(a.space_name or root.name, root)
    argv = lane_argv(a.lane, "start", a.model) + list(a.agent_arg or []) + [first_message(a.name, brief_path)]
    result = launch(a.name, a.lane, cwd, argv, space, {"chief.branch": git_branch(cwd)})

    address = result["address"]
    tab_named = name_tab(address, a.tab or a.name)
    # Give the agent a moment to boot, then look for a first-run dialog holding it.
    run(["hc", "wait", address, "--timeout", "15", "--json"], check=False)
    dialog = pending_dialog(address)
    print(json.dumps({
        "name": a.name,
        "address": address,
        "lane": a.lane,
        "model": a.model or LANES[a.lane]["default_model"] or "(lane default)",
        "cwd": str(cwd),
        "branch": git_branch(cwd),
        "space": space,
        "tab_named": tab_named,
        "brief": brief_path.as_posix(),
        "needs_owner": dialog and f"{dialog}: show the owner `hc read {address}`; never answer it yourself",
        "next": "end your turn: its reports arrive as messages (docs/orchestration.md step 4)",
    }, indent=2))
    return 2 if dialog else 0


def cmd_respawn(a: argparse.Namespace) -> int:
    term = find_staff(a.name)
    if term is None:
        raise StaffError(f"no staff worker named {a.name}")
    if term.get("state") == "live":
        raise StaffError(
            f"{a.name} is still live ({term['address']}): send it the next step with hc send instead"
        )
    labels = labels_of(term)
    lane, cwd, space = labels.get("chief.lane"), labels.get("chief.cwd"), labels.get("herdr.space")
    if lane not in LANES or not cwd or not space:
        raise StaffError(f"{a.name} lacks chief.lane / chief.cwd / herdr.space labels: {labels}")
    brief_path = STATE_DIR / a.name / "brief.md"
    if not brief_path.is_file():
        raise StaffError(f"brief for {a.name} is gone: {brief_path}")
    run(["hc", "rm", term["address"]], check=False)
    argv = lane_argv(lane, "resume", a.model) + [recovery_message(a.name, brief_path)]
    keep = {k: v for k, v in labels.items() if k.startswith("chief.") and k not in ("chief.chief",)}
    keep["chief.restarts"] = str(int(labels.get("chief.restarts", "0")) + 1)
    result = launch(a.name, lane, Path(cwd), argv, space, keep)
    name_tab(result["address"], a.name)
    print(json.dumps({"name": a.name, "address": result["address"], "lane": lane, "resumed_in": cwd}, indent=2))
    return 0


def cmd_teardown(a: argparse.Namespace) -> int:
    term = find_staff(a.name)
    if term is None:
        raise StaffError(f"no staff worker named {a.name}")
    if term.get("state") == "live":
        run(["hc", "kill", term["address"]], check=False)
    run(["hc", "rm", term["address"]], check=False)
    print(f"{a.name} ({term['address']}) torn down. Its worktree is untouched: remove it after the merge.")
    return 0


def age(ms: str | int | None) -> str:
    if not ms:
        return "-"
    secs = max(0, int(time.time() - int(ms) / 1000))
    return f"{secs}s" if secs < 120 else f"{secs // 60}m" if secs < 7200 else f"{secs // 3600}h"


def missed_report(term: dict, labels: dict) -> bool:
    """True when the worker's latest finished turn carries no report.

    hc's `turn` counts *finished* turns. `report` runs mid-turn and stores the counter
    then (k), so its turn ends at k + 1. An idle worker past k + 1 finished a later turn
    without reporting (verified 2026-11-23: report_turn 0, turn 1 after that turn ended).
    """
    if "chief.state" not in labels:
        return True
    try:
        return int(term.get("turn")) > int(labels.get("chief.report_turn", "")) + 1
    except (TypeError, ValueError):
        return False  # a report from before turn tracking: don't guess


def cmd_board(a: argparse.Namespace) -> int:
    rows = []
    for term in staff_terminals(a.all):
        labels = labels_of(term)
        hc_status = hc_state(term)
        if term.get("state") == "finished":
            hc_status = f"exited({term.get('exit_code')})"
        report = labels.get("chief.state", "-")
        silent_s = time.time() - (term.get("created_ms") or 0) / 1000
        if term.get("state") == "live" and report == "-" and hc_status == "-" and silent_s > SILENT_AFTER_S:
            dialog = pending_dialog(term["address"])
            hc_status = "silent"
            labels = {**labels, "chief.note": f"no report after {int(silent_s)}s: "
                      + (f"{dialog} (show the owner)" if dialog else f"read it: hc read {term['address']}")}
        elif term.get("state") == "live" and hc_status in ("idle", "done") and missed_report(term, labels):
            # The worker finished a turn and sent nothing: done, stuck or asking in its own
            # tab, the chief can't tell which without looking.
            hc_status = "no-report"
            labels = {**labels, "chief.note": f"turn {term.get('turn')} ended without a report: "
                      f"hc read {term['address']} --lines 60"}
        if report in NEEDS_CHIEF or hc_status in ("blocked", "error", "silent", "no-report") or hc_status.startswith("exited"):
            bucket = 0
        elif report == "ready":
            bucket = 1
        else:
            bucket = 2
        rows.append((bucket, term, labels, hc_status, report))
    if not rows:
        print("no staff workers" + ("" if a.all else " (live). --all includes finished ones"))
        return 0
    rows.sort(key=lambda r: (r[0], r[1].get("name") or ""))
    heads = ("NEEDS CHIEF", "READY TO INTEGRATE", "WORKING")
    current = None
    for bucket, term, labels, hc_status, report in rows:
        if bucket != current:
            current = bucket
            print(f"== {heads[bucket]}")
        print(
            f"  {term.get('name') or '?':<18} {term['address']:<5} {labels.get('chief.lane', '?'):<6} "
            f"report={report:<8} ({age(labels.get('chief.report_ms')):>4} ago) hc={hc_status:<10} "
            f"{labels.get('chief.branch', '')}"
        )
        if labels.get("chief.note"):
            print(f"      {labels['chief.note']}")
        if labels.get("chief.details"):
            print(f"      details: {labels['chief.details']}")
    return 0


def cmd_report(a: argparse.Namespace) -> int:
    me = os.environ.get("HC_TERMINAL_ID")
    if not me:
        raise StaffError("HC_TERMINAL_ID is not set: report only works inside an hc terminal")
    term = hc("get", me)
    labels = labels_of(term)
    name = term.get("name") or me
    chief = labels.get("chief.chief") or term.get("parent")
    if not chief:
        raise StaffError(f"{name} has no chief.chief label and no parent: nobody to report to")

    note = " ".join(a.note.split())
    if len(note) > NOTE_MAX:
        note = note[: NOTE_MAX - 3] + "..."
    details = ""
    if a.details:
        dpath = Path(a.details).resolve()
        if not dpath.is_file():
            raise StaffError(f"--details {dpath} does not exist: write the file first")
        details = dpath.as_posix()
    now_ms = str(int(time.time() * 1000))

    run(["hc", "label", me, f"chief.state={a.state}", f"chief.note={note}",
         f"chief.details={details}", f"chief.report_ms={now_ms}",
         f"chief.report_turn={term.get('turn', '')}", "--json"])
    with (worker_dir(name) / "reports.jsonl").open("a", encoding="utf-8") as log:
        log.write(json.dumps({"ms": int(now_ms), "state": a.state, "note": note, "details": details}) + "\n")

    message = f"[staff-report] {name} {a.state}: {note}" + (f" (details: {details})" if details else "")
    proc = run(["hc", "send", chief, message, "--json"], check=False)
    if proc.returncode == 0:
        print(f"reported {a.state} to {chief}")
        return 0
    if proc.returncode == 9:  # chief is in a dialog: the labels still carry the report
        print(f"recorded {a.state}; chief {chief} is in a dialog, it will see this on its board")
        return 0
    raise StaffError(f"report recorded on labels but delivery to {chief} failed: {proc.stderr.strip()[:300]}")


# --------------------------------------------------------------------------- main


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="staff.py", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("spawn", help="start a staff worker in its own Herdr tab")
    s.add_argument("name", help="unique worker name: 1-32 of a-z 0-9 - _")
    s.add_argument("--lane", default="omp", choices=sorted(LANES), help="default omp (docs/agents.md)")
    s.add_argument("--cwd", required=True, help="the worker's own worktree")
    s.add_argument("--brief-file")
    s.add_argument("--brief")
    s.add_argument("--model", help="override the lane's default model")
    s.add_argument("--space", help="Herdr space id (default: the space named after the repo)")
    s.add_argument("--space-name", help="Herdr space name to find or create")
    s.add_argument("--tab", help="tab label (default: the worker name)")
    s.add_argument("--agent-arg", action="append", help="extra argument for the agent CLI (repeatable)")
    s.set_defaults(func=cmd_spawn)

    s = sub.add_parser("respawn", help="restart a dead worker in its folder, resuming its session")
    s.add_argument("name")
    s.add_argument("--model")
    s.set_defaults(func=cmd_respawn)

    s = sub.add_parser("teardown", help="end and remove a worker's terminal (not its worktree)")
    s.add_argument("name")
    s.set_defaults(func=cmd_teardown)

    s = sub.add_parser("board", help="every staff worker, the ones that need the chief first")
    s.add_argument("--all", action="store_true", help="include finished workers")
    s.set_defaults(func=cmd_board)

    s = sub.add_parser("report", help="(staff) report your state to the chief")
    s.add_argument("state", choices=STATES)
    s.add_argument("note")
    s.add_argument("--details", help="Markdown file with the long version")
    s.set_defaults(func=cmd_report)

    a = p.parse_args(argv)
    try:
        return a.func(a)
    except StaffError as exc:
        print(f"staff: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"staff: missing program: {exc.filename}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
