# ngaokiem-myg

> Human-owned. `About`/`Current focus` filled from repo evidence on 2026-07-26;
> `Vision` is a **draft candidate** — confirm/adjust. Never overwritten by sync.

## About

A **headless bot for the myG game** `vn.myg.nkvsmobile`: native injection + a local
FastAPI scaffold. Login is minted from credentials with an RE-driven server hop (no UI
login); quests and rewards are driven through the game's own native dispatch layer
(a per-TargetType dispatcher + a native `/dialog` driver), not by tapping the UI.

## Vision

_Draft (confirm):_ fully headless, UI-less automation of the myG game — login, quests,
rewards, character growth — every action issued through the native dispatch/packet layer,
so it runs without a rendered client.

## Current focus

Headless **level-up reward claiming** via a decoded packet; auto-equip + character
improvement; the headless login path (mint session from credentials + RE-driven server
hop); quest handlers (Collect 7/15, Pos 13) with a transient-tolerant loop (#11). Branch
`feat/headless-login-mint`. No open PRs.

## Constraints & gotchas the chief must respect

- See [`lessons.md`](lessons.md) (mirror of the project's LESSONS.md).
- Native `/dialog` driver is the keystone for explicit quest dispatch — prefer it over
  UI-driven flows (see [`decisions.md`](decisions.md)).
