# Derive the set of worktrees from disk and git instead of a registry

cgwt keeps no registry. `list` walks every workforest named in the configuration and treats each directory with a `.git` file as a worktree, whoever created it. cgwt computes the project from the current remote URL on every invocation, so a stored path would drift after a URL change, and a registry would miss every worktree removed by hand.
