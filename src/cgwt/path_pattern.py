"""Rendering of the path pattern that places a worktree."""

import string
from collections.abc import Mapping
from pathlib import Path

from cgwt.errors import CgwtError


def render_path(
    pattern: str,
    values: Mapping[str, Mapping[str, object]],
    inputs: Mapping[str, str | tuple[str, ...]],
) -> Path:
    """Render `pattern` into the relative path of a worktree.

    The function works in four steps:

    1. `string.Formatter().parse` splits the pattern into literal text and placeholders.
       Each placeholder must be a plain name without a format spec or a conversion.
       The name must be a key of `inputs` or `values`.
    2. No key of `values` may also be a key of `inputs`.
    3. `resolve_placeholder` computes each placeholder. A list joins with `/`.
       An empty result is an error, because an empty first segment makes the path absolute.
    4. At least one placeholder must derive from the branch.
       `str.format_map` then fills the pattern with the computed texts.

    Each failed check raises a `CgwtError` that names the pattern, placeholder, or value.
    """
    try:
        chunks = list(string.Formatter().parse(pattern))
    except ValueError as error:
        raise CgwtError(
            f"path pattern {pattern!r} is malformed: {error}. Balance its braces."
        ) from error
    placeholder_names = []
    for _literal_text, field_name, format_spec, conversion in chunks:
        if field_name is None:
            continue
        placeholder_text = "{" + field_name + (f"!{conversion}" if conversion else "")
        placeholder_text += (f":{format_spec}" if format_spec else "") + "}"
        if not field_name.isidentifier() or format_spec or conversion:
            raise CgwtError(
                f"path pattern placeholder {placeholder_text} is not a plain name. Use {{<name>}}."
            )
        if field_name not in inputs and field_name not in values:
            raise CgwtError(
                f"path pattern names unknown placeholder {placeholder_text}. "
                f"Add [values.{field_name}] or use an input."
            )
        placeholder_names.append(field_name)
    if clashing_names := sorted(values.keys() & inputs.keys()):
        raise CgwtError(
            f"value {clashing_names[0]} has the name of an input. "
            f"Rename [values.{clashing_names[0]}]."
        )
    uses_branch = False
    rendered_texts = {}
    for name in placeholder_names:
        resolved, reaches_branch = resolve_placeholder(name, values, inputs)
        uses_branch |= reaches_branch
        text = resolved if isinstance(resolved, str) else "/".join(resolved)
        if not text:
            raise CgwtError(
                f"path pattern placeholder {{{name}}} renders empty. "
                "Pass a non-empty value or remove it from the pattern."
            )
        rendered_texts[name] = text
    if not uses_branch:
        raise CgwtError(
            f"path pattern {pattern!r} does not use the branch. Add {{branch}} to the pattern."
        )
    return Path(pattern.format_map(rendered_texts))


def resolve_placeholder(
    name: str,
    values: Mapping[str, Mapping[str, object]],
    inputs: Mapping[str, str | tuple[str, ...]],
) -> tuple[str | tuple[str, ...], bool]:
    """Resolve the placeholder `name` and tell whether its chain reaches the branch.

    An input resolves to its entry in `inputs`. A value resolves in three steps:

    1. The function follows the `input` key of each table from `name` to an input.
       The tables it visits form the chain. A name that repeats on the chain is a cycle.
       The walk also records the value nearest to the input that sets `slash`.
    2. When the input is `branch`, that `slash` replaces each `/` of the branch.
       The default is `-`. When the input is not `branch`, a `slash` is an error.
    3. The function applies the tables in reverse chain order, from the input back to `name`.
       Each table first applies its `split`, which turns a string into a tuple.
       It then applies its `at`, which takes one element of the tuple.
    """
    chain: list[str] = []
    source_name = name
    slash_value_name = None
    while source_name in values:
        if source_name in chain:
            raise CgwtError(
                f"value {source_name} is part of an input cycle. "
                f"Set the input of [values.{source_name}] to an input or another value."
            )
        chain.append(source_name)
        table = values[source_name]
        if "slash" in table:
            slash_value_name = source_name
        input_name = table["input"]
        assert isinstance(input_name, str)
        source_name = input_name
    if source_name not in inputs:
        raise CgwtError(
            f"value {chain[-1]} names unknown input {source_name}. "
            f"Set the input of [values.{chain[-1]}] to an input or another value."
        )
    reaches_branch = source_name == "branch"
    resolved = inputs[source_name]
    if reaches_branch:
        slash = values[slash_value_name]["slash"] if slash_value_name else "-"
        assert isinstance(slash, str)
        assert isinstance(resolved, str)
        resolved = resolved.replace("/", slash)
    elif slash_value_name:
        raise CgwtError(
            f"value {slash_value_name} sets slash but does not derive from the branch. "
            f"Remove slash from [values.{slash_value_name}]."
        )
    for value_name in reversed(chain):
        table = values[value_name]
        if "split" in table:
            separator = table["split"]
            assert isinstance(separator, str)
            if not isinstance(resolved, str):
                raise CgwtError(
                    f"value {value_name} splits a list. Remove split from [values.{value_name}]."
                )
            if not separator:
                raise CgwtError(
                    f"value {value_name} has an empty split. "
                    f"Set split to a non-empty separator in [values.{value_name}]."
                )
            resolved = tuple(resolved.split(separator))
        if "at" in table:
            index = table["at"]
            assert isinstance(index, int)
            if isinstance(resolved, str):
                raise CgwtError(
                    f"value {value_name} takes an element of a string. "
                    f"Add split to [values.{value_name}] or remove at."
                )
            try:
                resolved = resolved[index]
            except IndexError as error:
                raise CgwtError(
                    f"value {value_name} has at = {index} outside a list of {len(resolved)}. "
                    f"Set at to a valid index in [values.{value_name}]."
                ) from error
    return resolved, reaches_branch
