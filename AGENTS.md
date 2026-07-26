# chief-of-staff — Project Instructions

Project-specific guidance for this repo. General, cross-project engineering
guidelines are inherited separately via the global agent instructions — do **not**
duplicate them here. This file holds only what is true for *this* project.

## What this project is

A **planning & docs workspace** for chief-of-staff. No application code yet — the
repo exists to capture the thinking first: goals, specs, decisions, and notes.
Code and its own layout arrive later, once the design is settled.

> TODO(owner): replace this paragraph with a one-line mission statement and the
> problem chief-of-staff solves, once decided.

## How to work in this repo

- **Planning is the deliverable.** Turn ideas into settled designs before proposing
  code. Prefer the `brainstorming` → `writing-plans` flow (see `.claude/skills/`).
- **One document, one purpose.** Keep each doc atomic and cross-link rather than
  duplicating. Newest decisions win; supersede old ones explicitly.
- **`LESSONS.md`** at the repo root captures gotchas worth never hitting twice —
  read it before debugging, append after resolving a non-obvious problem.

## Layout

```
docs/
  vision.md      — mission, goals, non-goals (the "why")
  specs/         — settled feature/design specs (the "what")
  decisions/     — dated decision records (the "why we chose X")
  notes/         — scratch, research, open questions
LESSONS.md       — shared gotchas (read before debugging)
```

## Conventions

- **Decision records:** one file per decision in `docs/decisions/`, named
  `NNNN-short-title.md`, dated, stating context → decision → consequences.
- **Dates are absolute** (`2026-07-26`), never relative.
