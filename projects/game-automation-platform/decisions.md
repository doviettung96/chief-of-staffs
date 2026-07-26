# game-automation-platform — decisions

> Human-owned decision log: the calls the owner has made and *why*, so the chief
> and its staff don't relitigate settled ground. Newest on top. Dates absolute.

> ⚠ Entries below were **drafted from merged-PR/commit evidence on 2026-07-26**. The
> *Decision* is factual; the *Why* is inferred — confirm or correct it.

## 2026-07 — Cross-game concerns live in GAP; each game is a thin adapter (evidence: architecture, #14)
- Status: accepted (inferred — confirm)
- Context: many RE game bots were each re-implementing host, login, and device handling.
- Decision: one shared platform (GAP) owns everything above the per-game skeleton; games
  consume it via extension/login-profile seams.
- Why: avoid N copies of the same host logic; fix once, every game inherits it.
- Consequences: cross-cutting work must be authored upstream in GAP (global §7), not forked.

## 2026-07 — Team logic is party formation only; run behavior is per-device (evidence: #11, #13)
- Status: accepted (inferred — confirm)
- Context: early "team" logic conflated party formation with per-device run behavior.
- Decision: team = party formation only; each device runs its own behavior; reconcile
  formation per device; PartySupervisor coordinates at the fleet level (#20).
- Why: mixing the two caused stale-party bugs and coupled unrelated concerns.
- Consequences: clearer device isolation; DeviceGate (#19) coordinates exclusive access.

## 2026-07 — Bundle the emulator's adb, not the build machine's (evidence: #12)
- Status: accepted (inferred — confirm)
- Context: adb version mismatches between build host and emulator broke device comms.
- Decision: ship the emulator's own adb in the bundle.
- Why: protocol/version drift between adb client and emulator server.
- Consequences: reliable device connection regardless of the build machine.

<!-- Add new decisions above this line, newest on top. Template:
## YYYY-MM-DD — <decision title>
- Status: accepted
- Context: _what forced the choice_
- Decision: _what we chose_
- Why: _the reasoning; the alternatives rejected and why_
- Consequences: _what this makes easier / harder_
-->

