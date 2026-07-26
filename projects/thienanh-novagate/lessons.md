<!-- MIRROR of C:\Users\Tung\Projects\thienanh-novagate\LESSONS.md
     Source of truth is that file, in the project's own repo.
     Overwritten by scripts/sync-project.py — do not edit here. Synced 2026-07-26. -->

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

