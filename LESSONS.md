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
