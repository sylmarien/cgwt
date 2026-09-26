"""Command-line entry point."""

import argparse
import json
import sys
from importlib.metadata import version

from cgwt.create import create_command
from cgwt.errors import CgwtError

CREATE_EPILOG = """exit codes:
  1  failure: configuration error, missing origin, failed git command
  2  usage error
  5  the branch is checked out in another worktree
  6  path collision"""


def build_parser() -> argparse.ArgumentParser:
    """Build the parser; each command binds its handler with `set_defaults(command=...)`."""
    parser = argparse.ArgumentParser(prog="cgwt", description="Manage git worktrees.")
    parser.add_argument("--version", action="version", version=f"cgwt {version('cgwt')}")
    subparsers = parser.add_subparsers(required=True, metavar="command")
    create_parser = subparsers.add_parser(
        "create",
        help="Create a worktree for a branch.",
        description="Create a worktree for a branch.",
        epilog=CREATE_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    create_parser.add_argument("branch")
    create_parser.add_argument("--base", metavar="ref")
    create_parser.add_argument("--no-fetch", action="store_true")
    create_parser.add_argument("--repo", metavar="path")
    create_parser.add_argument("--json", action="store_true")
    create_parser.set_defaults(command=create_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the cgwt command line."""
    args = build_parser().parse_args(argv)
    try:
        output = args.command(args)
    except CgwtError as error:
        print(f"cgwt: error: {error.message}", file=sys.stderr)
        return error.exit_code
    if args.json:
        print(json.dumps(output.value, indent=2 if sys.stdout.isatty() else None))
    elif output.text:
        print(output.text)
    return 0
