# Run cgwt's own safety checks before deleting a worktree

`git worktree remove` checks only `git status --porcelain` and honours `status.showUntrackedFiles`, so it deletes a worktree that holds untracked files. cgwt runs `git status --porcelain=v2 --untracked-files=all`, checks for an operation in progress and a lock, and treats a commit as lost only when it exists on no remote and the ancestry, `git cherry`, and `git merge-tree --write-tree` checks all fail to find it merged into `origin/HEAD`. The squash check is a heuristic with accepted limits that the delete tests pin.
