# Render path patterns with str.format_map and [values] tables

A path pattern is a string of plain `{name}` placeholders. Each computed value is a `[values.<name>]` table with `input`, `split`, `at`, or `slash`, and values chain through `input`. `str.format_map` renders the pattern and `string.Formatter().parse` validates the placeholder names, so cgwt has no template parser and no template dependency. The tables express every layout of v1, including a project name split into path segments.
