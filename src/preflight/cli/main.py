import sys
import importlib
import typer
from typing import Optional
from loguru import logger

# -----------------------------------------------------------------------------
# CLI Application Setup
# -----------------------------------------------------------------------------
app = typer.Typer(
    name="preflight",
    help="Pre-Flight AI: Intelligent Pre-Push Code Review Assistant",
    no_args_is_help=True,
)

# Sub-command groups
auth_app = typer.Typer(help="Manage Firebase authentication")
report_app = typer.Typer(help="View and export AI push reports")
config_app = typer.Typer(help="Manage local settings and configuration")

app.add_typer(auth_app, name="auth")
app.add_typer(report_app, name="report")
app.add_typer(config_app, name="config")

# -----------------------------------------------------------------------------
# Dynamic Module Loader (For step-by-step development)
# -----------------------------------------------------------------------------
def _run(module_path: str, function_name: str, *args, **kwargs):
    """
    Dynamically loads the sub-command logic. 
    Prevents the CLI from crashing while we build the project file-by-file.
    """
    try:
        module = importlib.import_module(module_path)
        func = getattr(module, function_name)
        func(*args, **kwargs)
    except (ImportError, AttributeError) as e:
        typer.secho(
            f"\n[Development Mode] Module '{module_path}' is not yet built!", 
            fg=typer.colors.YELLOW
        )
        typer.secho(f"Details: {e}", fg=typer.colors.RED)
        raise typer.Exit(1)

# -----------------------------------------------------------------------------
# Global Flags (--verbose, --json)
# -----------------------------------------------------------------------------
@app.callback()
def global_setup(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose debug logging"),
    json_out: bool = typer.Option(False, "--json", "-j", help="Format output as JSON"),
):
    """Global configuration applied before any command runs."""
    logger.remove()
    if verbose:
        logger.add(sys.stderr, level="DEBUG", format="<cyan>{time:HH:mm:ss}</cyan> | <level>{level}</level> | <level>{message}</level>")
    else:
        logger.add(sys.stderr, level="INFO", format="<level>{message}</level>")

# -----------------------------------------------------------------------------
# Core Root Commands
# -----------------------------------------------------------------------------
@app.command()
def setup():
    """Install and configure Pre-Flight AI for the first time."""
    _run("preflight.cli.setup_cmd", "run_setup")

@app.command()
def doctor():
    """Check system environment (Git, Ollama, Models, LSP)."""
    _run("preflight.cli.doctor_cmd", "run_doctor")

@app.command()
def enable():
    """Enable Pre-Flight AI hook in the current Git repository."""
    _run("preflight.cli.enable_cmd", "run_enable")

@app.command()
def disable():
    """Disable Pre-Flight AI hook in the current Git repository."""
    _run("preflight.cli.enable_cmd", "run_disable")

@app.command()
def sync():
    """Manually force sync local SQLite reports to Firebase Firestore."""
    _run("preflight.cli.sync_cmd", "run_sync")

@app.command()
def uninstall():
    """Completely remove Pre-Flight AI hooks and optional data."""
    _run("preflight.cli.uninstall_cmd", "run_uninstall")

@app.command("hook-run", hidden=True)
def hook_run():
    """[INTERNAL] Entry point executed by the Git Pre-Push Hook. Do not run manually."""
    _run("preflight.git.hook_entry", "run_hook")

# -----------------------------------------------------------------------------
# Auth Commands
# -----------------------------------------------------------------------------
@auth_app.command("login")
def auth_login():
    """Login via browser using Firebase Authentication."""
    _run("preflight.cli.auth_cmd", "run_login")

@auth_app.command("logout")
def auth_logout():
    """Logout and clear local credentials."""
    _run("preflight.cli.auth_cmd", "run_logout")

@auth_app.command("whoami")
def auth_whoami():
    """Show the currently authenticated developer."""
    _run("preflight.cli.auth_cmd", "run_whoami")

# -----------------------------------------------------------------------------
# Report Commands
# -----------------------------------------------------------------------------
@report_app.command("list")
def report_list(limit: int = 10):
    """List recent AI push reports from the local database."""
    _run("preflight.cli.report_cmd", "run_list", limit)

@report_app.command("show")
def report_show(report_id: str):
    """Open a specific AI report in detail."""
    _run("preflight.cli.report_cmd", "run_show", report_id)

# -----------------------------------------------------------------------------
# Config Commands
# -----------------------------------------------------------------------------
@config_app.command("view")
def config_view():
    """View current active configuration (Defaults + config.json + Env Vars)."""
    _run("preflight.cli.config_cmd", "run_view")

if __name__ == "__main__":
    app()