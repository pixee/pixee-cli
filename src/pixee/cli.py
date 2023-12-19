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
from questionary import select, press_any_key_to_continue
from rich.console import Console
from rich.markdown import Markdown
from rich.progress import Progress
from rich.table import Table

from ._version import __version__
from .logo import logo2 as logo
from security import safe_command

# Enable overrides for local testing purposes
PYTHON_CODEMODDER = os.environ.get("PIXEE_PYTHON_CODEMODDER", "pixee-python-codemods")
JAVA_CODEMODDER = os.environ.get("PIXEE_JAVA_CODEMODDER", "pixee-java-codemods")

CODEMODDER_MAPPING = {
    "python": (PYTHON_CODEMODDER, "*.py"),
    "java": (JAVA_CODEMODDER, "*.java"),
}

# It's not ideal for the CLI to have to encode this information but it's necessary for now
DEFAULT_EXCLUDED_CODEMODS = {
    "pixee:python/unused-imports",
    "pixee:python/order-imports",
}

DEFAULT_CODETF_PATH = "results.codetf.json"


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


def parse_path_patterns(ctx, param, value) -> list[str]:
    del ctx, param

    if not value:
        return value

    return value.split(",")


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
    path_include: list[str],
    path_exclude: list[str],
    dry_run: bool,
    verbose: int,
):
    common_codemodder_args = ["--dry-run"] if dry_run else []
    common_codemodder_args.extend(["--codemod-include", ",".join(map(str, codemods))])
    if path_include:
        common_codemodder_args.extend(["--path-include", ",".join(path_include)])
    if path_exclude:
        common_codemodder_args.extend(["--path-exclude", ",".join(path_exclude)])
    if verbose == 0 or verbose > 1:
        common_codemodder_args.append("--verbose")

    num_codemods = len(codemods)

    with tempfile.NamedTemporaryFile() as codetf:
        with Progress(disable=bool(verbose)) as progress:
            task = progress.add_task(
                f"Applying {num_codemods} {language} codemods",
                total=num_codemods,
            )
            command = safe_command.run(
                subprocess.Popen,
                [codemodder, "--output", codetf.name, path] + common_codemodder_args,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE if not verbose else None,
            )
            if command.stdout:
                for line in iter(command.stdout.readline, b""):
                    if line.startswith(b"running codemod"):
                        progress.advance(task)
            command.wait()
            if command.returncode != 0:
                console.print(
                    f"Error running codemodder: {codemodder} (exit code {command.returncode})"
                )
                if command.stderr:
                    console.print(command.stderr.read().decode("utf-8"))
                sys.exit(1)

            progress.update(task, completed=num_codemods)
            return json.load(codetf)


@main.command()
def triage():
    """Coming soon!"""
    print_logo()
    console.print("Coming soon!", style="bold")


@main.command()
@click.argument("path", nargs=1, required=False, type=click.Path(exists=True))
@click.option("--apply-fixes", is_flag=True, help="Apply changes to files")
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
    "--path-include",
    callback=parse_path_patterns,
    help="Comma-separated list of path patterns to include",
)
@click.option(
    "--path-exclude",
    callback=parse_path_patterns,
    help="Comma-separated list of path patterns to exclude",
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
    apply_fixes,
    language,
    output,
    list_codemods,
    explain,
    verbose,
    codemod_include,
    codemod_exclude,
    path_include,
    path_exclude,
):
    """Find problems and harden your code"""
    if list_codemods:
        console.print("Available codemods:", style="bold")
        console.print(sorted(codemods()))
        return

    if codemod_include and codemod_exclude:
        raise click.BadArgumentUsage(
            "Cannot specify both --codemod-include and --codemod-exclude"
        )

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

    console.print(
        "Changes will be written to disk"
        if apply_fixes
        else "No changes will be written to disk (use --apply-fixes to make changes)",
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
    # Validation occurs above to ensure this is mutually exclusive
    if codemod_exclude:
        all_codemods = [
            codemod
            for codemod in all_codemods
            if str(codemod) not in codemod_exclude
            and codemod.name not in codemod_exclude
        ]
    elif not codemod_include:
        all_codemods = [
            codemod
            for codemod in all_codemods
            if str(codemod) not in DEFAULT_EXCLUDED_CODEMODS
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
            results = run_codemodder(
                lang,
                codemodder,
                path,
                codemods_by_lang,
                path_include,
                path_exclude,
                not apply_fixes,
                verbose,
            )
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

    result_file = Path(output or DEFAULT_CODETF_PATH)

    Path(result_file).write_text(json.dumps(combined_codetf, indent=2))
    console.print(f"Results written to {result_file}", style="bold")

    summarize_results(combined_codetf)


@main.command()
@click.argument("path", nargs=1, required=False, type=click.Path(exists=True))
def explain(path):
    """
    Interactively explain codemodder results (use after fix)

    Reads the results file from the fix command and allows you to interactively
    explain the changes made by a specific codemod.

    By default, the results file is assumed to be `results.codetf.json` in the
    current directory. You can specify a different path with the `path` argument.

    Run `pixee fix` first to generate the results file.
    """
    result_file = Path(path or DEFAULT_CODETF_PATH)
    if not result_file.exists():
        raise click.BadParameter(f"Could not find results file {DEFAULT_CODETF_PATH}")

    try:
        combined_codetf = json.loads(result_file.read_text())
    except json.JSONDecodeError:
        console.print(f"Could not parse results file: {result_file}", style="bold")
        return 1

    results = [
        result for result in combined_codetf["results"] if len(result["changeset"])
    ]

    console.print(f"Reading results from `{result_file}`", style="bold")
    summarize_results(combined_codetf)
    codemod = select(
        "Which codemod result would you like to explain?",
        choices=[result["codemod"] for result in results],
    ).ask()

    result = next(result for result in results if result["codemod"] == codemod)

    name = result["codemod"]
    summary = result["summary"]
    description = result["description"]
    console.print(f"{summary} ({name})", style="bold")
    console.print(Markdown(description))

    filename = select(
        "Which file change would you like to see?",
        choices=[entry["path"] for entry in result["changeset"]],
    ).ask()

    entry = next(entry for entry in result["changeset"] if entry["path"] == filename)
    console.print(f"\n\nFile: {entry['path']}", style="bold")
    console.print(Markdown(f"```diff\n{entry['diff']}```"))

    return 0


def summarize_results(combined_codetf):
    results = [
        result for result in combined_codetf["results"] if len(result["changeset"])
    ]
    if not len(results):
        console.print("No changes applied", style="bold")
        return

    console.print(
        f"Found {len(results)} opportunities to harden and improve your code:",
        style="bold",
    )
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
    console.print(
        "To experience the full benefits of automated code hardening via pull requests, install the Pixeebot GitHub app at https://app.pixee.ai"
    )


@lru_cache()
def list_codemods(codemodder: str):
    result = safe_command.run(
        subprocess.run,
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
