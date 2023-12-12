import datetime
from functools import lru_cache, total_ordering
from glob import glob
import json
import os
from pathlib import Path
import subprocess
import sys
import re
import tempfile

import click
from prompt_toolkit import prompt
from prompt_toolkit.completion.filesystem import PathCompleter
from rich.console import Console
from rich.markdown import Markdown
from rich.progress import Progress
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


@total_ordering
class Codemod:
    def __init__(self, org: str, language: str, name: str):
        self.org = org
        self.language = language
        self.name = name

    @classmethod
    def from_string(cls, codemod: str):
        parsed = re.match(r"(.*):(.*)/(.*)", codemod)
        assert parsed
        return cls(parsed.group(1), parsed.group(2), parsed.group(3))

    def __str__(self):
        return f"{self.org}:{self.language}/{self.name}"

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        return str(self) == str(other)

    def __lt__(self, other):
        return str(self) < str(other)


def validate_codemods(ctx, param, value) -> list[str]:
    del ctx, param

    if not value:
        return value

    available_codemods = codemods()
    available_codemod_ids = {str(codemod) for codemod in available_codemods}
    available_codemod_names = {codemod.name for codemod in available_codemods}
    given_codemods: list[str] = [codemod for codemod in value.split(",") if codemod]
    for codemod in given_codemods:
        if (
            codemod not in available_codemod_ids
            and codemod not in available_codemod_names
        ):
            raise click.BadParameter(
                f"Unknown codemod: {codemod}\nUse --list-codemods to see available codemods"
            )
    return given_codemods


def print_logo():
    lines = logo.split("\n")
    top_lines, bottom_lines = lines[: len(lines) // 2], lines[len(lines) // 2 :]
    for line in top_lines:
        console.print(line[:24], style="bold orange1", end="")
        console.print(line[24:], style="bold cyan")
    for line in bottom_lines:
        console.print(line[:24], style="bold salmon1", end="")
        console.print(line[24:], style="bold blue")


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


def run_codemodder(
    language: str,
    codemodder: str,
    path,
    codemods: list[Codemod],
    dry_run: bool,
    verbose: int,
):
    common_codemodder_args = ["--dry-run"] if dry_run else []
    common_codemodder_args.extend(["--codemod-include", ",".join(map(str, codemods))])
    if verbose == 0 or verbose > 1:
        common_codemodder_args.append("--verbose")

    codetf = tempfile.NamedTemporaryFile()

    num_codemods = len(codemods)

    with Progress(disable=bool(verbose)) as progress:
        task = progress.add_task(
            f"Applying {num_codemods} {language} codemods",
            total=num_codemods,
        )
        command = subprocess.Popen(
            [codemodder, "--output", codetf.name, path] + common_codemodder_args,
            stderr=subprocess.DEVNULL,
            stdout=subprocess.PIPE if not verbose else None,
        )
        if command.stdout:
            for line in iter(command.stdout.readline, b""):
                if line.startswith(b"running codemod"):
                    progress.advance(task)
        command.wait()
        progress.update(task, completed=num_codemods)

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
    "--codemod-include",
    callback=validate_codemods,
    help="Comma-separated list of codemods to run",
)
@click.option(
    "--codemod-exclude",
    callback=validate_codemods,
    help="Comma-separated list of codemods to skip",
)
@click.option(
    "--explain",
    is_flag=True,
    help="Interactively explain codemodder results (experimental)",
)
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Verbose output (repeat for more verbosity)",
)
def fix(
    path,
    dry_run,
    language,
    output,
    list_codemods,
    explain,
    verbose,
    codemod_include,
    codemod_exclude,
):
    """Find problems and harden your code"""
    if list_codemods:
        console.print("Available codemods:", style="bold")
        console.print(sorted(codemods()))
        return

    print_logo()
    console.print("Welcome to Pixee!", style="bold")
    console.print("Let's find problems and harden your code.", style="bold")
    if not path:
        path = prompt(
            "Path to the project to fix: ",
            complete_while_typing=True,
            complete_in_thread=True,
            completer=PathCompleter(),
            default=os.getcwd(),
        )

    console.print("Dry run:", dry_run, style="bold")
    console.print(
        "No changes will be written to disk"
        if dry_run
        else "Changes will be written to disk",
        style="bold",
    )

    combined_codetf = {
        "vendor": "pixee",
        "tool": "pixee-cli",
        "version": __version__,
        "commandLine": " ".join(sys.argv),
        "elapsed": 0,
        "results": [],
    }

    start = datetime.datetime.now()

    all_codemods = codemods()
    if codemod_include:
        all_codemods = [
            codemod
            for codemod in all_codemods
            if str(codemod) in codemod_include or codemod.name in codemod_include
        ]

    for lang, (codemodder, file_glob) in CODEMODDER_MAPPING.items():
        if language and lang != language:
            continue

        codemods_by_lang = [
            codemod for codemod in all_codemods if codemod.language == lang
        ]
        if not codemods_by_lang:
            continue

        if glob(str(Path(path) / "**" / file_glob), recursive=True):
            lang_codetf = run_codemodder(
                lang,
                codemodder,
                path,
                codemods_by_lang,
                dry_run,
                verbose,
            )
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

    console.print(f"Found and fixed the following {len(results)} issues:", style="bold")
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


@lru_cache()
def list_codemods(codemodder: str):
    result = subprocess.run(
        [codemodder, "--list"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    return result.stdout.decode("utf-8").splitlines()


@lru_cache(maxsize=1)
def codemods() -> list[Codemod]:
    """List available codemods"""

    codemods = []
    for codemodder in [PYTHON_CODEMODDER, JAVA_CODEMODDER]:
        result = list_codemods(codemodder)
        codemods.extend(result)
    # TODO: filter out non-pixee codemods?
    return [Codemod.from_string(codemod) for codemod in codemods]


if __name__ == "__main__":
    main()
