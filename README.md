# claude-project-template

This repository is the starting point for new projects. It carries the Claude Code setup and nothing else.

## What is included

- `.claude/settings.json` — enables the `mattpocock-skills` and `ponytail` plugins at project scope and turns off commit and PR attribution.
- `.claude/skills/implement-interactive/SKILL.md` — the `/implement-interactive` skill: PR rules, the three-axis review gate, and the plugin skill map. The user invokes it. Agents never invoke it unprompted.
- `.claude/skills/implement-mobile/SKILL.md` — the `/implement-mobile` skill: `/implement-interactive` plus the rule for asking the user from a client where `AskUserQuestion` does not work.
- `AGENTS.md` — agent instructions: repository content and standards.
- `CLAUDE.md` — imports `AGENTS.md` with the `@` syntax.
- `docs/agents/` — issue tracker conventions, triage labels, and domain docs layout. All three files are repo-agnostic.

## After creating a repository from this template

1. Create the five triage labels in the new repository: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`.
2. Replace this README with the project's own.
