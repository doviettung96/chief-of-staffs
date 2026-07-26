# tanglongbatbai

> Human-owned. `About`/`Current focus` filled from repo evidence on 2026-07-26;
> `Vision` is a **draft candidate** — confirm/adjust. Never overwritten by sync.

## About

A **multi-device fleet game bot** with a one-click launcher: auto-injects the fleet,
serves a web dashboard, and runs **self-running in-VM native loops** (team farm, skill-cast
autofight with no tapping) rather than host-side input. Includes per-device auto-login and
an auto-relogin watchdog that recovers from full game crashes (relaunch + re-inject).

## Vision

_Draft (confirm):_ a one-click, self-running multi-device farm — each VM runs its own
native loop and the whole fleet is operated from a single web dashboard, with zero manual
tapping and self-healing login/crash recovery.

## Current focus

Native item automation: keyword auto-drop via `CGDiscardItem` + an equipment-quality (star)
drop rule with fast bulk autodrop (#3, `native-auto-drop`, merged). Foundation in place:
one-click exe with fleet auto-inject + web UI + per-device autologin (#2), multi-device
backend + dashboard + native self-running loops (#1). Branch `main`; no open PRs.

## Constraints & gotchas the chief must respect

- See [`lessons.md`](lessons.md) (mirror of the project's LESSONS.md).
- Automation is **native in-VM loops**, not UI tapping — keep that intent (see
  [`decisions.md`](decisions.md)).
