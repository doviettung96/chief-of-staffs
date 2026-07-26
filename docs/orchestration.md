# The orchestration loop

How the chief turns an owner goal into merged, verified work across a fleet of staff.
Read [`identity.md`](../identity.md) first (who does what), [`docs/herdr.md`](herdr.md)
for the controls, and [`docs/git-worktrees.md`](git-worktrees.md) for integration.

## The loop

```
        ┌──────────────────────────────────────────────────────────┐
        │                                                          │
 INTAKE ─▶ PLAN ─▶ SPAWN ─▶ WATCH ─▶ (BLOCKED? decide / escalate) ─┤
                     ▲                        │                     │
                     │                        ▼                     │
                     └──────── INTEGRATE ◀── DONE ─▶ REPORT ────────┘
```

### 1. Intake
The owner states a goal — for one project or several. The chief restates it as a
concrete outcome and a definition of done. If the goal is underspecified in a way only
the owner can resolve, ask **now**, before spawning anyone.

### 2. Plan
- Read the project's record: `projects/<name>/overview.md`, `decisions.md`, `lessons.md`,
  and refresh `status.md` (`python scripts/sync-project.py <name>`).
- Decompose into **staff-sized tasks**: each independently scoped, each with its own
  branch, base, and done-condition. **Partition by file/module** so parallel staff don't
  touch the same code (this is how conflicts are prevented — see git-worktrees.md).
- Pick a **lane per task** ([`docs/agents.md`](agents.md)): Opus for hard/ambiguous/risky,
  codex for scoped/mechanical/parallel.
- Decide **degree of parallelism**. Independent tasks → fan out. Tasks that share code →
  sequence them.

### 3. Spawn
For each task: create an isolated worktree on a fresh branch, start the chosen agent in
it, wait for `idle`, then send a **complete brief**:

> GOAL — the outcome. SCOPE — files/areas in bounds and out. CONSTRAINTS — from
> `lessons.md`/`decisions.md`. DONE WHEN — the verifiable condition. Then: open a PR.

One staff, one worktree, one branch. Never two staff on the same branch.

### 4. Watch (this is the core of the job)
Poll `herdr agent list` on a cadence. For each staff:
- **`working`** → leave it; note its title/progress.
- **`idle`** after a brief → likely done or waiting; read the pane to confirm, then
  move it to Integrate or send the next step.
- **`blocked`** → **act immediately.** A blocked agent is burning wall-clock. Read its
  pane (`herdr agent read`), then decide or escalate (step 5).

Keep a running mental (or written) board of who's on what and its state. Do not spawn so
many staff that you can't watch them — throughput is worthless if blocks sit unnoticed.

### 5. Blocked → decide or escalate
Decision procedure (from `identity.md`):
1. **Read the evidence** — pane output, the diff, test/build logs.
2. **Can I answer it from evidence + the project record?** If yes and it's not
   irreversible or the owner's call → `herdr agent send <target> "<decision + why>"`.
3. **Otherwise escalate**: collapse the blocker into one crisp question with the real
   options and your recommendation, `herdr notification show "<proj>: decision needed"
   --body "..." --sound request`, and surface it to the owner. Park or reassign the
   staff meanwhile so a seat isn't wasted.

Bias: decide the *reversible* things yourself (they can be fixed in review); escalate the
*irreversible* or *product-direction* things.

### 6. Integrate
When a staff opens a PR: verify it, then integrate it **conflict-free** — decide merge
order, which branch wins on overlap, what to rebase, and **build/verify from the merged
result**, not from the individual worktree. Full procedure:
[`docs/git-worktrees.md`](git-worktrees.md).

### 7. Report
Tell the owner what merged, what's in flight, what's blocked on them, and what's next.
Update `projects/<name>/status.md` (re-run the sync). Capture any non-obvious lesson per
§6 of the global guidelines (ask before saving).

## Watching many staff at once — a concrete cadence

```bash
# one poll tick:
herdr agent list \
  | jq -r '.result.agents[] | "\(.agent_status)\t\(.pane_id)\t\(.cwd)\t\(.terminal_title_stripped)"'
# -> triage: handle every `blocked` first, then check `idle` (done?), then note `working`.
```
Between ticks, block efficiently on the next event instead of busy-polling:
```bash
herdr agent wait <the-one-i-care-about> --status blocked --timeout 600000
```

## What the chief must never do

- Merge unverified work, or merge two conflicting branches without deciding order first.
- Let a `blocked` staff sit while the chief does deep work itself.
- Spawn staff into a pane the owner is actively using, or onto a branch another staff owns.
- Make an irreversible/outward-facing call (force-push, prod deploy, shared default branch)
  without the owner — escalate instead (global guidelines §8).
