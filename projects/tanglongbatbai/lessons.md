<!-- MIRROR of C:\Users\Tung\Projects\tanglongbatbai\LESSONS.md
     Source of truth is that file, in the project's own repo.
     Overwritten by scripts/sync-project.py — do not edit here. Synced 2026-07-26. -->

﻿# Lessons Learned

Gotchas worth never hitting twice. Read before debugging (grep by error text or tag);
append after resolving a non-obvious error. One atomic entry each, newest on top.

Format:
```
### <one-line title>
- Date: YYYY-MM-DD
- Symptom: what was observed (paste the actual error text)
- Root cause: why it really happened
- Rule: what to do - and what never to do again
- Tags: #build #windows #flaky #async ...
```

---

<!-- Add lessons below this line -->

### Xinfa study is faction-scene native, not menu-gated
- Date: 2026-07-10
- Symptom: `AutoRunToTargetEx` transferred a Tiêu Dao character to Lăng Ba Động but stopped at the scene entry, and direct NPC coordinates did not move. The original `mempai + 9` scene mapping sent mempai 8 toward scene 17 instead of Tiêu Dao scene 14.
- Root cause: AutoSearch faction scene IDs are not ordered by `Player:GetData("MEMPAI")`; use an explicit mapping. Also `SkillsStudyFrame_study(defineId)` succeeds from inside the correct faction scene even when `ActionSkillsStudy` is not open.
- Rule: For xinfa/book automation, map mempai IDs explicitly and verify scene arrival; do not require reaching the trainer/menu before calling `SkillsStudyFrame_study`. Never use `mempai + 9` as the faction scene rule.
- Tags: #tlbb #xinfa #autobook #lua #navigation #runtime

### Shop transactions require a visible in-range shop window
- Date: 2026-07-10
- Symptom: `NpcShop:BulkBuyItem(idx, 1)` returned success and `NpcShop:GetNpcId()` stayed non-zero, but the item count and `money_jz` did not change. Selling via `EnumAction(pos, "packageitem"):DoAction()` failed with `attempt to call method 'DoAction' (a nil value)`.
- Root cause: `NpcShop:GetNpcId()` can remain populated from a stale/hidden shop object. Real buy/sell only works after opening a nearby NPC shop so the `Shop` window is visible. The mobile runtime's package/booth action objects expose metadata, but the reliable sale path is the game's Packet UI path.
- Rule: For NPC shop automation, require `IsWindowShow("Shop")` plus a valid `NpcShop` before transactions. Open the NPC dialog while in range, click the buy/sell dialog option, buy with `NpcShop:BulkBuyItem(idx, qty)`, and sell with `PrepearSale()` plus `Packet_ItemBtnClicked(pos + 1)`. Never treat a non-zero stale `NpcShop:GetNpcId()` as transaction-ready.
- Tags: #tlbb #shop #lua #runtime #automation

### Packaged TanglongBot uses bundled Lua, not checkout Lua
- Date: 2026-07-09
- Symptom: `POST /api/devices/553/reload` returned `{"loaded": true}`, but live
  `TLBot.State.get()` still lacked newly edited fields from `bot/lua/state.lua`.
- Root cause: the running dashboard was `dist/TanglongBot.exe`, so `paths.py`
  resolved Lua resources from the PyInstaller bundle, not the checkout. Direct
  source-side `Bridge.load_modules()` loaded the edited Lua only temporarily; the
  packaged bot could overwrite it again.
- Rule: when the active server is `dist/TanglongBot.exe`, rebuild and restart
  the exe for Lua/Python handler changes to persist in the current automation
  loop. Do not trust API reload as proof that checkout Lua is active.
- Tags: #pyinstaller #lua #runtime #tlbb #windows

### Auto-revive can miss the death edge while a device is offline
- Date: 2026-07-08
- Symptom: device 503 returned alive in town at about 5% HP after being killed, but did
  not visit the medic.
- Root cause: the auto-revive watcher only ran medic top-up after it personally
  observed death and completed revive. If the game or bridge was offline during
  death/reconnect, the next observable state was already alive with `needs_revive=false`,
  so the watcher skipped medic.
- Rule: auto-revive must also handle alive low-HP town/reconnect states, not only the
  death edge.
- Tags: #game-re #tlbb #revive #medic #reconnect

### Revive is a two-stage underworld path, not a single "respawn" call
- Date: 2026-07-06
- Symptom: after death we called `Player:SendReliveMessage_OutGhost()` ("Đầu thai")
  expecting a town respawn; the character stayed "dead" — actually a GHOST in the
  "Địa Phủ" (underworld) scene at hp=1. `state.dead` (hp<=0) reported FALSE (hp=1), so
  every death check and the revive verify thought he was alive, leaving him stranded.
- Root cause: `SendReliveMessage_*` only sends you to the underworld; it does NOT return
  you to the living world. From Địa Phủ you must TRAVEL to the "Mạnh Bà" transport point
  (AutoSearch tabtype-99) to arrive back in a town — still at ~1 hp, so a medic/regen is a
  separate final step. A ghost has hp=1, so hp is not a clean death/ghost signal.
- Rule: model revive as a state machine, not one call —
  (1) truly dead: fire OutGhost ONLY when the Relive popup is up — `IsWindowShow("Relive")`
      is the clean trigger (verified true exactly at death; hp can blip to 0);
  (2) ghost: detect by scene == "Địa Phủ" (NOT hp) and travel to "Mạnh Bà" to return;
  (3) restore HP at the town medic ("Giang Hồ Du Y", matched by role via tip/info — the
      personal name varies per town: `Trị liệu` -> `Có`). See TLBot.Revive (revive.lua),
      ReviveService/HealService (services.py), death_recovery.py, and state.lua's
      `underworld`/`needs_revive` fields.
- Tags: #game-re #tlbb #revive #death #lua #state-machine

### Bridge ping (`lua_ready`) is a false positive — gate recovery on an exec probe
- Date: 2026-07-06
- Symptom: `GET /ping` returned `{"lua_ready":true}` and the process was alive, yet every
  `POST /exec_lua` returned `{"success":false,"error":"dispatch timeout: game thread did not
  process task"}`. `GameRecovery.ensure_bridge()` early-returned on `bridge_ready()` (ping)
  and never recovered, so the device sat wedged at the login screen forever.
- Root cause: the native bridge runs queued Lua on the game's Lua thread via the `lua_pcall`
  hook. On a static non-gameplay screen (server-select, a "connection lost" modal, post-
  disconnect limbo) the engine stops driving `lua_pcall` on that VM, so dispatched tasks never
  execute — while ping (HTTP server + captured lua_State) stays green. Re-injecting over a
  wedged VM does not help; only a fresh process does.
- Rule: liveness = an EXEC probe, not ping. Use `Bridge.lua_alive()` / `GameRecovery.lua_alive()`
  (`return 1`, short timeout) and gate recovery on it. Recover a stall with FORCE-STOP +
  relaunch + reinject (not just reinject), then confirm `lua_alive` (not just `lua_ready`)
  before logging back in. `LoginService.phase()` already surfaces a stall as "unreachable", so
  once `ensure_bridge()` gates on `lua_alive` the LoginWatchdog auto-recovers it.
- Tags: #bridge #stability #injection #recovery #tlbb #windows

### Multi-device reconcile churn crashes game clients - throttle background form/recovery loops
- Date: 2026-07-06
- Symptom: Running the fleet server (bot/server.py) with a team that couldn't converge (leader
  in a scene the member couldn't autopath into), the poll loop re-ran team formation every
  ~10s: each attempt fired cross-scene autopath + a 3x invite/accept retry burst, all on top
  of the steady 2s per-device state/party polling. Two game CLIENTS crashed outright (pidof
  returned NEW pids - the always-on GameRecovery had relaunched them); their bridges were then
  gone ("connection closed unexpectedly") and the freshly relaunched clients sat at an idle
  login screen ("dispatch timeout: game thread did not process task").
- Root cause: the TLBB client is fragile under sustained concurrent exec_lua load (native
  autopath + party ops + reads stacked from multiple threads). An unthrottled reconcile that
  keeps retrying a non-converging team multiplies that load until the client dies. Separately,
  an idle login screen fires no lua_pcall, so the bridge captures no lua_State and every
  exec_lua times out - a relaunched-but-not-logged-in device looks "bridged" (/ping ok) yet
  can't run Lua.
- Rule: THROTTLE every background loop that drives the game. Team auto-form has a per-team
  cooldown (FORM_COOLDOWN=45s in bot/teams.py; manual "Form & Follow" bypasses it), runs in a
  single background worker per team (never on the poll thread), and skips teams already formed
  with a live follow loop. Give snapshot reads a short timeout (SNAPSHOT_TIMEOUT=6s) so one
  stalled client can't wedge the whole fleet poll. Don't auto-retry a team whose member can't
  reach the leader's scene indefinitely. To recover an idle-login-screen client, drive a login
  (or tap to fire a pcall) - re-inject alone won't make exec_lua work.
- Tags: #game-re #tlbb #tanglong #fleet #multi-device #crash #async #throttle #bridge

### Socket read timeout is TimeoutError (OSError), NOT urllib URLError - wrap OSError in HTTP transports
- Date: 2026-07-06
- Symptom: `POST /api/devices/513/party/info` returned HTTP 500 (uncaught exception) instead of
  a clean 502 when the game thread stalled. Traceback ended in `TimeoutError: timed out` from
  `bridge._post` -> urllib -> `http.client` -> `socket.readinto`. The endpoint's
  `except BridgeError` never caught it, and in the poll loop the same escape could kill a tick.
- Root cause: `bridge._post`/`_get` only caught `urllib.error.URLError`. A connection refused/
  DNS failure raises URLError, but a socket READ timeout (game thread busy past the timeout)
  surfaces as `TimeoutError` - a subclass of `OSError`, NOT of `URLError` - so it slipped past
  the handler and was never wrapped into BridgeError.
- Rule: in urllib-based transports catch `(urllib.error.URLError, OSError)` (OSError covers
  TimeoutError, ConnectionReset, etc.) and re-raise as the app's transport error, so every
  `except BridgeError` (services, controllers, poll loop, endpoints) degrades gracefully.
  General Python gotcha - promotable to global. See bot/bridge.py `_post`/`_get`.
- Tags: #python #http #urllib #timeout #async #bridge #tlbb

### Party roster getters segfault on out-of-range index; invite-accept is AgreeJoinTeam(0)
- Date: 2026-07-06
- Symptom: `TLBot.Party.info()` (which blind-probed team-member slots 0..6) killed the game
  PROCESS on a solo character — bridge "RemoteDisconnected", /ping dead, `pidof` empty.
  Isolated to `DataPool:GetTeamMemGUIDByUIIndex(0)` called while not in a team. Separately,
  accepting a team invite via `Player:SendAgreeJoinTeam_TeamMemberInvite()` (no-arg AND
  slot form `(1)`) returned ok but NEVER joined (invite_count stayed 1).
- Root cause: (a) the native roster getters read a fixed C array; the GUID getter has NO
  bounds check and faults (SIGSEGV) when the index is past the real member count — pcall
  can't catch a native fault (same class as the GetCurrentSceneNameById crash below).
  `GetTeamMemInfoByIndex` IS bounds-safe (returns "???"). (b) A leader's
  `Target:SendTeamRequest()` invite lands in the TeamFrame INVITE LIST (GetInviteTeamCount),
  which is accepted by `Player:AgreeJoinTeam(invitorIndex)` — NOT the TeamMemberInvite path.
- Rule: Only read roster getters when in_team AND within [0, count) (count 1..6); NEVER call
  `GetTeamMemGUIDByUIIndex` (avoid it entirely — name via GetTeamMemInfoByIndex is enough).
  Verify every party action by polling `TLBot.Party.info()` scalars (IsInTeam/IsLeader/
  InTeamFollowMode/GetTeamMemberCount/GetApplyMemberCount/GetInviteTeamCount are all safe).
  PROVEN cross-device recipe (533/543): leader `CreateTeamSelf` →
  `Target:SelectThePlayer(name)`+`SendTeamRequest` → member `AgreeJoinTeam(0)` (0-based) →
  leader `TeamFrame_AskTeamFollow()` = fast "Theo đội" (whole team InTeamFollowMode
  instantly, NO member accept needed; member auto-tracks leader). Leader `StopFollow()`
  clears the team's follow. Roster is self-at-slot-0, so kick/appoint index 1 = first other
  member. See bot/lua/party.lua, PartyService (bot/services.py), bot/party_orchestrator.py.
- Tags: #game-re #tlbb #tanglong #party #team #lua #crash #pcall #bridge

### GetCurrentSceneNameById() hard-crashes the client - never call it over the bridge
- Date: 2026-07-06
- Symptom: Iterating `GetCurrentSceneNameById(id)` over scene ids via the exec_lua bridge
  killed the game PROCESS (emulator fell back to its launcher). Bridge went
  "RemoteDisconnected: Remote end closed connection without response", /ping dead,
  `pidof vn.cmplay.tanglong` empty. Reproduced TWICE - with a raw 0..120 loop AND with ids
  read from the game's own valid lists (g_AutoSearch_CitySceneIDList / the
  DataPool:GetAutoSearchSceneStartEnd range). So it is NOT a bad-id issue.
- Root cause: GetCurrentSceneNameById faults in native code; the fault aborts the process
  and is NOT caught by Lua pcall (pcall catches Lua errors, not a native SIGSEGV). Unusable
  from the injected VM regardless of id validity.
- Rule: NEVER call GetCurrentSceneNameById() through the bridge - pcall will not save you.
  To resolve/travel scenes SAFELY, use the current scene's auto-search data:
  `DataPool:GetAutoSearch(id)` over `DataPool:GetAutoSearchSceneStartEnd(GetSceneID())` -
  tabtype 99 entries are scene links ("Bản Đồ: <scene>") carrying the portal's MAP coords;
  `AutoRunToTarget(x,y)` to one triggers the map transfer (verified: Đại Lý -> Vô Lượng Sơn).
  For a concrete destination scene id + coords use mission reads (GetMissionFinishInfo /
  GetKillMonsterMissionTrackInfo -> sceneId,x,y). Recovery when it does crash: bot/recovery.py
  GameRecovery.ensure_bridge() + LoginService.login() (cached CzLogin session, no creds).
- Tags: #game-re #tlbb #tanglong #lua #crash #scene #bridge #pcall

### Mount detection: GetMountID is blind to exterior rides - use MOVESPEED differential
- Date: 2026-07-05
- Symptom: GetMountID() returns -1 for the bird AND wings even while visibly mounted;
  mount/dismount toggle "fired" (character mounted on screen) but could not be verified.
  MainMenuBar_3_Button_Action3 (the UI ride button) also doesn't exist in the headless
  injected VM, so probing it returns nil.
- Root cause: this account's rides are EXTERIOR rides (bird, wings, ...), not ride-cards;
  GetMountID() only tracks ride-cards. There is no absolute base-speed field either
  (Player:GetData("BASESPEED")/"SPEED" don't exist; only "MOVESPEED" is live). The ride
  button handler MainMenuBar_Clicked_Ride() toggles reliably (confirmed visually both
  ways) but exposes no state.
- Rule: verify mount/dismount DIFFERENTIALLY via Player:GetData("MOVESPEED") (e.g. 4.2 on
  foot -> 5.0 on the bird): fire TLBot.Mount.toggle(), then confirm speed moved the
  intended direction; if it moved the wrong way we were already in the target state, so
  toggle back (self-correcting). Compare speed just-before vs just-after so STABLE speed
  buffs cancel out; only a buff transition inside the ~6s verify window can misfire (wait
  it out). Cosmetic rides with no speed delta (some wings) can't be verified -> report
  verified=False, never a false failure. Keep GetMountID only as a fast-positive for
  ride-card accounts. See bot/lua/mount.lua + MountService in bot/services.py.
- Tags: #game-re #mount #tlbb #detection #lua

### Per-emulator adb forward: host port can't reuse the emulator's own adb port
- Date: 2026-07-05
- Symptom: `adb -s 127.0.0.1:21523 forward tcp:21523 tcp:32123` fails with
  "cannot bind to 127.0.0.1:21523: Only one usage of each socket address ... (10048)".
- Root cause: 21523 is the emulator's OWN adb console/bridge port (already bound). The
  injected libtlbot always binds device port 32123; with 6 emulators, all forwarding host
  32123 would also collide.
- Rule: give each emulator a distinct HOST forward port that maps to device 32123, using
  the existing convention host = 32000 + last-3-digits (21503->32503, 21523->32523). The
  port is env-configurable via TLBOT_BRIDGE_PORT (bridge.py, inject.py); device port stays
  32123. Launch: `SERIAL=127.0.0.1:21523 TLBOT_BRIDGE_PORT=32523 py bot/inject.py`.
- Tags: #adb #windows #emulator #ports #tlbb

### Native item discard: base bag is CDataPool tab 22 (UserBag), not tab 4
- Date: 2026-07-09
- Symptom: `TLBOT_DiscardArm(4, pos)` returned 0 (item not found) for a real base-bag
  item, though `DiscardItem()`'s decompiled switch handles tab 4/5/22 and tab 4 uses a
  100-slot getter that looked like "the bag".
- Root cause: the `Lua_DiscardItem` switch tabs map to distinct CDataPool containers via
  vtable getters, and tab 4 is the storage BANK, not the player bag:
  tab 22 -> `UserBag_GetItem` (vtbl+312) = player bag (base + material, one flat array);
  tab 4 -> `UserBank_GetItem` (vtbl+816) = bank (empty unless at a banker);
  tab 5 -> `UserEquip_GetItem` (vtbl+216) = worn gear.
- Rule: arm base/material discards with **tab 22**, indexed by the GLOBAL bag position
  (`item.bag_pos`: base = pos, material = baseMax + pos), not the per-tab pos. The native
  arm = write `*CDataPool::s_pMe`+53672 (tab) / +53676 (index) + item `SetLock(1)`
  (vtbl+208), then call `DiscardItem()` -> sends `CGDiscardItem` (packet id 291, body
  {index, flag}; flag=1 for tab 4, 0 for tab 22). Full offset map + addresses:
  `re/discard_re_notes.md`; implementation: `native-lib/src/NativeBind.cpp` +
  `TLBot.Item.discardSlot` in `bot/lua/item.lua`.
- Tags: #game-re #tlbb #item #discard #lua #native #offsets

### Hot reload must clear removed Lua globals
- Date: 2026-07-10
- Symptom: After removing `TLBot.Item.useFirstMatching` from `item.lua` and reloading
  modules, live devices still reported the function existed.
- Root cause: `TLBot.Item = TLBot.Item or {}` preserves the existing table across hot
  reloads, so deleted source functions remain in the running Lua VM unless explicitly
  nilled.
- Rule: When removing a Lua helper from a hot-reloaded module, explicitly assign the old
  symbol to `nil` during reload. Do not assume deleting it from source removes it from
  the live VM.
- Tags: #tlbb #lua #hotreload #runtime
