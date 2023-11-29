from argparse import ArgumentParser, Namespace
import os
import subprocess

from prompt_toolkit import prompt
from prompt_toolkit.completion.filesystem import PathCompleter
from rich.console import Console

from .logo import logo2 as logo

# Enable overrides for local testing purposes
PYTHON_CODEMODDER = os.environ.get("PIXEE_PYTHON_CODEMODDER", "pixee-python-codemodder")


def run_fix(console: Console, args: Namespace):
    console.print("Welcome to Pixee!", style="bold")
    console.print("Let's find and fix vulnerabilities in your project.", style="bold")
    if not args.path:
        args.path = prompt(
            "Path to the project to fix: ",
            complete_while_typing=True,
            complete_in_thread=True,
            completer=PathCompleter(),
            default=os.getcwd(),
        )

    output_path = "results.codetf.json"
    subprocess.run([PYTHON_CODEMODDER, args.path, "--output", output_path], check=True)


def main():
    console = Console()
    console.print(logo, style="bold cyan")

    parser = ArgumentParser(description="Pixee CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    fix = subparsers.add_parser("fix", help="Find and fix vulnerabilities")
    fix.add_argument("path", nargs="?", help="Path to the project to fix")

    subparsers.add_parser("triage", help="Triage findings")
    subparsers.add_parser("remediate", help="Fix vulnerabilities from external tools")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    match args.command:
        case "fix":
            run_fix(console, args)


if __name__ == "__main__":
    main()
