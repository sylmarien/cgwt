# PROTOTYPE: path pattern syntax

Throwaway prototype for [Path pattern syntax in the config file](https://github.com/sylmarien/cgwt/issues/10). It holds configuration text and the paths each candidate yields. It holds no implementation.

## Example repository

| Input | Value |
|---|---|
| `origin` | `git@gitlab.example.com:platform/tools/meta.project.git` |
| `host` | `gitlab.example.com` |
| `remote_path` | `["platform", "tools", "meta.project"]` |
| `project` | `meta.project` |
| `main_worktree` | `src` |
| `branch` | `feature/x` |

Every candidate sets `workforest = "~/worktrees"` as a separate key. The path pattern is relative to the workforest.

## Paths every candidate must yield

1. Flat per project: `~/worktrees/meta.project/feature-x`
2. Remote-mirroring: `~/worktrees/gitlab.example.com/platform/tools/meta.project/feature-x`
3. Split project name: `~/worktrees/meta.project/feature-x/meta/project/src`

Three more cases test the transformations:

4. Nested branch: `~/worktrees/meta.project/feature/x`
5. Another replacement: `~/worktrees/meta.project/feature_x`
6. One element of a list: `~/worktrees/platform/meta/feature-x` (first remote path segment, then first part of the split project name)

## Candidate A: Jinja-style string

The syntax copies worktrunk. cgwt parses `{{ input | filter('argument') }}` itself, because Jinja is not in the standard library.

```toml
workforest = "~/worktrees"

# 1
path = "{{ project }}/{{ branch | sanitize }}"
# 2
path = "{{ host }}/{{ remote_path | join('/') }}/{{ branch | sanitize }}"
# 3
path = "{{ project }}/{{ branch | sanitize }}/{{ project | split('.') | join('/') }}/{{ main_worktree }}"
# 4
path = "{{ project }}/{{ branch }}"
# 5
path = "{{ project }}/{{ branch | sanitize('_') }}"
# 6
path = "{{ remote_path | first }}/{{ project | split('.') | first }}/{{ branch | sanitize }}"
```

- Filters: `sanitize`, `split`, `join`, `first`, `last`, `at(n)`.
- A worktrunk user reads it without help.
- The syntax promises Jinja. A user who writes `{% if %}` or `lower` gets an error.
- Filters chain, so case 6 is direct.
- cgwt needs a hand-written parser for the pipe chain and the quoted arguments.

## Candidate B: format string

The syntax is the Python format string. `string.Formatter` parses it. cgwt overrides only the meaning of the text after `:`.

```toml
workforest = "~/worktrees"

# 1
path = "{project}/{branch}"
# 2
path = "{host}/{remote_path}/{branch}"
# 3
path = "{project}/{branch}/{project:split=.}/{main_worktree}"
# 4
path = "{project}/{branch:slash=/}"
# 5
path = "{project}/{branch:slash=_}"
# 6: not expressible
path = "{remote_path[0]}/???/{branch}"
```

- A list renders as several path segments. No `join` exists.
- `{branch}` replaces `/` with `-` by default. `slash=` chooses another replacement. `slash=/` nests.
- `{remote_path[0]}` works. `{remote_path[-1]}` fails in the stock `string.Formatter` and needs a small override.
- A split result cannot be indexed, so case 6 fails. A chained form such as `{project:split=.,at=0}` fixes it. The candidate then equals Candidate A with other punctuation.
- It is the shortest text for cases 1 to 5.

## Candidate C: structured segments

The path pattern is a TOML array. A string is a literal segment. An inline table is a computed segment. cgwt parses nothing.

```toml
workforest = "~/worktrees"

# 1
path = [{ input = "project" }, { input = "branch" }]
# 2
path = [{ input = "host" }, { input = "remote_path" }, { input = "branch" }]
# 3
path = [
    { input = "project" },
    { input = "branch" },
    { input = "project", split = "." },
    { input = "main_worktree" },
]
# 4
path = [{ input = "project" }, { input = "branch", slash = "/" }]
# 5
path = [{ input = "project" }, { input = "branch", slash = "_" }]
# 6
path = [
    { input = "remote_path", at = 0 },
    { input = "project", split = ".", at = 0 },
    { input = "branch" },
]
```

- `tomllib` does all the parsing. cgwt validates keys and types.
- Every case is expressible. The order of `split` then `at` is fixed.
- A segment that mixes literal text and an input, such as `wt-<branch>`, needs extra keys (`prefix`, `suffix`).
- It is the longest text. Case 1 is hard to read at a glance.

## Candidate D: plain placeholders plus named values

The path pattern is a string with plain `{name}` placeholders. A `[values.<name>]` table defines a computed value from an input or from another value.

```toml
workforest = "~/worktrees"

# 1
path = "{project}/{branch}"
# 2
path = "{host}/{remote_path}/{branch}"
# 3
path = "{project}/{branch}/{project_parts}/{main_worktree}"

[values.project_parts]
input = "project"
split = "."
```

```toml
# 4
path = "{project}/{nested_branch}"

[values.nested_branch]
input = "branch"
slash = "/"
```

```toml
# 5: same as 4 with slash = "_"

# 6
path = "{owner}/{project_head}/{branch}"

[values.owner]
input = "remote_path"
at = 0

[values.project_head]
input = "project_parts"
at = 0
```

- Cases 1 and 2 need no `[values]` table. The user pays for a transformation only when a layout needs one.
- The path pattern reads as the final path. The reader looks up a computed value in a second place.
- A value can take another value as its input, so transformations chain.
- `{branch}` replaces `/` with `-` by default, as in Candidate B.
- The parser is `str.format_map` plus a check of the placeholder names.
- Open point: a `[values]` table is global, or an override can define its own. "How invocation-directory overrides and project overrides are matched and ordered" settles it.

## Comparison

| | A: Jinja-style | B: format string | C: structured | D: placeholders plus values |
|---|---|---|---|---|
| Case 1 text | `{{ project }}/{{ branch \| sanitize }}` | `{project}/{branch}` | two inline tables | `{project}/{branch}` |
| Cases 1 to 5 | yes | yes | yes | yes |
| Case 6 | yes | no | yes | yes |
| Literal text inside a segment | yes | yes | needs extra keys | yes |
| Parser cgwt writes | pipe chain with quoted arguments | format-spec reader | none | none |
| Familiar to worktrunk users | yes | no | no | no |
| New transformation later | new filter | new spec key | new table key | new table key |

## Questions for the verdict

1. Which candidate, or which mix.
2. `{branch}` sanitises by default, or the user writes the sanitiser each time.
3. The names of the inputs: `host`, `remote_path`, `project`, `main_worktree`, `branch`.
4. `workforest` is a separate key, or the path pattern holds the whole path.
