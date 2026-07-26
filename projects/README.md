# Project registry

One folder per project the chief of staff manages. This is the chief's **memory of
each project** — what it is, where it's going, its live status, its lessons, and the
owner's past decisions — so the chief can orchestrate without re-learning a project
every time.

## Each `projects/<name>/` holds

| File | Owner | Lifecycle |
|---|---|---|
| `overview.md`  | human | created once, **never overwritten** — about + vision + current focus |
| `decisions.md` | human | created once, **never overwritten** — the owner's past calls and *why* |
| `lessons.md`   | mirror | **overwritten every sync** — a copy of the project's own `LESSONS.md` |
| `status.md`    | auto  | **overwritten every sync** — live git branch, working tree, worktrees, open PRs, and active herdr agents |

`lessons.md` and `status.md` are generated — the source of truth for lessons is the
project's own repo. Edit only `overview.md` and `decisions.md` here.

## Onboard or refresh a project

```bash
python scripts/sync-project.py <repo-path-or-name>   # e.g. namlun-tpl-gamebot
python scripts/sync-project.py --lessons             # every ~/Projects repo that has a LESSONS.md
python scripts/sync-project.py --all                 # every git repo under ~/Projects
```

Re-run any time to refresh `lessons.md` + `status.md`. Human-owned files are only
created when missing, so your edits survive every sync.

## Currently seeded

The actively-developed set — every `~/Projects` repo that carries a `LESSONS.md`:
`game-automation-platform`, `namlun-tpl-gamebot`, `thienanh-novagate`, `ngaokiem-myg`,
`tanglongbatbai`, `vlcm`. Onboard any other project on demand with the command above.
(The `chief-of-staff` repo itself and the shared `agentic-workflow-template` infra are
intentionally excluded.)

See [`_template/`](_template/) for the shape of a fresh entry.
