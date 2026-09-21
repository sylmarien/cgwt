# Git signals for judging that a worktree is safe to delete

Research for issue #5. Every command was run against throwaway repositories with git 2.43.0, unless a section says otherwise. Sources are listed at the end.

## Summary

No single git command answers the question. cgwt needs a set of checks, and each check has blind spots.

| Signal | Command | Reliability |
| --- | --- | --- |
| Uncommitted and untracked files | `git status --porcelain=v2 --untracked-files=all` | Reliable when the flag is explicit. Misses ignored files. |
| Ignored files | add `--ignored` to the status command | Reliable. Reports build output as well as real work. |
| Stashes | `git stash list` | Stashes are shared by all worktrees. Deleting a worktree never deletes a stash. |
| Unpushed commits | `git rev-list --count <branch> --not --remotes` | Exact for the last fetch. Reports a false alarm after a squash merge or a rebase merge. |
| True merge | `git merge-base --is-ancestor <branch> <default>` | Exact. |
| Rebase merge | `git cherry <default> <branch>` | Reliable unless the rebase changed a diff. |
| Squash merge | `git merge-tree --write-tree <default> <branch>` compared to `<default>^{tree}` | Heuristic. Good in practice. |
| Default branch | `git symbolic-ref --short refs/remotes/origin/HEAD` | A cache. It can be absent or stale. |
| Deleted upstream | `git for-each-ref --format='%(upstream:track)'` prints `[gone]` | Only after `git fetch --prune`. It does not prove a merge. |
| Locked worktree | `locked` line in `git worktree list --porcelain` | Exact. |
| Detached commits | `git rev-list --count HEAD --not --branches --tags --remotes` | Exact. |

The check that git itself runs in `git worktree remove` is weaker than this table. cgwt cannot rely on it alone. See the next section.

## What `git worktree remove` checks on its own

`git worktree remove` runs `git status --porcelain --ignore-submodules=none` in the worktree. It refuses when that command prints anything. It also refuses a locked worktree unless `--force` is given twice. It refuses a worktree that contains submodules unless `--force` is given.

It checks nothing else. It ignores unpushed commits and merge state. Two verified gaps:

- A worktree that held only an ignored file was deleted without a warning.
- With `status.showUntrackedFiles=no` in the configuration, a worktree that held an untracked file was deleted without a warning. The internal status call does not pass `--untracked-files`, so the configuration applies to it.

cgwt must therefore run its own status command with explicit flags before it calls `git worktree remove`.

## Uncommitted and untracked files

Command, run inside the worktree:

```
git status --porcelain=v2 --untracked-files=all -z
```

Output: one record per path. `1` and `2` records are changed tracked files, staged or unstaged. `u` records are unmerged paths. `?` records are untracked files. Empty output means a clean worktree. Adding `--branch` prints `# branch.*` header lines, which a parser must skip.

False negatives:

- Ignored files are absent. Add `--ignored` to get `!` records. Ignored files often hold real work, such as `.env` files.
- Without `--untracked-files`, the `status.showUntrackedFiles` configuration can hide every untracked file. Always pass the flag.
- Paths marked with `git update-index --assume-unchanged` or `--skip-worktree` do not show modifications. Not verified here. The git-update-index manual documents the behaviour.
- After `git stash push`, the status is clean. See the stash section.

False positives:

- With `--ignored`, build output and caches appear next to real work. Git cannot tell them apart.

An operation in progress (merge, rebase, cherry-pick, bisect) does not appear in porcelain output. Conflicted paths do appear, as `u` records. cgwt can test for the state files with `git rev-parse --git-path rebase-merge`, `rebase-apply`, `MERGE_HEAD`, `CHERRY_PICK_HEAD`, and `BISECT_LOG`. Not verified here.

## Stashes

Command:

```
git stash list --format='%H %gs'
```

Output: one line per stash entry. The subject has the form `On <branch>: <message>` or `WIP on <branch>: ...`.

`refs/stash` is shared by all worktrees of a repository. The git-worktree manual states that all refs are shared except `refs/bisect`, `refs/worktree`, and `refs/rewritten`. Verified: a stash pushed in one worktree appeared in `git stash list` of another worktree, and `git rev-parse --git-path refs/stash` resolved to the main `.git` directory.

Consequences:

- Deleting a worktree does not delete a stash. A stash is not lost work.
- A stash entry does not record its worktree. It records only the branch name in its subject. cgwt can at most report "N stashes mention this branch". This gives false positives when the branch was checked out elsewhere and false negatives when the stash was made on another branch or on a detached HEAD.

## Unpushed commits

Two commands answer two different questions.

Against the configured upstream:

```
git status --porcelain=v2 --branch
git for-each-ref --format='%(upstream:short)|%(upstream:track)' refs/heads/<branch>
```

Output: status prints `# branch.upstream origin/x` and `# branch.ab +A -B`. `A` is the number of commits that the upstream lacks. `for-each-ref` prints `[ahead A, behind B]`, an empty string when in sync, or `[gone]`.

- A branch without an upstream prints no `branch.upstream` line and an empty `upstream` field. Absence of "ahead" is not proof that the commits are pushed.
- When the upstream is gone, status still prints `branch.upstream` and omits `branch.ab`.

Against every remote-tracking ref:

```
git rev-list --count <branch> --not --remotes
```

Output: the number of commits on the branch that no `refs/remotes/*` ref contains. `0` means every commit exists on some remote, as of the last fetch. This works without an upstream.

False negatives for both: none with respect to local knowledge. Both commands read remote-tracking refs, which are a snapshot from the last fetch. A remote branch that someone force-pushed or deleted after that fetch still counts as holding the commits.

False positives:

- After a squash merge or a rebase merge, followed by deletion of the remote branch and `git fetch --prune`, the original commits exist on no remote. Verified: the count went from `1` to `3` on a squash-merged branch after the prune. The merge checks below must run before this signal is read as "work would be lost".
- A branch with no commits of its own reports `0` even though it was never pushed. This is correct, because it holds no work.

## Branch merged into the default branch

GitHub offers three merge methods. Each needs a different check. Run the checks in this order and stop at the first that reports "merged". Compare against `origin/<default>` after a fetch, not against the local default branch, which may be behind.

### True merge (merge commit or fast-forward)

```
git merge-base --is-ancestor <branch> <default>
```

Exit code `0` means the branch tip is reachable from the default branch. Exit code `1` means it is not. `git branch --merged <default>` lists the same set.

This check is exact. GitHub's "Create a merge commit" uses `--no-ff`, so the original commits become ancestors of the default branch.

False positive, harmless: a branch with no commits of its own is an ancestor of the default branch. Verified with `git branch --merged`.

### Rebase merge

```
git cherry <default> <branch>
```

Output: one line per commit in `<default>..<branch>`. `-` means the default branch holds a commit with the same patch id. `+` means it does not. The branch is merged when no line starts with `+`. Verified with cherry-picked commits: both lines printed `-`.

GitHub's "Rebase and merge" always creates new commit SHAs and rewrites the committer, so the ancestry check fails and this check is required. The patch id depends only on the diff, so new SHAs and a new committer do not affect it.

False negatives:

- A commit whose diff changed during the rebase, for example through conflict resolution, prints `+`.
- GitHub drops commits that were empty. `git cherry` prints `+` for an empty commit that has no counterpart.

Blind spot: `git cherry` skips merge commits on the branch (`revs.max_parents = 1` in `cmd_cherry`). Work that exists only in a merge commit, such as a conflict resolution, is not examined.

This check does not detect a squash merge of two or more commits. Verified: both commits printed `+`.

### Squash merge

Git records no link between a squash commit and its source branch. Two heuristics exist.

Heuristic A, merge simulation (git 2.38 or later):

```
git merge-tree --write-tree <default> <branch>
git rev-parse '<default>^{tree}'
```

`merge-tree` prints the tree id that a merge of the branch into the default branch would produce. It exits with `1` on conflicts. When the tree id equals the tree id of the default branch, a merge of the branch would change nothing. The default branch already holds all of the branch's content. Verified on a squash-merged branch: both commands printed the same tree id.

- False negative: the default branch later changed the same lines. The merge then conflicts or produces a different tree.
- False positive: a branch whose commits cancel each other, such as a commit and its revert. The content is not lost. The history is.
- The command writes tree objects into the object database. It touches no ref, index, or working tree.
- This heuristic also covers true merges and rebase merges.

Heuristic B, synthetic squash commit:

```
git merge-base <default> <branch>
git commit-tree '<branch>^{tree}' -p <merge-base> -m probe
git cherry <default> <probe-commit>
```

The probe commit holds the whole branch diff as one commit. `git cherry` prints `-` when the default branch holds a commit with the same patch id. Verified: it printed `-`.

- False negative: the squash diff differs from the branch diff. This happens when the branch was behind and touched by later changes, when the branch merged the default branch in between, or when the pull request received more commits after the local branch was last updated.
- The command writes one unreachable commit object. `git gc` removes it later.

Heuristic A tolerates more cases than heuristic B and needs fewer commands.

A commit made locally after the pull request was merged makes both heuristics report "not merged", provided the commit changes content. This is the desired result.

Outside git: `gh pr list --state merged --head <branch>` asks GitHub directly. It needs the `gh` CLI, network access, and a GitHub remote. It matches by branch name, so a reused branch name gives a false positive. Not verified here.

## The default branch

No local git setting names the default branch of a repository. `init.defaultBranch` names only the first branch of a new repository. The default branch is a property of the remote, which is its `HEAD`.

Cached value, no network:

```
git symbolic-ref --short refs/remotes/origin/HEAD
```

Output: `origin/main` or similar. `git clone` sets this ref.

- Absent: the command fails with `ref refs/remotes/origin/HEAD is not a symbolic ref`. Verified for a clone of an empty repository. It is also absent for a repository made with `git init` plus `git remote add`, because only `git clone` and `git remote set-head` write it in git 2.43.0. This case was not run here.
- Stale: the ref does not follow a later change of the default branch on the remote.

Authoritative value, needs network:

```
git ls-remote --symref origin HEAD
```

Output: `ref: refs/heads/trunk<TAB>HEAD`, then the object id line. Verified. The output is empty when the remote `HEAD` points to a branch that does not exist. Verified with a bare repository whose `HEAD` named a missing branch.

`git remote set-head origin --auto` runs the same query and writes `refs/remotes/origin/HEAD`. Verified.

Other limits:

- The remote is not always named `origin`. A repository can have several remotes or none.
- A repository without a remote has no default branch that git can detect. Only a configuration value or a guess among `main` and `master` remains.

## A deleted upstream branch

```
git fetch --prune <remote>
git for-each-ref --format='%(refname:short)|%(upstream:short)|%(upstream:track)' refs/heads
```

`%(upstream:track)` prints `[gone]` when the branch has a configured upstream and the remote-tracking ref does not exist. Verified.

- False negative: the remote-tracking ref disappears only on a pruning fetch. Verified: after the remote branch was deleted, the field stayed `[ahead 1]` with no fetch and after a plain `git fetch`. It changed to `[gone]` only after `git fetch --prune`. The `fetch.prune` configuration makes every fetch prune.
- False negative: a branch that never had an upstream never prints `[gone]`.
- False positive as a merge signal: `[gone]` means "deleted". A person can delete a remote branch without merging it. GitHub deletes the head branch after a merge only when the repository enables "Automatically delete head branches".
- False positive as a safety signal: `[gone]` says nothing about commits made after the last push. Verified: a branch with one local-only commit printed `[gone]`.

`[gone]` is a hint that prompts the merge checks. It is not proof of anything on its own.

## Locked worktrees

`git worktree list --porcelain` prints a `locked` line for a locked worktree. The line carries the reason when one was given. The lock is a file at `$GIT_COMMON_DIR/worktrees/<id>/locked`.

`git worktree remove` refuses a locked worktree. `--force` given once does not override the lock. `--force --force` does. Verified message: `cannot remove a locked working tree, lock reason: ... use 'remove -f -f' to override or unlock first`.

The signal is exact. A lock is an explicit statement by a user or a tool. cgwt should treat it as "do not delete". The manual states that `git worktree remove` cannot remove the main worktree.

## Porcelain output of `git worktree list`

```
git worktree list --porcelain -z
```

Verified output without `-z`:

```
worktree /path/main
HEAD 297dc827e976487d0fdc5369a51fd782e1a2d48c
branch refs/heads/trunk

worktree /path/wt-det
HEAD ae0fbcea4946105134fa92db7afcb158b08f45c1
detached
locked "on usb\ndrive"

worktree /path/wt-dirty
HEAD ae0fbcea4946105134fa92db7afcb158b08f45c1
branch refs/heads/dirty
prunable gitdir file points to non-existent location
```

Format rules from the manual and the run above:

- One record per worktree. An empty line ends a record. The main worktree comes first.
- Each line is a label, then optionally one space and a value.
- `worktree <path>` starts the record. The path is absolute.
- `HEAD <oid>` is absent for a bare repository.
- Exactly one of `branch <full refname>`, `detached`, or `bare` follows. The branch is a full ref name such as `refs/heads/trunk`.
- `locked` or `locked <reason>` is present only for a locked worktree.
- `prunable <reason>` is present only when the worktree directory is missing or the administrative files are broken. Verified by deleting a worktree directory by hand.
- Boolean labels appear only when true. A parser must accept unknown labels, because git adds labels over time.
- Without `-z`, git quotes a lock reason that contains special characters, in C style. Verified: a reason with a newline printed as `"on usb\ndrive"`. With `-z`, git ends every line with NUL, ends every record with an extra NUL, and does not quote. `-z` requires git 2.36 or later. Use `-z`, because a path can contain a newline.

The list gives cgwt the path, the branch, the lock state, and the prunable state of each worktree in one call. It gives no information about cleanliness or merge state. Those need the per-worktree commands above.

## Detached HEAD worktrees

A worktree with a detached HEAD has no branch. Commits made there are reachable only from that worktree's `HEAD`. Deleting the worktree makes them unreachable, and `git gc` later deletes them.

```
git rev-list --count HEAD --not --branches --tags --remotes
```

Run inside the worktree. The output is the number of commits that no branch, tag, or remote-tracking ref reaches. Verified: `1` after one commit on a detached HEAD.

Do not use `--not --all`. `--all` includes `HEAD`, so the count is always `0`. Verified.

## Not verified

- The `--assume-unchanged` and `--skip-worktree` blind spot of `git status`.
- The state files of operations in progress.
- The `gh pr list` lookup.
- Behaviour on git versions other than 2.43.0. The minimum versions given for `merge-tree --write-tree` (2.38) and `worktree list -z` (2.36) come from memory of the release notes. This research did not open them.
- Whether later git versions create `refs/remotes/origin/HEAD` during `git fetch`.
- GitHub's squash and rebase merges were simulated with `git merge --squash` and `git cherry-pick`. No real GitHub pull request was merged.

## Sources

- git-worktree manual, git 2.43.0: `remove`, `lock`, `list --porcelain`, `-z`, and the REFS section. https://git-scm.com/docs/git-worktree
- `builtin/worktree.c`, git v2.43.0: `check_clean_worktree` and `remove_worktree`. https://github.com/git/git/blob/v2.43.0/builtin/worktree.c
- git-status manual: porcelain v2 format and `--untracked-files`. https://git-scm.com/docs/git-status
- git-for-each-ref manual: `%(upstream:track)` and `[gone]`. https://git-scm.com/docs/git-for-each-ref
- git-rev-list manual: `--all`, `--remotes`, `--branches`. https://git-scm.com/docs/git-rev-list
- git-cherry manual. https://git-scm.com/docs/git-cherry
- `builtin/log.c`, git v2.43.0: `cmd_cherry`. https://github.com/git/git/blob/v2.43.0/builtin/log.c
- git-merge-tree manual: `--write-tree`. https://git-scm.com/docs/git-merge-tree
- git-ls-remote manual: `--symref`. https://git-scm.com/docs/git-ls-remote
- git-remote manual: `set-head`. https://git-scm.com/docs/git-remote
- GitHub Docs, "About pull request merges". https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/incorporating-changes-from-a-pull-request/about-pull-request-merges
- GitHub Docs, "Managing the automatic deletion of branches". https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-the-automatic-deletion-of-branches
