import typer
from rich.console import Console

from preflight.cli.doctor_cmd import run_doctor
from preflight.config.paths import ensure_directories

console = Console()

def run_setup():
    """
    Orchestrates the entire installation process.
    Ensures idempotency (can be run multiple times safely).
    """
    console.print("[bold blue]Starting Pre-Flight AI Setup...[/bold blue]\n")

    # 1. Ensure basic application directories exist (Config, Data, Logs, Hooks)
    try:
        ensure_directories()
    except Exception as e:
        console.print(f"[bold red]❌ Failed to create application directories: {e}[/bold red]")
        raise typer.Exit(1)

    # 2. Run system diagnostics
    console.print("[bold]Step 1: System Diagnostics[/bold]")
    run_doctor()

    # 3. Generate Installation ID (M2)
    console.print("\n[bold]Step 2: Device Initialization[/bold]")
    try:
        from preflight.installer.install_id import generate_and_save_install_id
        install_id = generate_and_save_install_id()
        console.print(f"✅ [green]Device Installation ID:[/green] {install_id}")
    except ImportError:
        console.print("⚠️  [yellow][Development] Skipping ID generation (install_id.py not built yet).[/yellow]")

    # 4. Database Setup (M1)
    console.print("\n[bold]Step 3: Database Initialization[/bold]")
    try:
        from preflight.storage.db import initialize_database
        initialize_database()
        console.print("✅ [green]Local SQLite database initialized (WAL mode active).[/green]")
    except ImportError:
        console.print("⚠️  [yellow][Development] Skipping database init (storage/db.py not built yet).[/yellow]")

    # 5. Global Git Hook Installation (M2)
    console.print("\n[bold]Step 4: Git Pre-Push Hook Installation[/bold]")
    try:
        from preflight.installer.hook_installer import install_global_hook
        install_global_hook()
        console.print("✅ [green]Global Git pre-push hook installed successfully.[/green]")
    except ImportError:
        console.print("⚠️  [yellow][Development] Skipping Git hook installation (hook_installer.py not built yet).[/yellow]")

    # 6. Authentication (M3)
    console.print("\n[bold]Step 5: Cloud Authentication[/bold]")
    try:
        from preflight.cli.auth_cmd import run_login
        run_login()
    except ImportError:
        console.print("⚠️  [yellow][Development] Skipping browser authentication (auth_cmd.py not built yet).[/yellow]")
    
    console.print("\n[bold green]✅ Pre-Flight AI Setup Complete![/bold green]")
    console.print("You can now run [bold cyan]preflight enable[/bold cyan] inside any Git repository to activate the AI assistant.")