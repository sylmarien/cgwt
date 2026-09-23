# Claim the worktree path with os.mkdir and refuse any existing path

Create makes the parent directories and then creates the target directory with `os.mkdir`. That call is the collision check and the concurrency guard, because it fails atomically when the path exists. cgwt never appends a suffix, because an agent must be able to predict the path from the pattern and delete a worktree by branch name.
