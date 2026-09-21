# Prior art for worktree path layouts and rule syntax

Research for issue #4. Sources are the official documentation and the source code of each tool, read on 2026-09-21 from the default branch of each repository.

## Answer

Two tools compute the worktree path from a template: worktrunk and gwq. Every other tool joins a base directory and a name derived from the branch. The complaint that each tool supports a single layout style holds for wtp, gtr, git-wt, workmux, phantom, and ghq. It does not hold for worktrunk. Git Town does not create worktrees and has no path setting.

No tool selects a path rule by invocation directory. No tool offers a date, an environment variable, or the base branch as a path input. No tool offers regex capture on the branch name.

## Comparison

| Tool | Path syntax | Inputs | Branch transformations | Rule selection |
|---|---|---|---|---|
| worktrunk | Jinja template (minijinja) | `repo_path`, `repo`, `owner`, `remote_repo`, `branch` | `sanitize`, `sanitize_db`, `sanitize_hash`, `hash`, `codename(n)`, `dirname`, `basename`, minijinja builtins | Global value, then `[projects."<glob>"]` entries keyed by remote identifier |
| gwq | Go `text/template` | `Host`, `Owner`, `Repository`, `Branch`, `Hash` | `sanitize_chars` replacement map, then a fixed replacement of `/ \ : * ? " < > \|` with `-` | One global template. `basedir` alone varies per repository path |
| wtp | `base_dir` + branch | branch | None. `/` in the branch creates nested directories | One `.wtp.yml` per repository |
| gtr | `gtr.worktrees.dir` + `gtr.worktrees.prefix` + branch | branch | `/` becomes `-`. `--folder` and `--name` override per invocation | git config scopes, `.gtrconfig`, environment variables |
| git-wt | `wt.basedir` + target name | `{gitroot}`, branch | None documented | git config scopes, `--basedir` flag |
| workmux | `worktree_dir` + prefix + handle | `{project}`, branch | `worktree_naming`: `full` (`/` becomes `-`) or `basename` (text after the last `/`) | Global config, then project config |
| phantom | `worktreesDirectory` + branch | branch | `directoryNameSeparator` replaces `/` | `phantom preferences` (global git config) overrides `phantom.config.json` |
| ghq | Fixed `<root>/<host>/<path>` | Remote URL | None | `ghq.<url>.root` matched with `git config --get-urlmatch` |
| Git Town | None | None | None | None |
| git | Explicit path argument | None | None | None |

## worktrunk

Repository: <https://github.com/max-sixty/worktrunk>. Config: TOML at `~/.config/worktrunk/config.toml`.

**Inputs.** `format_path` in [`src/config/user/accessors.rs`](https://github.com/max-sixty/worktrunk/blob/main/src/config/user/accessors.rs) passes five variables to the template: `repo` (directory name of the main worktree), `branch`, `repo_path` (absolute path), `owner`, and `remote_repo`. It sets `owner` and `remote_repo` only when the primary remote URL parses. The [config docs](https://github.com/max-sixty/worktrunk/blob/main/docs/src/content/docs/config.md) state that this set is smaller than the set that hooks receive. The remote host, the base branch, the date, and environment variables are not inputs.

**Transformations.** [`template_environment` in `src/config/expansion.rs`](https://github.com/max-sixty/worktrunk/blob/main/src/config/expansion.rs) registers these filters:

- `sanitize` replaces `/` and `\` with `-`.
- `sanitize_db` lowercases, replaces non-alphanumeric characters with `_`, appends a 3-character hash, and truncates to 48 characters.
- `sanitize_hash` produces a filename-safe name with a hash.
- `hash` produces a short hash.
- `codename(n)` produces a deterministic name of `n` words from the branch.
- `dirname` and `basename` act on path strings.

`Cargo.toml` enables the minijinja `builtins` feature. The [minijinja builtin filters](https://docs.rs/minijinja/latest/minijinja/filters/index.html) include `replace`, `split`, `lower`, `upper`, `first`, `last`, `default`, `trim`, and `join`. Conditionals (`{% if owner %}`) work because the environment uses `UndefinedBehavior::SemiStrict`. minijinja has no regex filter and no date function.

**Syntax.**

```toml
worktree-path = "~/worktrees/{{ repo }}/{{ branch | sanitize }}"

[projects."git.company.example/platform/*"]
worktree-path = ".worktrees/{{ branch | sanitize }}"
```

`~` expands to the home directory. A relative path resolves from `repo_path`. An unfiltered `{{ branch }}` keeps `/` and creates nested directories.

**Rule selection.** Precedence is `--config-set`, then `WORKTRUNK_WORKTREE_PATH`, then the matching `[projects."<key>"]` entry, then the global key. A project key is `<host>/<owner>/<repo>` from the primary remote URL, or the canonical repository path when no remote exists. `*` is the only wildcard and matches `/`. The entry with the most non-`*` characters wins.

**Limits.**

- A rule cannot match on the invocation directory or on the branch name.
- The host is part of the project key but is not a template variable.
- An undefined variable in output position is an error. A repository without a remote needs an `{% if owner %}` guard.
- The documentation does not show branch decomposition. The minijinja `split` builtin makes it expressible. This research did not run it.

## gwq

Repository: <https://github.com/d-kuro/gwq>. Config: TOML at `~/.config/gwq/config.toml`, plus a local `.gwq.toml`.

**Inputs.** `TemplateData` in [`internal/template/template.go`](https://github.com/d-kuro/gwq/blob/main/internal/template/template.go) has `Host`, `Owner`, `Repository`, `Branch`, and `Hash`. `Hash` is the first 8 hex characters of the SHA-256 of the repository path and the branch. The README states that `Host`, `Owner`, `Repository`, and `Hash` are empty when the repository has no remote.

**Transformations.** gwq sanitises only the branch. It applies the `sanitize_chars` map first. It then applies `SanitizeForFilesystem` from [`internal/utils/utils.go`](https://github.com/d-kuro/gwq/blob/main/internal/utils/utils.go), which replaces `/ \ : * ? " < > |` with `-`. The template has no custom functions, so only the Go `text/template` builtins are available.

**Syntax.**

```toml
[worktree]
basedir = "~/worktrees"

[naming]
template = "{{.Host}}/{{.Owner}}/{{.Repository}}/{{.Branch}}"
sanitize_chars = { "/" = "-", ":" = "-" }

[[repository_settings]]
repository = "~/src/myproject"
basedir = "./worktrees"
```

**Limits.**

- The [README](https://github.com/d-kuro/gwq/blob/main/README.md) states that `naming.template` is a global setting and affects all repositories.
- `repository_settings` overrides `basedir` only, and matches on the repository path.
- A branch cannot create nested directories, because the fixed sanitiser always replaces `/`.
- The template has no string functions for case, replacement, or splitting.

## wtp

Repository: <https://github.com/satococoa/wtp>. Config: YAML at `.wtp.yml` in the repository root.

`ResolveWorktreePath` in [`internal/config/config.go`](https://github.com/satococoa/wtp/blob/main/internal/config/config.go) joins `defaults.base_dir` and the worktree name. A relative `base_dir` resolves from the repository root. The default is `../worktrees`.

```yaml
version: "1.0"
defaults:
  base_dir: "../worktrees"
```

**Limits.** wtp has no template and no variables. The [README](https://github.com/satococoa/wtp/blob/main/README.md) states that branch names with slashes are preserved as directory structure, and offers no setting to flatten them. wtp has no user-level config file, so every repository needs its own `.wtp.yml`. `ResolveWorktreePath` does not expand `~`.

## git-worktree-runner (gtr)

Repository: <https://github.com/coderabbitai/git-worktree-runner>. Config: git config keys, a `.gtrconfig` file, and environment variables, per [`docs/configuration.md`](https://github.com/coderabbitai/git-worktree-runner/blob/main/docs/configuration.md).

```
gtr.worktrees.dir = ~/worktrees/my-project
gtr.worktrees.prefix = dev-
```

The default directory is `<repo-name>-worktrees` next to the repository. The folder name is the branch with `/` replaced by `-`. `--folder <name>` replaces the folder name for one invocation. `--name <suffix>` appends a suffix.

**Limits.** The directory value has no variables. A shared global value places every repository in the same directory, so the documented examples hardcode the project name.

## git-wt

Repository: <https://github.com/k1LoW/git-wt>. Config: git config.

```console
$ git config wt.basedir "../{gitroot}-worktrees"
```

`expandTemplate` in [`internal/git/config.go`](https://github.com/k1LoW/git-wt/blob/HEAD/internal/git/config.go) replaces `{gitroot}` with the repository directory name. It supports no other variable. `~` expands. A relative path resolves from the main repository root. The default is `.wt`. `--basedir` overrides the value for one invocation.

## workmux

Repository: <https://github.com/raine/workmux>. Config: YAML, global and per project.

```yaml
worktree_dir: ~/.workmux/{project}
worktree_naming: basename
worktree_prefix: wm-
```

Per the [README](https://github.com/raine/workmux/blob/main/README.md), `{project}` resolves to the directory name of the main worktree. `worktree_naming` has two values. `full` replaces `/` with `-`. `basename` keeps the text after the last `/`. `--name` overrides the handle for one invocation. The default directory is `<project>__worktrees/`.

**Limits.** `{project}` is the only variable. The branch is always the last path segment.

## phantom

Repository: <https://github.com/aku11i/phantom>. Config: `phantom.config.json` in the repository root, and `phantom preferences` in the global git config. A preference overrides the project file.

Per [`docs/configuration.md`](https://github.com/aku11i/phantom/blob/main/docs/configuration.md), `worktreesDirectory` is absolute or relative to the repository root, and defaults to `.git/phantom/worktrees`. `directoryNameSeparator` replaces `/` in the branch name. Without it, a branch with `/` creates nested directories.

```json
{ "worktreesDirectory": "../phantom-worktrees", "directoryNameSeparator": "-" }
```

**Limits.** phantom has no variables. The separator is the only transformation.

## ghq

Repository: <https://github.com/x-motemen/ghq>. Config: git config variables. ghq places repository clones, not worktrees.

Per the [README](https://github.com/x-motemen/ghq/blob/master/README.adoc), the layout is fixed: `<root>/<host>/<user>/<repo>`, derived from the remote URL. `ghq.root` sets the root and accepts several values. The last value is the primary root for new clones. `GHQ_ROOT` replaces all roots. `ghq.<url>.root` sets a root for the URLs that match, with `git config --get-urlmatch` semantics.

```
[ghq "https://git.example.com/repos/"]
root = ~/myproj
```

**Limits.** The segments below the root are not configurable. The rule selects a root by URL prefix and changes nothing else. The reuse of `--get-urlmatch` is notable: ghq delegates rule matching and specificity ordering to git.

## Git Town

Repository: <https://github.com/git-town/git-town>. Config: TOML at `git-town.toml`, git config, and environment variables.

The [command list](https://github.com/git-town/git-town/tree/main/website/src/commands) has no command that creates a worktree. The [preferences](https://github.com/git-town/git-town/tree/main/website/src/preferences) have no path setting. The changelog entries about worktrees cover only how Git Town behaves when a branch is checked out in another worktree.

Two preferences are prior art for rule syntax on branch names:

- `create.branch-prefix` adds a fixed prefix to the branches Git Town creates.
- `branches.feature-regex`, `contribution-regex`, `observed-regex`, and `perennial-regex` classify a branch by regular expression.

```toml
[branches]
feature-regex = "^my-*"
```

Each of the three config sources can set every preference: the config file, git config, and a `GIT_TOWN_*` environment variable.

## git

[`git worktree add <path>`](https://git-scm.com/docs/git-worktree) requires an explicit path. git has no layout setting. When the command omits the branch, git derives the branch name from the last component of the path.

## Layout features no tool offers

- **Rule selection by invocation directory.** worktrunk selects by remote identifier glob. gwq selects `basedir` by repository path. ghq selects by URL prefix. No tool selects by the directory in which the user runs the command.
- **Rule selection by branch name.** No tool chooses a different layout for branches that match a pattern. Git Town classifies branches by regex but does not place worktrees.
- **Date or time input.** No tool offers it.
- **Environment variable input.** gtr and worktrunk read an environment variable that replaces the whole value. No tool reads an environment variable inside a path rule.
- **Base branch input.** worktrunk gives `base` to hooks and not to `worktree-path`. No other tool has it.
- **Remote host input together with per-project rules.** gwq has `Host` and a single global template. worktrunk has per-project rules and no host variable.
- **Regex capture or substitution on the branch.** No tool offers it. An issue key such as `PRJ-123` cannot become its own path segment, except through the undocumented `split` builtin in worktrunk.
- **Documented branch decomposition.** workmux `basename` is the only documented case. No tool documents access to the first segment or to a segment by index.
- **Length limit on a segment.** Only worktrunk `sanitize_db` truncates, at a fixed 48 characters.
- **A choice between nesting and flattening per rule, outside worktrunk.** wtp always nests. gwq, gtr, and workmux always flatten. phantom chooses one separator per configuration.

## Not verified

- This research read documentation and source code. It ran none of the tools.
- git-wt: the source lines that join `wt.basedir` and the branch were not located, so the handling of `/` in a branch name is unconfirmed.
- worktrunk: minijinja builtins such as `split` and `replace` are enabled at compile time. Their use inside `worktree-path` was not executed.
- gwq: the behaviour of Go template builtins such as `slice` on the branch string was not executed.
