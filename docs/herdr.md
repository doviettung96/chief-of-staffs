# Driving staff with `herdr`

`herdr` is a terminal-workspace manager for AI coding agents (`herdr.dev`). It is the
chief's control plane: it spawns real agent terminals, isolates each in a git
worktree, reports every agent's live status, lets the chief read a pane and send it
text, and can notify the owner. **All commands below are verified against the running
build** (`herdr <group> --help`). Config: `~/AppData/Roaming/herdr/`.

> Golden rule: the chief drives staff **only** through `herdr`. Sub-agents are summoned
> by staff inside their own harness — never by the chief.

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
herdr agent start <name> --cwd <worktree-path> -- codex          # GPT-5.6 lane
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

```bash
# 1. Isolate
WT=$(herdr worktree create --cwd C:/Users/Tung/Projects/<proj> \
      --branch feat/<task> --base <integration-branch> --json | jq -r .result.worktrees...path)
# 2. Spawn (pick lane per docs/agents.md)
herdr agent start <task> --cwd "$WT" -- claude
# 3. Brief
herdr agent wait <task> --status idle --timeout 120000
herdr agent send <task> "GOAL: ...  SCOPE: ...  DONE WHEN: ...  Open a PR when green."
# 4. Watch — loop over `herdr agent list`; on `blocked`, read + decide or escalate
# 5. Integrate — see docs/git-worktrees.md (verify PR mergeable, decide order, merge, build)
# 6. Teardown
herdr worktree remove --workspace <id>
```

## Notes / gotchas

- `agent send` is literal text — it does **not** press Enter for a shell; use `pane run`
  for shell command lines. For a chat agent (claude/codex prompt), `agent send` is right.
- Pane ids can churn as the workspace changes; re-run `herdr agent list` to re-resolve a
  target rather than caching a pane id across a long session.
- The **owner's live session** already runs many agents (see `herdr agent list`). When the
  chief spawns staff, do it in **new worktrees/workspaces** — never reuse or disturb a pane
  the owner is actively driving.
- Integrations herdr can install/launch: `claude`, `codex`, `copilot`, `droid`, `opencode`,
  and more (`herdr integration status`). This repo uses the `claude` and `codex` lanes.
