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

Consuming gap-host **DeviceGate** and evacuating `app/maintenance.py` upstream (PR #38);
native login-error dialog detection + `session.dismiss_error` (#37); death-state detection
in `/state` (#35); loot star-filter + native sell-by-star wired into team hunts (#31/#33).
Branch `feat/upstream-device-gate`.

## Constraints & gotchas the chief must respect

- See [`lessons.md`](lessons.md) — e.g. bound the injector call with a timeout, not just the ping.
- Consumes **GAP** as an editable package — cross-cutting behavior belongs upstream in GAP
  (global §7), not forked here. Ask before bumping the GAP pin.
