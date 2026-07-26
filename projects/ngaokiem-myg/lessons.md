<!-- MIRROR of C:\Users\Tung\Projects\ngaokiem-myg\LESSONS.md
     Source of truth is that file, in the project's own repo.
     Overwritten by scripts/sync-project.py — do not edit here. Synced 2026-07-26. -->

# Lessons — ngaokiem-myg

Project-specific gotchas. Grep by error text or tag before debugging. See also the global
`~/.agents/LESSONS.md` and the `memory/` notes.

### jadx 1.4+ needs Java 11; use jadx 1.3.5 on a Java-8 box
- Date: 2026-06-23
- Symptom: `Error: A JNI error has occurred ... java.lang.UnsupportedClassVersionError: jadx/cli/JadxCLI has been compiled by a more recent version of the Java Runtime (class file version 55.0), this version of the Java Runtime only recognizes class file versions up to 52.0`
- Root cause: only JRE 8 (class version 52) is installed here; jadx 1.4.0+ is compiled for Java 11 (class version 55).
- Rule: to decompile `apk/base.apk` on this machine, download **jadx 1.3.5** (last Java-8-compatible release): `jadx -d out --no-res --no-debug-info <apk>`. Don't grab "latest" jadx. (Alternatively install a JDK 17+.)
- Tags: #tooling #java #jadx #re #apk

### Inject the BNM helper ONLY when the game is idle — never during world-load
- Date: 2026-06-29
- Symptom: game SIGSEGVs back to the launcher right after injection: `Fatal signal 11 (SIGSEGV), code 2 (SEGV_ACCERR), fault addr 0x81e73a4 in tid <N> (IL2CPP Threadpo)`, logged concurrently with BNM's `[SetupBNM] il2cpp::vm::Class::Init`.
- Root cause: BNM's one-time il2cpp setup (run on its startup thread) races with the IL2CPP threadpool whenever the threadpool is churning — i.e. during splash / asset-load / server-select world-load. Injecting at those moments crashes the process. It survives only at a calm state (idle SDK login screen, or fully-loaded + idle in-world).
- Rule: cold-start with the session restored but DO NOT inject during load. Drive to world first (taps, no helper), let it fully settle (~15s idle), THEN inject into the running pid. BNM setup runs once, so driving to world after the helper is up does not re-trigger the race. Corollary: a freshly-restored session auto-loads straight into the world, so `login.py --mint --inject` (which injects at +22s splash) reliably crashes — split mint/restore from inject.
- **UPDATE 2026-07-03: FIXED in code** — inject-anytime now works. See "Hook-free BNM init…" and "The dispatcher's Dobby hooks…" below. This operational workaround is no longer required.
- Tags: #inject #bnm #il2cpp #race #ldplayer #crash

### login.py APP_UID must be resolved dynamically, not hardcoded
- Date: 2026-06-29
- Symptom: after `login.py --mint`, the minted session does not auto-restore — the game lands on the myG SDK login screen instead of server-select. `grep` of `shared_prefs/app_sharedprefs.xml` shows the `myg_pref_current_user`/`myg_pref_list_users` keys absent after launch.
- Root cause: `write_session`/`clear_session` chowned the prefs to the hardcoded `APP_UID=10064`, but the app's real uid varies per install/emulator (10060 on LDPlayer emulator-5556). A wrong-owner, mode-660 prefs file is unreadable by the app, so the SDK sees no session and rewrites a fresh (session-less) prefs on launch → login screen.
- Rule: resolve the app uid at runtime from the package data dir (`stat -c %u /data/data/<pkg>`), never hardcode it. Added `resolve_app_uid()` in login.py (fallback 10060). Verify the restored prefs are owned by the live app uid, not a guessed constant.
- Tags: #login #prefs #uid #android #ldplayer

### subprocess capture of adb/binary output crashes on Windows cp1252
- Date: 2026-06-23
- Symptom: `UnicodeDecodeError: 'charmap' codec can't decode byte 0x90 in position N: character maps to <undefined>` raised in a `Thread-N (_readerthread)`, mid-run, when capturing `adb` output.
- Root cause: `subprocess.run(..., text=True)` decodes with the locale default (cp1252) on Windows; adb output (inject logs, `/proc/<pid>/maps`, screencap) contains bytes cp1252 can't decode, and the reader thread dies.
- Rule: when capturing process output that may contain non-UTF-8/non-ASCII bytes, always pass `encoding="utf-8", errors="replace"` (not bare `text=True`). Applied in `login.py:adb()` and `inject()`.
- Tags: #windows #python #subprocess #encoding #adb

### The game has NO reliable one-button quest automation — it's per-step, and even that stalls
- Date: 2026-07-01
- Symptom: recurring question "does the game auto-run the whole main quest with one click?" The answer is no, and it's easy to over-assume the built-in automation is more capable than it is.
- Root cause: the game ships only a **per-step** guided-quest UX (tap the tracker hyperlink → `QuestClickEvent` auto-paths/fights that ONE step). There is no always-on "auto entire mainline" toggle. Even the per-step link is unreliable: it silently no-ops on class-2 training quests, in auto-path dead zones (grid not loaded), and for dynamic/not-yet-loaded NPCs (`NpcListByID.TryGetValue` miss → `ret`); and when it does path correctly it still can't finish steps needing a different trigger — server-pushed quizzes (type 8), story cutscene dialogs (type 0, some wait for input forever), or domain instances (type 14).
- Rule: treat quest automation as a **two-layer** effort, not a game feature. Layer 1 = per-step handlers we built (`taskclick`, `/dialog`, `answer`, `confirm`, `useitem`, `gotomap`, …), each patching one no-op/stall case. Layer 2 = the whole-journey loop `python control.py autoquest run`, only as good as handler coverage. Do NOT claim the game itself does hands-off questing. Current terminal stop is NOT a mechanics gap but the **character-power wall at task 10776** (char at quest-gear ceiling, too weak) — the next unlock is a gear-farm/grind subsystem, not another quest handler. Full detail in `memory/autoquest-ok.md`, `memory/quest-automation-leads.md`, `memory/taskclick-handler.md`, `memory/character-power-wall.md`.
- Tags: #quest #automation #autoquest #scope #gotcha

### Hook-free BNM init lets you inject at ANY game state (fixes the inject-during-churn crash)
- Date: 2026-07-03
- Symptom: injecting `libngaokiem.so` during splash / world-load / a busy scene SIGSEGVs the game — `Fatal signal 11 (SIGSEGV) … tid <N> (IL2CPP Threadpo)` (fatal), or a non-fatal `No handler for signal 11` loop on the BNM startup thread. Reproduces with EVERY build including known-good ones, at the same fault addr.
- Root cause: BNM's default init inline-hooks the HOT `il2cpp::vm::Class::FromIl2CppType` — via `AllowLateInitHook()` AND (under `BNM_CLASSES_MANAGEMENT`) inside `SetupBNM` (which also hooks `GetClassOrElementClass`/`FromName`). Installing a Dobby inline hook on a function the IL2CPP threadpool executes every frame is a patch-running-code race → SIGSEGV. NOT a game/APK change (APK `lastUpdateTime` unchanged; a known-good `.so` crashes identically) — a pure timing race.
- Rule: we inject AFTER il2cpp is fully up, so load BNM with ZERO hooks: `SetMethodFinder(dlsym-finder, handle)` + `TrySetupByUsersFinder()` (→ `Internal::Load`: resolves every export via the finder and fires OnLoaded synchronously, no hooks) instead of `AllowLateInitHook` + `TryLoadByDlfcnHandle` + a kick loop. AND disable `BNM_CLASSES_MANAGEMENT`/`BNM_COROUTINE` (guarded `#ifndef BNM_DISABLE_*` in the shared `GlobalSettings.hpp`; opt out per-project via `target_compile_definitions(BNM PUBLIC BNM_DISABLE_...)`) to drop the SetupBNM hooks — the helper is a read-only il2cpp client that creates no custom classes, so these are unused and class resolution still works (verified: role/quest/autofight all fine). Supersedes the "inject ONLY when idle" workaround for the BNM half. In `native-lib.cpp:BnmStartupMain`.
- Tags: #inject #bnm #il2cpp #dobby #race #crash #fix

### The dispatcher's Dobby hooks must be installed pre-world (eager at BNM-load), not lazily
- Date: 2026-07-03
- Symptom: after the BNM-init fix, inject was clean, but the first in-world action needing the main-thread task queue (`RunOnUnityThreadSync`/`EnqueueTask` — e.g. any `improve` packet action) triggered a non-fatal `No handler for signal 11` loop (~1600/s) in a busy scene.
- Root cause: `InstallDispatcher()` (called lazily by `RunOnUnityThreadSync`) Dobby-hooks hot per-frame game methods (`GSprite::get_IsTruyenCong`/`DoRun`, `GScene::OnFrameEvents`, `MainGame`/`BootCtrl`/…`Update`) to pump the queue. Installing those while the Unity main thread is executing them every frame = the same patch-running-code race. Proof: installing at server-select (methods not executing yet) = clean; installing in a busy town = crash loop.
- Rule: install the dispatcher EAGERLY in `BnmStartupMain` right after BNM loads. Injection normally happens at login/server-select where those in-world tick methods aren't running yet, so Dobby patches them race-free; every later action reuses the installed hooks (no re-patch). Keep the lazy `InstallDispatcher()` as an idempotent fallback.
- Tags: #inject #dobby #dispatcher #race #crash #fix

### Do NOT drive or read Unity UI frames from native — the object is a fake-null and SIGSEGVs
- Date: 2026-07-03
- Symptom: trying to make stat-point allocation apply headlessly (`addpoints`) crashed the game 3× — `Fatal signal 11 (SIGSEGV), code 128 (SI_KERNEL), fault addr 0x0 in tid <N> (UnityMain)`. Crashed whether I called `PlayZone.ShowUIRoleRemainPoint`, clicked `UIRoleRemainPoint.ButtonRecomend/Accept_Clicked`, or even just READ the frame's getters (`get_RemainPoint`, `get_RecommendStr`).
- Root cause: `PlayZone.get_UIRoleRemainPoint()` returns a Unity "fake-null" (destroyed / half-async-built MonoBehaviour) — `BNM::IsAllocated` passes but the internals are gone, so ANY method call on it (getter or `*_Clicked` handler) derefs null. Button handlers additionally expect a real EventSystem/`PointerEventData` context that's null when invoked from native.
- Rule: never drive an interactive UI frame (Show/click/read a live `UIxxx` MonoBehaviour) from the native helper — it is not a stable callable object. Send the underlying server packet instead. When the game HARD-gates an action behind a UI-only confirm (attribute allocation: `UIRoleRemainPoint.ButtonAccept` → `TCPGame.SpriteRecommendPoint(str,sta,dex,int)`), and the bare 0-arg packet doesn't apply, you must reverse-engineer the exact wire payload — you cannot shortcut via the panel. `addpoints` is therefore a safe no-op packet; reliable headless stat allocation is unsolved. Skill leveling (`SendDistributeSkillPoints(Dictionary<int,int>,int)`) is similarly un-done pending payload RE.
- Tags: #bnm #unity #ui #fakenull #crash #addpoints #scope

### Claim rewards by their decoded packet, not by driving the Welfare UI — and brute-force server-authoritative claims
- Date: 2026-07-04
- Symptom: level-up ("Thưởng cấp") award claiming was stuck for a whole session — the award IDs live only in `UIWelfare_LevelUp.Data`, which is null until that tab is active; opening it from native (`PlayZone.OpenUIWelfare`) SIGSEGV'd (fake-null UI, see above) and blind tap-navigation couldn't switch tabs.
- Root cause: we coupled claiming to the game UI, but the UI can't be driven headlessly. The actual claim never needed the UI: every reward is a plain server-authoritative TCP packet. Decoded from `HotUpdate.dll` IL — `TCPGame.SendSpriteGetLevelUpAward(int nRoleID, int nIndex)` → opcode **635**, body `"{roleID}:{nIndex}"`; the query is `QueryWelfareLevelUpInfo(int)` → opcode **634**. Crucially `nIndex` is a small LIST INDEX (the caller passes `LevelUpItem.get_ID`, a milestone position), not a sparse config ID.
- Rule: to claim rewards headlessly, send the decoded packet (a pure `SendData`, touches no UI object → cannot fake-null-crash), never open the panel. When claims are server-authoritative (invalid / unearned / already-claimed silently no-op) and the selector is a small bounded index, **brute-force the range** (`claimlevelup` sweeps nIndex 0..120 via `?map=<start>&?npc=<end>`) instead of enumerating from the UI — it's idempotent, repeat-safe (verified: bag stable across 2 runs, no flood-kick, no crash). Resolve `roleID` from `Global.Data.RoleData.get_RoleID` (int). To DECODE a packet: dnfile-disassemble the `Send*`/`Query*` method — the trailing `ldc.i4 <op>; MakeTCPOutPacket` gives the opcode and the `string.Format` template gives the body. Caveat: a brute sweep can't be *observed* to grant on an already-claimed char (release build logs no server responses; config unreadable without the UI) — confirm grants on a fresh/low char.
- Tags: #bnm #packet #reward #levelup #re #dnfile #brute-force #server-authoritative

### Prove an inject crash is environmental (not your diff) by injecting a known-good build
- Date: 2026-07-03
- Symptom: after a code change, injection crashes the game; unclear whether the change caused it.
- Root cause / method: A/B against a KNOWN-GOOD prior `.so` (e.g. `native-lib/.build-orig/libngaokiem.so`) — push and inject it the same way. If it crashes identically (same `fault addr`), the cause is environmental/timing, not your diff. Also check `adb shell dumpsys package <pkg> | grep -E 'versionName|lastUpdateTime'` — `firstInstallTime == lastUpdateTime` ⇒ the APK/`libil2cpp.so` didn't change, ruling out a game update.
- Rule: before deep-diving a post-change crash, A/B against a known-good binary and check APK update time. A same-fault-addr crash across two different binaries = shared/infra cause. (Saved hours here — the "regression" was actually a pre-existing timing race.) *Generalizes across projects — promote to global if it recurs.*
- Tags: #debug #inject #crash #method #bisect

### Build libngaokiem.so on this machine: JDK17 + NDK pin + EXTERN_ROOT + direct-cmake fallback
- Date: 2026-07-03
- Symptom: `./gradlew :app:copyNativeLib` fails variously — invalid `org.gradle.java.home`; `ndk;27.0.12077973` license not accepted; `platforms;android-35` / `build-tools;35.0.0` not installed.
- Root cause: this machine has a BARE Android SDK (NDK 29 only — no platform/build-tools/sdkmanager), and the tracked `gradle.properties` pins a JDK path that doesn't exist here.
- Rule: JDK17 = `C:/Users/Tung/Projects/thanlongmobile-BNM/.toolchain/jdk-17`; SDK = `C:/Users/Tung/AppData/Local/Android/Sdk` (fix `local.properties` `sdk.dir`, it's gitignored). BNM/Dobby `EXTERN_ROOT=C:/Users/Tung/Projects/namlun-tpl-gamebot/lib/extern`. Pin `ndkVersion "29.0.14206865"` in `app/build.gradle` (AGP 8.13 defaults to an uninstalled NDK 27). To build ONLY the `.so` (no APK/SDK-platform needed) skip gradle and run cmake+ninja directly against the existing config: `<Sdk>/cmake/3.22.1/bin/cmake.exe --build native-lib/.build-direct --target ngaokiem` → `native-lib/.build-direct/libngaokiem.so`. Recompiles only changed sources.
- Tags: #build #ndk #jdk #gradle #cmake #windows
