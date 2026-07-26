# thienanh-novagate — decisions

> Human-owned decision log: the calls the owner has made and *why*, so the chief
> and its staff don't relitigate settled ground. Newest on top. Dates absolute.

> ⚠ Entries below were **drafted from merged-PR/commit evidence on 2026-07-26**. The
> *Decision* is factual; the *Why* is inferred — confirm or correct it.

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

