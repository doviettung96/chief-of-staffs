# namlun-tpl-gamebot — decisions

> Human-owned decision log: the calls the owner has made and *why*, so the chief
> and its staff don't relitigate settled ground. Newest on top. Dates absolute.

> ⚠ Entries below were **drafted from merged-PR/commit evidence on 2026-07-26**. The
> *Decision* is factual; the *Why* is inferred — confirm or correct it.

## 2026-07-27 — Autologin must be FULLY headless — no host start-tap (owner call)
- Status: DONE — merged to main as PR #37 (`1192b36`), live-verified zero-tap on emulator-5554.
  Follow-ups in flight on `fix/inject-reliability`: find_injector fallback + stale-`.so` build fix,
  and restart the 5554 farm the T0 test interrupted.
- Context: owner observed the autologin still relies on a host-side "start" tap. The
  headless chain already mostly exists — world-select via
  `WorldSelectPopup::OnWorldSelectItem` (#31), away-parked login retry (#29), native
  `CharacterSelect.StartGame()` (namlun_stub.cpp ~2887 + `POST /lobby/start`). The gap:
  lobby→field entry is half-migrated — `g_lobby_autoselect` defaults OFF and its comment
  (~510-513) still says entry "is driven by on-screen taps from the host", contradicting
  the unconditional native `StartGame()`.
- Decision: eliminate every host-side/adb tap in title→login→world-select→lobby→field so
  cold launch → in-world is 100% mod-native. Reconcile the `g_lobby_autoselect` default +
  stale comment; check the host/gap-host side for any adb start/world-card tap too.
- Why: taps are fragile to resolution/UI drift (LESSONS #0x10010009); native is durable.
- Consequences: fix runs in parallel in its own worktree off `main`. LIVE VERIFY IS GATED
  on the single emulator — it stays with the auto-potion staff until that task finishes;
  the fix-staff does all RE/code/build now and stops at "ready for live verify".

## 2026-07-27 — Meso-shop restock must be NATIVE, not UI-tap (owner call)
- Status: DONE — shipped + merged. The real command is `QA_ProductListItemBuy.Send(
  productListIndex, itemIndex, storeIndex, count)` (NOT `CQ_Buy`, which is skills); the mod
  opens the store session first (`StoreOpen.Send_ByStore`, int overload) then buys. Verified
  LIVE in the star field, no store UI: HP 4980 + MP 4981 bags rose, mesos deducted. Merged as
  PR #39 (`80313c6`). Follow-up in flight: gap-host `feat/maintenance-keepalive` (auto-drink+
  restock 4980/4981) — live-verify then PR (shared submodule, §7, owner-approved).
- Context: RE (feat/canonical-potion-verbs) found the meso-shop buy is the game command
  `CQ_Buy(skillIndex, Dictionary<Item,int> mesoSaleItemTree)`; `CQ_BuyItem` is the defunct
  NPC path. Native is deeper than a 3-int call (needs a managed `Dictionary<Item,int>`
  keyed by the store product Item + resolved store/catalog index). A mod-driven UI-tap
  flow was confirmed working (bought 4980 via a 6-tap modal) and the staff recommended it
  as the faster path, with native as later hardening.
- Decision: NATIVE ONLY. Implement restock via `CQ_Buy`. The UI-tap / mod-driven tap flow
  is off the table entirely — not even as a fallback. Build a temporary command-logging
  hook to capture exact live args first, then fire natively and remove the hook. Cover
  both HP and MP potions.
- Why: the project principle is "below the contract, robust" — native game logic is
  immune to UI-layout drift; UI-tap is fragile. Owner weights long-term robustness over
  time-to-first-restock.
- Consequences: multi-cycle RE accepted. DONE WHEN: with autofarm/autofight ON, the
  character drives to the star field and natively restocks HP+MP meso-shop potions,
  verified live (mesos deducted, bag counts up); then PR on feat/canonical-potion-verbs.

## 2026-07 — Retire the hand-written app/ host; consolidate on gap-host (evidence: #30, Phase 5)
- Status: accepted (inferred — confirm)
- Context: this repo carried its own host code duplicating what GAP provides.
- Decision: move the host onto gap-host and delete the hand-written `app/` host.
- Why: inherit GAP's reliability/orchestration; stop maintaining a parallel host.
- Consequences: repo carries game-specific reversing + verbs; host bugs fixed upstream.

## 2026-07 — Unify normal + star-field farming behind one Auto-farm toggle (evidence: #28)
- Status: accepted (inferred — confirm)
- Context: normal and star-field farming were separate flows.
- Decision: one Auto-farm toggle drives both; `ext.star_fields` enumerates the live catalog (#34).
- Why: simpler operator model; one code path to keep reliable.
- Consequences: star-field farm now hosted on gap-host (draft PR #35).

## 2026-07 — Drive world-select via WorldSelectPopup after client update (evidence: #31, #32)
- Status: accepted (inferred — confirm)
- Context: a client update caused `0x10010009` login loops — world-select had moved.
- Decision: select the world via `WorldSelectPopup.OnWorldSelectItem`.
- Why: the old entry point no longer exists after the update.
- Consequences: resilient auto-login; captured as a lesson.

<!-- Add new decisions above this line, newest on top. Template:
## YYYY-MM-DD — <decision title>
- Status: accepted
- Context: … / Decision: … / Why: … / Consequences: …
-->

