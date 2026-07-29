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

**char.revive actuator + fixes (2026-07-28, GAP #33 + thienanh #52, merged).** The #51
finding — HuntBehavior posts `char.revive` but thienanh's bridge had no actuator, so it was a
silent no-op (death recovery relied on the game's ~18s passive auto-revive) — is now RESOLVED:
a real `char.revive` actuator (native `TriggerRevive` → `UIReviveFrame` buttons, `mode=town`)
wired via the 3-edit adapter path. Also fixed a latent broken window: `session.dismiss_error`
had no native route since #37 (silent 404). GAP got the `RestockRunner` `trigger_at < to` guard.
**Live-verified** on 5557 (death #1): owner bled the char to 0 → our `char.revive` fired at
death+0.69s → alive in a town at +1.73s (vs the ~18s passive auto-revive → that 10× gap is our
actuator). Owner accepted death #1's evidence to merge (the lone "unconfirmed" flag was a
verify-script field-parse bug, not a code issue). Note: the game's own CDN briefly failed to
serve `Config.unity3d`, blocking world entry mid-task — recorded as a lesson.

**Unified consume (2026-07-27, GAP #30 + thienanh #49, merged).** GAP had grown TWO
genre-blind HP/MP drinkers — `ConsumeMixin` (behavior-tick, #26/#28) and a `Maintenance`
concern (#27, controller-tick, single fixed id, trusted the meaningless `item.use.ok`) —
which would double-drink. Reconciled into **one** controller-owned `Consumer` (the proven
count-drop probe + candidate lists + food-buff), ticked cross-cutting so a parked char still
drinks; behaviors no longer consume (double-drink now structurally impossible); `Maintenance`
deleted; single `consume` config, OFF by default; installed per-device on **leader + all
mimics** via `set_consume`. Live-verified on 5557.

**Restock verb layering (2026-07-27, GAP #31 + thienanh #50, merged).** `shop.buy` stays the
atomic buy; new composed verb **`shop.buy_from_npc`** (navigate→open→buy) is served via a
host-side **local-verb registry** (`ctl.register_local_verb`), so it's a real capability. A new
genre-blind GAP **`RestockRunner`** (background sweeper, off by default) owns the restock policy —
prefer `shop.buy_from_npc`, else atomic `shop.buy`, else inert. thienanh's `SupplyRunner`
collapsed to a slim `SupplyInstaller` that maps config → `set_restock` and registers its
`SupplyTour` as the `shop.buy_from_npc` handler (DeviceGate lives in the handler, since
exclusivity is a property of the traversal). Live-verified on 5557 (bag 211→226).

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
team-hunt path (ON by default).

**Refined 2026-07-27: server-probe item selection** (GAP #28 + thienanh #48, both merged).
The earlier guessed grade→level table is **gone**. thienanh now emits, per category, the bag's
items **ordered by grade descending**; GAP's `ConsumeMixin` tries each candidate and treats the
**bag stack-count drop** as the success signal — using the strongest grade the server actually
accepts (stateless, probe every consume). Confirmed by RE that this is the *only* reliable
signal: `SpriteUseGoods` is fire-and-forget (void) and `IsItemCanUse` is a type-only check, so
the server is the sole authority. Live-proven on 5557 (lv50): grade-4 rejected → grade-3
102/113/130 consumed, nothing wasted. Deferred still: a grade-4 food whose regen buff id
differs from 100020 (fleet is grade-3 today).

## Constraints & gotchas the chief must respect

- See [`lessons.md`](lessons.md) — e.g. bound the injector call with a timeout, not just the ping.
- Consumes **GAP** as an editable package — cross-cutting behavior belongs upstream in GAP
  (global §7), not forked here. Ask before bumping the GAP pin.
