# tanglongbatbai — decisions

> Human-owned decision log: the calls the owner has made and *why*, so the chief
> and its staff don't relitigate settled ground. Newest on top. Dates absolute.

> ⚠ Entries below were **drafted from merged-PR/commit evidence on 2026-07-26**. The
> *Decision* is factual; the *Why* is inferred — confirm or correct it.

## 2026-07 — Automation is native self-running in-VM loops, not UI tapping (evidence: "Enforce UI automation intent", native-loop commits)
- Status: accepted (inferred — confirm)
- Context: host-side UI tapping is slow and fragile across a fleet.
- Decision: each VM runs its own native self-running loop (team farm, skill-cast autofight).
- Why: reliability and scale — no host-side input, no per-frame tapping.
- Consequences: behavior lives in-VM; host coordinates rather than drives input.

## 2026-07 — One-click exe: fleet auto-inject + web UI + per-device autologin (evidence: #2)
- Status: accepted (inferred — confirm)
- Context: starting a multi-device fleet by hand was tedious and error-prone.
- Decision: a single executable that auto-injects the fleet, serves a web UI, and auto-logins per device.
- Why: one action to bring the whole fleet up.
- Consequences: operation centers on the one-click exe + dashboard.

## 2026-07 — Multi-device fleet backend + web dashboard (evidence: #1)
- Status: accepted (inferred — confirm)
- Context: needed to operate many devices at once.
- Decision: a fleet backend with a web dashboard as the control surface.
- Why: central visibility/control over all devices.
- Consequences: foundation for the one-click exe and native loops above.

<!-- Add new decisions above this line, newest on top. Template:
## YYYY-MM-DD — <decision title>
- Status: accepted
- Context: … / Decision: … / Why: … / Consequences: …
-->

