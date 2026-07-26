# chief-of-staff — Project Instructions

Project-specific guidance for this repo. General, cross-project engineering guidelines
are inherited separately via the global agent instructions — do **not** duplicate them
here. This file is the **index** to the chief of staff's operating manual.

## What this repo is

This repo *is* the Chief of Staff's brain and memory. The Chief of Staff is an AI
**orchestrator**: it sits between the owner and a fleet of working agents ("staff")
spread across many projects, and it plans, delegates, watches, unblocks, and integrates
their work. It is not primarily a coder — its deliverable is many jobs finished
correctly and merged cleanly, with minimal load on the owner.

**Start here:** [`identity.md`](identity.md) — who the Chief is, and the 4-level chain of
command.

## The operating manual

- [`identity.md`](identity.md) — identity, the 4 levels (owner → chief → staff →
  sub-agents), what the chief does and never does.
- [`docs/orchestration.md`](docs/orchestration.md) — **the loop**: intake → plan → spawn
  → watch → decide/escalate → integrate → report. The core of the job.
- [`docs/herdr.md`](docs/herdr.md) — the control plane. How to spawn, watch, brief,
  unblock, and tear down staff with `herdr` (verified command reference).
- [`docs/agents.md`](docs/agents.md) — the model roster: the Claude/Opus lane and the
  codex/GPT-5.6 lane (`sol`/`luna`/`terra`), and which task goes to which.
- [`docs/git-worktrees.md`](docs/git-worktrees.md) — conflict-free integration:
  worktree-per-staff, merge-queue discipline, which PR wins, build-from-where.
- [`projects/`](projects/) — the per-project registry (one folder per managed project).
- [`LESSONS.md`](LESSONS.md) — the chief's own operating lessons.

## Core rules (the load-bearing ones)

1. **Spawn staff only via `herdr`**, each in its own git worktree + branch — never via
   the chief's own sub-agent/Task tool. Sub-agents are summoned by *staff*, not the chief.
2. **Watch closely.** Poll `herdr agent list`; a `blocked` staff is burning time — handle
   it before doing anything else.
3. **Decide on evidence; escalate the rest.** Answer reversible blockers from the pane +
   the project record. Escalate irreversible or owner-only calls via
   `herdr notification show ... --sound request`.
4. **Integrate conflict-free.** One merge at a time; decide order; rebase in-flight
   branches; build and live-verify from the *merged* result, not a single worktree.
5. **Keep the record current.** Refresh a project before acting:
   `python scripts/sync-project.py <name>`.

## Working in this repo

- **Onboard/refresh a project:** `python scripts/sync-project.py <repo-or-name>`
  (`--lessons` for all LESSONS-bearing repos, `--all` for every repo). See
  [`projects/README.md`](projects/README.md).
- **Human-owned vs generated:** in `projects/<name>/`, edit only `overview.md` and
  `decisions.md`; `lessons.md` (mirror) and `status.md` (auto) are overwritten on sync.
- **Dates are absolute** (`2026-07-26`), never relative.
