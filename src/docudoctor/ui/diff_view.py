"""Syntax-highlighted diff viewer for inspecting proposed docstring patches."""

import difflib
from rich.panel import Panel
from rich.text import Text

from docudoctor.ui.console import console


def display_code_diff(original_code: str, modified_code: str, file_name: str) -> None:
    """Displays a git-style colorized unified diff in the terminal."""
    orig_lines = original_code.splitlines(keepends=True)
    mod_lines = modified_code.splitlines(keepends=True)

    diff = list(
        difflib.unified_diff(
            orig_lines,
            mod_lines,
            fromfile=f"a/{file_name}",
            tofile=f"b/{file_name}",
            lineterm="\n",
        )
    )

    if not diff:
        console.print("[dim]No textual differences.[/dim]")
        return

    diff_text = Text()
    for line in diff:
        # line already ends with newline
        if line.startswith("+++") or line.startswith("---"):
            diff_text.append(line, style="bold white")
        elif line.startswith("@@"):
            diff_text.append(line, style="bold cyan")
        elif line.startswith("+"):
            diff_text.append(line, style="bold green")
        elif line.startswith("-"):
            diff_text.append(line, style="bold red")
        else:
            diff_text.append(line, style="dim grey70")

    console.print(
        Panel(
            diff_text,
            title=f"[bold cyan]Proposed Patch Preview: {file_name}[/bold cyan]",
            border_style="cyan",
            expand=False,
        )
    )
