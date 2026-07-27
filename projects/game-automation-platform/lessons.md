<!-- MIRROR of C:\Users\Tung\Projects\game-automation-platform\LESSONS.md
     Source of truth is that file, in the project's own repo.
     Overwritten by scripts/sync-project.py — do not edit here. Synced 2026-07-27. -->

# GAP Lessons

Gotchas and reusable design rules for GAP-powered projects.

### A restarted host leaves the leader owning a stale party
- Date: 2026-07-24
- Symptom: after restarting the fleet-host dashboard, a hunt team never re-formed — status stuck on "forming" with the members frozen and scattered mid-follow across the map (auto-combat off), even though all devices were in-world and control-ready. Toggling hunt off→on (which force-leaves every party, then recreates) instantly fixed it.
- Root cause: on the restart the *members'* game clients dropped out of the in-game party, but the *leader's* client kept owning it — so the party still held the departed members as "ghost" slots. The formation code reused the leader's existing party (only re-adding members whose `team_id != leader's`), but the party still looked full, so the members' re-joins silently failed. Nothing logged an error; the team just never converged.
- Rule: formation must not trust/reuse a party that survived a restart. When a device that should be the leader finds formation broken, have it **`party.leave` its current party and `party.create` a fresh one** before members re-join — since that path only runs when formation is already broken, recreating is safe and clears the ghost slots. Equivalently, a per-device reconcile must let the leader recreate (or kick non-members) when its live roster doesn't match the desired members; an idempotent "already in team → do nothing" reconcile alone will livelock against ghost slots. Whether this bites depends on how long the game keeps offline members in a party. Design detail in WORKFLOW.md, "Party hunt mimic model".
- Tags: #party #team #formation #restart #gap #runtime

### Bundle the emulator's adb, not the build machine's
- Date: 2026-07-24
- Symptom: a freshly rebuilt fleet-host dashboard crashed every ~8–15 min with a native access violation (`0xc0000005`, faulting module "unknown"), and its log always ended right after `Failed to list adb devices: ... adb server version (31) doesn't match this client (41); killing...`. The host machine also dropped off the network (Tailscale) repeatedly, each time shortly after the fleet went active.
- Root cause: the PyInstaller bundle shipped the *build machine's* SDK adb (`platform-tools` v37.0.0, adb server protocol 41). The target host runs an Android emulator (MuMuPlayer) whose own adb is v36.0.0 (protocol 31). There is exactly one adb server per host (127.0.0.1:5037); the two adb versions each kept killing the other's server and restarting their own. That constant server churn destabilized the host process (native crash) and the machine's network stack. A prior build had bundled a matching adb, so it never showed this.
- Rule: a fleet tool must speak the **same adb the target emulator uses** — bundle the emulator's own adb binary (e.g. MuMu `nx_main\adb.exe`), or point the tool at it. Never assume the SDK/`platform-tools` adb is safe on an emulator host; a version-mismatched client triggers an endless kill/restart war. Design the launcher to honor a preset `ADB_PATH` and only bundle its own adb as a fallback. Two gotchas when patching a live host without a rebuild: Windows Task Scheduler does **not** reliably inherit a freshly-set user `ADB_PATH` env var (set it in-process via the launch wrapper, or bake the right adb into the build); and the orphaned mismatched adb *server* can survive `taskkill /F` while the old binary is still present, so the durable fix is to bundle the matching adb, not to fight the server at runtime.
- Tags: #adb #emulator #mumu #deploy #runtime #crash #gap

### Team logic is party formation only — run per-device behavior independently
- Date: 2026-07-24
- Symptom: A 6-emulator party processed members sequentially, not in parallel; laggards rarely auto-fought and looked like they were "waiting" for everyone to reach the leader. All member follow/mimic was driven by one background runner thread ticking every ~2s, which serialized 30–40 blocking HTTP calls per tick across the fleet (readiness ping + `party_info` on every member + per-member mimic each doing 4+ round-trips). At ~440ms RTT one member's state updated only after the previous member's calls returned.
- Root cause: The "team" was modeled as an *execution context* (one loop drives every device) instead of as *shared state* (roster + leader + flags) that independent workers consult. Only the leader hunt got its own thread; every member's mimic/follow ran inline in the shared tick. Nothing actually gated members on each other — the serialization only *looked* like a "wait for everyone to arrive" barrier.
- Rule: Keep team logic to **formation only** — the continuous invariant "these N devices are in one party led by `members[0]`." Everything else (leader hunt, member mimic/follow) is per-device and runs on its own loop, gated only on a cheap local "am I in my leader's party?" check, never on another device. Treat the team as state, not an executor: a supervisor spawns/stops per-device workers on roster/flag changes. Formation is continuous, not one-shot — a member in ANY party other than the leader's is unformed and must `party.leave` before (re)applying, and that leave must be re-checked *inside* the apply/accept retry loop (a slow leave packet otherwise burns every retry still in the wrong party). A single serial runner over N devices does not scale past a couple targets and degrades badly with per-device RTT. Design detail in WORKFLOW.md, "Party hunt mimic model".
- Tags: #party #team #formation #orchestration #concurrency #gap #runtime

### A rooted device is not a root adb shell — elevate before ptrace injection
- Date: 2026-07-22
- Symptom: On a newly-provisioned machine, bridge injection failed on every target with `Couldn't open mem file /proc/<pid>/mem, error=Permission denied` → `KittyInjector: Failed to initialize kittyMgr` → `injector exited 1` (sometimes with `adb: error: failed to read copy response: EOF` on the push), while the identical build injected fine on already-provisioned machines.
- Root cause: ptrace injection (open `/proc/<pid>/mem`, stop threads) requires real uid 0. Running the injector via a bare `adb shell <injector>` runs it as the `shell` user (uid 2000). A "rooted" emulator/device only guarantees `su` exists; `adb shell` stays uid 2000 unless `adbd` itself was restarted as root. Images that run `adbd` as root by default hide the missing elevation until a non-root-adbd image exposes it.
- Rule: The target-plumbing layer must make the shell root before it pushes or injects — never assume adb shell is root. Preflight `adb shell id -u`; if not `0`, restart adbd as root (`adb root`) once per serial (cached), wait for adbd to return and re-arm the dropped forward. Run the injector on a root adbd via plain shell, else fall back to `su -c "…" 2>/dev/null || su 0 sh -c "…"` (Magisk + redroid/BusyBox variants). Elevate *before* the asset push: `adb root` restarts adbd mid-transfer, which is the `failed to read copy response: EOF`. Surface "device not rooted / cannot elevate" as a distinct lifecycle state instead of a cryptic injector exit code. Reference implementations: `thienanh-novagate` `Controller.ensure_root`/`run_injector`, `thanlongmobile-BNM` `AdbHelper.ensure_root` + ADB_COMMAND_POLICY.md, `tgun` `_wrap_root_shell_command`.
- Tags: #android #injector #adb #root #ptrace #runtime #deploy #gap

### Do not hot-inject a second dispatcher build over an already-hooked process
- Date: 2026-07-21
- Symptom: After hot-injecting a fresh `libmodtemplate.so` into a process that already had an injected dispatcher, calling the new bridge led to `Fatal signal 11 (SIGSEGV) ... UnityMain` with a backtrace through the memfd-injected library.
- Root cause: The second injected copy had its own dispatcher globals and tried to hook the same Unity tick already hooked by the previous copy.
- Rule: For dispatcher-bearing native changes, prefer force-stop/relaunch plus fresh injection. Never validate a second injected dispatcher copy over an already-hooked process.
- Tags: #android #injector #dispatcher #runtime #crash

### Disable built-in team follow while host-routing a member
- Date: 2026-07-21
- Symptom: With the leader fighting on a target map, a party member correctly stayed out of auto-fight but host travel failed on a later map hop while built-in follow was enabled; the same `nav.move_to` command succeeded after follow was turned off.
- Root cause: A game's built-in team-follow state can conflict with explicit host navigation, especially after a cross-map hop while the leader is elsewhere.
- Rule: Out-of-range party mimic should preserve final follow behavior, but temporarily disable built-in follow around host-driven travel, verify arrival through `/state`, then restore follow; mimic combat only after the member is same-map and inside the configured range.
- Tags: #party #navigation #gap #runtime #follow

### Native map command success is not party-follow arrival proof
- Date: 2026-07-20
- Symptom: a party member stayed on map 23 with `following=true` while the leader fought on map 88; native map commands returned `ok=true` without an actual map transition.
- Root cause: many game movement calls are fire-and-forget/no-exception paths, and built-in team follow may not cross maps. The reusable contract needs reference-map routing plus state-confirmed arrival.
- Rule: party follow/mimic engines should keep out-of-range members in follow mode with auto-fight off, route with `map_edges` + `nav.move_to`/transfer hops, and verify `/state` map/position before treating travel as complete.
- Tags: #party #navigation #gap #runtime #automation

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
- Rule: before reinjecting, force-stop/relaunch or foreground the Unity activity, verify `TracerPid: 0`, and kill stale injector tracers; do not hot-inject over an already-hooked or already-traced process. Enforce this as an automatic preflight in the target-plumbing reconciler (reap stale injectors, read `TracerPid`, force-stop/relaunch if traced) rather than relying on manual recovery — see the Bring-up invariant in ARCHITECTURE.md.
- Tags: #android #injector #ptrace #hooking #runtime

### Save is not relogin
- Date: 2026-07-18
- Symptom: changing saved credentials looked like it should trigger a separate relogin state.
- Root cause: the host model added a pending relogin concept instead of treating saved credentials as the desired login state.
- Rule: keep save-only credentials and let the login watchdog key off session stage plus the autologin toggle; do not invent a separate relogin mode unless the game contract itself exposes one.
- Tags: #login #gap #state #automation

### A behavior that enables a native toggle must undo it in a stop() hook
- Date: 2026-07-25
- Symptom: `POST /behavior/stop` (or replacing one behavior with another) left combat auto-on in-game — the host loop stopped but the character kept auto-fighting.
- Root cause: the `Behavior` ABC had only `applicable`/`tick`/`status`; `stop_behavior()` just flipped a flag, and `set_behavior`/`start_campaign`/`start_farm` overwrote `self.behavior` without stopping the outgoing one. A behavior that posts a native enable (e.g. `combat.auto_combat` on) had no teardown path, so the toggle leaked past the loop's lifetime.
- Rule: give `Behavior` a default no-op `stop(cmd)` hook; behaviors that enable a native toggle override it to post the disable (capability-gated). Invoke it from the controller on EVERY path that ends or replaces a behavior — `stop_behavior` AND `set_behavior`/`start_campaign`/`start_farm` — not just explicit stop. Capture the outgoing behavior under the controller lock, then call `stop()` OUTSIDE the lock (it network-posts and can block on a blocking native verb). Never assume synchronous teardown.
- Tags: #gap #host #behavior #lifecycle #native-toggle

### Bound the injector call itself with a timeout, not just the post-inject ping
- Date: 2026-07-25
- Symptom: packaged bring-up could hang indefinitely inside `run_injector` — the injector process never returned, so the lifecycle neither advanced nor surfaced a failure (distinct from the stale-tracer case above, where a *timed-out* injector leaves `TracerPid` set).
- Root cause: `run_injector` had no execution deadline; only the post-inject ping had a timeout. A wedged injector (traced/frozen target, root-elevation stall) blocked the whole reconcile with no bound.
- Rule: pass an explicit timeout to `run_injector` (`INJECTOR_TIMEOUT`) so a wedged injector is killed and reported instead of hanging; keep the `time.monotonic()` deadline wait loops (`_wait_for_bridge`/`_wait_for_ping`) for readiness. Combine with the existing untraced-target preflight (reap stale `AndKittyInjector`, check `TracerPid`, force-stop/relaunch if traced) so both the hang and the leftover-tracer failure modes are bounded.
- Tags: #android #injector #timeout #deploy #runtime #gap

### Unity IL2CPP game crash-loops on an x86 emulator = 32-bit ABI via native bridge
- Date: 2026-07-25
- Symptom: the game SIGSEGVs every ~2 min. Tombstones: `signal 11 (SIGSEGV)` on
  thread `UnityMain`, faulting inside `libhoudini.so`-translated code (anon
  `Mem_0x20000000` region); the injected mod (`libnamlun`) absent from ALL tombstones.
- Root cause: the game was installed `armeabi-v7a` (32-bit) and runs through the
  emulator's ARM->x86 native bridge (Houdini / libnb), which is unstable for Unity
  IL2CPP under JIT/GC load. Nothing to do with the mod. A 64-bit Android still
  installs/keeps 32-bit apps, and `primaryCpuAbi` is sticky once installed.
- Rule: run the arm64-v8a build. Install with `adb install --abi arm64-v8a <apk>`
  (uninstall first — `-r` won't re-pin the ABI) and verify with
  `adb shell dumpsys package <pkg> | grep primaryCpuAbi`. Don't trust the emulator's
  default install (LDPlayer/MuMu can pin 32-bit even when arm64 is in the abilist).
  The arm64 mod injects fine via the same native bridge (`AndKittyInjector_x86_64`).
- Tags: #android #emulator #houdini #nativebridge #il2cpp #abi #arm64 #crash
