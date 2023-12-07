import datetime
from glob import glob
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import click
from prompt_toolkit import prompt
from prompt_toolkit.completion.filesystem import PathCompleter
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from ._version import __version__
from .logo import logo2 as logo

# Enable overrides for local testing purposes
PYTHON_CODEMODDER = os.environ.get("PIXEE_PYTHON_CODEMODDER", "pixee-python-codemodder")
JAVA_CODEMODDER = os.environ.get("PIXEE_JAVA_CODEMODDER", "pixee-java-codemodder")

CODEMODDER_MAPPING = {
    "python": (
        os.environ.get("PIXEE_PYTHON_CODEMODDER", "pixee-python-codemodder"),
        "*.py",
    ),
    "java": (
        os.environ.get("PIXEE_JAVA_CODEMODDER", "pixee-java-codemodder"),
        "*.java",
    ),
}

console = Console()


def print_logo():
    console.print(logo, style="bold cyan")


@click.group(invoke_without_command=True)
@click.version_option(__version__)
@click.pass_context
def main(ctx):
    if ctx.invoked_subcommand is None:
        print_logo()
        console.print(
            "Pixee is your automated product security engineer",
            style="bold",
        )
        console.print("Learn more at https://pixee.ai")
        console.print("Install the GitHub app at https://app.pixee.ai")
        console.print(
            "Learn more about the Codemodder framework at https://codemodder.io\n",
        )
        console.print(
            "To report bugs or request features: https://github.com/pixee/pixee-cli/issues"
        )
        console.print(f"\nCLI Version: {__version__}", style="bold", highlight=False)
        console.print("License: AGPL-3\n", style="bold", highlight=False)
        console.print(ctx.get_help(), highlight=False)


def run_codemodder(codemodder, path, dry_run):
    common_codemodder_args = ["--dry-run"] if dry_run else []

    codetf = tempfile.NamedTemporaryFile()
    subprocess.run(
        [codemodder, "--output", codetf.name, path] + common_codemodder_args,
        stderr=subprocess.DEVNULL,
        check=True,
    )

    return codetf


@main.command()
def triage():
    """Coming soon!"""
    print_logo()
    console.print("Coming soon!", style="bold")


@main.command()
@click.argument("path", nargs=1, required=False, type=click.Path(exists=True))
@click.option("--dry-run", is_flag=True, help="Don't write changes to disk")
@click.option(
    "--language",
    type=click.Choice(["python", "java"]),
    help="Restrict to a single language",
)
@click.option("--output", type=click.Path(), help="Output CodeTF file path")
@click.option("--list-codemods", is_flag=True, help="List available codemods and exit")
@click.option(
    "--explain",
    is_flag=True,
    help="Interactively explain codemodder results (experimental)",
)
def fix(path, dry_run, language, output, list_codemods, explain):
    """Find problems and harden your code"""
    if list_codemods:
        return codemods()

    print_logo()
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

    console.print("Dry run:", dry_run, style="bold")

    combined_codetf = {
        "vendor": "pixee",
        "tool": "pixee-cli",
        "version": __version__,
        "commandLine": " ".join(sys.argv),
        "elapsed": 0,
        "results": [],
    }

    start = datetime.datetime.now()

    for lang, (codemodder, file_glob) in CODEMODDER_MAPPING.items():
        if language and lang != language:
            continue

        if glob(str(Path(path) / "**" / file_glob), recursive=True):
            console.print(f"Running {lang} codemods...", style="bold")
            lang_codetf = run_codemodder(codemodder, path, dry_run)
            results = json.load(lang_codetf)
            combined_codetf["results"].extend(results["results"])

    elapsed = datetime.datetime.now() - start
    combined_codetf["elapsed"] = int(elapsed.total_seconds() * 1000)

    if explain:
        for result in combined_codetf["results"]:
            name = result["codemod"]
            summary = result["summary"]
            description = result["description"]
            console.print(f"{summary} ({name})", style="bold")
            console.print(Markdown(description))
            prompt("Press Enter to see the updated files")
            for entry in result["changeset"]:
                console.print(f"File: {entry['path']}", style="bold")
                console.print(Markdown(f"```diff\n{entry['diff']}```"))
            prompt("Press Enter to continue...")

    result_file = Path(output or "results.codetf.json")

    Path(result_file).write_text(json.dumps(combined_codetf, indent=2))
    console.print(f"Results written to {result_file}", style="bold")

    summarize_results(combined_codetf)


def summarize_results(combined_codetf):
    results = [
        result for result in combined_codetf["results"] if len(result["changeset"])
    ]
    if not len(results):
        console.print("No changes applied", style="bold")
        return

    console.print(f"Applied the following {len(results)} codemods:", style="bold")
    table = Table(show_header=True, header_style="bold")
    table.add_column("Codemod", style="dim")
    table.add_column("Summary", style="bold")
    table.add_column("# Files Changed")

    for result in results:
        table.add_row(
            result["codemod"],
            result["summary"],
            str(len(result["changeset"])),
        )
    console.print(table)


def codemods():
    """List available codemods"""
    console.print("Available codemods:", style="bold")

    codemods = []
    for codemodder in [PYTHON_CODEMODDER, JAVA_CODEMODDER]:
        result = subprocess.run(
            [codemodder, "--list"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        codemods.extend(result.stdout.decode("utf-8").splitlines())
    # TODO: filter out non-pixee codemods?
    console.print(sorted(codemods))


if __name__ == "__main__":
    main()
