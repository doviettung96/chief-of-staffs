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
  judgment, work where being *right* matters more than being fast.
- **Assign Opus staff to:** the hard, ambiguous, or risky task — a design, a
  cross-cutting refactor, a gnarly root-cause debug, anything where a wrong-but-fast
  answer is expensive.

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
- **Strengths:** fast iteration inside the codex sandbox, high-volume parallel work,
  well-scoped mechanical changes, cheap breadth.
- **Assign codex staff to:** clearly-specified, self-contained tasks you want done in
  parallel and fast — apply-a-pattern-across-N-files, mechanical migrations,
  scaffolding, first-draft implementations the chief will review.

## Picking a lane per task

| Task shape | Lane |
|---|---|
| Design / plan / architecture decision | Opus |
| Risky or cross-cutting refactor | Opus |
| Hard root-cause debugging | Opus |
| Reading a large unfamiliar codebase to answer a question | Opus |
| Well-scoped implementation from a settled spec | codex (sol) |
| Apply one pattern across many files / mechanical migration | codex (sol), fan out |
| High-volume parallel drafts to review | codex (sol/luna/terra) |
| The chief itself (orchestration) | Opus |

Two independent knobs, always both in play: **which lane** (capability) and **how
many in parallel** (throughput). Reserve Opus seats for work that needs the judgment;
spend codex breadth on work that needs the volume.

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
