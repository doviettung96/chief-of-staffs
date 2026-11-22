# Agents & models the chief works with

Three lanes are available in this environment. The chief assigns each staff task to
the lane and variant that fits it. Verify the live roster any time with the commands
at the bottom — do not trust this list blind; it is a snapshot.

## Lane A — Claude Code (the "Opus" lane)

- **Launch:** `claude` (Claude Code CLI). Version at last check: `2.1.212`.
- **Model:** Opus-class. This environment provisions **Opus 5.00**; a given running
  agent may report a different exact build — confirm inside the agent with `/model`
  or `claude --version`. Default reasoning effort is set high (`~/.claude/settings.json`).
- **This is the chief's own lane** — the chief itself runs here.
- **Strengths:** long-context reasoning, architecture and planning, careful
  multi-file refactors, reading large unfamiliar codebases, orchestration and
  judgment. Fully capable across every task shape.
- **Role for staff — permission-gated only.** On the owner's flat subscription, so always
  available — but the chief never spawns Claude staff on its own. It requires explicit owner
  confirmation, even when codex cannot run (see "Picking a lane per task"). Ask first.

## Lane B — codex (the "GPT-5.5" lane)

- **Launch:** `staff.py spawn <name> --lane codex ...` runs `codex -m gpt-5.5 "<msg>"`
  (codex-cli `0.145.0`, now a native exe at `...\Programs\OpenAI\Codex\bin\codex`, so
  the old `codex.cmd` workaround is gone). Routed through a local proxy (**CLIProxyAPI**
  on `http://127.0.0.1:8317`); reasoning effort `high`, plan-mode `xhigh`.
  - **The model is passed explicitly** because `~/.codex/config.toml` itself now says
    `model = "gpt-5.6-sol"` (seen 2026-11-22). `--model` on `spawn` overrides it.
  - **codex reports no hc status**, not even in a dialog: the chief knows its state
    only from its `staff.py report`s, and a codex worker that never reports shows as
    `silent` on the board.
  - **First worker in a repo hits two dialogs**: "trust this directory" (stored per
    **repo root**, so once per repo covers all its worktrees), then a hook review (the
    old herdr TUI's hook, inert under hc). Both are the owner's to answer.
- **Default staff model:** `gpt-5.5`. Use this for staff unless the owner explicitly
  requests a different model. The GPT-5.6 variants are currently high-load and often
  report capacity errors, which can halt staff execution mid-task.
- **High-load / explicit-only GPT-5.6 variants** served by the proxy:
  - `gpt-5.6-sol` — general-purpose 5.6 variant.
  - `gpt-5.6-luna` — alternate 5.6 variant.
  - `gpt-5.6-terra` — alternate 5.6 variant.
  - _Characterize luna/terra empirically before leaning on a distinction — treat them
    as peers of sol until proven otherwise; don't invent a hierarchy._
- **Other models on the proxy:** `gpt-5.4`, `gpt-5.4-mini`,
  `gpt-5.3-codex-spark`, plus `codex-auto-review` and image models
  (`gpt-image-1.5`, `gpt-image-2`).
- **Strengths:** equally capable across task shapes; fast iteration inside the codex
  sandbox and cheap to fan out for high-volume parallel work.
- **Role for staff — the default lane.** Assign every staff task here on `gpt-5.5`
  unless the owner explicitly requests another model. Metered through CLIProxyAPI, so it can be
  unavailable — when it is, ask the owner before using Claude (never auto-fall-back).

## Lane C — omp (the "GLM" lane)

- **Launch:** `staff.py spawn <name> --lane omp ...` runs `omp "<msg>"` (omp `v19.1.0`).
  Its own model roles pick the model: `default: delify/GLM-5.3`, `rea: delify/GLM-5.3-rea`
  (`~/.omp/agent/config.yml`). `--model` on `spawn` overrides (`--model GLM-5.3-rea`).
- **Watchable:** reports hc status itself (`app: omp`), and showed no first-run dialog
  in a fresh worktree. It has the `rea` MCP tools connected.
- **Resume:** `omp --continue` (what `staff.py respawn` uses).
- **Instructions it loads** (asked it, 2026-11-22): only `~/.omp/agent/AGENTS.md` and the
  repo's `AGENTS.md`. Not the global guidelines (deliberately: that file claims omp's
  user slot) and not `D:/Projects/AGENTS.md`. Its file carries a copy of global §10 and a
  summary of §12 (staff mode); the brief `staff.py` writes carries the rest.
- **Verified 2026-11-22**: spawned in its own tab, fixed + tested + committed a bug, sent
  4 reports, was killed and resumed: it checked its state, found the work done, and did
  not repeat it.
- **Role for staff:** available for any staff task the owner assigns to it. Like
  every cheaper model, verify its `ready` claims in the worktree.

## Picking a lane per task

**codex is the default for EVERY staff task. Claude staff requires explicit owner
permission — it is NOT an automatic fallback.** Both lanes are equally capable; codex is
the standing choice regardless of task shape, difficulty, or prod-sensitivity.

- **Default lane — codex.** Assign every staff task to codex on `gpt-5.5` unless the
  owner explicitly requests another model. This is the standing rule for all work shapes:
  design, refactor, debugging, mechanical fan-out, drafts — and for hard or prod-touching
  work too. Do **not** switch to Claude for "safety", "caution", or "checkpoint discipline"
  reasons; instead constrain codex through a tight brief and watch it closely.
- **Claude staff — ask the owner first, every time.** Never `staff.py spawn ... --lane
  claude` on your own initiative. Even when codex genuinely cannot run (CLIProxyAPI down,
  api-key expired/rate-limited, `gpt-5.5` at capacity, or a codex staff erroring mid-task that
  can't recover), you **stop and ask**: state the specific codex failure and request
  permission — "codex is <failure> — OK to run this on Claude instead?" — then wait for a
  yes. No silent auto-fallback. (Owner's rule, set 2026-07-29, after the chief auto-summoned
  Claude without asking — once on a codex-capacity fallback, once as a prod-safety judgment
  call.) Note: a launch error from the codex binary itself (a wrong flag, a missing exe) is
  the chief's invocation bug, NOT a codex failure — fix it and retry codex, don't ask for
  Claude.

The chief itself still runs on Opus (it is the Claude Code process the owner talks to);
this policy is about which lane the chief spawns **staff** into.

**State the lane before spawning.** Before every `staff.py spawn`, say the lane and
the one-line reason: e.g. "Lane: codex (`gpt-5.5`)". If you believe Claude is warranted, do not
spawn — ask the owner and wait.

## Reasoning effort

- Claude: `~/.claude/settings.json` → `effortLevel` (currently `high`); per-agent via `/model`-adjacent controls.
- codex: `~/.codex/config.toml` → `model_reasoning_effort` (`high`), `plan_mode_reasoning_effort` (`xhigh`); or `/model` inside codex.

Raise effort for the hard reasoning stages; drop it for cheap mechanical fan-out.

## Verify the live roster

```bash
omp --version ; grep -A3 modelRoles ~/.omp/agent/config.yml   # omp lane + its model roles
```

```bash
# GPT / proxy models (needs the local proxy api-key from ~/CLIProxyAPI/config.yaml):
curl -s -H "Authorization: Bearer <sk-local-...>" http://127.0.0.1:8317/v1/models

# codex + claude versions and current model config:
codex --version ;  cat ~/.codex/config.toml
claude --version   # then /model inside a running agent
```
