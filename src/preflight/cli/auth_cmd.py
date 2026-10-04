import json
import base64
import typer
from rich.console import Console

from preflight.auth.login_server import start_loopback_server
from preflight.auth.token_store import save_credentials, get_credentials, clear_credentials

console = Console()

def _decode_jwt_email(id_token: str) -> str:
    """
    Safely decodes the payload of the Firebase ID Token (JWT) 
    to extract the user's email address for display purposes.
    """
    try:
        # JWTs are split into Header, Payload, and Signature by periods
        payload_b64 = id_token.split('.')[1]
        # Add required padding for base64 decoding
        payload_b64 += '=' * (-len(payload_b64) % 4)
        payload_json = base64.urlsafe_b64decode(payload_b64).decode('utf-8')
        payload = json.loads(payload_json)
        return payload.get("email", "Unknown Email")
    except Exception:
        return "Unknown Email"

def run_login():
    """
    Executes the browser-based login flow.
    Called by `preflight auth login` and during `preflight setup`.
    """
    console.print("\n[bold cyan]🔐 Pre-Flight AI Authentication[/bold cyan]")
    
    # Check if already logged in
    existing = get_credentials()
    if existing:
        console.print(f"✅ Already logged in as [bold green]{existing.get('email', existing.get('uid'))}[/bold green].")
        console.print("Run [bold]preflight auth logout[/bold] first if you want to switch accounts.")
        return

    console.print("Opening your browser to securely log in via Firebase...")
    
    # Block CLI and wait for the browser to post back the tokens (120 sec timeout)
    auth_data = start_loopback_server(timeout_seconds=120)
    
    if auth_data:
        uid = auth_data["uid"]
        refresh_token = auth_data["refresh_token"]
        id_token = auth_data["id_token"]
        
        # Extract email from the JWT payload
        email = _decode_jwt_email(id_token)
        
        # Securely save to OS Keyring and config
        try:
            save_credentials(uid=uid, email=email, refresh_token=refresh_token)
            console.print(f"\n✅ [bold green]Successfully authenticated as {email}[/bold green]!")
        except Exception as e:
            console.print(f"\n❌ [bold red]Failed to save credentials: {e}[/bold red]")
            raise typer.Exit(1)
    else:
        console.print("\n❌ [bold red]Authentication failed or timed out.[/bold red]")
        raise typer.Exit(1)

def run_logout():
    """
    Clears local credentials.
    Called by `preflight auth logout`.
    """
    clear_credentials()
    console.print("✅ [green]Successfully logged out. Credentials removed from OS keyring.[/green]")

def run_whoami():
    """
    Displays the currently authenticated user.
    Called by `preflight auth whoami`.
    """
    credentials = get_credentials()
    
    if credentials:
        email = credentials.get("email", "Unknown")
        uid = credentials.get("uid", "Unknown")
        console.print(f"👤 [bold]Currently logged in as:[/bold] [cyan]{email}[/cyan]")
        console.print(f"🔑 [bold]Firebase UID:[/bold] {uid}")
        console.print("🔒 [green]Refresh token is secured in the OS keyring.[/green]")
    else:
        console.print("❌ [yellow]You are not currently logged in.[/yellow]")
        console.print("Run [bold cyan]preflight auth login[/bold cyan] to authenticate.")