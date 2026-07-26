<!-- MIRROR of C:\Users\Tung\Projects\namlun-tpl-gamebot\LESSONS.md
     Source of truth is that file, in the project's own repo.
     Overwritten by scripts/sync-project.py — do not edit here. Synced 2026-07-26. -->

# Lessons Learned — namlun-tpl-gamebot

Project-specific gotchas worth never hitting twice. Read before debugging (grep by error
text or tag); append after resolving a non-obvious error. Newest on top.

Entry format:
```
### <one-line title>
- Date: YYYY-MM-DD
- Symptom: what was observed (paste the actual error text)
- Root cause: why it really happened
- Rule: what to do — and what never to do again
- Tags: #build #il2cpp #login ...
```

---

### ext.star_fields: enumerate the flyweight table + filter by Count>0 — NOT sub-object presence or RecommendationLevel
- Date: 2026-07-26
- Symptom: `ext.star_fields` returned an empty catalog on a fresh in-world session. First
  rewrite (scan the World flyweight table, keep worlds whose star sub-object is non-null)
  returned 93 false positives — plain towns/maps like `Ellinia_01town_0`. Filtering by
  `RecommendationLevel > 0` then returned 1621 arcane false positives (`req:0, level:1`).
- Root cause: THREE traps stacked. (1) It read `World.Static.{StarForceList,
  DarkStarForceList, ArcaneForceList}` — convenience lists populated *lazily* by a
  `WorldChangeRegister` callback, so empty until a world-change fires. (2) Every
  `World.BinaryFlyweight` ALWAYS carries all three `{StarForce, DarkStarForce, ArcaneForce}`
  sub-objects (towns included), so presence ≠ membership. (3) `ArcaneForce` carries a default
  `RecommendationLevel` of 1 on ~1600 ordinary maps, so a level test floods the arcane list.
  Also: the container deserializes worlds lazily, so cold reads miss the high-index fields.
- Rule: enumerate via a full `CodeIndexContainer.SearchIndex` sweep — it deserializes each
  world from the FileTable on demand, so a full index sweep surfaces the high-index star
  fields that aren't resident cold. Classify a world as a field of type T iff that sub's
  required COUNT > 0: `StarForce.Count`, `DarkStarForce.DuctilityCount`, `ArcaneForce.Count`
  (the field name differs per type). Count is the reliable signal — never
  `RecommendationLevel` (arcane default = 1), never sub-object presence. Resolve the container
  + `SearchIndex` method ONCE outside the loop (`SearchWorldByIndex` re-resolves the container
  every call → ~200k managed invokes over the sweep → overruns the dispatch deadline) and
  cache the static catalog. `ext.world_search {index:N}` is the live per-world inspector for
  determining discriminators like this. Verified live: starforce=34 (`_S`, req 40-171),
  darkstarforce=3 (`_DS`, Ductility 1/6/11), arcaneforce=119 (ChuChu/VanishingJourney/Arcana).
- Tags: #il2cpp #namdaichien #starforce #arcaneforce #flyweight #enumeration #lazy-load

### inject.sh early-inject spurious retry + injector hang: stale loader-log marker after gap/2 migration
- Date: 2026-07-26
- Symptom: `tools/inject.sh` early mode logged `title-inject saw no loader log; retrying once`
  on EVERY run, force-stopped and relaunched the game repeatedly, and sometimes left an
  `AndKittyInjector` stuck in `do_wait` on-device — ptrace-freezing the game so its control
  server never came up (`/health` empty, `Connection refused` on the forwarded port).
- Root cause: `loader_count()` grep'd logcat for `namlun: loader attached` — the LEGACY stub
  marker (`namlun_stub.cpp`). The current gap/2 adapter (`namlun_main.cpp`) logs
  `namlun-gap starting (build …)` at `JNI_OnLoad` and never emits the old line, so the marker
  never matched → `wait_for_loader_line` always failed → spurious retry → a second/third attach
  to the same process, which is what hung the injector.
- Rule: keep inject.sh's loader marker in sync with the mod's actual `JNI_OnLoad` log. Current
  marker = `namlun-gap starting` (tag `namlun-gap`); inject.sh now matches either form. If a
  stuck injector freezes the game (health down, no log progress), find and `kill -9` the
  `AndKittyInjector` in `do_wait` on-device, then re-inject cleanly. The first title-inject
  loads the mod fine; it's the retries that break it.
- Tags: #inject #tooling #ndk-translation #andkitty #gap #broken-window

### 0x10010009 login loop after a client update = world-select moved to WorldSelectPopup
- Date: 2026-07-25
- Symptom: login loops forever at ServerJoin — `NTitle.OnFailure / 0x10010009` →
  `SN_Fail` → `Protocol State: Login -> Init`. The mod fires its login and then spams
  `session: post_world_select`, but the world never connects. Reserve-away retries,
  `enter_world`, and a multi-minute quiet-then-retry ALL still hit `0x10010009`. A real
  screen tap on the "Chọn Thế Giới" world card, however, drives straight to in-world.
- Root cause: a client update moved the world-select entry point. The mod called the
  static `ServerJoin.OnWorldSelectItem(int)`, but the current client drives the world
  list through `WorldSelectPopup.OnWorldSelectItem(int)` (namespace
  `NGameProcess.NTitle.NFunction`; the popup whose fields — CloseButton/ScrollView/Grid
  of `WorldSelectPopupElement` cards/RecentServerName — match the live UI). The stale
  call no-ops, so the world is never selected and the world-login times out at
  `0x10010009`. This is a DIFFERENT cause of `0x10010009` than the away-parked session
  below — and here the away-retry/reserve-away path does NOT fix it.
- Rule: when a name-resolved mod call silently stops working after a client update, diff
  `dump.cs` for the moved handler and prefer the class that owns the VISIBLE UI. Fix:
  resolve `WorldSelectPopup::OnWorldSelectItem(int)` by name and call it in the
  WorldSelect pump action (fall back to `ServerJoin` only if it doesn't resolve) —
  `lib/src/gap/session_namlun.hpp` (PR #31). Verified live on the 64-bit build: a single
  `POST /session/enter_world` drove offline → role_select → in_world with NO screen tap.
  A host-side adb world-card tap works too but is fragile (resolution/multi-server) — the
  mod-side call is the durable fix. NB: this supersedes the away-retry theory below as the
  current primary cause of `0x10010009`; that entry may have been an earlier client version.
- Tags: #il2cpp #login #namdaichien #0x10010009 #worldselect #reverse-engineering

### Use CQ_Warp for known local portals; do not drive DirectMove UI headlessly
- Date: 2026-07-21
- Symptom: `POST /nav/move_to_ex {"world_code":"Henesys_00sporehill_0"}` crashed in
  `WorldMap.GetPoint`, and later DirectMove packet setup failed with
  `Navigation.SetDirectMoveData_Map: managed exception class=NullReferenceException`.
- Root cause: DirectMove/WorldMap UI helpers require UI-managed state and can throw or
  corrupt Unity state when called headlessly. The actual Henesys -> Spore route is a
  normal portal warp: `Henesys_01_0_P03_Henesys_00_0_P01`.
- Rule: for known adjacent map portals, resolve `Warp.BinaryFlyweight` by code and send
  `CQ_Warp.Send`; keep `WorldMap.GetPoint`, `DirectMoveNavigation.StartNavigation`,
  `BtnDirectMove.OnUp`, and `LoadUI_WithTargetWorld` out of live nav.
- Tags: #il2cpp #navigation #portal #directmove #crash

### Away-parked character login needs a RETRY, not one shot (0x10010009)
- Date: 2026-07-17
- Symptom: `session.enter_world`/`login` correctly detects ServerJoin and fires the login
  (logcat `session: post_start_login`), but then loops on
  `NTitle.OnFailure / 0x10010009 → SN_Fail → ServerJoin:Initialize`. A single
  `IDLoginNew(reserve_away=true)` never reaches the world — yet a manual "touch to start" tap
  does (observed repeatedly).
- Root cause: an away-parked character still holds its world session server-side. The FIRST
  login attempt is rejected with `0x10010009` — and that rejection is *what parks the
  character "away."* Only a LATER attempt reclaims it via the `QA_Away` away-reconnect
  (`Logic.NPerform.Away:Execute`). One shot can never succeed; the first failure is a required
  step, not an error. (Confirmed: the successful tap runs showed `0x10010009` first, then
  `Away`×22 + `QA_Away` → in-world.)
- Rule: for away-resume, RETRY the login while idle at ServerJoin (~every 18s) on the
  reserve-away path; treat the first `0x10010009` as expected. Only re-post when
  `!login_processing` — never stack two concurrent logins (they self-conflict into the same
  `0x10010009`). Do NOT set `AutoStartAfterDownload` (it kicks a competing plain-IDLogin that
  fails identically). The retry lives in `ExecuteEnterWorld` (`lib/src/gap/session_namlun.hpp`)
  and is what repeated "touch to start" taps do by hand; the host's force-stop+wait recovery is
  the heavier fallback, not the primary path. The general half ("login is not one-shot — retry
  until in_world") is reflected up in the GAP `CONTRACT.md` `session.*` note.
- Tags: #il2cpp #login #namdaichien #0x10010009 #away-reconnect #session
