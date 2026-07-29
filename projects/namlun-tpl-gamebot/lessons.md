<!-- MIRROR of C:\Users\Tung\Projects\namlun-tpl-gamebot\LESSONS.md
     Source of truth is that file, in the project's own repo.
     Overwritten by scripts/sync-project.py — do not edit here. Synced 2026-07-29. -->

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

### Shared box: auto-discovery must not auto-deploy — gate device registration on operator opt-in
- Date: 2026-07-28
- Symptom: the namlun dashboard's auto-discovery loop (adb devices + `pm path` game probe)
  registered EVERY discovered device with the Fleet. On this shared box (4 live LDPlayer
  instances, 2 with the game installed), that would force-stop a co-located device's game the
  moment it was registered — clobbering another agent's running farm on an emulator this task
  never should have touched.
- Root cause: registering a Target attaches the gap-host `AndroidDeployer`, and the controller
  loop calls `deployer.ensure_ready()` as soon as the adapter endpoint is unreachable —
  regardless of credentials or autologin. `ensure_ready`→`deploy` **force-stops the package and
  injects**. So merely *registering* a discovered device (not even logging in) is enough to
  force-stop its game. Discovering + registering all installed devices therefore reaches into
  every emulator on the box, not just the one the operator is onboarding.
- Rule: separate DETECTION from REGISTRATION. Detect + display all devices, but register (→
  deploy → force-stop → inject) ONLY devices the operator has explicitly opted into — here,
  gated on saved credentials (`login` + `password` present). Never auto-deploy to a device the
  operator hasn't onboarded. `NamlunExtension._sync_once` builds `want = {serial for detected
  if _has_creds(serial)}` and registers/reconciles only that set; detected-but-uncredentialed
  devices stay detect-only rows in the UI. Pairs with the existing "kill by PID, not imagename"
  shared-box rule — both are about not disrupting co-located work.
- Tags: #shared-box #gap-host #deployer #discovery #force-stop #dashboard #namlun_gap

### build-dist.ps1 aborts on PyInstaller's stderr: PS 5.1 wraps native stderr into terminating errors
- Date: 2026-07-28
- Symptom: `scripts/build-dist.ps1` (the `dist/NamlunControl.exe` bundle build) threw and
  exited non-zero the instant PyInstaller started, whenever its output was captured
  (redirection, CI, or a tool harness). The `.so` built fine; the freeze never ran. Error:
  `py.exe : 254 INFO: PyInstaller: 6.21.0, contrib hooks: 2026.6 ... + CategoryInfo :
  NotSpecified: (254 INFO: PyIns...b hooks: 2026.6:String) [], RemoteException +
  FullyQualifiedErrorId : NativeCommandError` — pointing at the `& $python -m PyInstaller …`
  line. Ran fine interactively (console), failed only when stdout/stderr were captured.
- Root cause: PyInstaller logs progress to **stderr** (INFO lines). Under Windows PowerShell
  5.1, when a native exe's output is captured/redirected, each stderr line is wrapped into a
  `NativeCommandError` ErrorRecord. With `$ErrorActionPreference = "Stop"` at the top of the
  script, the FIRST such record is treated as terminating and aborts the script — even though
  PyInstaller returned exit code 0 and produced the exe. So it's not a build failure; it's PS
  5.1 mistaking informational stderr for a fatal error. (This is the same class of trap the
  PowerShell tool docs warn about for `2>&1` on native exes.)
- Rule: for a native exe whose stderr is *informational* (PyInstaller, many build tools),
  don't call it bare under `$ErrorActionPreference = "Stop"` when output may be captured.
  Route it through cmd so stderr is merged at the OS level and never becomes an ErrorRecord —
  `& cmd /c "`"$python`" -m PyInstaller launcher.spec --clean --noconfirm 2>&1"` — then gate
  success ONLY on `$LASTEXITCODE`, never on `$?` or the absence of stderr. Do NOT "fix" it by
  parsing stderr or by blanket-suppressing errors. `scripts/build-dist.ps1`.
- Tags: #build #windows #powershell #pyinstaller #bundle #stderr

### Geofarm parks & starves on star-field 1649: `nearby[]` freezes on empty cell + colliders are all `m_TerrainKey=-1`
- Date: 2026-07-27
- Symptom: `GeoFarmBehavior` on Star Force Field 1649 (`Zenumistlab_05labunit102_S`) never
  farms — char parks on its spawn cell, gap-host logs `stall — no progress for 143s`, 0 kills.
  While parked, `/state` `nearby[]` is FROZEN (identical id-set / hash for minutes) and
  `combat.in_combat=false`, MP flat — even though HP slowly bleeds (mobs hitting a wedged char)
  and keep-alive keeps drinking. Moving the char does NOT unfreeze it; it un-freezes only once
  the char lands on a cell that actually has mobs and the autofight engages.
- Root cause: TWO stacked. (1) The `starfield_1649` map pack has **0 traversal edges**, so the
  planner can't route off an empty cell. It has 0 edges because on this map `ext.terrain` returns
  ALL 35 colliders with `m_TerrainKey = -1` (unkeyed) and every `ext.map` rope edge resolves
  `to=-1`, so `map_capture._pair_edges` (keys platforms by collider key) builds nothing. Normal
  maps (spore_hill/Henesys) capture fine — their colliders ARE keyed. So it's a **star-field
  map-class capture gap**, not general. (2) The adapter's `nearby[]` scan only refreshes while
  the char is in an active-combat field context; a char stranded on an empty/entrance cell reads
  a stale cached snapshot → looks frozen. Not a hang: the client + `ext.runto` stay responsive.
- Rule: "frozen `nearby[]` + `in_combat=false` + MP flat" = char stranded on an empty cell, NOT
  a mod crash — the fix is to get it onto a populated cell, not to restart. Do NOT try to fix 1649
  by re-running the geometry capture — colliders are key=-1, it will keep yielding 0 edges. Shipped
  fix = gap-host runtime mob-position routing (`GeoFarmBehavior` edgeless fallback) steering via the
  canonical `nav.move_to` (added to the .so as a thin `request_runto` wrapper), gated so keyed maps
  keep the static graph. KEY traversal facts proven live (avoid the wrong rabbit holes):
  (1) `nav.move_to`/`request_runto` DOES traverse vertically — it walks up ramps AND down between
  platforms via the .so's walk-path; you do NOT need explicit rope/down-jump verbs for most hops.
  (2) The strand cause was steering to the NEAREST mob, whose x can lie inside the char's own empty
  platform → run-to-x never leaves it; steer to the FARTHEST mob (escape bias) + blacklist-and-rotate
  if the cell doesn't change. (3) Keeping `combat.auto_combat` ON while moving lets the native
  autofight lock an unreachable mob and freeze the move — disengage combat while routing.
  (4a) COLD/AFTER-DEATH ENTRY STALL: `g_field_ticked` (in-world flag) is set by the field Updater
  which keeps ticking at char-select too, so it stays stale-TRUE after any field exit that isn't a
  clean `session.logout` (death→revive→relogin, or a cold login landing at char-select). Effect:
  `/state` reports `in_world=true` at the lobby AND the login pump's `if (IsInWorld()) return true`
  short-circuits BEFORE `CharacterSelect.StartGame()` → stuck at char-select (needs a manual
  `session.logout` to recover). FIX (PR namlun #44): `g_lobby_scene_active` gate, set from the active
  IScene being `NGameObject.NObject.Lobby` (char-select scene, sibling of Title) via `GetActiveLobby()`
  every pump tick; `in_world()` returns false when the lobby scene is active. Verified cold (no logout):
  ServerJoin → lobby_detected → start_game (native) → field tick, honest /state at every stage.
  (4) LIFECYCLE: `combat.auto_combat` ON with keep-alive stopped = the char fights unhealed and DIES.
  Combat and keep-alive MUST be coupled: gap-host `controller.stop()` now disengages combat on
  teardown; never leave auto_combat on after stopping the host (a manual `/combat/auto_combat {on}`
  in a probe will kill the char if consume isn't running). Autonomous 10-min proof: 0 stalls, 0
  deaths, 6 cells / 21 heights, 70% time on the densest cell, EXP +2.28%.
- Tags: #geofarm #gap-host #starfield #capture #terrain #il2cpp #nearby #traversal #lifecycle

### Away-parked cold login hung at "touch to start": the reserve-away retry must survive g_login_initiated
- Date: 2026-07-27
- Symptom: cold `POST /session/login` for an AWAY-PARKED char hung at the title/"touch to
  start" screen (`/state` stage=`title`, `in_world`=false), never reclaiming. Logcat:
  `ServerJoin:IDLogin(String,String,String,String,Int32)` → ~60s later
  `NTitle.OnFailure / 0x10010009` → `SN_Fail` → `Protocol State: Login -> Init`, then stuck.
- Root cause: TWO things stacked. (1) The game's OWN spontaneous auto-login uses
  `ServerJoin.IDLogin(...)` — a DIFFERENT method than the reserve-away `IDLoginNew(bool,bool)`
  the mod hooks — so it logs in PLAIN (no reserve-away) and an away-parked char's world session
  rejects it with `0x10010009`. (2) The recovery is a reserve-away `IDLoginNew` RETRY (→ QA_Away
  away-reconnect), but PR #31 made the ServerJoin drive machine post StartLogin ONLY while
  `!g_login_initiated` and switch to WorldSelect-only once a login had fired. So after the first
  attempt latched `g_login_initiated=true`, the reserve-away login never re-fired — WorldSelect
  no-ops on an unlogged session — and the char stranded at "touch to start" (this regressed the
  2026-07-17 "away login needs a RETRY, not one shot" behavior, which PR #31 verified only on a
  non-away account).
- Rule: keep the reserve-away StartLogin retry alive on its ~18s cadence at ServerJoin
  REGARDLESS of `g_login_initiated`, interleaved with (not replaced by) the ~6s WorldSelect for
  the fresh/no-recent-server case. It's idempotent for the success path (you leave ServerJoin
  within 18s once logged in). `ExecuteEnterWorld` (`lib/src/gap/session_namlun.hpp`). Verified
  live 2026-07-27 on emulator-5554: reproduced the hang (plain `IDLogin` → `0x10010009` → stuck
  at title), then `POST /session/login` → `(re)post_start_login reserve_away=1` →
  `Protocol State: Login -> QA_Away.Away` → `Away.GameJoining -> Run` → `start_game (native)` →
  in_world, ZERO taps. Possible future hardening: also hook the plain `ServerJoin.IDLogin` to
  force reserve-away so the game's spontaneous auto-login never eats the `0x10010009` at all.
- Tags: #il2cpp #login #namdaichien #0x10010009 #away-reconnect #reserve-away #session #regression

### Headless inject-to-field: drive the mod's /session/enter_world, not adb screen taps
- Date: 2026-07-27
- Symptom: `tools/inject.sh` reached the field after a title-inject via two blind adb screen
  taps (`input tap 480 382` = touch-to-start, `input tap 800 460` = the character-select
  "start" button). Not headless, and fragile — the coordinates are resolution/account
  specific and the "start" tap in particular silently missed on any board that wasn't the
  exact layout it was written for.
- Root cause: inject.sh predated the native login subsystem. The mod already drives the whole
  chain in-mod (`lib/src/gap/session_namlun.hpp`): `IDLoginNew` → `WorldSelectPopup.OnWorldSelectItem`
  → `CharacterSelect.StartGame` (logged as `start_game (native)`), publishing `in_world` on
  `GET /state`. inject.sh just wasn't wired to use it, so the taps were the last non-headless step.
- Rule: for headless entry, `adb forward tcp:<host> tcp:18080` → wait `GET /health` → POST
  `/session/enter_world` (or `/session/login {account,password}` for a cold-token account; the
  mod auto-fills the Roid web form) → poll `GET /state` for `"in_world":true`. Keep screen taps
  only behind an explicit `ENTER_FIELD_VIA=tap` fallback. Verified live 2026-07-27 on
  emulator-5554: cold title-inject → in_world, zero taps (PR #37). Injector discovery: the
  worktree ships no injector binary — inject.sh now reads the fleet injector from
  `gap_accounts.json` (`"injector"`), so a bare run finds it; else set `ANDKITTY_INJECTOR`.
- Tags: #inject #headless #session #login #tooling #tap

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

### gap-host is an editable install — its config schema drifts; track it in make_gap_accounts.py
- Date: 2026-07-27
- Symptom: `gap-host run --accounts gap_accounts.json` drove deploy+login+farm fine, but the
  keep-alive never fired — a farming char fell to <55% HP and never drank. No `consume`/drink
  event ever appeared. The config had a populated `maintenance` block.
- Root cause: `scripts/make_gap_accounts.py` emitted a top-level `maintenance` block
  (`{enabled, hp:{item_id,pct}, mp:{...}, restock}`), but upstream gap-host **retired that
  shape**. `gap_host.config.load_fleet_config` only reads a top-level **`consume`** block, and
  `gap_host.engine.consume.ConsumeConfig.from_dict` expects a different schema — so the
  `maintenance` block was silently ignored and the drinker stayed OFF (default). gap-host is an
  *editable* pip install from the sibling `game-automation-platform` repo, so a `git pull` there
  can change the host's config contract underneath this repo with no version bump.
- Rule: `make_gap_accounts.py` must track the upstream host's config schema, not a frozen copy.
  Keep-alive is a top-level `consume` block:
  `{"hp_items":[<id>], "hp_pct":N, "mp_items":[<id>], "mp_pct":N, "cooldown_s":N, "restock":{"enabled":bool,"to":N,"at":N,"interval_s":N}}`
  (verified live: applying it healed 48%->100% via `item.use 4980`; it round-trips through
  `load_fleet_config` -> `ConsumeConfig.from_dict(active=True)`). When a host feature seems inert,
  diff the emitted config keys against the current `gap_host` loader/`*Config.from_dict` — don't
  assume the block is read just because it's present. Re-check after any gap-host `git pull`.
- Tags: #gap-host #config #editable-install #consume #keep-alive #schema-drift
