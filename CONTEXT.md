# cgwt

cgwt creates, tracks, and deletes git worktrees according to a per-user configuration file.

## Language

**Project**:
The codebase that the remote of a repository identifies. Several repositories can belong to one project.
_Avoid_: Repo, codebase

**Repository**:
One clone on disk, together with the worktrees git records for it.
_Avoid_: Clone, copy, checkout

**Path pattern**:
The configuration entry that computes the path of a worktree from facts about the project, the repository, and the branch.
_Avoid_: Path rule, template, layout

**Project override**:
A configuration entry that replaces the default settings for every project it matches.
_Avoid_: Project rule, per-project config

**Base**:
The commit a new branch starts from.
_Avoid_: Start point

**Workforest**:
A directory that contains the worktrees cgwt creates, for any number of projects.
_Avoid_: Forest, forest location, worktree root

**Worktree**:
A linked git worktree inside a workforest. A main clone is a Repository, never a Worktree.
_Avoid_: Managed worktree, tracked worktree

**Safe worktree**:
A worktree that cgwt deletes without force. It has no changed or untracked file, no git operation in progress, no lock, and no commit that both exists on no remote and is unmerged into the default branch of origin.
_Avoid_: Clean worktree, merged worktree
