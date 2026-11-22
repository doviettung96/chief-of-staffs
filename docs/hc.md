# The control plane: `hc`, the Herdr app, and `scripts/staff.py`

Staff run in the **Herdr desktop app** on top of **herdr-core**. Three tools, three jobs:

| tool | job |
| --- | --- |
| `hc` (herdr-core) | start, message, wait on, read, label and end terminals. The chief's hands. |
| `herdr-app` | what the owner **sees**: spaces, tabs, focus. Only to make staff visible. |
| `scripts/staff.py` | the chief's staff protocol on top of both: spawn, board, respawn, teardown, and the `report` command every staff runs. |

The old herdr TUI (`herdr agent ...`, `herdr pane ...`, `herdr-send.py`) is **retired**: it
cannot see the app's agents. The general `hc` rules (ask a fork for questions, `hc send`
for everything else, never answer a dialog yourself) are in **§10 of the global agent
guidelines** and are not repeated here. `hc --skill` and `herdr-app --skill` print the
tools' own current manuals; `hc <command> --help` beats anything written down.

## The staff protocol in one screen

```bash
S=scripts/staff.py                      # from this repo; staff get the absolute path in their brief

# 1. Isolate: one task -> one worktree -> one branch (docs/git-worktrees.md)
git -C <repo> worktree add <wt> -b <branch> <base>

# 2. Spawn: own tab in the project's Herdr space, brief from a file, report protocol appended
python $S spawn <name> --lane omp --cwd <wt> --brief-file brief.md
#    exit 2 + "needs_owner" = a first-run dialog holds it -> show the owner, never answer it

# 3. Wait for news. Never sleep or poll.
hc wait --children any --timeout 600   # wakes on a staff report, a child blocking/erroring/exiting,
                                       # or the owner typing to the chief
# 4. Triage
python $S board                        # NEEDS CHIEF first, then READY, then WORKING

# 5. Follow-up / answer -> the SAME worker
hc send <name> "<decision + why>"

# 6. Dead worker (crash, closed tab, core restart) -> resume it, don't start over
python $S respawn <name>

# 7. Verified + merged -> tear down (terminal), then remove the worktree yourself
python $S teardown <name>
```

## What `staff.py` does, exactly

**`spawn <name> --lane omp|codex|claude --cwd <wt> --brief-file <f>`**
- Writes the brief to `~/.chief-of-staff/staff/<name>/brief.md` (`CHIEF_STATE_DIR`
  overrides the root) **with the report protocol appended**. The agent's first message only
  points at that file, so a restarted worker can re-read the same brief.
- Starts the lane's agent with `hc run --bg --outlive-parent`: the worker is the chief's
  child (its reports and exit notes come to the chief, `hc wait --children` sees it), but it
  survives if the chief's own session ends.
- Labels it: `chief.role=staff`, `chief.lane`, `chief.chief` (the chief's address),
  `chief.cwd`, `chief.branch`, `herdr.space`. **Labels are the durable state**: they survive
  a core restart, and `board`/`respawn` read them back. There is no other database.
- Finds or creates the Herdr space named after the repo (`--space-name` / `--space` to
  override, never stealing focus) and names the worker's tab after it. Long-running staff
  must be visible to the owner (global §10).
- Waits up to 15 s and checks the screen for a known first-run dialog. Exit 2 with
  `needs_owner` when one holds the worker.

**`report <state> "<note>" [--details <file>]`** (run *by staff*)
- States: `progress`, `waiting` (needs an answer), `ready` (done **and** verified),
  `blocked`, `failed`.
- Sets `chief.state` / `chief.note` / `chief.details` / `chief.report_ms` on the worker's own
  terminal, appends to `~/.chief-of-staff/staff/<name>/reports.jsonl`, and `hc send`s one line
  to the chief: `[staff-report] <name> <state>: <note>`. It arrives as an `<hc from=...>`
  message, which is a staff report, **not** the owner.
- If the chief is sitting in a dialog, the send is refused; the report is still on the
  labels and shows on the board.

**`board [--all]`** reads every staff terminal's labels plus hc's own status and groups them:
- **NEEDS CHIEF**: `waiting`/`blocked`/`failed` reports, hc `blocked`/`error`, exited
  workers, and **silent** ones (no report and no hc status for 90 s; it names the
  first-run dialog when it sees one).
- **READY TO INTEGRATE**: `ready` reports. Verify them yourself before trusting them.
- **WORKING**: everything else.

**`respawn <name>`** restarts a *finished* worker in its own folder with the lane's resume
command (`omp --continue`, `claude --continue`, `codex resume --last`). Its worktree is its
own, so "continue the last session here" means its own session. It sends a **recovery note**:
re-read the brief, check git and every outside effect before repeating anything. For a live
worker it refuses: send it the next step instead.

**`teardown <name>`**: `hc kill` + `hc rm`. The worktree is left for you to remove after
the merge.

## Lanes as `hc` sees them (verified 2026-11-22, hc 0.1.21)

| lane | command `staff.py` runs | hc status | first-run dialogs |
| --- | --- | --- | --- |
| omp | `omp [--model M] "<msg>"` (default role GLM-5.3) | **yes** (`app: omp`) | none seen |
| claude | `claude [--model M] "<msg>"` | **yes** (`app: claude-code`) | folder trust, once per folder |
| codex | `codex -m gpt-5.5 "<msg>"` | **none at all**, even in a dialog | repo trust (once per **repo root**, so it covers every worktree of that repo), then hook review |

- codex reporting nothing is why the **staff report is the done signal**, not hc status.
- codex 0.145 is a native exe now (`...\Programs\OpenAI\Codex\bin\codex`): no more
  `codex.cmd`. It also rejects `--no-daemon`, which the hc manual tells you to pass.
- The hook codex asks about is the **old herdr TUI's** `~/.codex/herdr-agent-state.ps1`.
  Under hc it does nothing (it exits unless `HERDR_ENV=1`).

## Raw `hc` you still use directly

```bash
hc ls                              # every live terminal (the owner's too: touch only yours)
hc get <t> --json                  # one terminal: .status.state, .turn, .labels, .foreground
hc read <t> --lines 80             # its screen + history: for diagnosis, not for status
hc send <t> "<msg>" [--wait]       # deliver + Enter; waits for the owner's unfinished draft
hc interrupt <t>                   # stop its current turn
hc run --bg --rm --no-notify --name build <cmd> ; hc wait build   # slow command, chief stays reachable
```

Exit codes worth knowing: 3 not found, 9 blocked (refused; never `--force` past a
permission decision), 10 status mismatch, 11 finished.

## Escalate to the owner

The owner talks to the chief, so a question for the owner goes in the chief's own reply,
or `AskUserQuestion` when it needs a decision. Never answer a staff dialog yourself, and
never ask the owner to type into a staff tab.

## Gotchas (each one bit in practice)

- **Put `hc` flags before the program.** Everything after the program name is the
  program's: `hc run --bg omp "x" --json` hands `--json` to omp (`unknown flag: --json`).
- **`hc ls` has no labels** and its `status` is a bare string. `hc get` has
  `labels` and `status` as `{app, state, msg}`. `staff.py` reads `hc get`.
- **`herdr-app do space.close` needs `--confirmed true`**, because it ends the space's
  terminals. Close only spaces you made.
- **A finished worker can still hold its worktree** (`Device or resource busy` on removal):
  a leftover child process. Do not kill by image name: other agents run the same binaries.
  Leave the folder, `git worktree prune`, and retry later (see LESSONS.md).
- **A `<hc from=...>` message is a staff report or an hc note**, not the owner speaking.
  Read the claim, then verify it in the worktree before acting on it.
