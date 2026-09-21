# cgwt

cgwt creates, tracks, and deletes git worktrees according to a per-user configuration file.

## Language

**Project**:
The codebase that the remote of a repository identifies. Several repositories can belong to one project. A repository with no remote is a project of its own.
_Avoid_: Repo, codebase

**Repository**:
One clone on disk, together with the worktrees git records for it.
_Avoid_: Clone, copy, checkout

**Path pattern**:
The configuration entry that computes the path of a worktree from facts about the project, the repository, and the branch.
_Avoid_: Path rule, template, layout

**Workforest**:
A directory that contains the worktrees cgwt creates, for any number of projects.
_Avoid_: Forest, forest location, worktree root
