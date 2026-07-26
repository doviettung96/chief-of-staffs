# game-automation-platform

> Human-owned. `About`/`Current focus` filled from repo evidence on 2026-07-26;
> `Vision` is a **draft candidate** — confirm/adjust. Never overwritten by sync.

## About

One architecture for all the RE game-bot projects (GAP). Instead of re-inventing a bot
per game, you implement **one small, known skeleton per game** and reuse everything
above it — host, fleet orchestration, device coordination, login/session recovery — so
each new game is a thin adapter over a shared platform.

## Vision

_Draft (confirm):_ GAP owns every cross-game concern exactly once — fleet/party
orchestration, exclusive device access, login and session recovery, extension/profile
seams — and every downstream game bot (namlun, thienanh, …) inherits them by consuming
GAP, never re-implementing them. Adding a game becomes "write the adapter," nothing more.

## Current focus

Fleet-level orchestration: **PartySupervisor** (fleet party formation + mimic, PR #20)
and a generic **DeviceGate** for exclusive device coordination (PR #19). Recently landed:
host login-error surfacing + recovery instead of hanging (#16), data-driven geo map entry
(#18), extension/login-profile seams (#14). Branch `feat/upstream-device-gate`.

## Constraints & gotchas the chief must respect

- See [`lessons.md`](lessons.md) (mirror of the project's LESSONS.md) — it is rich here.
- GAP is a **shared dependency** for the downstream bots. Per global §7, reflect general
  work upstream in GAP, and ask before bumping pins / pushing.
- Team logic = party formation only; run behavior is per-device (see [`decisions.md`](decisions.md)).
