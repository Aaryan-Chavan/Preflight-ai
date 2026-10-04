import sys
import shutil
import subprocess
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table

from preflight.config.paths import DATA_DIR, ensure_directories
from preflight.config.settings import settings

console = Console()

def _check_binary(name: str) -> bool:
    """Safely check if a command-line tool is installed and available in the PATH."""
    return shutil.which(name) is not None

def _run_cmd(cmd: list) -> tuple[bool, str]:
    """Execute a shell command with a timeout, returning success status and output."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, result.stderr.strip()
    except Exception as e:
        return False, str(e)

def run_doctor():
    """
    Executes the system environment diagnostic check.
    Ensures all critical dependencies are met before installation.
    """
    console.print("\n[bold cyan]✈️  Pre-Flight AI System Doctor[/bold cyan]\n")
    
    # Initialize the diagnostic table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Component", width=25)
    table.add_column("Status", justify="center", width=10)
    table.add_column("Details & Fix Hints")

    all_passed = True

    # 1. OS & Python Check
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 12):
        table.add_row("Python", "[green]PASS[/green]", f"v{py_version} (Required >= 3.12)")
    else:
        table.add_row("Python", "[red]FAIL[/red]", f"v{py_version} installed. Please upgrade to 3.12+")
        all_passed = False

    # 2. Write Permissions Check
    try:
        ensure_directories()
        test_file = DATA_DIR / ".doctor_test"
        test_file.touch()
        test_file.unlink()
        table.add_row("Permissions", "[green]PASS[/green]", f"Read/Write access to {DATA_DIR}")
    except Exception as e:
        table.add_row("Permissions", "[red]FAIL[/red]", f"Cannot write to app data: {e}")
        all_passed = False

    # 3. Git CLI Check
    if _check_binary("git"):
        _, version = _run_cmd(["git", "--version"])
        table.add_row("Git CLI", "[green]PASS[/green]", version)
    else:
        table.add_row("Git CLI", "[red]FAIL[/red]", "Git not found in PATH. Please install Git.")
        all_passed = False

    # 4. Ollama & AI Model Check
    if _check_binary("ollama"):
        _, version = _run_cmd(["ollama", "--version"])
        table.add_row("Ollama Engine", "[green]PASS[/green]", version)
        
        # Verify the specific required models exist locally
        success, models = _run_cmd(["ollama", "list"])
        if success and settings.llm_model_name in models:
            table.add_row("Primary AI Model", "[green]PASS[/green]", f"'{settings.llm_model_name}' is downloaded")
        elif success and settings.llm_fallback_model in models:
            table.add_row("AI Model", "[yellow]WARN[/yellow]", f"Primary missing. Fallback '{settings.llm_fallback_model}' found")
        else:
            table.add_row("AI Model", "[red]FAIL[/red]", f"Missing. Run: ollama pull {settings.llm_model_name}")
            all_passed = False
    else:
        table.add_row("Ollama Engine", "[red]FAIL[/red]", "Ollama not found. Install from ollama.com")
        table.add_row("AI Model", "[red]FAIL[/red]", "Ollama is required to pull the AI models.")
        all_passed = False

    # 5. Static Analysis Tools (MVP)
    tools = [
        ("ruff", "Ruff (Python)"), 
        ("semgrep", "Semgrep (Security)"), 
        ("eslint", "ESLint (JS/TS)")
    ]
    for cmd, name in tools:
        if _check_binary(cmd):
            table.add_row(name, "[green]PASS[/green]", f"Found in PATH")
        else:
            table.add_row(name, "[yellow]WARN[/yellow]", f"Missing '{cmd}'. Will degrade gracefully during analysis.")

    # 6. LSP Servers (MVP)
    lsps = [
        ("pyright-langserver", "Pyright (Python)"), 
        ("typescript-language-server", "TS LSP (JS/TS)")
    ]
    for cmd, name in lsps:
        if _check_binary(cmd):
            table.add_row(name, "[green]PASS[/green]", f"Found in PATH")
        else:
            table.add_row(name, "[yellow]WARN[/yellow]", f"Missing '{cmd}'. Will fallback to AST import graphs.")

    # Render table to terminal
    console.print(table)
    
    # Final Verdict
    if all_passed:
        console.print("\n[bold green]✅ System is healthy and ready for Pre-Flight AI setup![/bold green]\n")
    else:
        console.print("\n[bold red]❌ System check failed. Please resolve the red errors above before running 'preflight setup'.[/bold red]\n")
        raise typer.Exit(1)