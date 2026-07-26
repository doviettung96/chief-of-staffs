# ngaokiem-myg — decisions

> Human-owned decision log: the calls the owner has made and *why*, so the chief
> and its staff don't relitigate settled ground. Newest on top. Dates absolute.

> ⚠ Entries below were **drafted from merged-PR/commit evidence on 2026-07-26**. The
> *Decision* is factual; the *Why* is inferred — confirm or correct it.

## 2026-07 — Headless login: mint session from credentials + RE-driven server hop (evidence: feat/headless-login-mint)
- Status: accepted (inferred — confirm)
- Context: UI login requires a rendered client and is fragile to automate.
- Decision: mint the session directly from credentials and hop servers via the reversed flow.
- Why: enables fully headless operation; no rendered client needed.
- Consequences: login is code, not UI — must track protocol/auth changes.

## 2026-07 — Native /dialog driver is the keystone for explicit quest dispatch (evidence: #5)
- Status: accepted (inferred — confirm)
- Context: quests needed deterministic dispatch rather than UI tapping.
- Decision: add a native `/dialog` driver endpoint and drive quests through it.
- Why: explicit, reproducible quest progression; avoids brittle UI paths.
- Consequences: quest handlers build on the native driver (Collect/Pos, #11).

## 2026-07 — Per-TargetType dispatcher framework in control.py (evidence: #8)
- Status: accepted (inferred — confirm)
- Context: different target types needed different handling in one host.
- Decision: a per-TargetType dispatcher framework in `control.py`.
- Why: extensible dispatch without special-casing each flow.
- Consequences: new target types plug into the framework.

<!-- Add new decisions above this line, newest on top. Template:
## YYYY-MM-DD — <decision title>
- Status: accepted
- Context: … / Decision: … / Why: … / Consequences: …
-->

