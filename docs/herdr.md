# Driving staff with `herdr`

`herdr` is a terminal-workspace manager for AI coding agents (`herdr.dev`). It is the
chief's control plane: it spawns real agent terminals, isolates each in a git
worktree, reports every agent's live status, lets the chief read a pane and send it
text, and can notify the owner. **All commands below are verified against the running
build** (`herdr <group> --help`).

**Config location** — the chief runs on more than one OS, so never hard-code one path:

| platform | config file |
| --- | --- |
| macOS / Linux | `$XDG_CONFIG_HOME/herdr/config.toml`, i.e. `~/.config/herdr/config.toml` |
| Windows | `%APPDATA%\herdr\config.toml` (`~/AppData/Roaming/herdr/`) |

`HERDR_CONFIG_PATH` overrides the file outright on every platform, and `herdr
--default-config` prints the fully-commented defaults. `herdr config check` validates
the live file — use it rather than guessing where the config went.

> Golden rule: the chief drives staff **only** through `herdr`. Sub-agents are summoned
> by staff inside their own harness — never by the chief.

> **`herdr` supersedes `agtx`.** Some projects' own docs still reference an older `agtx`
> board/worktree workflow — that is **retired**. Orchestrate everything through `herdr`;
> where a project still names agtx, mark it for cleanup in its `projects/<name>/overview.md`.

## Targets

A staff agent is addressed by any of: its **terminal id** (`term_...`), its **pane id**
(`w4:pD`), a unique **agent name**, or a detected label. `herdr agent list` prints all
of these. Deliver messages with `scripts/herdr-send.py`, never `agent send` (see below);
`pane run` writes a command **and** Enter, and is the right tool for a shell pane.

## The primitives

### See the fleet
```bash
herdr agent list                       # JSON: every agent, its cwd, status, pane/tab/workspace
herdr agent get <target>               # one agent's metadata
herdr agent read <target> --lines 40   # read what the agent's pane shows (source: visible|recent)
herdr api snapshot                     # full live state of all workspaces/panes
```
`agent_status` is the heartbeat the chief watches: **`idle`** (waiting for a task or
done), **`working`**, **`blocked`** (waiting on a decision/permission — act on this),
`unknown`.

### Create an isolated worktree (one per staff task)
```bash
herdr worktree create --cwd <repo> --branch <new-branch> --base <ref> --label "<task>" --json
# -> creates a linked git worktree on a fresh branch, opens it as a workspace, returns its path
herdr worktree list --cwd <repo> --json     # existing worktrees for a repo
herdr worktree remove --workspace <id> [--force]   # tear down when the task is merged/abandoned
```

### Spawn a staff agent into that worktree
```bash
# Start an agent process in a given cwd (the worktree path), optionally in a specific workspace/tab:
herdr agent start <name> --cwd <worktree-path> --workspace <id> -- claude
herdr agent start <name> --cwd <worktree-path> -- codex.cmd      # GPT-5.5 lane
# NOTE (Windows): launch the codex lane as `codex.cmd`, NOT bare `codex`. herdr
# does a raw CreateProcessW; bare `codex` resolves to npm's extensionless Unix
# shell shim, which Windows can't execute -> `agent_start_failed ... %1 is not a
# valid Win32 application (os error 193)`, and the lane silently falls back to
# Claude. `codex.cmd` is the npm-generated Windows launcher (recreated on every
# codex update), so it stays valid across upgrades. See LESSONS.md.
# `start` launches the agent; give it its task once it's up (see "Hand a task", below).
```

### Hand a task / answer a block

**Always deliver through the helper — never `herdr agent send`:**
```bash
python scripts/herdr-send.py <target> "<task brief or decision text>"
python scripts/herdr-send.py <target> --stdin < brief.md      # long briefs
python scripts/herdr-send.py <target> "<msg>" --wait 300      # owner types a lot
python scripts/herdr-send.py <target> "<msg>" --force         # deliberate interrupt
```
Pattern: `agent start ...` → wait for `idle` (agent booted) → `herdr-send.py <target> "<full task brief>"`.

The helper re-resolves the pane id on every call, waits until the staff's input box is
clear, delivers with `herdr pane run` (one atomic write: bracketed-paste text **plus** the
Enter), and fails loudly if the message is still sitting in the box afterwards. It exits
non-zero on every failure — **check the exit code**; a silent failure means the staff never
got the message and will never reply.

<a id="delivering-a-message-to-staff"></a>
**Why not `herdr agent send`** (measured on the receiving TTY, 2026-08-17):

| command | bytes the agent actually receives |
| --- | --- |
| `pane send-text "HELLO"` | `HELLO` — no newline, **no submit** |
| `pane send-keys Enter` | `\r` — a *separate* write, ~4 ms later |
| `pane run "HELLO"` | `\x1b[200~HELLO\x1b[201~\r` — one atomic write |

`agent send` is raw keystroke injection, so it lands at the cursor inside whatever the
input box already holds and fuses with the owner's half-typed text; and because the Enter
is a second command, any time it is skipped, errors on a stale pane id, or loses a race,
the message just sits in the draft. The box is never cleared, so **every later message
piles onto the same stale draft and none are ever sent** — the staff sees nothing and the
chief waits forever on a reply that cannot come. Multi-line briefs can't rescue themselves
either: an embedded `\n` is inserted as a newline (both TUIs submit on `\r`, not `\n`).

Raw `herdr pane run <pane_id> "<command>"` remains correct for driving a **shell** pane.

### Watch and wait (blocking)
```bash
herdr agent wait <target> --status blocked --timeout 600000    # returns when it needs me
herdr wait agent-status <pane_id> --status done --timeout 0    # or working|idle|blocked
herdr wait output <pane_id> --match "<text>" [--regex] --timeout 60000
```

### Escalate to the owner
```bash
herdr notification show "<title>" --body "<the crisp question + options>" --sound request
```

### Cleanup
```bash
herdr agent focus <target>     # bring a pane to the foreground for the owner to inspect
herdr pane close <pane_id>     # close a finished agent's pane
herdr worktree remove --workspace <id>   # remove the worktree (after merge)
```

## The spawn-to-teardown sequence (one staff task)

_This sequence is verified — it is exactly the loop the chief ran end-to-end to build
`scripts/board.py`. The commented steps are the ones that bit in practice._

```bash
# 1. Isolate (plain git worktree is fine when the chief edits directly; use
#    `herdr worktree create` when you want it opened as a herdr workspace too)
git -C C:/Users/Tung/Projects/<proj> worktree add "$WT" -b feat/<task> <integration-branch>

# 2. Spawn (pick lane per docs/agents.md; default staff lane is codex on gpt-5.5;
#    --no-focus so it doesn't grab the owner's screen)
herdr agent start <task> --cwd "$WT" --no-focus -- codex.cmd

# 3. Boot: wait for idle, then clear any FIRST-RUN TRUST PROMPT.
herdr agent wait <task> --status idle --timeout 120000
herdr agent read <task> --lines 20          # a fresh agent may ask "trust this folder?" — option 1
herdr pane send-keys <pane_id> Enter        # accept (it's your own worktree)

# 4. Brief — one atomic delivery; check the exit code, it is the only proof it landed.
python scripts/herdr-send.py <task> "GOAL: ...  SCOPE: ...  DONE WHEN: ...  <commit / open a PR>"

# 5. Watch — confirm it's working, then block until it finishes or blocks.
herdr agent wait <task> --status working --timeout 30000
herdr agent wait <task> --status idle --timeout 300000

# 6. Verify for real — do NOT trust the pane. Check the worktree git state and run the
#    deliverable yourself (an API error can cut a staff off mid-task, before its commit).
git -C "$WT" log --oneline -2 ; git -C "$WT" status --short
#    If DONE WHEN is unmet, nudge the staff with herdr-send.py rather than finishing it silently.

# 7. Integrate — see docs/git-worktrees.md; build/verify from the MERGED result.

# 8. Teardown
herdr pane close <pane_id>
git -C C:/Users/Tung/Projects/<proj> worktree remove --force "$WT"   # may need a retry — see gotchas
```

## Notes / gotchas

- **Never `agent send` a chat agent — use `scripts/herdr-send.py`.** `agent send` is raw
  keystroke injection with no submit, so briefs fuse with the owner's typing and, whenever
  the follow-up Enter goes missing, pile up unsent in the draft forever. Full measurements
  in [Hand a task](#delivering-a-message-to-staff). For a shell line, `pane run` is right.
- **A message you can't prove landed did not land.** `herdr-send.py` exits non-zero on
  every failure and verifies the box is clear afterwards; check the exit code instead of
  assuming, then confirm the staff actually went `working`.
- **Fresh staff hit a trust-folder prompt.** A new claude in a new worktree asks
  "Is this a project you trust?" — option 1 is pre-selected, so `pane send-keys <pane> Enter`.
  It's the chief's own worktree, so this is a decide-on-evidence, not an escalate.
- **Verify state, not the pane.** A staff can report progress and still be cut off by an
  `API Error: Connection closed mid-response` before committing. Always check `git log`/`status`
  in the worktree and run the deliverable before integrating.
- **`worktree remove` right after `pane close` can fail with `Permission denied`** — the
  just-exited agent process still holds a handle. Retry once (or `rm -rf` the path then
  `git worktree prune`).
- Pane ids can churn as the workspace changes; re-run `herdr agent list` to re-resolve a
  target rather than caching a pane id across a long session.
- The **owner's live session** already runs many agents (see `herdr agent list`). When the
  chief spawns staff, do it in **new worktrees/workspaces** — never reuse or disturb a pane
  the owner is actively driving.
- Integrations herdr can install/launch: `claude`, `codex`, `copilot`, `droid`, `opencode`,
  and more (`herdr integration status`). This repo uses the `claude` and `codex` lanes.
