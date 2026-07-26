# chief-of-staff

The brain and memory of an AI **Chief of Staff** — an orchestrator that sits between
the owner and a fleet of working agents ("staff") across many projects. It plans,
delegates, watches, unblocks, and integrates their work so the owner only sets goals
and answers the few decisions that truly need them.

```
Owner (human)  →  Chief of Staff  →  Staff (1 per worktree, via herdr)  →  Sub-agents
   L0                  L1                        L2                            L3
```

## Read in this order

1. [`identity.md`](identity.md) — who the Chief is; the 4-level chain of command.
2. [`docs/orchestration.md`](docs/orchestration.md) — the loop the Chief runs.
3. [`docs/herdr.md`](docs/herdr.md) — how it spawns and drives staff.
4. [`docs/agents.md`](docs/agents.md) — the Claude/Opus and codex/GPT-5.6 lanes.
5. [`docs/git-worktrees.md`](docs/git-worktrees.md) — conflict-free integration.
6. [`AGENTS.md`](AGENTS.md) — the full index and core rules.

## Layout

```
identity.md            who the Chief is
docs/                  the operating manual (orchestration, herdr, agents, git)
projects/              per-project registry — one folder per managed project
  <name>/overview.md   about + vision + focus        (human-owned)
  <name>/decisions.md  past decisions and why        (human-owned)
  <name>/lessons.md    mirror of the project's LESSONS.md   (generated)
  <name>/status.md     live git + PRs + agents        (generated)
scripts/sync-project.py  onboard/refresh a project entry
LESSONS.md             the Chief's own operating lessons
```

## Onboard a project

```bash
python scripts/sync-project.py <repo-or-name>   # one project
python scripts/sync-project.py --lessons        # all repos with a LESSONS.md
```
