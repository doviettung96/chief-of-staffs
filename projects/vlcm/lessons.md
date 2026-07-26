<!-- MIRROR of C:\Users\Tung\Projects\vlcm\LESSONS.md
     Source of truth is that file, in the project's own repo.
     Overwritten by scripts/sync-project.py — do not edit here. Synced 2026-07-26. -->

# Lessons — vlcm

Project-scoped lessons (committed, shared with the team and every agent that opens
this repo). For non-obvious bugs/insights specific to this codebase. General lessons
live in `~/.agents/LESSONS.md`. Before debugging, skim this file first, then global.

---

### Drive the game's OWN mechanism (PipeManager notifications + UI events), never hand-crafted packets — even NetWorkManager.sendMsg is too low-level for a stateful flow
- Date: 2026-07-04
- Symptom: entering a `team` dungeon by hand-sending the reversed enter opcode from the
  agent (`NetWorkManager.sendMsg(10701, [npc,map,reward,diff])`) teleported the char into
  the instance map for ~10s then auto-reverted — the instance never "started" (no `10724`
  start-timer, no `10726` clear) and re-entry then failed. Same class of failure whether
  using `10701` (free), `10721` (token) or pre-sending `10711`.
- Root cause: the enter is a STATEFUL multi-step client↔server handshake, not one packet.
  The real client must (1) have the NPC locked (`GameInstance.lockOnChar`, set via the
  click), (2) have sent the NPC-interact `send_10129` that opens the SERVER-side NPC
  session, (3) have opened the instance panel (whose `addedToStage` requests the list into
  `currentFubenList`), and only then does the panel's own handler send the enter WITH that
  state — after which the client runs its scene-load pipeline on the server's teleport
  reply. A hand-built enter packet carries none of that client state, so client and server
  desync (server teleports; client never loads the instance scene) and the run never starts.
- Rule: NEVER hand-craft packets (not even `NetWorkManager.sendMsg` with a correctly
  reversed payload) to drive a stateful game flow. Drive the game's OWN high-level
  mechanism from the in-VM agent — fire the same PipeManager notifications and dispatch the
  same UI events the real client fires:
  `PipeManager.sendMsg("SINGLE_CLICK",[null,npc,null])` to click an NPC (locks it + sends
  `10129` + walks + opens dialog), `PipeManager.sendMsg("SHOW_INSTANCE_SELECT_PANEL")` to
  open the panel, `panel.dispatchEvent(new BaseEvent("UI_INSTANCECONVECTION_BTNCLICK","",
  [id,reward,diff]))` to enter. The game then emits the correct packets, in order, with the
  correct client state. Reserve raw `sendMsg` for STATELESS self-contained actions only
  (e.g. the afk toggle `50583`) where there is no client-side follow-through.
- Status (2026-07-04): the mechanism verbs are built (`team:click/open/go`) and partially
  proven live — `SINGLE_CLICK` walks the char to the NPC, `team:open` opens the panel and
  loads the list. The final `team:go` dispatch does not yet fire the enter; the remaining
  gap is a precondition in `onClickEnterTeamPanel` (likely the panel must be reached via the
  NPC dialog's dungeon option / `REQ_NPC_FUNCTION`, not `SHOW_INSTANCE_SELECT_PANEL` direct,
  so `lockOnChar` + the panel's selection state are established the game's way).
- Tags: #botbridge #agent #gamemechanism #pipemanager #dungeon #stateful

### The swf-bridge agent parses ONLY raw newline verbs — JSON command envelopes are silently dropped
- Date: 2026-07-03
- Symptom: bringing up a new feature (Zodiac dungeon), `POST /sessions/{id}/send`
  (`{socket,msg_id,payload}`) and `POST /sessions/{id}/swf_bridge/command`
  (`{cmd,params}`) both returned `{"status":"ok"}`, but the game did nothing and no
  reply packet ever came back. Looked like the opcode/payload was wrong.
- Root cause: `"ok"` from those endpoints only means the app QUEUED/wrote the command;
  it does not mean the in-VM agent executed it. The live agent (`BotBridge.as` /
  `build_tgame3441`, version `BotBridge/3.0-min`) dispatches commands purely by raw
  string prefix in `bbOnData` (`line.indexOf("afk:")==0`, `"hit:"`, `"q:"`, `"zx:"`,
  bare `x,y` = walk). It has NO `JSON.parse` of a `{cmd,...}` envelope and no generic
  "send arbitrary msg_id" verb, so the JSON that `send_packet`/`bot_command` emit
  (`swf_bridge.py` `_send_loop` writes `json.dumps(cmds)`) matches no prefix and is
  dropped. Its forwarded/received msg-id set is likewise HARD-CODED in
  `bbRegisterForwardedMsgs`, so `register_msg` (JSON) is a no-op too — a received id
  the agent didn't pre-register never reaches `/debug/packets`.
- Rule: to bring up a new feature through the running app, add a **raw-line verb** to
  `BotBridge.as` (`bbOnData` prefix branch → the game's own `NetWorkManager.sendMsg` /
  PipeManager call), forward any new received ids by adding `bbRegisterMsg(<id>)` to
  `bbRegisterForwardedMsgs`, rebuild the blob (`vlcm-toolchain/build_botbridge.sh`) and
  re-inject (relaunch the client). Trigger the verb via `bridge.send_line(...)` — exposed
  as `POST /sessions/{id}/swf_bridge/line` (added this session; also returns the agent's
  echo `agent_text`, e.g. `ZX:info:0` / `gn2129=0`). To CONFIRM a verb actually ran, look
  for its echo on the bridge socket (`fd=3592`) in `MongChiTonClient/vlcm_mod.log`
  (`5a 58 3a…` = `"ZX:"`); the DLL shadow-logs every send. Do NOT trust the endpoint's
  `"ok"` as proof of execution.
- Related gotcha (persisting a background helper): a Windows Scheduled Task must launch
  `python.exe` DIRECTLY, not the `py.exe` launcher — `py.exe` spawns `python.exe` and
  exits, so the task instantly drops to `Ready` and its own tracking is useless. (Seen
  wiring up `scripts/zodiac_watch.py` as `VLCM_ZodiacWatch`.)
- Tags: #botbridge #swf_bridge #agent #protocol #bringup #windows #scheduledtask

### The DLL's HTTP API port is dynamic (per-PID mapping file), never 32123
- Date: 2026-06-29
- Symptom: `Invoke-RestMethod http://127.0.0.1:32123/ping` "failed: connection closed
  unexpectedly", with a storm of `TimeWait` sockets on 32123. Looked like the injected
  DLL's API was dead or port-blocked. 32123 turned out to be owned by an unrelated
  `adb.exe` (LDPlayer emulator) holding an `adb forward tcp:32123` LISTEN socket.
- Root cause: the DLL does NOT bind 32123. `native-lib/src/main.cpp` calls
  `HttpServer::start(0, ...)` → `bind_to_any_port` (OS-assigned port), then writes the
  real port to `%TEMP%\vlcm_dll\<pid>.json` (`writeMappingFile`). The app resolves it
  per-PID (`app/core/auto_injector.py` reads that dir; `config.dll_http_url_for_port`).
  `32123` survived only as a dead default in `config.py` (`DLL_HTTP_PORT`/`DLL_HTTP_URL`,
  imported nowhere) and as a hardcoded hint `printf` in `injector/injector.cpp` — both
  pointed at a port the DLL never uses, which is what sent debugging down the adb path.
- Rule: to reach a running client's DLL API, READ `%TEMP%\vlcm_dll\<pid>.json` for the
  actual `port` — never assume 32123. Do not "free" / kill whatever holds 32123; it is
  irrelevant to the PC bot. (Cleaned up: removed the dead `config.py` default and the
  injector hint in this session.)
- Tags: #windows #ports #dll #injector #adb #ldplayer #config

### Quest target with no position hint must navigate via the game's one-click, not fight in place
- Date: 2026-06-29
- Symptom: a reset daily (`scripts.autoquest --run 3002`) logged "stuck (no progress for
  150s) at fight" and was skipped. Its next target was `goods 1201` with
  `scene=0, x=0, y=0` (no position). The bot auto-battled wherever the char happened to
  stand and never collected anything.
- Root cause: `app/net/quests.py decide()` only navigates when `QuestTarget.has_pos` is
  true; a kill/collect target with no coords fell straight through to `ACT_FIGHT`
  (fight-in-place). The server still knows the target's location — the client heartbeat
  just didn't carry coords — so the game's own `TaskTracker.doTaskNextBehavior` CAN
  pathfind to it. Fighting in place never moves the char there.
- Rule: for a `monster`/`goods` target with `not has_pos`, return `ACT_ADVANCE` (drive
  `doTaskNextBehavior` via `q:next` to pathfind to the server-known spot, then act) —
  never fight in place. NPC/area/action targets are position-agnostic (the talk/report
  is client-authoritative) and still act on-kind immediately. Verified end-to-end: the
  fix makes the no-pos daily navigate instead of grinding nothing (note: navigation ≠
  guaranteed completion — some no-pos items have a source the client can't resolve).
- Proven sub-case (daily 3002, goods 1201): the buy diagnostic was constant —
  `buy echo: g=1201 n=38 idx=-1 npc=-1` (38 vendor NPCs in scene, NONE sells 1201) and
  `n` never changed (char never moved, because there is no position to walk to). So this
  item has neither a quest map-position NOR a current-scene vendor → genuinely
  un-completable client-side; its source (other-town vendor / craft / grant / specific
  drop) lives in server-side `res/data/*.tsze`, not this checkout. This is a DATA gap,
  not a missing target-type handler. To debug such echoes, the controller now surfaces
  `QB:` (buy) and `QN:` (next) echoes via `_ingest` (`last_buy_echo`/`last_next_echo`).
- Side effect to remember: making a no-pos target NAVIGATE (move) defeats the
  position-based stuck detector, so an un-completable no-pos quest now burns the full
  per-quest `--timeout` instead of tripping `stuck_after`. Mitigate by pre-skipping a
  no-pos goods whose buy echo reports `idx=-1/npc=-1`.
- Tags: #quests #automation #botbridge #navigation #decide

### Main-story / some quests gate on scripted-boss/instance spawns, not target type
- Date: 2026-06-29
- Symptom: main quest 9100 ("kill 4 of monster 1290") ran 15 min at `0/4` — the bot
  reached the tile (logged `ACT_FIGHT` = `decide()` only does that when at the target)
  and auto-battled, but never landed a single kill. A field-mob weekly (monster 1160/1170)
  killed fine in parallel.
- Root cause: in the heartbeat, 9100's `next_id == end_npc == 1290` (target equals the
  hand-in entity). `BotBridge.bbHitMob(1290)` scans only the current scene for a live
  `res.id_kind==1290` and found none. The fingerprint is a scripted/boss/instance spawn
  that the field auto-path/auto-battle loop can't materialize or trigger — it is NOT an
  unimplemented `TaskTargetType` (still type `monster`).
- Rule: when a kill quest stalls at `0/N` despite reaching the tile, suspect a
  boss/instance/scripted spawn (tell: target id == end_npc, or the mob is absent from the
  scene). These need a separate instance-entry + boss-fight capability, not a new
  target-type handler. The monster/scene/task static tables are server-side
  (`res/data/*.tsze`) and NOT in this checkout — confirm such data live via the injected
  client (`MonsterResManager`/`TaskResManager`), not from `dumps/`.
- Tags: #quests #automation #boss #instance #static-data #botbridge

### Launching a VISIBLE game from an agent shell: Session 0 vs Session 1 (DEBUG-ONLY)
- Date: 2026-07-01
- Symptom: the agent launched `MCTClient.exe` (directly, via the injector, or via the
  launcher) and it ran fine — process alive, DLL injected, sockets up — but the user
  never saw a window. Window enumeration from the agent shell also returned nothing.
- Root cause: the agent's Bash/PowerShell tools run in **Session 0** (the non-interactive
  services session, no visible desktop). A child process **inherits its parent's session**,
  so anything the agent spawns lands in Session 0 and draws onto an invisible desktop. A
  Session-0 process also **cannot enumerate Session-1 windows** (separate window stations),
  so `EnumWindows` from the agent shows an empty list even when the user clearly sees the
  client. `Get-Process ... SessionId` is the tell (0 = invisible, 1 = user's desktop).
- Rule (debug workaround): to make the agent able to start a VISIBLE client, use a
  **Task Scheduler task with the interactive flag** (`schtasks /create ... /it`, runs "only
  when the user is logged on"). Triggering it with `schtasks /run /tn <name>` executes the
  program in the **user's Session 1** (visible), and every process IT spawns
  (launcher → injector → game) inherits Session 1 too. `127.0.0.1` APIs (`:9898`) cross
  sessions freely — only desktops/windows are isolated. Token-duplication
  (`CreateProcessWithTokenW` off explorer's token) was tried and the child died on startup;
  the scheduled task is the reliable path. Set up here as task `VLCM_Launcher` →
  `start_launcher.bat` → `py launcher.py` (from source, so code edits need no rebuild).
- IMPORTANT scope: this is a **DEBUGGING aid for the agent only**. In real usage the user
  starts the final bundle themselves from their interactive desktop, so it is already in
  Session 1 and NO scheduled task is needed. Do not bake this into production flows.
- Tags: #windows #session0 #visibility #scheduledtask #debug #launcher

### Windows Defender quarantines injector.exe as a false-positive trojan
- Date: 2026-07-01
- Symptom: `injector/build/Release/injector.exe` kept vanishing seconds after appearing —
  `/game/launch` intermittently 400'd ("injector not found") and freshly-copied/extracted
  copies disappeared within seconds. Looked like a concurrent agent cleaning build dirs.
- Root cause: Defender real-time protection flagged the injector as
  `Trojan:Win32/Bearfoos.A!ml` (an ML heuristic — it does `CreateRemoteThread` +
  `LoadLibrary`, classic injection behavior) and quarantined it. Confirmed via
  `Get-MpThreatDetection` (Resources pointed at the exact injector paths). It is a FALSE
  positive on our own tool.
- Rule: add a Defender exclusion for the repo so build artifacts survive:
  `Add-MpPreference -ExclusionPath 'C:\Users\Tung\Projects\vlcm'` (needs an elevated token;
  the agent shell had one). Check `Get-MpThreatDetection` whenever a built binary
  mysteriously disappears — suspect AV before blaming concurrent processes or the build.
- Tags: #windows #defender #antivirus #injector #falsepositive #build

### Auto-login needs .cache/credentials.json AND a freshly-built shell patch
- Date: 2026-07-01
- Symptom: game launched + injected fine (DLL `hooks_installed:true`, mapping present) but
  sat at the MANUAL id/password login screen (DLL `/status` sockets=0) — no auto-login.
- Root cause: two independent pieces are required. (1) The client's `MongChiTonClient.swf`
  shell must be auto-login-PATCHED (`scripts/build_autologin_shell.py`, marker
  `autologin.json`); an unpatched/reverted shell shows manual login. (2) The patch build
  reads credentials from `.cache/credentials.json` (`{username,password,server_id}`); if
  that file is missing/empty it errors "no credentials" and the shell stays stock. The
  patched shell reads `MongChiTonClient/autologin.json` at RUNTIME (deployed by the build),
  which is what actually feeds login — editable without a rebuild. Note `server_id` (e.g. 2
  = "Thiên Ảnh"); wrong server = wrong login target. Also: the API's `CredentialStore`
  rewrites `.cache/credentials.json` to its own schema (blanking username/password), so
  don't rely on that file surviving — the deployed `autologin.json` is the source of truth.
- Rule: to enable auto-login, write `.cache/credentials.json` with real
  `username/password/server_id`, run `py scripts/build_autologin_shell.py` (verify
  `shell_is_patched()` → True), then launch. A relaunch then reaches in-world (sockets>0)
  with no typing. Debug diagnosis order: shell patched? → creds present? → server_id right?
- Tags: #autologin #credentials #swf-patch #shell #botbridge

### Don't gate "in-world" on the heartbeat's hp; partyID can drop from bbCollectState
- Date: 2026-07-02
- Symptom: `grow_stronger` saw the char at tile (44,27) with `hp=None`/`class=None` for
  minutes and concluded "character not loaded" — yet `bbAddAttr` read `partyID=1` and
  `points_action=190` fine at the same time, and the attribute allocation actually worked
  (free 190 -> 0). The heartbeat also flickered fully empty every ~12s.
- Root cause: `bbCollectState` set `player.party` AFTER the `hp`/`mp` reads inside a single
  `try`; a mid-load blip on `attributeInfo.hpNow` skipped the rest of the block, so `hp`
  AND `party` were dropped from the heartbeat even though the char was fully in-world and
  `attributeInfo` was readable. Downstream, `send_add_attr_for_class` read `party` from the
  (blank) heartbeat, fell back to the DEFAULT preset (50/10/20/20), and MIS-allocated a
  Shaolin char's 190 points as 95/19/38/38 instead of 76/38/19/57 — irreversible.
- Rule: do NOT gate "in-world / ready" on the heartbeat's `hp` — it under-reports a loaded
  char. Gate on `enter_scene`/`has_selected_char`, or just fire the bridge command and read
  its echo (the `bb*` methods read `goodsBagArr`/`skillObj`/`attributeInfo` DIRECTLY, so
  they work even when the heartbeat's `player` block is momentarily blank). For irreversible
  actions keyed on class (attribute allocation), never fall back to a default preset — wait
  for `partyID` and refuse if still unknown. In `bbCollectState`, capture `partyID`
  first + in its own `try` so a later stat read can't drop it. (All three fixed this session.)
- Tags: #botbridge #heartbeat #attributes #autologin #liveverify #grow_stronger

