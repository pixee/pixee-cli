from glob import glob
import os
from pathlib import Path
import subprocess
import tempfile

import click
from prompt_toolkit import prompt
from prompt_toolkit.completion.filesystem import PathCompleter
from rich.console import Console

from .logo import logo2 as logo

# Enable overrides for local testing purposes
PYTHON_CODEMODDER = os.environ.get("PIXEE_PYTHON_CODEMODDER", "pixee-python-codemodder")
JAVA_CODEMODDER = os.environ.get("PIXEE_JAVA_CODEMODDER", "pixee-java-codemodder")

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

    python_codetf = tempfile.NamedTemporaryFile()
    # TODO: better file glob patterns
    if python_files := glob(str(Path(path) / "**" / "*.py"), recursive=True):
        console.print("Running Python codemods...", style="bold")
        subprocess.run(
            [PYTHON_CODEMODDER, "--output", python_codetf.name, path], check=True
        )

    java_codetf = tempfile.NamedTemporaryFile()
    if java_files := glob(str(Path(path) / "**" / "*.java"), recursive=True):
        console.print("Running Java codemods...", style="bold")
        subprocess.run(
            [JAVA_CODEMODDER, "--output", java_codetf.name, path], check=True
        )


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
