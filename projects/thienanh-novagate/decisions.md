# thienanh-novagate — decisions

> Human-owned decision log: the calls the owner has made and *why*, so the chief
> and its staff don't relitigate settled ground. Newest on top. Dates absolute.

> ⚠ Entries below were **drafted from merged-PR/commit evidence on 2026-07-26**. The
> *Decision* is factual; the *Why* is inferred — confirm or correct it.

## 2026-07-29 — Own a private adb server on a dedicated port, not the shared 5037 (evidence: GAP #34/#36, thienanh #54)
- Status: accepted (owner-directed this session)
- Context: the prod box (100.65.48.37) runs several emulator brands at once — MuMuPlayer +
  LDPlayer9 + xiaowei — each shipping a different-version adb (LD 1.0.31, MuMu 1.0.41,
  xiaowei 34.x). adb has one server per host port (5037); a different-version client keeps
  declaring the running server "out of date" and kills+restarts it, wiping every `adb forward`.
  Live symptom: 0/15 devices online, all stuck lifecycle "deploying", timeouts. The older
  single-brand fix ("bundle the emulator's adb") can't work when >1 brand is present — no single
  version to match.
- Decision: give thienanh its OWN adb server on a private port (5137), isolated from the 5037
  war, and reach each instance over TCP. Baked into the bundle (`launcher.py` + `python/controller.py`
  set `ANDROID_ADB_SERVER_PORT`/`-P` **process-scoped**, operator-overridable) so even a
  double-click is safe. Driven by MuMu's 1.0.41 adb on the box (proven to drive LD's 1.0.31
  daemon over TCP). Shared capability authored upstream in GAP first (`AndroidDeployConfig.adb_server_port`,
  #34) so downstream games inherit it; lesson captured in GAP LESSONS (#36).
- Why: don't fight for a shared port you can't win — step out of the ring. isolation holds for
  any mix of adb versions (and survives emulator updates), unlike version-matching. Never set the
  port machine-wide, or the other brands' adb join it and recreate the war. Per global §7 the
  cross-cutting capability lives in GAP; thienanh (which uses its own Controller, not GAP's
  AndroidDeployer) applies the same in-process.
- Consequences: 0/15 → 15/15 online/in-world on 5137, forwards persist, 5037 untouched. namlun
  (uses GAP's AndroidDeployer) inherits #34 but must rebuild its frozen bundle + set a DISTINCT
  port if co-resident. Device selection is in-memory, so a restart needs a re-confirm (by design,
  per owner). One device (5571) still has a separate, pre-existing injection failure.

## 2026-07-28 — Implement a real char.revive actuator; merge on death-#1 live evidence (evidence: GAP #33, thienanh #52)
- Status: accepted (owner-directed this session)
- Context: the 4-feature integration verify surfaced that `char.revive` was a silent no-op on
  thienanh (no native actuator) — death recovery only worked via the game's ~18s passive
  auto-revive. Owner chose to fix it.
- Decision: implement a real `char.revive` actuator (native `TriggerRevive` clicking the
  `UIReviveFrame` buttons, `mode=town`) via the 3-edit adapter path; also fix `session.dismiss_error`
  (missing native route since #37) and add the GAP `RestockRunner` `trigger_at < to` guard.
- Live verification + the merge call: driving a controlled death was hard (strong HP-regen +
  mob-leashing; the game's Config.unity3d CDN briefly failed, blocking world entry). Eventually
  the owner manually killed the char; our `char.revive` fired at death+0.69s and she was alive in
  a town at +1.73s — vs the game's ~18s passive auto-revive. Owner accepted this timing evidence
  (1.73s ≪ 18s) as proof and merged; the lone "actuator unconfirmed" flag was a verify-script
  field-parse bug (nested vs flat result), not a code defect (see [[config-unity3d-cdn-gate]]).
- Consequences: death recovery no longer depends on the game self-reviving. A fully clean
  actuator-payload capture (die out of town, ~1s poll) remains an optional future confirmation.

## 2026-07-27 — Restock layering: shop.buy_from_npc composed verb + shared GAP restock policy (evidence: GAP #31, thienanh #50)
- Status: accepted (owner-directed this session)
- Context: restock was fully owned in thienanh (`SupplyRunner`/`SupplyTour`); GAP's parked
  simple restock only worked for buy-from-anywhere games. Buying decomposes into decide
  (genre-blind), reach-a-vendor (game-specific), execute (`shop.buy`).
- Decision: keep `shop.buy` as the atomic verb; add composed **`shop.buy_from_npc`**
  (navigate→open→buy), served via a host-side **local-verb registry** so it's a real declared
  capability. Move the restock POLICY into a genre-blind GAP **`RestockRunner`** (background
  sweeper, off by default) that prefers `shop.buy_from_npc`, else `shop.buy`, else inert.
  thienanh keeps only the traversal: `SupplyTour` registered as the handler; `SupplyRunner`
  collapses to a slim installer. DeviceGate stays in the handler (exclusivity = a property of
  the traversal, so atomic-buy games stay ungated).
- Why: buy op AND restock policy shared upstream; per-game contributes only navigation
  (global §7). One consistent capability-gated mechanism; no per-game restock scheduling.
- Consequences: other games (namlun/vlcm) unaffected (off by default, no handler ⇒ inert).
  Completes the consume/restock arc for this session.

## 2026-07-27 — One consume path: unify Maintenance + ConsumeMixin into a controller-owned Consumer (evidence: GAP #30, thienanh #49)
- Status: accepted (owner-directed this session)
- Context: GAP main ended up with two genre-blind HP/MP drinkers that would double-drink —
  `ConsumeMixin` (behavior-tick) and a separate `Maintenance` concern (#27, controller-tick)
  that also had two bugs #48 already solved (trusted `item.use.ok`; single fixed item id).
- Decision: extract the proven consume logic (count-drop probe + candidate lists + food-buff)
  into ONE controller-owned `Consumer`, ticked cross-cutting (a parked/idle char still drinks);
  behaviors stop consuming (double-drink structurally impossible); DELETE `Maintenance`; one
  `consume` config, OFF by default; install per-device on leader + all mimics via `set_consume`.
- Why: one correct drinker beats two competing ones; controller-level ticking keeps the
  cross-cutting benefit Maintenance had, without its bugs. Genre-blind + off-by-default keeps
  other GAP games unaffected.
- Consequences: GAP restock parked off-by-default for now. **Follow-up queued:** `shop.buy` vs
  `shop.buy_from_npc` verb layering + shared GAP restock policy (thienanh `SupplyTour` becomes
  the `shop.buy_from_npc` impl) — the owner deferred this to its own task.

## 2026-07-27 — Consumable selection = server-probe by grade, not a guessed level table (evidence: GAP #28, thienanh #48)
- Status: accepted (owner-directed this session)
- Context: the first cut resolved which item to use via a guessed grade→required-level config
  map — fragile data we invented from two live points, because consumables expose no numeric
  required level (`ReqProp` is equipment-only; reads 0).
- Decision: drop the table. Probe the server instead — try the strongest item highest grade →
  lowest, and use the first one whose **bag stack-count drops** after `item.use` (that drop is
  the success signal). Stateless: probe on every consume; a too-high grade is a no-op. GAP takes
  an ordered candidate-id list per category and tries until one is accepted (stays genre-blind);
  thienanh emits the list ordered by grade desc.
- Why: needs zero knowledge of the level mapping, adapts to any game/grade, and removes a magic
  constant. RE confirmed it's the ONLY reliable signal: `SpriteUseGoods` is fire-and-forget and
  `IsItemCanUse` is type-only — the server is the sole authority (see [[consume-success-signal]]).
- Consequences: a few no-op use calls per consume (owner accepts). Supersedes the grade→level
  map from the entry below. Overlaps with a separate GAP workstream (#27 keep-alive maintenance)
  that also drinks HP/MP — reconcile before both land.


- Status: accepted (owner-directed this session)
- Context: autofight/team-hunts did death-recovery only (revive after death; HP never used
  preemptively). Nothing drank potions or ate food.
- Decision: add auto-consume. Potions = threshold (HP<50% / MP<30%, configurable). Food =
  maintain a regen buff — re-eat whenever the buff status is absent (owner rejected a timer
  hack; requires a real buff reader). Item eligibility is **grade-based**: consumables carry
  a grade, gated by a config `grade→required-level` map (grade2=30, grade3=50, grade4=70,
  overridable); the resolver picks the strongest item the character can actually use per
  category — NOT a fixed id, and NOT the `ItemData.Level` field (which reads 0). Cross-cutting
  behavior + `Character.buffs` live upstream in GAP (genre-blind `ConsumeMixin`, OFF by
  default); the native buff reader + grade map + wiring live in thienanh (ON by default).
- Why: keeps the char alive/regen'd during hunts without owner babysitting; genre-blind
  consume is a platform concern (every GAP bot inherits it), game-specifics stay here.
- Consequences: GAP consumers get consume for free once they opt in via config. Deferred:
  a grade-4 food whose buff id differs from 100020 (current fleet is grade-3).

## 2026-07 — Consume GAP as an editable package, not a submodule (evidence: #34)
- Status: accepted (inferred — confirm)
- Context: GAP was vendored as a git submodule, making cross-repo iteration heavy.
- Decision: migrate to an editable package install of GAP.
- Why: faster local iteration on shared host code without submodule pin churn.
- Consequences: still shared — push cross-cutting changes upstream (global §7).

## 2026-07 — Push maintenance + DeviceGate upstream; evacuate app/maintenance.py (evidence: #38)
- Status: accepted (inferred — confirm)
- Context: maintenance/device-coordination logic lived locally, duplicating GAP concerns.
- Decision: consume gap-host `DeviceGate`; move `app/maintenance.py` behavior upstream.
- Why: exclusive-device coordination is a cross-game concern GAP should own.
- Consequences: thinner consumer; behavior shared by every GAP bot.

## 2026-07 — Loot policy: star-filter + native sell-by-star (evidence: #31, #33)
- Status: accepted (inferred — confirm)
- Context: needed selective loot/economy handling during team hunts.
- Decision: filter loot by star and sell-by-star natively; wire into team hunts + auto-pickup.
- Why: native path is reliable and avoids UI-driven inventory handling.
- Consequences: economy behavior expressed as policy over native calls.

<!-- Add new decisions above this line, newest on top. Template:
## YYYY-MM-DD — <decision title>
- Status: accepted
- Context: … / Decision: … / Why: … / Consequences: …
-->

