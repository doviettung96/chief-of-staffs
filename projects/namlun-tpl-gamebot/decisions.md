# namlun-tpl-gamebot — decisions

> Human-owned decision log: the calls the owner has made and *why*, so the chief
> and its staff don't relitigate settled ground. Newest on top. Dates absolute.

> ⚠ Entries below were **drafted from merged-PR/commit evidence on 2026-07-26**. The
> *Decision* is factual; the *Why* is inferred — confirm or correct it.

## 2026-07-28 — "Just the exe": dashboard onboarding replaces the hand-written config
- Status: DONE — PR #46 (`2baed5d`, squash-merged). Updated exe pushed to dkdca09 (byte-verified);
  the obsolete `control_accounts.example.json` removed from the box.
- Context: the first bundle (PR #45) made the operator hand-write a `control_accounts.json`
  beside the exe — not user-friendly ("usually I'd expect just the exe" — owner). thienanh's
  bundle already proves the friendly shape off the SAME gap-host: launch exe → dashboard →
  auto-discover device → manage in the browser, no config file.
- Decision (owner): make it "just the exe" via the DASHBOARD. The only thing that can't be
  auto-derived — and must never be baked into a distributed binary — is the game
  login/password; everything else (device serial/port, injection, login) the exe derives.
  Credentials entered once in a dashboard form, stored machine-local, remembered.
- Built a `namlun_gap` HostExtension (mirroring `thienanh_gap`): auto-discovers LDPlayer
  devices, serves a webui dashboard with a credentials form + Start/Stop, persists creds to
  `%APPDATA%\NamlunControl\accounts.json` (per-user, outside the bundle, never committed,
  never in `_MEIPASS`, never logged/returned to UI). `launcher.py` drops the config-file read
  and explicitly instantiates the extension (robust in a frozen exe — entry-point discovery is
  unreliable under PyInstaller).
- Shared-box safety gate (found + fixed live): auto-registering EVERY discovered device
  force-stops other agents' games via the deployer. Fixed: register/deploy ONLY devices the
  operator onboards (creds present); detect-only otherwise. Lesson saved (project scope, PR #46);
  pairs with [[the kill-by-PID-not-imagename lesson]].
- Start-map fix (found live): Start defaulted to a hardcoded `spore_hill`, but GeoFarm can't
  cross-map — clicking Start farmed nothing when the char was elsewhere. Fixed: Start defaults to
  the device's CURRENT in-game map (pack list to change).
- Verified live on the FROZEN exe (cold-start = the operator's real path): auto-detect
  emulator-5554 → creds via the dashboard form → deploy/on-device-inject → cold login (~75s, #44)
  landed the char ON mobs (nearby=32) → Start (auto-targeted starfield_1649) → farm ran 3.75 min:
  routes 2→17, in_combat cycling, cells cleared 0→1→16, reroutes=0, deaths=0, keep-alive armed.
  Honest signal caveat: this adapter build doesn't expose exp/currency in `/state`, so the proof
  is kills/combat/routing over time, not a raw XP counter.
- Scoped follow-ups (not in this PR): star-enter-on-Start (only matters for a stale in-world
  session wedged on an empty starfield cell); re-capture the stale `starfield_1649` pack.

## 2026-07-28 — Self-contained NamlunControl.exe bundle; shipped to production box dkdca09
- Status: DONE (build+deploy) — PR #45 (`6ed1ff6`, squash-merged to main). LIVE FARM TEST on
  dkdca09 is the owner's next step (pending).
- Context: to run the gap-host automation on a bare Windows box (only LDPlayer9 + the game,
  no python/adb/git), namlun needed a self-contained bundle. Its old launcher was retired in
  #43. thienanh-novagate already ships this exact form off the *same* shared gap-host, so we
  mirrored it: `launcher.py` + `launcher.spec` + `scripts/build-dist.ps1` → PyInstaller
  onefile `dist/NamlunControl.exe` bundling python + adb + gap_host + the game `.so` + the
  on-device injector + `data/maps/`.
- Key ABI decision (owner: dkdca09 is "similar to here"): the game adapter `.so` is
  **arm64-v8a**, but the injector is **x86_64** — LDPlayer9 is an x86_64 Android *device*
  running arm64 libs under ndk-translation, and the injector ptraces the on-device process.
  Two different axes; the brief had conflated them. The launcher picks the injector by live
  device-ABI probe (ABI-parametric), so one bundle is correct on any box with its matching
  injector.
- Creds: zero passwords frozen in the exe (grep-verified against dummy/real/placeholder).
  Passwords live only in a machine-local `control_accounts.json` beside the exe, read at
  runtime to generate `gap_accounts.json` (never into read-only `_MEIPASS`). `make_gap_accounts.py`
  refactored to a shared `build_config()` — single source of truth for inject data + the
  keep-alive `consume` schema (see [[state-lane-before-spawn]]-era LESSONS: `consume`, not
  `maintenance`).
- Verified on the dev box (behavioral, not compile): `.so` rebuilt fresh (arm64,
  `e_machine=0xb7`); frozen exe launches → dashboard **HTTP 200** on :8771; `_MEIPASS` carries
  adb + x86_64 injector + arm64 `.so` + maps; runtime config gen ran against a live device
  (ABI probe hit, injector selected). Artifact `NamlunControl.exe` (23,225,745 bytes) scp'd to
  `dkdca09:C:\Users\admin\Desktop`, **byte-for-byte verified** on the remote.
- To run on dkdca09 (owner): ensure LDPlayer9 + game up and adb-visible; copy the
  `control_accounts.example.json` (also on the Desktop) → `control_accounts.json` beside the
  exe with the real roster (name/serial/port/login/password); run `NamlunControl.exe`.
- Lesson recorded (project scope, in PR #45): PS 5.1 wraps a native exe's informational stderr
  (PyInstaller) into terminating ErrorRecords under `$ErrorActionPreference=Stop` when output is
  captured → false build failure; route through `cmd /c ... 2>&1`, gate on `$LASTEXITCODE`.
  Global-promotion of this lesson pending owner call.

## 2026-07-28 — Autonomous star-field farm via gap-host — PROVEN end-to-end (login→autofarm)
- Status: DONE (milestone) — gap-host #32 (`90ad0f1`) + namlun #44 (`a3b7806`).
- Context: after the WinError-193 fix (#29/#42) proved deploy/login/keep-alive, the actual
  GeoFarm loop was NOT autonomous on star-field maps. Live watching (owner's eyes caught every
  gap) surfaced a chain of real defects, each fixed + live-verified:
  1. Stranding — the pack had 0 edges (star-field colliders are unkeyed, `m_TerrainKey=-1`, so
     capture can't build a graph). Fix: runtime mob-position routing in `GeoFarmBehavior` for
     edgeless maps (no static graph) — gated so keyed maps keep the graph. + canonical
     `nav.move_to`.
  2. No vertical traversal — char stranded on empty platforms / locked on unreachable mobs.
     Fix: reachability + down-jump/rope traversal across platforms.
  3. Death — keep-alive stopped when the farm stopped but auto-combat stayed on → char fought
     unhealed with a full potion bag. Fix: couple combat with keep-alive (never combat without
     heal; stopping the farm turns auto-combat off).
  4. Cold-entry stall + lying `/state` — `g_field_ticked` only cleared on `session.logout`, so a
     death→revive→re-login left it stale-true → `/state` faked `in_world` at char-select AND the
     login pump short-circuited before `StartGame()` → stuck at char-select. Fix: `g_lobby_scene_active`
     (mirrors the Title gate) so `in_world()` is honest at the lobby and the pump reaches StartGame.
- Verified live (pure, 0 nudges, 10 min): 0 stalls, 0 deaths, cross-platform roam (6 cells/21
  heights), 70% time on the densest cell (was 6%), keep-alive coupled, +2.28% EXP. Cold entry
  reaches the field unaided. Owner confirmed end-to-end login→autofarm.
- Open follow-up (owner, next session): farming SPEED is not yet optimal. Also: the
  blacklist-rotate reroute path is unit-tested but not exercised live.
- Lesson: for live-behavior verification, do NOT trust `/state`/staff summaries — confirm via a
  real behavioral signal (field map_id + XP/kills over time); the owner's live screen caught what
  instruments masked.

## 2026-07-27 — gap-host consolidation completed for namlun; legacy NamlunControl retired
- Status: DONE — PR #43 (`b459167`).
- Context: Phase 5 retired `app/` onto gap-host in *code*, but in *practice* the legacy
  `NamlunControl.exe` (bundled app/ host) still ran the farm because gap-host couldn't inject
  into namlun devices (WinError 193). Fixing that (gap-host #29 OnDeviceInjector + namlun #42
  deploy.inject) unblocked the real cutover.
- Decision: prove the gap-host farm chain live, then retire the legacy. Chain PROVEN on 5554:
  deploy (on-device inject) → cold-login (via #41) → `start_farm`/`GeoFarmBehavior` + keep-alive.
  Legacy retired: `archive/legacy-host/` deleted, `NamlunControl.exe`/`build_pyi/`/dist creds
  removed from the box.
- Caught while proving: keep-alive was silently INERT — `make_gap_accounts.py` emitted the
  retired `maintenance` shape but gap-host now reads `consume` (editable-install schema drift).
  Fixed the generator → `consume`, re-verified the heal fires. Lesson saved (project scope).
- Open follow-ups: re-capture `starfield_1649` map pack (stale cells, 0 edges → farms-in-place);
  multi-hop cross-map-nav stall at Magatia (blocks optimal star-field routing). Router is sound.

## 2026-07-27 — Autologin must be FULLY headless — no host start-tap (owner call)
- Status: DONE — PR #37 (`1192b36`, headless enter, zero-tap) + PR #38 (find_injector auto-discovery)
  + PR #41 (`b615652`, cold-login away-parked reclaim: keep the reserve-away retry alive past the
  `g_login_initiated` latch) — all merged, all live-verified on emulator-5554. Cold `/session/login`
  for an away-parked char now reclaims via QA_Away instead of hanging at touch-to-start.
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
  PR #39 (`80313c6`). Follow-up SHIPPED: HP/MP keep-alive (auto-drink + auto-restock)
  live-verified with a negative control and merged — gap-host PR #27 (engine) + namlun PR #40
  (config: HP 55% / MP 50%, restock to 200). Open follow-ups: login-retry gap on cold
  `/session/login` (fix in flight, headless-lobby); gap-host AndroidDeployer can't drive
  namlun (`WinError 193`).
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

