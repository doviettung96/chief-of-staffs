# thienanh-novagate

> Human-owned. `About`/`Current focus` filled from repo evidence on 2026-07-26;
> `Vision` is a **draft candidate** — confirm/adjust. Never overwritten by sync.

## About

A **GAP-consuming game bot** focused on team hunts. It layers loot/economy logic on top
of GAP — loot star-filtering, native sell-by-star, auto-pickup — plus local-player
death-state detection and native login-error handling. GAP is consumed as an **editable
package** (migrated off a submodule).

## Vision

_Draft (confirm):_ a team-hunt automation built entirely on GAP capabilities — hunting,
loot decisions, and multi-device coordination all inherited from the platform, with this
repo owning only game-specific reversing and the hunt/economy policy.

## Current focus

The GAP-migration wave has landed on `main` (working tree clean, no open PRs as of
2026-07-27): DeviceGate consumed + `app/maintenance.py` evacuated (#40); the big GAP
migration — HuntBehavior, Deployer, pure-GAP supply, controller→toolkit (#46);
native login-error dialog detection + `session.dismiss_error` (#37).

**Shipped 2026-07-27: auto-consume during autofight/team-hunts** (GAP #26 + thienanh #47,
both merged). GAP now carries `buffs` on the `Character` contract + a genre-blind,
config-gated `ConsumeMixin` (OFF by default, `item.use`-only, one decision/tick after
death-recovery): threshold HP/MP potions (defaults 50%/30%) + food-buff *maintenance*
(re-eat when the regen buff is absent). thienanh consumes it via a native buff reader
(`RoleData.BufferDataList`) + `SpriteUseGoods` + level-aware auto-selection wired into the
team-hunt path (ON by default). Item eligibility is **grade-based** (consumables carry a
*grade*; a char can use up to a grade→required-level map — verified live: lv50 uses grade-3
food 130/hp 102/mp 113, excluded from grade-4). Live-proven on device 5557. Deferred: a
grade-4 food whose regen buff id differs from 100020 (fleet is grade-3 today).

## Constraints & gotchas the chief must respect

- See [`lessons.md`](lessons.md) — e.g. bound the injector call with a timeout, not just the ping.
- Consumes **GAP** as an editable package — cross-cutting behavior belongs upstream in GAP
  (global §7), not forked here. Ask before bumping the GAP pin.
