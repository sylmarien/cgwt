# CLI output conventions that serve AI agents

Research for issue #6. Sources were read on 2026-09-21.

## Question

Which output and error conventions make a CLI efficient for AI agents to drive? How do established CLIs offer a human mode and a machine mode side by side?

## Answer

1. cgwt prints plain, undecorated, line-based text by default. One default serves humans, pipes, and agents.
2. A per-command `--json` flag selects the machine format. cgwt does not select the data format from an environment variable or from TTY detection.
3. TTY detection controls decoration only: color, JSON indentation, and prompts. cgwt never prompts when stdin is not a TTY.
4. `--json` prints one JSON document on stdout. A list command prints an array of objects. The same object shape appears in every command. Later versions add keys and never rename or remove them.
5. Compact text costs about 20% fewer tokens than compact JSON for the same records. Indented JSON costs about 27% more than compact JSON. An agent reads the text default. A program that parses uses `--json`.
6. Results go to stdout. Errors, warnings, and progress go to stderr. A failed command prints nothing on stdout.
7. An error is one line of text on stderr in every mode. It states what failed and which command or flag fixes it. cgwt prints no traceback.
8. Exit codes are 0 for success, 1 for a failure, and 2 for a usage error. cgwt adds a distinct code only for a failure that a caller handles differently, such as a delete that a safety check refused.

## How an agent reads a CLI

An agent harness runs the command without a terminal and returns the text to the model.

- Claude Code returns a bounded amount of output. `BASH_MAX_OUTPUT_LENGTH` is the "Maximum number of characters of bash output that Claude Code reads back into a command's result (default: 30000; maximum: 150000)". [claude-env]
- Claude Code sets `CLAUDECODE=1` in the subprocesses it spawns. The variable is specific to one vendor. [claude-env]
- Anthropic restricts tool responses in Claude Code to 25,000 tokens by default. It advises "pagination, range selection, filtering, and/or truncation with sensible default parameter values for any tool responses that could use up lots of context". [anthropic-tools]
- Anthropic advises that tools "return only high signal information back to agents". It reports that resolving "arbitrary alphanumeric UUIDs to more semantically meaningful and interpretable language significantly improves Claude's precision". [anthropic-tools]
- Anthropic states that the response structure, "for example XML, JSON, or Markdown", affects performance and that "there is no one-size-fits-all solution". [anthropic-tools]

Consequences for cgwt:

- An agent is a non-TTY caller. Every rule that clig.dev gives for pipes and scripts applies to agents.
- The absolute worktree path is the high-signal value. The next action of the agent uses it.
- cgwt output is small. Pagination and a `concise` or `detailed` switch are not needed in v1.

## Mode selection

| CLI | Default | Machine mode | Environment variable | TTY detection |
| --- | --- | --- | --- | --- |
| gh | Line-based text | `--json <fields>`, `--jq`, `--template` | `GH_FORCE_TTY`, `NO_COLOR`, `CLICOLOR`, `GH_PROMPT_DISABLED` | Piped text becomes tab-delimited, untruncated, and uncolored. JSON is indented only on a terminal. |
| kubectl | Table | `-o json`, `-o yaml`, `-o name`, `-o jsonpath`, `-o custom-columns` | None for the format | None for the format |
| docker | Table | `--format json`, `--format <Go template>`, `--quiet` | None for the format | None for the format |
| cargo | Human diagnostics | `--message-format=json`, `cargo metadata --format-version 1` | None for the format | None for the format |
| git | Human text | `--porcelain`, `-z` | None for the format | Color and pager only |
| aws | JSON | `--output json\|yaml\|yaml-stream\|text\|table\|off`, `--query` | `AWS_DEFAULT_OUTPUT` | None for the format |

Sources: [gh-formatting], [gh-env], [gh-scripting], [kubectl-ref], [docker-ls], [cargo-external], [git-worktree], [git-status], [aws-output].

Findings:

- Every CLI in the table selects the data format with an explicit flag. Only aws also reads an environment variable and a configuration file. The aws precedence is flag, then environment variable, then configuration file. [aws-output]
- Only gh changes the text layout on TTY detection. The gh team describes it: "fields are tab-delimited; we no longer truncate any text; and, there are no escape sequences for color in the output". [gh-scripting]
- clig.dev treats TTY detection as the heuristic for whether a human reads a stream. It uses the result for color, animations, prompts, and the pager. It selects JSON with a flag: "Display output as formatted JSON if `--json` is passed." [clig]
- clig.dev recommends `--plain` only when the human format breaks the rule of one record per line. [clig]
- kubectl tells script authors to request a machine-oriented output form and not to rely on implicit state. [kubectl-conventions]
- The human format is free to change. The machine format is an interface. clig.dev: "Encourage your users to use `--plain` or `--json` in scripts to keep output stable". [clig]
- Color is off when the stream is not a TTY, when `NO_COLOR` is set and not empty, or when `TERM=dumb`. [clig] [no-color]
- Prompts are off when stdin is not a TTY. clig.dev: "Never require a prompt." A dangerous action requires `-f` or `--force` in that case. [clig]

cgwt does not need a second text layout. Its default text has no color, no truncation, and one record per line, so the TTY output and the piped output are the same.

## JSON shape

The established CLIs do not agree on one shape.

| CLI | Top level of a list | Key case | Stability statement |
| --- | --- | --- | --- |
| gh | Array of objects | camelCase | The caller names the fields it wants. |
| kubectl | Object with `kind: List` and `items` | camelCase | The API version is part of the document. |
| aws | Object with one named key, such as `Users` | PascalCase | None found |
| docker | One object per line | PascalCase | None found |
| cargo build | One object per line with a `reason` key | snake_case | `cargo metadata` requires `--format-version` "to avoid forward incompatibility hazard". |
| git porcelain | One label per line, records separated by an empty line | Not applicable | "will remain stable across Git versions and regardless of user configuration" |

Sources: [gh-formatting], [kubectl-jsonpath], [aws-output], [docker-ls], [cargo-external], [git-worktree].

Conventions that the sources share:

- The machine format ignores user configuration. git porcelain ignores `color.status` and `status.relativePaths`. [git-status]
- A parser ignores what it does not recognize. git: "Parsers should ignore headers they don't recognize." [git-status] A producer can then add keys without a version bump.
- Line-delimited JSON serves streams of events, as in cargo. A short, complete result is one document, as in gh.
- gh prints compact JSON on one line when stdout is not a terminal and indents it on a terminal. [gh-formatting] Verified with gh 2.100.0.
- A path can contain a newline. git offers `-z` for that case. [git-worktree] JSON escapes the newline, so `--json` covers the case without a `-z` flag.

Recommendation for cgwt:

- A list command prints an array of worktree objects.
- A command that acts on one worktree prints that one object.
- Keys use snake_case. No source dictates the case. snake_case matches the Python code and the TOML configuration.
- A boolean key is always present with `true` or `false`. A consumer then needs no presence check.
- A path is always absolute.

## Token efficiency

Anthropic publishes one measurement: a concise tool response used 72 tokens where the detailed response used 206. [anthropic-tools] No primary source compares JSON against compact text, so this research measured it.

Method: five worktree records with the keys `path`, `branch`, `head` (40 hexadecimal characters), `locked`, and `dirty`. The tokenizer is tiktoken.

| Format | Characters | Tokens (o200k_base) | Ratio to compact JSON |
| --- | --- | --- | --- |
| JSON, `indent=2` | 985 | 373 | 1.27 |
| JSON, compact separators | 804 | 293 | 1.00 |
| JSON Lines, compact | 802 | 296 | 1.01 |
| TSV with a header line | 592 | 229 | 0.78 |
| Label per line, git porcelain style | 633 | 247 | 0.84 |

cl100k_base gives the same ratios within 0.02.

Limits of the measurement:

- tiktoken implements OpenAI tokenizers. The Claude tokenizer can give other counts. The ratios are indicative.
- The 40-character hash dominates every row. A short hash, or no hash, increases the relative cost of JSON keys and punctuation.
- The text formats repeat no key names. The saving grows with the number of records.

Conclusions:

- Indentation is the largest avoidable cost. cgwt prints compact JSON when stdout is not a TTY.
- Compact text is the cheapest format for an agent that reads the result. JSON is the safest format for a program that parses the result.
- A state-changing command prints little on success. clig.dev: "Display output on success, but keep it brief." and "If you change state, tell the user." [clig] A create command that prints only the new absolute path on stdout satisfies both rules and supports `cd "$(cgwt ...)"`.

## Errors, stdout, and stderr

- clig.dev: "The primary output for your command should go to `stdout`. Anything that is machine readable should also go to `stdout`". "Log messages, errors, and so on should all be sent to `stderr`." [clig]
- clig.dev: "Catch errors and rewrite them for humans." "Signal-to-noise ratio is crucial." "Put the most important information at the end of the output." [clig]
- Anthropic: error responses should "clearly communicate specific and actionable improvements, rather than opaque error codes or tracebacks". [anthropic-tools]
- gh prints a plain text error on stderr and nothing on stdout when `--json` is set. Verified with gh 2.100.0 and `gh issue view 99999 --json title`.
- aws writes errors to stderr, also when `--output off` suppresses stdout. [aws-output]
- cargo keeps JSON messages on stdout. [cargo-external]
- gh prints its update notice on stderr. [gh-env] A notice on stderr does not corrupt a parsed stdout.
- `argparse` prints usage errors to stderr. [argparse]

Recommendation for cgwt:

- The error format is `cgwt: error: <what failed>. <what to run or pass instead>.` on stderr.
- The error is text in every mode. A JSON error object on stdout would force every consumer to inspect the document before it trusts it. The exit code already carries the failure class.
- A refused delete names the reason for the refusal and the flag that overrides it.
- Python tracebacks appear only for an unexpected error. clig.dev asks for debug information and bug report instructions in that case. [clig]

## Exit codes

| Source | Codes |
| --- | --- |
| clig.dev | "Return zero exit code on success, non-zero on failure." "Map the non-zero exit codes to the most important failure modes." |
| gh | 0 success, 1 failure, 2 cancelled, 4 authentication required |
| aws | 0 success, 2 parse failure, 130 SIGINT, 252 invalid syntax or parameter, 253 invalid environment or configuration, 254 service error, 255 general failure |
| argparse | 2 for an invalid argument list |
| bash | 0 success, 126 not executable, 127 not found, 128+N for a fatal signal N. The shell uses values above 125 specially. |

Sources: [clig], [gh-exit], [aws-returncodes], [argparse], [bash].

Recommendation for cgwt:

- 0 means success.
- 1 means the command failed.
- 2 means a usage error. `argparse` already exits with 2.
- A distinct code exists only for a failure that a caller handles differently. The delete safety refusal is the known candidate. The delete ticket decides its number.
- Every code stays below 126.
- The help text of each command lists its codes, because an agent reads `--help`.

## Not verified

- The token ratios use OpenAI tokenizers. No Claude tokenizer was available offline.
- The docker formatting guide does not state that `--format json` prints one object per line. The `container ls` reference shows one object on one line.
- `git-scm.com` and `clig.dev` did not load. The git text comes from `Documentation/*.adoc` on the git `master` branch. The clig.dev text comes from the source file of the site.
- The GNU Bash manual page returned HTTP 429. The bash text comes from the local `man bash`.
- OpenAI and Google publish no guidance specific to CLI output for agents that this research found. The guidance from AI labs here is from Anthropic only.

## Sources

- [clig]: https://clig.dev/ , read from https://github.com/cli-guidelines/cli-guidelines/blob/main/content/_index.md
- [gh-formatting]: https://cli.github.com/manual/gh_help_formatting
- [gh-env]: https://cli.github.com/manual/gh_help_environment
- [gh-exit]: https://cli.github.com/manual/gh_help_exit-codes
- [gh-scripting]: https://github.blog/engineering/engineering-principles/scripting-with-github-cli/
- [kubectl-ref]: https://kubernetes.io/docs/reference/kubectl/
- [kubectl-conventions]: https://kubernetes.io/docs/reference/kubectl/conventions/
- [kubectl-jsonpath]: https://kubernetes.io/docs/reference/kubectl/jsonpath/
- [docker-ls]: https://docs.docker.com/reference/cli/docker/container/ls/
- [cargo-external]: https://doc.rust-lang.org/cargo/reference/external-tools.html
- [git-worktree]: https://github.com/git/git/blob/master/Documentation/git-worktree.adoc
- [git-status]: https://github.com/git/git/blob/master/Documentation/git-status.adoc
- [aws-output]: https://docs.aws.amazon.com/cli/latest/userguide/cli-usage-output-format.html
- [aws-returncodes]: https://docs.aws.amazon.com/cli/latest/userguide/cli-usage-returncodes.html
- [no-color]: https://no-color.org/
- [argparse]: https://docs.python.org/3/library/argparse.html
- [bash]: `man bash`, section EXIT STATUS
- [anthropic-tools]: https://www.anthropic.com/engineering/writing-tools-for-agents
- [claude-env]: https://code.claude.com/docs/en/env-vars
