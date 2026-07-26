# vlcm

> Human-owned. `About`/`Current focus` filled from repo evidence on 2026-07-26;
> `Vision` is a **draft candidate** — confirm/adjust. Never overwritten by sync.

## About

RE + automation workspace for **Vo Lam Chan Menh Origin** (`com.tepaylink.vlcm`). The
PC-client stack: `native-lib/` (C++ DLL hooking ws2_32 via MinHook, local HTTP API on
`:32123`), `injector/`, a Python FastAPI/Tkinter `app/` on `:9898`, `frida/` helpers, and
decrypted protocol dumps. Automation **drives the client's own ActionScript in-process**
(BotBridge) rather than hand-crafting packets.

> ⚠ **CLEANUP (in progress):** vlcm's own `AGENTS.md` pointed at **agtx** as the
> multi-agent owner. **agtx is retired** — orchestrate via **herdr** now
> (see [`../../docs/herdr.md`](../../docs/herdr.md)). PR open to drop the agtx
> sections: doviettung96/vlcm-gamebot#18. Follow-up: migrate the runtime-target config
> off the legacy `.agtx/` directory name in `scripts/shared/target_runtime.py`.

## Vision

_Draft (confirm):_ full automation of VLCM by calling the client's own AS3 (BotBridge) for
every feature — quests, dungeons, growth, login — reusing the client's exact serialization
and encryption, so no hand-built wire-protocol layer is ever needed.

## Current focus

Reverse + drive the **Zodiac Challenge dungeon** (Path A, branch `feat/zodiac-dungeon`);
character-growth automation + web UI toggles. Plus the agtx→herdr cleanup (PR #18).

## Constraints & gotchas the chief must respect

- See [`lessons.md`](lessons.md) (mirror of the project's LESSONS.md).
- **Core principle:** drive the reversed AS3 via BotBridge; do **not** re-implement the
  wire protocol by hand (see [`decisions.md`](decisions.md)). Capture is a confirmation
  tool, not the primary method.
