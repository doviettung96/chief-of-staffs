# The orchestration loop

How the chief turns an owner goal into merged, verified work across a fleet of staff.
Read [`identity.md`](../identity.md) first (who does what), [`docs/hc.md`](hc.md) for the
controls, and [`docs/git-worktrees.md`](git-worktrees.md) for integration.

## When to orchestrate at all

An orchestrator costs tokens, latency and detail lost in every handoff. It pays when the
owner would otherwise be the bottleneck:
- **several independent tasks** (projects, targets, modules) that can run in parallel;
- **long tasks** that should progress while the owner is away;
- **cheaper staff models** whose "done" needs an independent check;
- tasks that **share** something (a repo to merge into, findings, devices).

A small, tightly coupled task the owner is driving live (one hook chain on one game) is
better done by one agent directly. Say so instead of spawning.

## The loop

```
        ┌──────────────────────────────────────────────────────────┐
        │                                                          │
 INTAKE ─▶ PLAN ─▶ SPAWN ─▶ WAIT FOR NEWS ─▶ TRIAGE ─▶ decide / escalate
                     ▲                          │                  │
                     │                          ▼                  │
                     └────────── INTEGRATE ◀── READY ─▶ REPORT ────┘
```

### 1. Intake
The owner states a goal. The chief restates it as a concrete outcome and a definition of
done. If only the owner can resolve an ambiguity, ask **now**, before spawning anyone.

### 2. Plan
- Read the project record: `projects/<name>/overview.md`, `decisions.md`, `lessons.md`,
  and refresh `status.md` (`python scripts/sync-project.py <name>`).
- Decompose into **staff-sized tasks**, each with its own branch, base and done-condition.
  **Partition by file/module** so parallel staff don't touch the same code
  (docs/git-worktrees.md). Tasks that share code are sequenced, not parallelised.
- Pick a lane per task ([`docs/agents.md`](agents.md)) and say it before spawning.
- Spawn no more staff than you can triage. A report nobody reads is a stalled worker.

### 3. Spawn
For each task: worktree on a fresh branch, then

```bash
python scripts/staff.py spawn <name> --lane <lane> --cwd <worktree> --brief-file <brief.md>
```

The brief has four parts, and `staff.py` appends the reporting rules itself:

> **GOAL**: the outcome. **SCOPE**: what is in and out of bounds (files, targets, devices).
> **CONSTRAINTS**: from `lessons.md` / `decisions.md`. **DONE WHEN**: the verifiable
> condition, then commit + PR (or what to deliver instead).

Write the brief so the worker can start without asking. Its first message only points at
the brief file. A spawn that exits 2 (`needs_owner`) is held by a first-run dialog: show the
owner, never answer it.

### 4. Wait for news (never poll)
```bash
hc wait --children any --timeout 600
```
It returns on the **next piece of news**: a staff report (`reason: message`), a child that
blocked, errored or exited, or the owner typing to the chief. A `timeout` is a check-in,
not a failure: look at the board, then wait again. Do not loop on `hc ls`, do not
`sleep`, and do not block on one worker while others report.

### 5. Triage
`python scripts/staff.py board`. Handle **NEEDS CHIEF** first, then **READY**, and leave
**WORKING** alone.

| what you see | what it means | do |
| --- | --- | --- |
| report `waiting` | it asked a question (in the note) | answer it from evidence + the record, or escalate (step 6) |
| report `blocked` / `failed` | it cannot go on | read the note + `--details`, decide: unblock, re-scope, or stop |
| hc `blocked` | a permission/question dialog in the agent | `hc read` it and show the owner. Never answer it yourself |
| `silent` | no report, no status for 90 s | `hc read` it. Usually a first-run dialog (codex) or a hung tool |
| `exited(n)` | the process died | `staff.py respawn <name>` if the task is still live |
| report `ready` | it claims DONE WHEN | **verify it yourself** (step 7). Its claim is not evidence |

### 6. Decide or escalate
1. **Read the evidence**: the report and its details file, the diff, the logs.
2. **Can I answer it from evidence + the project record**, and is it reversible? Then
   `hc send <name> "<decision + why>"`.
3. **Otherwise escalate**: one crisp question with the real options and your
   recommendation, in your reply to the owner (or `AskUserQuestion`). Relay the answer to
   the same worker.

Decide the *reversible* things yourself; escalate the *irreversible*, product-direction and
outward-facing ones.

### 7. Integrate
Verify the `ready` claim in the worktree: `git log`, `git status`, run the test or the
deliverable. Workers misreport. In the trial run, a worker amended a commit it was told not
to amend, then said so itself. Then integrate conflict-free, one merge at a time, and build
and verify from the **merged** result ([`docs/git-worktrees.md`](git-worktrees.md)).

### 8. Report and tear down
Tell the owner what merged, what is in flight, what is blocked on them and what is next.
`staff.py teardown <name>`, remove the worktree, refresh `status.md`. Capture non-obvious
lessons (global §6: ask before saving).

## Operating principles

These came from studying other orchestrators (herd, DeepSeek's dsh-superagent) against what
went wrong here. Each one names the failure it prevents.

1. **The chief routes. It does not do the work.** No reverse engineering, implementation
   or long investigation in the chief's own context: that is what staff are for. A chief
   deep in a decompile is a chief not answering reports, and its context fills with detail
   that crowds out the fleet. It reads code only to verify a claim or to write a brief.
2. **Staff report their state; the chief never guesses it from a screen.** Every turn ends
   with `staff.py report`. hc status is a fallback, and codex has none. `idle` alone can
   mean done, stuck or waiting.
3. **News is pushed, not polled.** `hc wait --children any` is the only waiting the chief
   does. No `sleep`, no polling loops, no long blocking call on a single worker.
4. **The owner always gets through.** The owner talks to the chief; a message from the
   owner ends the chief's wait (`reason: message`). Never sit in a command that blocks
   longer than a few minutes. Run slow builds and tests in an hc terminal
   (`hc run --bg ... ; hc wait`). Answer "what's going on?" from the board, not by reading
   every screen.
5. **A task keeps its worker.** Follow-ups, answers and "also do X" go to the worker that
   owns the task, by name, because its context holds what it learned. Route a message to a
   worker only on an explicit match (same task, same branch). Two tasks that merely sound
   similar are not the same task. A dead worker is **resumed** in its own worktree
   (`staff.py respawn`), not replaced by a fresh one.
6. **After a restart, check before acting again.** A resumed worker gets a recovery note:
   re-read the brief, check git and every outside effect (PRs, processes, devices, game
   clients, locks) before repeating anything. Re-injecting into a game or re-launching an
   emulator blindly is the failure this prevents.
7. **Leftovers have an owner and a limit.** Anything a worker starts (a Frida session, an
   emulator, a server) is that worker's to stop when its turn or task ends. A worker that
   finishes with background work still running is told to stop it. Long-lived runtime
   resources are claimed and released through the resource broker once it exists, so a
   dead worker's claims can be freed.
8. **Enforce in code what must hold; prompts are advice.** Scope a worker by what it can
   reach (its own worktree, its own target address in its environment, its own MCP config),
   not only by "don't touch X" in the brief. Prompt rules are for judgment calls.
