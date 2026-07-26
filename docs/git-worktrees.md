# Conflict-free git: worktrees, branches, and merge decisions

Many staff run in parallel, often on the **same project**, across many `herdr` sessions.
Conflicts are therefore *expected* — the chief's job is to make them rare by design and
resolve them deliberately. This is the integration discipline.

## The invariants

1. **One task → one worktree → one branch → one staff.** Never two staff on one branch.
2. **Every worktree is disposable.** Create it to do the task, remove it once merged or
   abandoned. Nothing important lives only in a worktree.
3. **The source checkout is sacred.** Staff work in *linked* worktrees (herdr creates
   them off in a temp/scratch path); the owner's primary checkout of the repo is never
   where a staff agent runs.

## Preventing conflicts (before they happen)

- **Partition at plan time.** When fanning out parallel staff on one project, split the
  work so no two branches touch the same files/modules. This single choice prevents most
  conflicts.
- **Pick a clear base per branch.** Base each new branch on the current **integration
  branch** (usually the project's active `feat/*` branch or `main` — check
  `projects/<name>/status.md`). Record the base you chose.
- **Sequence unavoidable overlap.** If two tasks must touch the same code, do not run
  them in parallel — run one, merge it, rebase the second on the result, then run it.

```bash
herdr worktree create --cwd C:/Users/Tung/Projects/<proj> \
  --branch feat/<task> --base <integration-branch> --label "<task>" --json
```

## Integrating (when a staff opens a PR)

The chief owns the merge queue. Process PRs **one at a time** per project:

1. **Verify the PR in isolation.** Is it green? Does it meet the done-condition? Live-check
   the behavior, not just tests (global §3). If not, send it back to its staff.
2. **Check mergeability.** `gh pr view <n> --json mergeable,mergeStateStatus` (or read
   `status.md`, which records `mergeable` per open PR).
3. **Decide order when several are ready.** Merge in this priority:
   - blocks-the-most-others first (unblock the critical path),
   - then smallest / most-isolated (cheap, low-risk, shrinks the queue),
   - then largest / riskiest last (so it rebases onto everything else, not vice-versa).
4. **Merge one.** Prefer a clean merge/rebase. `gh pr merge <n> --squash --delete-branch`
   (choose squash/merge/rebase per the project's convention in `overview.md`).
5. **Refresh every in-flight branch.** After each merge, the base moved. For each still-open
   staff branch that could overlap: have its staff `git fetch && git rebase <integration>`
   (or the chief does it in the worktree), then **re-verify** — a clean merge can still
   break behavior.
6. **Resolve a real conflict deliberately.** If two ready PRs touch the same lines: merge
   the higher-priority / more-complete one first, then rebase the other onto the result and
   let its staff (or the chief) resolve, then re-verify. Never blind-merge both and hope.

## Which one wins, checkout where, build from where

- **Which PR wins on overlap:** the one that is verified + mergeable + higher-priority. The
  loser is *rebased*, not discarded — its work is re-applied on top and re-verified.
- **Check out where to verify:** always the **integration branch after the merge**, in a
  clean checkout — never inside a single staff's worktree (that worktree only knows its own
  branch).
- **Build from where:** from that merged integration branch. The deliverable is built and
  live-verified from the *combined* result before anything is called done (global §8). A
  per-branch green PR does not prove the *merged* set is green.

## Teardown

```bash
gh pr merge <n> --squash --delete-branch      # remote branch gone
herdr worktree remove --workspace <id>        # local worktree gone
git -C <repo> worktree prune                   # tidy stale entries
herdr pane close <pane_id>                      # close the finished agent
```

## Quick reference

```bash
herdr worktree list --cwd <repo> --json                       # what worktrees exist
git -C <repo> worktree list                                    # same, raw git
gh pr list --state open --json number,title,headRefName,mergeable   # the merge queue
gh pr view <n> --json mergeable,mergeStateStatus,files          # is #n safe to merge
python scripts/sync-project.py <proj>                           # refresh status.md
```
