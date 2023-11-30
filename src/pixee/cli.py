import os
import subprocess

import click
from prompt_toolkit import prompt
from prompt_toolkit.completion.filesystem import PathCompleter
from rich.console import Console

from .logo import logo2 as logo

# Enable overrides for local testing purposes
PYTHON_CODEMODDER = os.environ.get("PIXEE_PYTHON_CODEMODDER", "pixee-python-codemodder")

console = Console()


@click.group()
def main():
    console.print(logo, style="bold cyan")


@main.command()
@click.argument("path", nargs=1, required=False, type=click.Path(exists=True))
def fix(path):
    """Find and fix vulnerabilities in your project"""
    console.print("Welcome to Pixee!", style="bold")
    console.print("Let's find and fix vulnerabilities in your project.", style="bold")
    if not path:
        path = prompt(
            "Path to the project to fix: ",
            complete_while_typing=True,
            complete_in_thread=True,
            completer=PathCompleter(),
            default=os.getcwd(),
        )

    output_path = "results.codetf.json"
    subprocess.run([PYTHON_CODEMODDER, path, "--output", output_path], check=True)


@main.command()
def codemods():
    """List available codemods"""
    console.print("Available codemods:", style="bold")
    result = subprocess.run(
        [PYTHON_CODEMODDER, "--list"], stdout=subprocess.PIPE, check=True
    )
    console.print(result.stdout.decode("utf-8").splitlines())


if __name__ == "__main__":
    main()
