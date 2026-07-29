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

### codex shares a code-mode-host daemon — never force-kill codex process trees on a shared box
- Date: 2026-07-29
- Symptom: after a codex staff finished, `herdr pane close` left orphaned codex process
  trees (`codex.cmd`→`cmd`→`node`→`codex.exe`→`codex-code-mode-host.exe`) alive, holding the
  worktree dir busy (`rm: Device or resource busy`, `worktree_remove_failed: Permission denied`).
  I force-killed MY orphans by PID with `taskkill /PID <mine> /T /F`. Immediately after, the
  fleet's codex count dropped to 0 and ZERO codex processes survived — a peer chief's two live
  codex agents (`party-convergence`, `w4:p12`) were killed as collateral.
- Root cause: codex on this box runs a SHARED `codex-code-mode-host.exe` daemon (and interlinked
  node trees) across all codex agents. `taskkill /T` (kill process tree) cascaded through that
  shared daemon, so killing one agent's tree took down every codex agent on the box. Also:
  `herdr pane close` does NOT terminate the codex process tree — it detaches the pane and leaves
  the processes orphaned.
- Rule: NEVER `taskkill /T` (or otherwise force-kill) codex process trees on a shared box —
  it's as broad as an IMAGENAME kill (see the by-PID lesson below). Tear codex down via herdr's
  own teardown path only. If pane-close leaves orphaned codex processes holding a worktree busy,
  LEAVE the worktree dir (git already untracks it after `worktree prune`; it's harmless disk
  clutter) and prune later once handles release — do NOT escalate to force-kill. If a codex proc
  genuinely must die, kill only the exact leaf PID without `/T`, never the tree, and never the
  shared `code-mode-host`. When it happens anyway, alert the peer chief immediately so it can
  respawn (as I did — the peer recovered).
- Tags: #codex #herdr #shared-box #collateral #taskkill #teardown #fleet #worktree

### Spawn the codex lane via `codex.cmd`, not bare `codex` — herdr CreateProcessW fails on the npm shim
- Date: 2026-07-28
- Symptom: `herdr agent start <name> --cwd <path> -- codex` →
  `agent_start_failed: CreateProcessW "...\npm\codex" ... "%1 is not a valid Win32 application. (os error 193)"`.
  The codex lane silently fell back to Claude — every running staff was `claude`,
  including a namlun worktree that policy said should be codex. Yet `codex --version` and
  `codex exec "..."` (a live PONG through CLIProxyAPI on :8317) worked from Git Bash, so
  codex, the proxy, and the upstream all looked healthy.
- Root cause: herdr launches with a raw `CreateProcessW`. Bare `codex` on PATH resolves to
  npm's extensionless Unix shell shim (`...\npm\codex`, a `#!/bin/sh` file, not a PE image).
  Git Bash runs that shim fine (so the CLI "works"); `CreateProcessW` can only launch real
  Win32 images and rejects a PE-less file with os error 193.
- Rule: spawn the codex lane as `codex.cmd` (`... -- codex.cmd`) — npm's real Windows
  launcher, recreated on every codex update, so it survives upgrades. Never bare `codex`.
  When a lane "isn't available" but its CLI works from Git Bash, reproduce the *actual*
  spawn path (`herdr agent start ... --`), not just the CLI — the break is in the launcher,
  not the tool. docs/herdr.md + docs/agents.md now document this.
- Tags: #windows #herdr #codex #npm #spawn #createprocess

### Staff must kill processes by PID, never by IMAGENAME — broad taskkill hits peers
- Date: 2026-07-27
- Symptom: a namlun staff cleaning up its own idle verify ran
  `taskkill //FI "IMAGENAME eq python.exe"` and killed unrelated `python.exe` across the box —
  including a co-located peer project's (thienanh) venv python. Cross-project collateral; the
  kill can't be undone.
- Root cause: on a shared runtime box many agents/projects run `python.exe`/`node.exe`
  simultaneously. An image-name filter matches ALL of them, not just the staff's own process.
- Rule: kill ONLY by specific PID (track the pid you spawned). Never `taskkill`/`Stop-Process`
  by IMAGENAME/name on a shared box. When briefing staff that may spawn+kill background procs,
  say this explicitly. (Here it was harmless — the victim was an orphan from an already-merged,
  torn-down task — but that was luck, not design.)
- Tags: #windows #taskkill #process #shared-box #collateral #herdr #fleet

### Windows Python: subprocess text=True decodes as cp1252 and crashes on git/gh output
- Date: 2026-07-26
- Symptom: `UnicodeDecodeError: 'charmap' codec can't decode byte 0x90 in position ...`
  raised in a reader thread when capturing `git log` / `gh` output via
  `subprocess.run(..., text=True)` (seen while building projects/*/status.md).
- Root cause: with `text=True` and no explicit `encoding`, Python decodes child output
  with the locale codec — cp1252 on this machine — but git/gh emit UTF-8, so any
  non-Latin-1 byte (accented commit text, box-drawing, emoji) blows up.
- Rule: when capturing text from subprocess on Windows, always pass
  `encoding="utf-8", errors="replace"`. Never rely on the default locale codec.
- Tags: #windows #python #subprocess #encoding
