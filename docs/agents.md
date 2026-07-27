# Agents & models the chief works with

Two lanes are available in this environment. The chief assigns each staff task to
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
- **Role for staff — the fallback lane.** On the owner's flat subscription, so always
  available. Assign staff here only when codex cannot run the task (see "Picking a lane
  per task"): proxy down, api-key expired/rate-limited, model unavailable, or a codex
  staff erroring out mid-task.

## Lane B — codex (the "GPT-5.6" lane)

- **Launch:** `codex` (codex-cli, `0.145.0` at last check), routed through a local
  proxy (**CLIProxyAPI** on `http://127.0.0.1:8317`). Default model `gpt-5.6-sol`,
  reasoning effort `high`, plan-mode `xhigh` (`~/.codex/config.toml`).
- **GPT-5.6 variants** served by the proxy:
  - `gpt-5.6-sol` — codex's current default. The general-purpose 5.6.
  - `gpt-5.6-luna` — alternate 5.6 variant.
  - `gpt-5.6-terra` — alternate 5.6 variant.
  - _Characterize luna/terra empirically before leaning on a distinction — treat them
    as peers of sol until proven otherwise; don't invent a hierarchy._
- **Older / fallback models on the proxy:** `gpt-5.5`, `gpt-5.4`, `gpt-5.4-mini`,
  `gpt-5.3-codex-spark`, plus `codex-auto-review` and image models
  (`gpt-image-1.5`, `gpt-image-2`).
- **Strengths:** equally capable across task shapes; fast iteration inside the codex
  sandbox and cheap to fan out for high-volume parallel work.
- **Role for staff — the default lane.** Assign every staff task here (`sol` unless a
  task specifically calls for `luna`/`terra`). Metered through CLIProxyAPI, so it can be
  unavailable — when it is, fall back to the Claude lane.

## Picking a lane per task

**Default to codex; fall back to Claude only when codex is unavailable.** Both lanes
are equally capable — the deciding factor is *availability*, not task shape. codex runs
through CLIProxyAPI (metered; its api-key can expire or rate-limit, and the proxy can be
down), while the Claude lane is on the owner's flat subscription and is therefore the
reliable backstop.

- **Default lane — codex.** Assign every staff task to codex (`sol` unless a task
  specifically calls for `luna`/`terra`). This is the standing rule for all work shapes:
  design, refactor, debugging, mechanical fan-out, drafts.
- **Fallback lane — Claude (Opus).** Summon a Claude staff agent only when codex cannot
  run the task: CLIProxyAPI is down, the proxy api-key has expired or is rate-limited,
  the requested model isn't served, or a codex staff errors out mid-task and can't
  recover. When falling back, say so and name the codex failure.

The chief itself still runs on Opus (it is the Claude Code process the owner talks to);
this policy is about which lane the chief spawns **staff** into.

Two independent knobs remain in play: **which lane** (now: codex by default, Claude on
failure) and **how many in parallel** (throughput — fan codex out freely).

**State the lane before spawning.** Before every `herdr agent start`, say the lane and
the one-line reason: e.g. "Lane: codex (sol)" or "Lane: claude — codex proxy returned
401, api-key expired".

## Reasoning effort

- Claude: `~/.claude/settings.json` → `effortLevel` (currently `high`); per-agent via `/model`-adjacent controls.
- codex: `~/.codex/config.toml` → `model_reasoning_effort` (`high`), `plan_mode_reasoning_effort` (`xhigh`); or `/model` inside codex.

Raise effort for the hard reasoning stages; drop it for cheap mechanical fan-out.

## Verify the live roster

```bash
# GPT / proxy models (needs the local proxy api-key from ~/CLIProxyAPI/config.yaml):
curl -s -H "Authorization: Bearer <sk-local-...>" http://127.0.0.1:8317/v1/models

# codex + claude versions and current model config:
codex --version ;  cat ~/.codex/config.toml
claude --version   # then /model inside a running agent
```
