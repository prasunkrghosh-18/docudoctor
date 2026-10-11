"""Visual dashboards, scorecards, and formatted tables for DocuDoctor."""

from pathlib import Path
from typing import List

from rich import box
from rich.columns import Columns
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from docudoctor.models import CodeIssue, ProjectReport, Severity
from docudoctor.ui.console import console


def _get_health_grade(score: float) -> tuple[str, str, str]:
    """Returns (Grade, Label, Color) based on score."""
    if score >= 90:
        return "A", "EXCELLENT", "bold green"
    elif score >= 75:
        return "B", "HEALTHY", "bold cyan"
    elif score >= 50:
        return "C", "FAIR", "bold yellow"
    elif score >= 30:
        return "D", "NEEDS WORK", "bold yellow"
    else:
        return "F", "CRITICAL", "bold red"


def _render_progress_bar(percentage: float, width: int = 24) -> str:
    """Render a clean progress bar."""
    filled = int(round((percentage / 100.0) * width))
    empty = max(0, width - filled)
    return f"[bold cyan]{'#' * filled}[/bold cyan][dim grey50]{'-' * empty}[/dim grey50]"


def render_project_scorecard(report: ProjectReport) -> None:
    """Renders the top-level visual health scorecard for the project."""
    score = report.overall_score
    grade, label, color = _get_health_grade(score)
    bar = _render_progress_bar(score, width=20)

    # Left Column: Big Score display
    score_content = Text()
    score_content.append(f"\n   Grade {grade}\n", style=f"{color} bold")
    score_content.append(f"   {score}/100\n", style="bold white")
    score_content.append(f"   [{label}]\n", style=color)

    score_panel = Panel(
        score_content,
        title="[bold cyan]Doc Health[/bold cyan]",
        border_style=color.split()[-1],
        width=24,
    )

    # Right Column: Key Metrics
    total_funcs = report.total_functions
    doc_funcs = sum(f.documented_functions for f in report.file_reports)
    func_pct = round((doc_funcs / total_funcs * 100), 1) if total_funcs > 0 else 100.0

    typed_ret = sum(f.typed_returns for f in report.file_reports)
    ret_pct = round((typed_ret / total_funcs * 100), 1) if total_funcs > 0 else 100.0

    metrics_text = Text()
    metrics_text.append(f"\n  Progress:  [{bar}]  [bold white]{score}%[/bold white]\n\n")
    metrics_text.append(f"  * Files Scanned:       [bold white]{report.total_files}[/bold white]\n")
    metrics_text.append(
        f"  * Functions / Methods: [bold white]{total_funcs}[/bold white]  "
        f"([cyan]{doc_funcs}/{total_funcs} documented - {func_pct}%[/cyan])\n"
    )
    metrics_text.append(
        f"  * Return Type Hints:   [bold white]{typed_ret}/{total_funcs}[/bold white] "
        f"([magenta]{ret_pct}% typed[/magenta])\n"
    )
    metrics_text.append(f"  * Issues Detected:     [bold yellow]{report.total_issues}[/bold yellow]\n")

    metrics_panel = Panel(
        metrics_text,
        title="[bold cyan]Audit Overview[/bold cyan]",
        border_style="cyan",
        expand=True,
    )

    console.print(Columns([score_panel, metrics_panel], equal=False))


def render_issues_table(issues: List[CodeIssue], base_dir: Path) -> None:
    """Renders a sleek, clean table of detected issues."""
    if not issues:
        console.print(
            Panel(
                "[bold green][OK] No documentation defects found! Your code is fully documented and typed.[/bold green]",
                border_style="green",
            )
        )
        return

    table = Table(
        title="[bold white]Detected Documentation & Typing Defects[/bold white]",
        box=box.ROUNDED,
        header_style="bold cyan",
        show_lines=True,
        expand=True,
    )

    table.add_column("Sev", justify="center", no_wrap=True)
    table.add_column("Location", style="dim", no_wrap=True)
    table.add_column("Type", style="magenta", no_wrap=True)
    table.add_column("Target", style="bold cyan", no_wrap=True)
    table.add_column("Issue & Recommendation", style="white", ratio=1)

    severity_icons = {
        Severity.ERROR: "[bold red][ERR][/bold red]",
        Severity.WARNING: "[bold yellow][WRN][/bold yellow]",
        Severity.INFO: "[bold cyan][INF][/bold cyan]",
    }

    for issue in issues:
        try:
            rel_path = issue.file_path.relative_to(base_dir)
        except ValueError:
            rel_path = issue.file_path

        location_str = f"{rel_path}:{issue.line_no}"
        sev_icon = severity_icons.get(issue.severity, "[bold white][--][/bold white]")

        table.add_row(
            sev_icon,
            location_str,
            issue.entity_type,
            issue.entity_name,
            issue.message,
        )

    console.print(table)
