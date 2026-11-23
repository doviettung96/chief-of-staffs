# Agents & models the chief works with

Two lanes are in use: **omp** for staff, **Claude Code** for the chief (and for staff
only with the owner's yes). Verify the live roster any time with the commands at the
bottom; this list is a snapshot.

codex is no longer used (owner, 2026-11-23). Its lane was removed from `staff.py`; git
history has it if it ever comes back.

## Lane A — omp (the "GLM" lane): the staff default

- **Launch:** `staff.py spawn <name> --cwd <wt> --brief-file <f>` (omp is the default
  lane) runs `omp "<msg>"` (omp `v19.1.0`). Its own model roles pick the model:
  `default: delify/GLM-5.3`, `rea: delify/GLM-5.3-rea` (`~/.omp/agent/config.yml`).
  `--model` on `spawn` overrides it (`--model GLM-5.3-rea` for reverse-engineering work).
- **Watchable:** reports hc status itself (`app: omp`), and showed no first-run dialog
  in a fresh worktree. It has the `rea` MCP tools connected.
- **Resume:** `omp --continue` (what `staff.py respawn` uses).
- **Instructions it loads** (asked it, 2026-11-22): only `~/.omp/agent/AGENTS.md` and the
  repo's `AGENTS.md`. Not the global guidelines (deliberately: that file claims omp's
  user slot) and not `D:/Projects/AGENTS.md`. Its file carries a copy of global §10 and a
  summary of §12 (staff mode); the brief `staff.py` writes carries the rest. So **a rule
  every worker must follow goes in the brief**, never only in a parent `AGENTS.md`.
- **Verified 2026-11-22**: spawned in its own tab, fixed + tested + committed a bug, sent
  4 reports, was killed and resumed: it checked its state, found the work done, and did
  not repeat it. In the staff-mode test it asked the chief before changing a test (the
  spec), stayed in scope and named the out-of-scope typo it had left.
- **Watch for:** it can misstate details (one details file said "not committed" about a
  commit that existed). Verify every `ready` in the worktree.

## Lane B — Claude Code (the "Opus" lane): the chief, and staff on request

- **Launch:** `claude` (Claude Code CLI); `staff.py spawn ... --lane claude` for staff.
- **Model:** Opus-class; confirm inside the agent with `/model` or `claude --version`.
  Default reasoning effort is set high (`~/.claude/settings.json`).
- **This is the chief's own lane**: the chief itself runs here.
- **Strengths:** long-context reasoning, architecture and planning, careful multi-file
  refactors, reading large unfamiliar codebases, orchestration and judgment.
- **Role for staff: permission-gated.** The chief never spawns Claude staff on its own.

## Picking a lane per task

- **Default: omp, for every staff task**, whatever its shape: design, refactor,
  debugging, reverse engineering, mechanical fan-out. Constrain it with a tight brief
  and verify its claims; don't switch lanes for "safety".
- **Claude staff: ask the owner first, every time.** Never `--lane claude` on your own
  initiative. Even when omp genuinely cannot run (provider down, rate-limited, a worker
  erroring mid-task that can't recover), stop and ask: "omp is <failure>: OK to run this
  on Claude instead?", then wait for a yes. No silent fallback. (Owner's rule, set
  2026-07-29, after the chief summoned Claude without asking.) A launch error from your
  own invocation (a wrong flag, a missing exe) is your bug, not an omp failure: fix it
  and retry omp.
- **State the lane before spawning**: "Lane: omp (GLM-5.3)" or "Lane: omp
  (GLM-5.3-rea), RE work".

## Reasoning effort

- omp: `--thinking off|minimal|low|medium|high|xhigh|max|auto`, passed through
  `staff.py spawn ... --agent-arg=--thinking=high`.
- Claude: `~/.claude/settings.json` → `effortLevel` (currently `high`).

Raise effort for the hard reasoning stages; drop it for cheap mechanical fan-out.

## Verify the live roster

```bash
omp --version ; grep -A3 modelRoles ~/.omp/agent/config.yml   # omp + its model roles
omp models                                                     # what omp can reach
claude --version                                               # then /model inside it
```
