# vlcm — decisions

> Human-owned decision log: the calls the owner has made and *why*, so the chief
> and its staff don't relitigate settled ground. Newest on top. Dates absolute.

> ⚠ Entries below were **drafted from merged-PR/commit evidence on 2026-07-26**. The
> *Decision* is factual; the *Why* is inferred — confirm or correct it.

## 2026-07 — Retire agtx; orchestrate via herdr (evidence: PR #18)
- Status: accepted (confirmed by owner 2026-07-26)
- Context: the repo's AGENTS.md described an agtx board/worktree workflow.
- Decision: retire agtx; use herdr as the sole orchestration control plane.
- Why: agtx is outdated; herdr is the standard across all projects.
- Consequences: agtx sections removed; follow-up to migrate `.agtx/runtime-target.json` path.

## 2026-06 — Drive the game's own AS3 via BotBridge; never hand-craft packets (evidence: core principle in AGENTS.md, #14/#15)
- Status: accepted (inferred — confirm)
- Context: re-implementing the wire protocol by hand is error-prone and drifts from the client.
- Decision: call the client's own ActionScript in-process (BotBridge); capture is confirmation only.
- Why: reuse the client's exact serialization, framing, and encryption — always correct.
- Consequences: features require reversing the AS3 module + a BotBridge command + Python wrapper.

## 2026-06 — Consolidate automation on the ws2_32 DLL hook (evidence: #11)
- Status: accepted (inferred — confirm)
- Context: multiple interception approaches (incl. file-redirect) were in play.
- Decision: standardize on the `native-lib` ws2_32 hook + local HTTP API.
- Why: one stable interception point; removed the obsolete swf_redirect (#13).
- Consequences: in-memory auto-login via AVM2 ABC-parse hooks builds on it (#12).

<!-- Add new decisions above this line, newest on top. Template:
## YYYY-MM-DD — <decision title>
- Status: accepted
- Context: … / Decision: … / Why: … / Consequences: …
-->

