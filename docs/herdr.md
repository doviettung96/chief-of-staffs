# Driving staff with `herdr`

`herdr` is a terminal-workspace manager for AI coding agents (`herdr.dev`). It is the
chief's control plane: it spawns real agent terminals, isolates each in a git
worktree, reports every agent's live status, lets the chief read a pane and send it
text, and can notify the owner. **All commands below are verified against the running
build** (`herdr <group> --help`). Config: `~/AppData/Roaming/herdr/`.

> Golden rule: the chief drives staff **only** through `herdr`. Sub-agents are summoned
> by staff inside their own harness — never by the chief.

> **`herdr` supersedes `agtx`.** Some projects' own docs still reference an older `agtx`
> board/worktree workflow — that is **retired**. Orchestrate everything through `herdr`;
> where a project still names agtx, mark it for cleanup in its `projects/<name>/overview.md`.

## Targets

A staff agent is addressed by any of: its **terminal id** (`term_...`), its **pane id**
(`w4:pD`), a unique **agent name**, or a detected label. `herdr agent list` prints all
of these. `agent send` writes literal text; `pane run` writes a command **and** Enter.

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
herdr agent start <name> --cwd <worktree-path> -- codex.cmd      # GPT-5.6 lane
# NOTE (Windows): launch the codex lane as `codex.cmd`, NOT bare `codex`. herdr
# does a raw CreateProcessW; bare `codex` resolves to npm's extensionless Unix
# shell shim, which Windows can't execute -> `agent_start_failed ... %1 is not a
# valid Win32 application (os error 193)`, and the lane silently falls back to
# Claude. `codex.cmd` is the npm-generated Windows launcher (recreated on every
# codex update), so it stays valid across upgrades. See LESSONS.md.
# `start` launches the agent; give it its task once it's up (see "Hand a task", below).
```

### Hand a task / answer a block
```bash
herdr agent send <target> "<task or decision text>"   # literal text into the agent
herdr pane run <pane_id> "<command>"                   # command text + Enter
```
Pattern: `agent start ...` → wait for `idle` (agent booted) → `agent send <target> "<full task brief>"`.

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

# 2. Spawn (pick lane per docs/agents.md; --no-focus so it doesn't grab the owner's screen)
herdr agent start <task> --cwd "$WT" --no-focus -- claude

# 3. Boot: wait for idle, then clear the FIRST-RUN TRUST PROMPT.
herdr agent wait <task> --status idle --timeout 120000
herdr agent read <task> --lines 20          # a fresh claude asks "trust this folder?" — option 1
herdr pane send-keys <pane_id> Enter        # accept (it's your own worktree)

# 4. Brief — send the text, THEN submit with Enter (agent send does NOT press Enter).
herdr agent send <task> "GOAL: ...  SCOPE: ...  DONE WHEN: ...  <commit / open a PR>"
herdr pane send-keys <pane_id> Enter

# 5. Watch — confirm it's working, then block until it finishes or blocks.
herdr agent wait <task> --status working --timeout 30000
herdr agent wait <task> --status idle --timeout 300000

# 6. Verify for real — do NOT trust the pane. Check the worktree git state and run the
#    deliverable yourself (an API error can cut a staff off mid-task, before its commit).
git -C "$WT" log --oneline -2 ; git -C "$WT" status --short
#    If DONE WHEN is unmet, nudge the staff to finish (send + Enter) rather than doing it silently.

# 7. Integrate — see docs/git-worktrees.md; build/verify from the MERGED result.

# 8. Teardown
herdr pane close <pane_id>
git -C C:/Users/Tung/Projects/<proj> worktree remove --force "$WT"   # may need a retry — see gotchas
```

## Notes / gotchas

- **`agent send` writes literal text and does NOT submit.** For a chat agent (claude/codex),
  send the text then `herdr pane send-keys <pane_id> Enter`. For a shell line, use `pane run`
  (command + Enter). This bit during the dry-run — the brief sat unsent until Enter.
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
