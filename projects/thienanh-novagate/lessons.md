<!-- MIRROR of C:\Users\Tung\Projects\thienanh-novagate\LESSONS.md
     Source of truth is that file, in the project's own repo.
     Overwritten by scripts/sync-project.py — do not edit here. Synced 2026-07-29. -->

# Lessons Learned

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

### Restore device selection after a packaged host restart before judging team health
- Date: 2026-07-29
- Symptom: after deploying and successfully launching a fresh `ThienAnhControl.exe`, the dashboard API was healthy but `/api/targets` and `/api/extensions/thienanh/devices` were empty, configured teams reported `follow: idle`, and no formation ran. The private MuMu ADB server still listed all expected emulators.
- Root cause: operator device selection is deliberately session-scoped and is not persisted across host restarts. The new host therefore had no selected targets even though team configuration, emulator connectivity, bridges, and credentials were intact.
- Rule: after restarting the packaged host, verify the private ADB server first, then restore the configured devices through `POST /api/extensions/thienanh/devices/selection` before diagnosing deployment, bridge, login, or party failures. Reattachment probes the existing bridges; do not assume an empty fleet requires native reinjection.
- Tags: #thienanh #deployment #restart #devices #selection #adb #party

### A console/GUI launcher started over SSH lands in Windows session 0 and dies — relaunch it into the active console session via a one-shot interactive-token scheduled task
- Date: 2026-07-28
- Symptom: after scp'ing the rebuilt `ThienAnhControl.exe` bundle to a remote Windows host and swapping it into place, relaunching it with a plain `ssh host "Start-Process ThienAnhControl.exe"` showed 2 processes at +6s but then `Get-Process` returned `count=0` — the launcher started and immediately exited. (`scp` had also refused to overwrite the old exe with SFTP `dest open Failure` because the prior launcher was still running and holding a lock on the file.)
- Root cause: an interactive `ssh` command runs in Windows **session 0** (the non-interactive `services` session), while the real desktop/console user (`admin`) is logged into **session 1**. A console/GUI app launched from session 0 can't attach to the interactive desktop and is torn down when the SSH channel closes. `query session` confirmed `console  ADMIN  1  Active` vs `services  0  Disc`.
- Rule: to (re)start a desktop app on a remote Windows box over SSH, don't `Start-Process` it directly — create a one-shot scheduled task with an **interactive token** so it runs in the logged-on user's session, then delete the task: `schtasks /create /tn T /tr "<exe>" /sc once /st 23:59 /ru <user> /it /f` → `schtasks /run /tn T` → verify the process has `SessionId=1` and persists → `schtasks /delete /tn T /f`. Point `/tr` straight at the bare exe path (PyInstaller apps resolve assets from `sys._MEIPASS`, not cwd) — a `cmd /c cd … ^& start …` wrapper just breaks schtasks quoting. To swap a locked, running exe: stop the old instance **by PID** first (it holds the file lock), then rename the staged copy into place.
- Tags: #windows #ssh #deploy #scheduled-task #session0 #launcher #pyinstaller

### HuntBehavior posts char.revive but thienanh has NO revive actuator → revive is a silent no-op; death recovery relies entirely on the game's auto-revive-to-town
- Date: 2026-07-27
- Symptom: during a live integration hunt on 5557, a lv50 char died on a fight map (map 115 spawns lv95 named mobs); `/state` showed `alive:false, needs_revive:true, revive_frame_shown:true`. GAP's `HuntBehavior.tick` calls `cmd.post("char.revive", mode="town")` on death, but the char sat dead until the GAME's own auto-revive returned it to a nearby town (~18s later, map 7, hp ~22% then fast-regen to full). While dead, every `item.use` (hp/mp/food) was server-rejected and the auto-consume Consumer correctly did nothing (its `ch.alive is False`/`needs_revive` guard).
- Root cause: `char.revive` is NOT a declared verb in thienanh's bridge — `/capabilities` lists no revive command or route, and `CommandSink` gates undeclared verbs, so HuntBehavior's revive post is silently dropped (no-op). thienanh's native `Character.cpp` only DETECTS death (reads `UIReviveFrame` / `needs_revive`) — it exposes no actuator to click the revive button. So host-driven revive cannot work here; recovery depends entirely on the game's built-in auto-revive-to-town countdown.
- Rule: on thienanh, do NOT rely on GAP's `char.revive` for death recovery — it no-ops; the game auto-revives to a nearby town after ~18s, so a hunt just waits it out. If host-driven revive is ever actually needed, thienanh must first add a `char.revive` adapter verb (the three edits: `HandleCommand` branch + `BuildCapabilities` + `postGapCommand` route) backed by the `UIReviveFrame` revive button — capabilities listing alone won't create the route. And never route a char to hunt maps whose mobs far outlevel it (map 115 = lv95 vs a lv50 char) — it will die repeatedly.
- RESOLVED (2026-07-28, thienanh #52): the actuator now EXISTS — the no-op is fixed. `ThienAnh::TriggerRevive(mode)` (Character.cpp) resolves `PlayZone.GlobalPlayZone.UIReviveFrame` and invokes the `ButtonBackToCity`/`ButtonReviveAtPos`/`ButtonUseRevivePill` onClick handler (dump-verified each just invokes the frame's backing `Action` = a real press), wired as a VERIFIED verb via all three edits above (incl. the `postGapCommand("/char.revive")` route). Live-confirmed on 5557: char.revive is in `/capabilities` and `POST` resolves (dotted+slashed, not 404) with the structured payload + dispatcher-not-ready guard + mode validation. STILL NOT verified on an ACTUAL death (in-world entry blocked by an external game asset-download failure, `Config.unity3d` — CDN/patch-server outage, not our bug). The general rule that outlived the fix: a verb present in `HandleCommand` + `BuildCapabilities` but MISSING its `postGapCommand` route is a silent 404 no-op (this is exactly the #48 broken window — `session.dismiss_error` had the same miss and was fixed in the same PR); always confirm a new verb with a live `POST`, not just `/capabilities`.
- Tags: #thienanh #gap #revive #death #hunt #capabilities #verification #resolved

### Restock trigger_at >= to causes an endless zero-buy re-tour; restocked:true is reported despite buying nothing
- Date: 2026-07-27
- Symptom: verifying restock on 5557 with `trigger_at=60, to=60` for an item at bag count 34 — the first tour correctly bought it up to 60 (30->60) via `shop.buy_from_npc`. But then the shared `RestockRunner` re-ran the full navigate->open->buy tour EVERY interval, buying 0 each time yet reporting `restocked:true`, repeatedly pausing the active hunt (gate churn).
- Root cause: `RestockConfig` gates "low" as `have <= trigger_at` (inclusive) while `_buy_list`/`_restock_atomic` buy `shortfall = to - have`. With `trigger_at == to` (or `trigger_at >= to`), an item bought up to `to` is still `<= trigger_at`, so `needs_restock` stays true forever → the tour re-fires every interval, buys nothing, never clears. The `shop.buy_from_npc` handler / `SupplyTour` also return `restocked:true` whenever the gated tour ran, even when every shortfall was 0.
- Rule: always configure `trigger_at` STRICTLY LESS than `to` (e.g. trigger 30, to 60) so a completed buy lifts the count above the trigger and the sweep goes quiet. Two robustness follow-ups (owner-prioritized, NOT yet fixed): `RestockConfig`/`RestockRunner` should guard/normalize `trigger_at < to` (or reject `trigger_at >= to` as misconfig), and the composed buy path should report `restocked:false` when a tour bought nothing (all shortfalls 0), not `true`.
- Tags: #gap #thienanh #restock #config #footgun #supplytour

### Vendor NPC: map-object name is a SIGN, not the clickable NPC; shop opens only after walking; bag rows carry no item_id
- Date: 2026-07-27
- Symptom: verifying restock on 5557, `ext.npcs` (clickable) had no "Thuốc"; `dialog.talk_by_id` on the object labelled "Thuốc" (or a single talk from across the plaza) returned no shop (`_open_npc_shop` → null, 0 items). Separately, `item.bag_scan` rows came back with `name` + `count` but `item_id: null`, while the same items inside an open shop DO carry `item_id` (114–137).
- Root cause: three facts. (1) The town-map vendor at (6878,3856) is TWO entities — an `ext.map_objects type=npc` SIGN named "Thuốc" (what the operator configures / the tour name-matches to locate the spot) and a *separately-named* clickable NPC at the same coords ("Trương Trạm Kinh", npc_id 51) that actually owns the shop. The clickable list never contains the sign's name. (2) `dialog.talk_by_id` only opens the shop when the character is within range — you must `nav.move_to` the vendor first (arrival_radius ~400); talking from spawn distance opens nothing. (3) thienanh's bag adapter emits consumables by NAME only (no template id), so bag↔shop reconciliation MUST be by fuzzy name — an id-based restock top-up can't work for this game (this is exactly why the shared GAP RestockRunner picks the composed `shop.buy_from_npc`/name path here, not atomic `shop.buy`).
- Rule: to open a town vendor, match the configured npc name against `ext.map_objects` to get the SPOT, `nav.move_to` it, THEN pick the nearest `ext.npcs` clickable and open that (this is what `SupplyTour.run` does — reuse it, don't reimplement a bare talk_by_id). Never assume the map-object name equals a clickable npc, and never assume a shop opens without walking. For any bag reconciliation on thienanh, match by name (`best_name_match`), not `item_id` — bag rows have none.
- Tags: #thienanh #gap #shop #vendor #restock #supplytour #navigation

### Consume success = stack-count drop; item.use ok is fire-and-forget, IsItemCanUse is type-only
- Date: 2026-07-27
- Symptom: needed a deterministic "did this consumable actually get used?" signal to probe grades highest→lowest. `item.use` returned `ok=True` for BOTH a grade the char could use AND a too-high grade the server silently rejected (live: grade-4 food 131 → `ok=True`, bag count 280→280, no buff; grade-3 food 130 → `ok=True`, 61→60, buff 100020 appeared).
- Root cause: `TCPGame.SpriteUseGoods(int[])` is `void` — a fire-and-forget TCP send — so the native `item.use` returns `!exc` ("the invoke didn't throw"), never "the server accepted". The obvious client-side predicate `KTGlobal.IsItemCanUse(int itemID)` is NOT a level/grade gate either: disassembled (x86-64 `libil2cpp.device.so`), it resolves the ItemData template and checks only the item's TYPE byte (`@0x41 ∈ {0x11,0x12}`) — no RoleData/character-level lookup. Consumables carry no client-readable required level (`ReqProp` is equipment-only, reads 0), so the client literally cannot know if a grade is usable; only the SERVER does. The server confirms by decrementing the bag stack (client does NOT decrement optimistically — a rejected use leaves the count unchanged).
- Rule: to tell an accepted consume from a rejected one, read back the used stack's COUNT via `item.bag_scan` and check it dropped (settles <0.3s live; poll a bounded ~1.2s window). Never trust the `item.use` `ok`, `IsItemCanUse`, or a guessed grade→level table. For the granted food buff, observe `character.buffs` after a confirmed eat and maintain the buff that actually appeared (grades can grant different buff ids) rather than hardcoding one. This is the signal GAP's consume probe relies on (thienanh #48 / GAP #28).
- Tags: #consume #il2cpp #reversing #grade #probe #thienanh #gap

### A new GAP verb needs an HTTP route registered, not just a HandleCommand branch
- Date: 2026-07-27
- Symptom: added `item.use` to `GapAdapter::HandleCommand` AND to `BuildCapabilities` (so `/capabilities` listed it), rebuilt + injected, but `POST /item/use` returned plain HTTP 404 "Not Found" — the verb never reached HandleCommand.
- Root cause: `native-lib.cpp` registers each command path explicitly with httplib via `postGapCommand("/item.use", "item.use")` (and its slashed alias). Only registered paths exist on the server; an unregistered path 404s at the HTTP layer before HandleCommand runs. Capabilities listing a verb does NOT create its route.
- Rule: a new adapter verb needs THREE edits in the native bridge — (1) the `if (v == "...")` branch in `GapAdapter::HandleCommand`, (2) the `commands`/`ext` list in `BuildCapabilities`, and (3) a `postGapCommand(...)` route registration in `native-lib.cpp`. Miss (3) and it 404s despite (2). Confirm with a live `POST`, not just `/capabilities`.
- Tags: #gap #adapter #native #httplib #routing #verification

### A memfd-injected bridge isn't in /proc/maps by name → deployer re-injects and crashes Unity
- Date: 2026-07-27
- Symptom: redeploying a rebuilt bridge, the deployer injected repeatedly over the SAME pid (`bridge ping timed out after injection` → inject again, 4+ times); the game process ended up wedged (pid alive, HTTP dead). Earlier redeploys "worked" only because the first post-inject ping happened to succeed before the next reconcile.
- Root cause: the injector runs with `-dl_memfd` (loads the .so from an anonymous memfd), so it does NOT appear in `/proc/<pid>/maps` under `libmodtemplate.so`. `_reconcile`'s `process_maps_contains(pid, BRIDGE_NAME)` guard therefore returns False every reconcile, so any tick where the first ping hadn't yet succeeded triggered ANOTHER hot injection — and multiple dispatcher copies over one process SIGSEGV Unity (see the older hot-inject lesson).
- Rule: to load a rebuilt bridge deterministically, do ONE controlled inject and wait generously for `/ping` before anything can reconcile again (a single force-stop → launch → inject → long `_wait_for_bridge`, then drive login with a NullDeployer controller so nothing re-injects). Don't rely on `process_maps_contains` to detect a memfd-loaded bridge. For scripted bring-up, bypass the reconcile loop entirely and inject once.
- Tags: #android #injector #memfd #deploy #dispatcher #crash #gap

### A git worktree needs the gitignored .toolchain/ and cpp extern/ junctioned in to build
- Date: 2026-07-27
- Symptom: `scripts/build-native-lib.ps1` in a fresh worktree failed first with "Missing JDK at .../.toolchain/jdk-17" (setup script absent), then CMake configure exit 1 (extern deps missing).
- Root cause: `.toolchain/` and `native-lib/app/src/main/cpp/extern/` (BNM-Android, Dobby, KittyMemory, OpenSSL) are gitignored / restored out-of-band, so a linked worktree created off `main` has neither. Passing an absolute `-ToolchainRoot` also mis-joins (the script treats it relative to repo root).
- Rule: for native builds in a worktree, create directory junctions to the primary checkout: `New-Item -ItemType Junction .toolchain -Target <primary>\.toolchain` and the same for `native-lib\app\src\main\cpp\extern`, then build with the default `-ToolchainRoot .toolchain -SkipSetup -AndroidSdkRoot C:\Users\Tung\AppData\Local\Android\Sdk`. Both junction targets are gitignored so they never show in `git status`.
- Tags: #build #worktree #gradle #cmake #ndk #windows

### Consumables gate by GRADE not ReqProp; buff duration is ms; food buff id is server-assigned
- Date: 2026-07-27
- Symptom: (a) a food buff's `remaining_ms` read ~1.8e9 (~500 h); (b) auto-consume re-ate food every tick — the maintained buff never appeared; the auto-picked food/medicine was a higher grade the character couldn't use, so the server silently rejected the use.
- Root cause: three separate facts. (1) `BufferData` field @0x20 (dumped `BufferSecs`) is MILLISECONDS on the same clock as `StartTime`/`KTGlobal.GetCurrentTimeMilis` (a fresh food buff ≈ 1,799,901 ⇒ 30 min); a stray `*1000` gave 500 h. (2) Consumables do NOT list a level in `ItemData.ListReqProp` (that's equipment-only: `KE_ITEM_REQUIREMENT.emEQUIP_REQ_LEVEL=5`) — `req_level` reads 0. Their required level is encoded by the GRADE `ItemData.Level` (byte@0x46): grade 3 ⇒ lv50, grade 4 ⇒ lv70 (goods 130/131, confirmed live — a lv50 char consumes the grade-3 food + gets buff 100020, but the grade-4 food is NOT consumed and grants nothing). (3) The numeric buff id a food grants (100020) is assigned by the SERVER on use — not in client `ItemData` (EffectID=0; `MedicineProp` is name+value).
- Rule: compute buff remaining as `StartTime + durationField - now` with NO `*1000`. Select a consumable by grade: derive required level from `ItemData.Level` (≈ `20*grade - 10`) and only pick items whose required level ≤ the character's level — never rank purely by stack count, or you pick an unusable higher grade and the use no-ops. Configure the food's maintained buff id (server-assigned, can't be read per food); food auto-selects the strongest usable grade. Verify usability the direct way: `item.use` a grade and check the bag count drops + the buff appears.
- Tags: #il2cpp #reversing #buff #consume #grade #level #thienanh



### A rooted emulator is not a root adb shell — elevate before injecting
- Date: 2026-07-22
- Symptom: On a freshly-deployed machine, every injection failed with `W: inject_lib: Failed to stop target process threads.` then `E: Couldn't open mem file /proc/<pid>/mem, error=Permission denied` → `KittyInjector: Failed to initialize kittyMgr` → `injector exited 1`, sometimes preceded by `adb: error: failed to read copy response: EOF` on the bridge push. The exact same build injected fine on the older machines.
- Root cause: `AndKittyInjector` must `ptrace` the game and open `/proc/<pid>/mem`, which requires real uid 0. The lifecycle ran the injector with a bare `adb -s <serial> shell <injector> …`, which runs as the `shell` user (uid 2000). "The emulator is rooted" only means `su` exists on the device; `adb shell` is still uid 2000 unless `adbd` was restarted as root. The older machines' emulator images happened to run `adbd` as root by default, so the missing elevation was invisible until a new image (non-root adbd) exposed it. (`adb shell id -u` prints `2000` on the broken machine, `0` on the working ones.)
- Rule: Never assume `adb shell` is root just because the device is rooted. Before pushing/injecting, call `Controller.ensure_root(serial)` — it checks `id -u`, runs `adb root` once (cached per serial) to restart adbd as root, waits for adbd to come back and re-arms the dropped forward, and returns whether the shell is now root. Run the injector via `Controller.run_injector(...)`: plain shell when adbd is root, else a `su -c "…" 2>/dev/null || su 0 sh -c "…"` fallback (covers Magisk and redroid/BusyBox). Ensure root *before* the push, because `adb root` restarts adbd mid-transfer → that's the `failed to read copy response: EOF`. Pattern taken from `~/Projects/thanlongmobile-BNM` (`AdbHelper.ensure_root`, ADB_COMMAND_POLICY.md) and `~/Projects/tgun` (`_wrap_root_shell_command`).
- Tags: #android #injector #adb #root #ptrace #runtime #deploy

### Loot: use the game's native auto-pickup, not a host per-kill loot poller
- Date: 2026-07-22
- Symptom: Autofarm killed mobs that "sure will drop", but nothing looked collected. The host `HuntEngine.collect_loot()` reported `clicked=0`; live probing showed `item.loot` returning `before_count=0 note='no drops'` on every poll right after a kill.
- Root cause: Two things. (1) Ground drops materialize on the client several seconds after the kill (~10s observed on 5557), but `collect_loot` broke on the FIRST empty read (`before<=0 and clicked<=0 and remaining<=0`), treating "not spawned yet" as "all collected" and giving up after ~0.8s. (2) It was redundant anyway: the game ships its own auto-pickup (`Server.Data.PickItemConfig.IsAutoPickUp`/`RadiusPick`, reached via `KTAutoAttackSetting._AutoConfig`; executed by `KTAutoFightManager.AutoPickUpItems` / `KTAutoPickUpItemAround`), and it was already ON here (take-all + auto-sell), so drops were being collected+sold natively (which also hid the loss — nothing lands in the bag, money moves instead).
- Rule: For loot in Thien Anh, wire the game's own auto-pickup (`ext.auto_pickup` -> flip `PickItemConfig.IsAutoPickUp`), enabled once at hunt startup; don't reimplement pickup with host-side `DropItemClick` polling. `DropItemClick` isn't instant (it walks the character to the drop), and an empty ground read right after a kill means "too early", never "done". When a game ships an auto-behavior, prefer configuring its own setting over duplicating it above the contract.
- Tags: #gap #thienanh #loot #native-vs-host #timing #autofarm

### Do not hot-inject a second dispatcher build over an already-hooked process
- Date: 2026-07-21
- Symptom: After hot-injecting a fresh `libmodtemplate.so` into a process that already had an injected dispatcher, calling the new bridge led to `Fatal signal 11 (SIGSEGV) ... UnityMain` with a backtrace through the memfd-injected library.
- Root cause: The second injected copy had its own dispatcher globals and tried to hook the same Unity tick already hooked by the previous copy.
- Rule: For dispatcher-bearing native changes, prefer force-stop/relaunch plus fresh injection. Never validate a second injected dispatcher copy over an already-hooked process.
- Tags: #android #injector #dispatcher #runtime #crash

### Disable built-in team follow while host-routing a member
- Date: 2026-07-21
- Symptom: With the leader fighting on map 88, `party-mimic` kept the member out of auto-fight but host travel failed on the `95 -> 88` hop: `nav.move_to` returned HTTP 400 while the member had `MiniTheoSau=1`. Turning follow off made the same `nav.move_to(map=95,x=6258,y=1137)` succeed.
- Root cause: The game's built-in team-follow state can conflict with explicit host navigation, especially after a map hop while the leader is on another map.
- Rule: Out-of-range party mimic should keep the final desired behavior as follow, but temporarily disable built-in follow around host-driven travel, verify arrival through `/state`, then restore follow; only start member auto-fight when same-map distance is inside the mimic range.
- Tags: #party #navigation #gap #runtime #follow

### Read host config JSON with UTF-8 BOM tolerance
- Date: 2026-07-20
- Symptom: packaged smoke served the dashboard but `/api/config` crashed with `json.decoder.JSONDecodeError: Unexpected UTF-8 BOM (decode using utf-8-sig): line 1 column 1 (char 0)`.
- Root cause: a Windows PowerShell smoke config written with `Set-Content -Encoding UTF8` included a BOM, while `hunt_config.load()` read the file as plain `utf-8`.
- Rule: read operator-edited JSON config with `utf-8-sig` so BOM and non-BOM files both work; avoid creating test configs with BOM unless the test is intentionally covering it.
- Tags: #windows #config #json #bundle #smoke

### Native map command success is not party-follow arrival proof
- Date: 2026-07-20
- Symptom: a party member stayed on map 23 with `following=true` while the leader fought on map 88; `goto_map_pos`, `goto_map`, `autopath_change_map`, and `nav.move_to` returned `ok=true` without the member changing maps.
- Root cause: those native movement calls are fire-and-forget/no-exception paths, and built-in team follow does not cross maps by itself. Cross-map party follow needs the map graph plus state-confirmed arrival.
- Rule: for out-of-range party mimic, keep member auto-fight off, keep leader follow on, route with GAP `map_edges` + `nav.move_to`/transfer hops, and verify `/state` map/position; never treat immediate native `ok=true` as movement proof.
- Tags: #party #gap #navigation #runtime #automation

### Do not use `$pid` as a PowerShell injection variable
- Date: 2026-07-20
- Symptom: hot injection failed with `Cannot overwrite variable PID because it is read-only or constant`, then left the target process stopped/traced during recovery.
- Root cause: PowerShell has a read-only automatic `$PID` variable; using `$pid` for the Android target process ID collides with it and can pass the wrong value into the injector command.
- Rule: use names like `$targetPid` for injection scripts, verify `/proc/<pid>/status` has `TracerPid: 0`, and clear stale tracers or force-stop/relaunch before retrying.
- Tags: #powershell #injector #ptrace #runtime #windows

### Stable ADB forwards are required for team maintenance
- Date: 2026-07-20
- Symptom: team maintenance showed two devices as separate party leaders instead of forming one party.
- Root cause: selected-device auto-register shifted emulator host ports and lifecycle treated dispatcher=false pings as ready.
- Rule: keep emulator host ports deterministic by serial, clean mismatched forwards, and never mark dispatcher/ticking false as control-ready.
- Tags: #adb #party #lifecycle #automation #gap

### Foreground and untraced target before bridge injection
- Date: 2026-07-20
- Symptom: injector hung, then later `PTRACE_ATTACH failed ... Operation not permitted`; `/proc/<pid>/status` showed `TracerPid=<AndKittyInjector pid>`.
- Root cause: a timed-out injector left the game process traced, and the first attempt targeted a background/frozen app process.
- Rule: before reinjecting, force-stop/relaunch or foreground the Unity activity, verify `TracerPid: 0`, and kill stale injector tracers; do not hot-inject over an already-hooked or already-traced process.
- Enforced in code: `BridgeLifecycle._ensure_untraced_target` (app/lifecycle.py) runs before every injection — reaps stale `AndKittyInjector` procs, checks `TracerPid`, and force-stops/relaunches if traced. Backed by `Controller.tracer_pid` / `force_stop` / `reap_processes`.
- Tags: #android #injector #ptrace #hooking #runtime

### TMP input fields need setter-based login writes
- Date: 2026-07-20
- Symptom: autologin reported wrong credentials while the game appeared to enter empty account/password fields.
- Root cause: native login wrote TMP_InputField backing text directly instead of using TMP's set_text path and had no readback proof before clicking.
- Rule: for Unity TMP login fields, call the public setter and verify readback lengths before submitting; raw m_Text writes are only a fallback.
- Tags: #login #unity #tmp #automation #native

### Save is not relogin
- Date: 2026-07-18
- Symptom: changing saved device credentials felt like it should trigger a separate relogin state.
- Root cause: the host model added an extra pending relogin concept instead of treating saved credentials as the desired login state.
- Rule: keep save-only credentials and let the login watchdog key off session stage plus the autologin toggle; do not invent a separate relogin mode unless the game contract itself exposes one.
- Tags: #login #gap #state #automation

### Defer main-thread hooks until the world is real
- Date: 2026-07-17
- Symptom: `signal 11 (SIGSEGV), code 2 (SEGV_ACCERR)` on `UnityMain` during pre-world injection; tombstone traced it to `HookedInner()` / `gOriginalInner(self)`.
- Root cause: `Dispatcher::InstallHooks()` and party hooks were armed from `JNI_OnLoad` before the game had a live character/world snapshot, so the startup hook path ran too early.
- Rule: keep pre-world injection hook-free, start the HTTP/control plane first, and only arm dispatcher-style Unity-thread hooks after `/state` proves the game is in-world.
- Tags: #android #il2cpp #hooking #login #crash

### A live game session blocks re-login during manual verification
- Date: 2026-07-24
- Symptom: autologin fails with the in-game dialog "Tài khoản đã đăng nhập ở thiết bị khác" (account already logged in on another device), or `session.login` / `session.select_role` returning `UILoginGame not ready` / `UISelectRole not ready`, after an earlier attempt had already reached role select.
- Root cause: the first login established a server-side session (it got as far as role select); firing `session.login` again while that session was still live triggered the "logged in elsewhere" conflict and wedged the login UI. Overlapping login reconciles self-conflict.
- Rule: during hand-driven verification do ONE clean login — force-stop the game and wait ~100s for the server to release the prior session before retrying; don't loop `LoginWatchdog.reconcile_now` hoping it settles. Screencap the emulator to read the real UI state before assuming a code bug.
- Tags: #login #verification #session #automation

### Dispatcher-backed verbs (ext.auto_pickup, combat, nav) need an in-world character
- Date: 2026-07-24
- Symptom: a freshly injected bridge pings `il2cpp:true, dispatcher:false`; `POST /ext.auto_pickup` returns just `{"verb":"ext.auto_pickup"}` with no config fields; `/state` character is empty; `is_in_game` can still say true at a pre-world screen.
- Root cause: the Unity main-thread dispatcher arms lazily only after `/state` proves a real in-world character (see "Defer main-thread hooks until the world is real"). Off-main-thread, `Dispatcher::ExecuteOnUnityThread` returns an empty json and the verb lambda never runs, so reads/writes silently no-op.
- Rule: to verify any dispatcher-backed verb, first drive the character in-world (login), poll `/state` until a real character appears and `/ping` shows `dispatcher:true`, THEN exercise the verb and read back. A reachable HTTP server alone is not "ready".
- Tags: #il2cpp #dispatcher #verification #gap #automation

### Bound the injector call itself with a timeout, not just the post-inject ping
- Date: 2026-07-25
- Symptom: packaged bring-up could hang indefinitely inside `Controller.run_injector` — the injector process never returned, so `BridgeLifecycle` neither advanced to `loaded` nor surfaced a failure (distinct from the stale-tracer case, where a *timed-out* injector leaves `TracerPid` set).
- Root cause: `run_injector` had no execution deadline; only the post-inject ping (`POST_INJECT_TIMEOUT`) had a timeout. A wedged injector (traced/frozen target, root-elevation stall) blocked the whole reconcile with no bound.
- Rule: pass an explicit `INJECTOR_TIMEOUT` to `run_injector` so a wedged injector is killed and reported instead of hanging; keep the `time.monotonic()` deadline wait loops (`_wait_for_bridge`/`_wait_for_ping`) for readiness. This layers on top of the existing `_ensure_untraced_target` preflight so both the hang and the leftover-tracer failure modes are bounded.
- Tags: #android #injector #timeout #deploy #runtime #gap

### GAP native command payloads must nest data under `result` to survive the host
- Date: 2026-07-27
- Symptom: a new adapter verb returns rich fields (e.g. `ext.map_objects` -> `{ok, objects:[...], count}`) and the raw HTTP response over the wire is correct, but a Behavior reading `cmd.post("ext.map_objects").result` gets `None` — the discovery data vanished.
- Root cause: `TransportClient.post` does `CommandResult.model_validate(response)`, and gap_host's `CommandResult` has no `extra=allow` — it keeps only `ok/detail/result/busy`. Any flat extra field on the adapter payload is dropped at the contract boundary. The old `app/hunt.py` path only preserved them because it used a raw-dict `GapClient`, not `CommandResult`.
- Rule: any Adapter.cpp verb whose output a Behavior consumes must nest that output under `result` (`{"ok":true,"result":{...}}`); flat top-level fields beyond ok/detail/busy are silently discarded once the verb is driven through `CommandSink`.
- Tags: #gap #contract #adapter #transport #commandresult

### A rebuilt bridge .so is NOT re-injected while the old one is still reachable
- Date: 2026-07-27
- Symptom: rebuild `libmodtemplate.so` with new verbs, restart the host, but the live `/capabilities` still lacks the new verbs — the running game keeps answering with the old bridge.
- Root cause: `BridgeLifecycle._maybe_reconcile` returns early if `_bridge_reachable` (old bridge still pings), and `_reconcile_device` returns early if `process_maps_contains(pid, libmodtemplate.so)` (the .so is already mapped). Neither path re-injects a fresh build into a live process.
- Rule: to load a rebuilt bridge, force-stop the game first (`adb -s <dev> shell am force-stop com.novagate.thienanh`) so the pid/bridge disappear; the lifecycle then relaunches and injects the new .so. Confirm with live `/capabilities`, not just that the file on disk changed.
- Tags: #android #injector #deploy #native #verification

### Native build: local.properties SDK path is machine-specific and goes stale
- Date: 2026-07-27
- Symptom: `scripts/build-native-lib.ps1 -SkipSetup` fails with "Missing Android SDK at ...\.toolchain\android\sdk"; `native-lib/local.properties` points at `C:/Users/Admin/AppData/Local/Android/Sdk` (a different user).
- Root cause: `local.properties` is a committed/leftover file with another machine's `sdk.dir`, and no `.toolchain/android/sdk` exists on this box. The real SDK (ndk 29.0.14206865 + cmake 3.22.1 + android-35, matching `app/build.gradle`) lives at `C:/Users/Tung/AppData/Local/Android/Sdk`.
- Rule: build with `-AndroidSdkRoot "C:\Users\Tung\AppData\Local\Android\Sdk"` (the script rewrites + restores local.properties around the build). Don't trust the checked-in `local.properties` sdk.dir on a fresh machine.
- Tags: #android #build #gradle #sdk #windows

