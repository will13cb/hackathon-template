---
name: sync
description: Merge feature-branch worktrees into main, run tests, then bring main back into every worktree. Use when the user says /sync or asks to integrate parallel work.
argument-hint: "[branch ...]  (default: every feat/* branch)"
disable-model-invocation: true
---

# Sync worktrees

Branches to merge: `$ARGUMENTS` (default: every local `feat/*` branch that is ahead of `main`).

1. **Survey.** Run `git worktree list` and, for each branch, `git log --oneline main..<branch>`. Show a short table (branch, path, commits ahead, dirty?). If a worktree has uncommitted changes, **stop and ask**. Never commit someone else's in-progress work without asking.
2. **Merge into main**, from the main worktree (the path whose branch is `main`), one branch at a time:
   - `git -C <main-path> merge --no-ff <branch> -m "sync: merge <branch>"`
   - On conflict: show the conflicting files and hunks. Resolve them only if the right answer is obvious (e.g. both sides added different entries to a list). Otherwise abort with `git merge --abort` and ask. Respect the file-ownership rules in CLAUDE.md when you decide.
3. **Test main:** `make -C <main-path> test`. If it fails, fix it on main (small fix) or revert the last merge with `git revert -m 1 HEAD` and report which branch broke it.
4. **Fan out:** for every feat worktree that is clean, run `git -C <path> merge main --ff-only || git -C <path> merge main -m "sync: main into <branch>"`.
5. **Report:** what merged, test result, and any worktrees skipped (and why). Remind the user to restart the dev server in worktrees whose dependencies changed (e.g. `requirements.txt`).

Never use `push --force`, `reset --hard`, or `clean -f`. The guard hook blocks them anyway.
