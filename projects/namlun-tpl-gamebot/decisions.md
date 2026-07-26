# namlun-tpl-gamebot — decisions

> Human-owned decision log: the calls the owner has made and *why*, so the chief
> and its staff don't relitigate settled ground. Newest on top. Dates absolute.

> ⚠ Entries below were **drafted from merged-PR/commit evidence on 2026-07-26**. The
> *Decision* is factual; the *Why* is inferred — confirm or correct it.

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

