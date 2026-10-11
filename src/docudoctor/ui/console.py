"""Terminal console setup, custom themes, and visual branding."""

import sys
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme

# Ensure Windows consoles support UTF-8 characters cleanly
if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Custom modern theme
custom_theme = Theme(
    {
        "info": "dim cyan",
        "warning": "bold yellow",
        "danger": "bold red",
        "success": "bold green",
        "primary": "bold magenta",
        "accent": "bold cyan",
        "muted": "dim grey70",
    }
)

console = Console(theme=custom_theme, safe_box=True)


def print_banner() -> None:
    """Prints a sleek, modern header banner for DocuDoctor."""
    banner_text = Text()
    banner_text.append("[+] DOCU", style="bold cyan")
    banner_text.append("DOCTOR", style="bold magenta")
    banner_text.append("  |  AST Code Health & Docstring Engine", style="dim white")

    panel = Panel(
        banner_text,
        border_style="cyan",
        padding=(0, 2),
        subtitle="[dim]v0.1.0[/dim]",
        subtitle_align="right",
    )
    console.print(panel)


def print_step(title: str) -> None:
    """Print a styled section step indicator."""
    console.print(f"\n[bold cyan]>[/bold cyan] [bold white]{title}[/bold white]")
