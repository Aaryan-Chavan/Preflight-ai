import json
import base64
import typer
from rich.console import Console

from preflight.auth.login_server import start_loopback_server
from preflight.auth.token_store import save_credentials, get_credentials, clear_credentials
from preflight.git.repo_info import get_repo_root

console = Console()

def _decode_jwt_email(id_token: str) -> str:
    try:
        payload_b64 = id_token.split('.')[1]
        payload_b64 += '=' * (-len(payload_b64) % 4)
        payload_json = base64.urlsafe_b64decode(payload_b64).decode('utf-8')
        payload = json.loads(payload_json)
        return payload.get("email", "Unknown Email")
    except Exception:
        return "Unknown Email"

def run_login():
    repo_path = get_repo_root()
    console.print(f"\n[bold cyan]🔐 Pre-Flight AI Authentication for:[/bold cyan] {repo_path}")
    
    existing = get_credentials(repo_path)
    if existing:
        console.print(f"✅ Already logged into this project as [bold green]{existing.get('email')}[/bold green].")
        return

    console.print("Opening your browser to securely log in via Firebase...")
    auth_data = start_loopback_server(timeout_seconds=120)
    
    if auth_data:
        email = _decode_jwt_email(auth_data["id_token"])
        try:
            save_credentials(
                repo_path=repo_path, 
                uid=auth_data["uid"], 
                email=email, 
                refresh_token=auth_data["refresh_token"]
            )
            console.print(f"\n✅ [bold green]Successfully authenticated this project as {email}[/bold green]!")
        except Exception as e:
            console.print(f"\n❌ [bold red]Failed to save credentials: {e}[/bold red]")
            raise typer.Exit(1)
    else:
        console.print("\n❌ [bold red]Authentication failed or timed out.[/bold red]")
        raise typer.Exit(1)

def run_logout():
    repo_path = get_repo_root()
    clear_credentials(repo_path)
    console.print("✅ [green]Logged out of current project.[/green]")

def run_whoami():
    repo_path = get_repo_root()
    credentials = get_credentials(repo_path)
    if credentials:
        console.print(f"👤 [bold]Project logged in as:[/bold] [cyan]{credentials.get('email')}[/cyan]")
    else:
        console.print("❌ [yellow]You are not authenticated for this project.[/yellow]")