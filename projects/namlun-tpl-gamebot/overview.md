# namlun-tpl-gamebot

> Human-owned. `About`/`Current focus` filled from repo evidence on 2026-07-26;
> `Vision` is a **draft candidate** — confirm/adjust. Never overwritten by sync.

## About

A **GAP-hosted autofarm bot**. Phase 5 retired the hand-written `app/` host and moved
everything onto **gap-host**; features include normal + star-field farming behind one
Auto-farm toggle, resilient auto-login (world-select via `WorldSelectPopup`), and
canonical maintenance verbs (`item.use` / `item.bag_scan` / `shop.buy`).

> ⚠ **CLEANUP (in progress):** the project's README anchored it to **Harbor/agtx**
> worktrees. **agtx is retired** — orchestrate via **herdr** now
> (see [`../../docs/herdr.md`](../../docs/herdr.md)). PR open to drop the agtx framing:
> doviettung96/namlun-tpl-gamebot#36.

## Vision

_Draft (confirm):_ a zero-hand-written-host autofarm — every farming, maintenance, and
login behavior expressed as gap-host capabilities/verbs, so the bot inherits reliability
and orchestration from GAP and this repo carries only game-specific reversing.

## Current focus

Phase 5 consolidation on gap-host (#30 merged) plus canonical maintenance verbs
(`item.use`/`bag_scan`/`shop.buy`) and **star-field farming on gap-host** (draft PR #35);
`ext.star_fields` now enumerates the live star/dark/arcane catalog (#34). Branch
`feat/canonical-potion-verbs`.

## Constraints & gotchas the chief must respect

- See [`lessons.md`](lessons.md) — e.g. `0x10010009` after a client update means
  world-select moved to `WorldSelectPopup`.
- Consumes **GAP** — coordinate host changes upstream (global §7), don't fork them here.
