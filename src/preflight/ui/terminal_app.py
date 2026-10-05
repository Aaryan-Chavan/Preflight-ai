from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.prompt import Confirm
from loguru import logger

from preflight.core.models import Report, Decision, RiskLevel

console = Console()

def show_review_ui(report: Report) -> Decision:
    console.print("\n")
    
    # 1. Color mapping based on AI Risk Level
    if getattr(report.popup.risk_level, "name", str(report.popup.risk_level)) in ("UNKNOWN", "UNAVAILABLE"):
        border_color = "dim"
        risk_text = "[bold dim]UNAVAILABLE[/bold dim]"
        default_choice = True
    elif report.popup.risk_level == RiskLevel.LOW:
        border_color = "green"
        risk_text = "[bold green]LOW RISK[/bold green]"
        default_choice = True
    elif report.popup.risk_level == RiskLevel.MEDIUM:
        border_color = "yellow"
        risk_text = "[bold yellow]MEDIUM RISK[/bold yellow]"
        default_choice = False
    else:
        border_color = "red"
        risk_text = "[bold red]HIGH RISK[/bold red]"
        default_choice = False

    # 2. Build the Metadata Table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Property", style="cyan", justify="right")
    table.add_column("Value")

    table.add_row("Risk Level:", risk_text)
    table.add_row("AI Confidence:", f"[bold]{report.popup.confidence_percentage}%[/bold]")
    table.add_row("Target Branch:", f"[magenta]{report.meta.branch}[/magenta]")
    table.add_row("Analysis Time:", f"{report.meta.analysis_ms}ms")
    
    # 3. Format the Verification Checklist (formerly key_concerns)
    concerns_text = Text()
    if report.popup.verification_checklist:
        for item in report.popup.verification_checklist:
            concerns_text.append(f"• [ ] {item}\n")
    else:
        concerns_text.append("None detected. Code looks clean!\n", style="green")

    # Safely extract the impact summary (handling both lists and strings)
    impact = "\n".join(report.popup.impact_summary) if isinstance(report.popup.impact_summary, list) else str(report.popup.impact_summary)

    # 4. Assemble the Panels
    header_panel = Panel(
        table,
        title="[bold]✈️  Pre-Flight AI Code Review[/bold]",
        subtitle="[italic]Local Analysis[/italic]",
        border_style=border_color,
        expand=False
    )
    
    content_panel = Panel(
        f"{impact}\n\n[bold cyan]Verification Checklist:[/bold cyan]\n{concerns_text}",
        border_style="dim",
        expand=False
    )

    # 5. Render to Terminal
    console.print(header_panel)
    console.print(content_panel)
    
    # 6. Interactive Prompt (Blocking)
    try:
        console.print("\n")
        proceed = Confirm.ask(
            "[bold]Do you want to proceed with this Git push?[/bold]",
            default=default_choice
        )
        return Decision.CONTINUE if proceed else Decision.CANCEL
        
    except KeyboardInterrupt:
        logger.info("Developer aborted via KeyboardInterrupt.")
        console.print("\n[bold red]Push aborted by user.[/bold red]")
        return Decision.CANCEL