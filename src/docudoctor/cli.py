"""Typer CLI interface for DocuDoctor."""

from pathlib import Path
from typing import Optional
import typer
from rich.panel import Panel
from rich.prompt import Confirm

from docudoctor import __version__
from docudoctor.badge import save_project_badge
from docudoctor.doctor.generator import DocstringStyle
from docudoctor.doctor.patcher import patch_file_docstrings
from docudoctor.scanner import scan_file, scan_path
from docudoctor.ui.console import console, print_banner, print_step
from docudoctor.ui.dashboard import render_issues_table, render_project_scorecard
from docudoctor.ui.diff_view import display_code_diff

app = typer.Typer(
    name="docudoctor",
    help="DocuDoctor: AST-powered Python documentation auditor & auto-docstring engine.",
    add_completion=False,
)


@app.command()
def scan(
    path: Path = typer.Argument(
        Path("."),
        help="Directory or Python file to analyze.",
        exists=True,
    ),
    fail_under: Optional[float] = typer.Option(
        None,
        "--fail-under",
        "-f",
        help="Minimum required health score (0-100). Exits with code 1 if score is lower (useful for CI/CD).",
    ),
) -> None:
    """Audit Python files, calculate health score, and display detailed issue breakdown."""
    print_banner()

    target = path.resolve()
    print_step(f"Scanning target: [bold magenta]{target}[/bold magenta]")

    report, _ = scan_path(target)

    if report.total_files == 0:
        console.print("[bold yellow]No Python files found in target path.[/bold yellow]")
        raise typer.Exit(code=0)

    # 1. Render Top Scorecard
    render_project_scorecard(report)

    # 2. Render Issues Table
    base_dir = target if target.is_dir() else target.parent
    all_issues = [issue for f_rep in report.file_reports for issue in f_rep.issues]
    render_issues_table(all_issues, base_dir)

    # 3. Check CI fail-under threshold
    if fail_under is not None:
        if report.overall_score < fail_under:
            console.print(
                f"\n[bold red]✖ CI Check Failed:[/bold red] Overall score "
                f"[bold red]{report.overall_score}%[/bold red] is below requirement of [bold yellow]{fail_under}%[/bold yellow]."
            )
            raise typer.Exit(code=1)
        else:
            console.print(
                f"\n[bold green]✔ CI Check Passed:[/bold green] Score {report.overall_score}% meets threshold ({fail_under}%)."
            )


@app.command()
def fix(
    path: Path = typer.Argument(
        ...,
        help="Python file or folder to automatically document.",
        exists=True,
    ),
    style: DocstringStyle = typer.Option(
        DocstringStyle.GOOGLE,
        "--style",
        "-s",
        help="Docstring convention to generate: google, numpy, or sphinx.",
    ),
    use_ai: bool = typer.Option(
        False,
        "--ai",
        help="Use local Ollama LLM to synthesize docstring summaries.",
    ),
    model: str = typer.Option(
        "llama3:latest",
        "--model",
        "-m",
        help="Ollama model name if --ai is enabled.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview changes without modifying any files.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Automatically apply changes without interactive confirmation.",
    ),
) -> None:
    """Interactively generate and insert missing docstrings (Google, NumPy, or Sphinx format)."""
    print_banner()

    target = path.resolve()
    if target.is_dir():
        py_files = [
            p
            for p in target.rglob("*.py")
            if not any(part.startswith(".") or part in ("venv", "env", "build", "dist", "__pycache__") for part in p.parts)
        ]
    else:
        py_files = [target] if target.suffix == ".py" else []

    if not py_files:
        console.print("[bold yellow]No Python files found to fix.[/bold yellow]")
        raise typer.Exit(code=0)

    total_patched_functions = 0
    total_patched_files = 0

    console.print(f"[dim]Using docstring style:[/dim] [bold cyan]{style.value}[/bold cyan]")

    for file_p in py_files:
        _, functions = scan_file(file_p)
        missing_docs = [f for f in functions if not f.docstring or not f.docstring.strip()]

        if not missing_docs:
            continue

        print_step(f"Diagnosing [bold white]{file_p.name}[/bold white] ({len(missing_docs)} undocumented functions)")

        orig, patched, count = patch_file_docstrings(
            file_p, functions, style=style, use_ai=use_ai, ai_model=model
        )

        if count == 0:
            continue

        # Show visual diff
        display_code_diff(orig, patched, file_p.name)

        if dry_run:
            console.print("[dim italic]Dry-run mode enabled: file not modified.[/dim italic]\n")
            continue

        should_apply = yes or Confirm.ask(
            f"Apply this patch to [bold cyan]{file_p.name}[/bold cyan]?",
            default=True,
        )

        if should_apply:
            file_p.write_text(patched, encoding="utf-8")
            console.print(f"[bold green]✔ Successfully updated {file_p.name} ({count} docstrings added)![/bold green]\n")
            total_patched_functions += count
            total_patched_files += 1
        else:
            console.print("[dim]Skipped.[/dim]\n")

    console.print(
        f"[bold cyan]Done![/bold cyan] Patched [bold green]{total_patched_functions}[/bold green] "
        f"functions across [bold green]{total_patched_files}[/bold green] files."
    )


@app.command()
def badge(
    path: Path = typer.Argument(
        Path("."),
        help="Directory or file to audit for badge score.",
        exists=True,
    ),
    output: Path = typer.Option(
        Path("doc-health.svg"),
        "--output",
        "-o",
        help="Path where the SVG badge should be saved.",
    ),
) -> None:
    """Generate a vector SVG documentation health badge to embed in README."""
    print_banner()

    target = path.resolve()
    print_step(f"Calculating health score for: [bold magenta]{target}[/bold magenta]")

    report, _ = scan_path(target)
    out_file = output.resolve()
    save_project_badge(report, out_file)

    snippet = f"![Doc Health](./{output.name})"
    panel_msg = (
        f"[bold green]✔ SVG Badge generated successfully![/bold green]\n\n"
        f"• Saved to: [bold white]{out_file}[/bold white]\n"
        f"• Health Score: [bold cyan]{report.overall_score}%[/bold cyan]\n\n"
        f"[dim]Paste this markdown into your README.md:[/dim]\n"
        f"[bold yellow]{snippet}[/bold yellow]"
    )
    console.print(Panel(panel_msg, title="[bold cyan]Badge Export[/bold cyan]", border_style="green"))


@app.command()
def report(
    path: Path = typer.Argument(
        Path("."),
        help="Python file or folder to audit and generate report for.",
        exists=True,
    ),
    output: Path = typer.Option(
        Path("DOCUDOCTOR_REPORT.md"),
        "--output",
        "-o",
        help="Path where Markdown report should be saved.",
    ),
) -> None:
    """Generate a GitHub-ready Markdown audit report (DOCUDOCTOR_REPORT.md)."""
    from docudoctor.languages.base import LanguageAuditResult, LanguageIssue, compute_health_grade
    from docudoctor.languages.python_engine import audit_python_code
    from docudoctor.reporter import generate_markdown_report

    print_banner()
    target = path.resolve()
    print_step(f"Generating health report for: [bold magenta]{target}[/bold magenta]")

    if target.is_file():
        code = target.read_text(encoding="utf-8")
        audit_res = audit_python_code(code)
        report_content = generate_markdown_report(audit_res, filename=target.name, language="python")
    else:
        proj_report, _ = scan_path(target)
        grade, label, color = compute_health_grade(proj_report.overall_score)
        all_issues = [
            LanguageIssue(
                line=i.line_no,
                entity=i.entity_name,
                entity_type=i.entity_type,
                issue_type=str(i.issue_type.value if hasattr(i.issue_type, "value") else i.issue_type),
                severity=str(i.severity.value if hasattr(i.severity, "value") else i.severity),
                message=i.message,
                recommendation="Address defect to improve documentation health.",
            )
            for f in proj_report.file_reports
            for i in f.issues
        ]
        audit_res = LanguageAuditResult(
            score=proj_report.overall_score,
            grade=grade,
            label=label,
            color=color,
            total_functions=proj_report.total_functions,
            total_classes=proj_report.total_classes,
            documented_functions=sum(f.documented_functions for f in proj_report.file_reports),
            typed_returns=sum(f.typed_returns for f in proj_report.file_reports),
            issues=all_issues,
        )
        report_content = generate_markdown_report(audit_res, filename=target.name, language="python")

    out_file = output.resolve()
    out_file.write_text(report_content, encoding="utf-8")
    console.print(
        Panel(
            f"[bold green]✔ Report written successfully![/bold green]\n\n"
            f"• Saved to: [bold white]{out_file}[/bold white]\n"
            f"• Health Score: [bold cyan]{audit_res.score}% (Grade {audit_res.grade})[/bold cyan]\n"
            f"• Defect Count: [bold yellow]{len(audit_res.issues)} issue(s)[/bold yellow]\n\n"
            f"[dim]Attach this file to your GitHub PR or commit to your repo documentation.[/dim]",
            title="[bold cyan]Audit Report Export[/bold cyan]",
            border_style="green",
        )
    )


@app.command()
def web(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind host address."),
    port: int = typer.Option(8000, "--port", "-p", help="Bind port number."),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for development."),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Automatically open browser tab."),
) -> None:
    """Launch the interactive DocuDoctor Web Application dashboard."""
    import webbrowser
    import uvicorn

    print_banner()
    console.print(f"[bold cyan]Starting DocuDoctor Web Dashboard...[/bold cyan]")
    console.print(f"URL: [bold green]http://{host}:{port}[/bold green]\n")

    if open_browser:
        try:
            webbrowser.open(f"http://{host}:{port}")
        except Exception:
            pass

    uvicorn.run("docudoctor.web:app", host=host, port=port, reload=reload)


@app.command()
def version() -> None:
    """Show the current DocuDoctor version."""
    print_banner()
    console.print(f"[bold cyan]DocuDoctor[/bold cyan] version [bold white]{__version__}[/bold white]")


if __name__ == "__main__":
    app()
