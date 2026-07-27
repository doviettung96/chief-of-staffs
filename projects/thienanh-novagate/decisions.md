# thienanh-novagate — decisions

> Human-owned decision log: the calls the owner has made and *why*, so the chief
> and its staff don't relitigate settled ground. Newest on top. Dates absolute.

> ⚠ Entries below were **drafted from merged-PR/commit evidence on 2026-07-26**. The
> *Decision* is factual; the *Why* is inferred — confirm or correct it.

## 2026-07-27 — Auto-consume during autofight: potions (threshold) + food (maintain-buff), grade-gated (evidence: GAP #26, thienanh #47)
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

