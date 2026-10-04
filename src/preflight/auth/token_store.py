import json
import keyring
from typing import Optional, Dict
from loguru import logger

from preflight.config.paths import CONFIG_DIR

# File to store non-sensitive user identity
AUTH_CONFIG_FILE = CONFIG_DIR / "auth.json"

# Constants for OS Keyring access
KEYRING_SERVICE_NAME = "preflight-ai"
KEYRING_USERNAME = "refresh_token_holder"

def save_credentials(uid: str, email: str, refresh_token: str) -> None:
    """
    Saves the user's UID and email to a standard config file,
    but securely encrypts the refresh token into the OS Keyring.
    """
    # 1. Save Public Identity (UID & Email) to JSON
    auth_data = {"uid": uid, "email": email}
    try:
        with open(AUTH_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(auth_data, f, indent=4)
    except Exception as e:
        logger.error(f"Failed to save auth config: {e}")
        raise

    # 2. Save Sensitive Refresh Token to OS Keyring
    try:
        keyring.set_password(KEYRING_SERVICE_NAME, KEYRING_USERNAME, refresh_token)
        logger.debug("Firebase refresh token securely encrypted in OS keyring.")
    except Exception as e:
        logger.error(f"Failed to access OS keyring: {e}")
        raise RuntimeError("OS Keyring is required for secure token storage but is unavailable.")

def get_credentials() -> Optional[Dict[str, str]]:
    """
    Retrieves the user's identity and refresh token.
    Returns None if the user is not logged in.
    """
    # 1. Load Public Identity
    if not AUTH_CONFIG_FILE.exists():
        return None
    
    try:
        with open(AUTH_CONFIG_FILE, "r", encoding="utf-8") as f:
            auth_data = json.load(f)
    except Exception:
        return None

    # 2. Load Secure Refresh Token
    try:
        refresh_token = keyring.get_password(KEYRING_SERVICE_NAME, KEYRING_USERNAME)
        if not refresh_token:
            return None
            
        auth_data["refresh_token"] = refresh_token
        return auth_data
    except Exception as e:
        logger.warning(f"Failed to retrieve token from OS keyring: {e}")
        return None

def clear_credentials() -> None:
    """
    Completely logs the user out by wiping the JSON config 
    and deleting the token from the OS Keyring.
    """
    # 1. Delete JSON Config
    if AUTH_CONFIG_FILE.exists():
        AUTH_CONFIG_FILE.unlink()

    # 2. Delete Token from Keyring
    try:
        keyring.delete_password(KEYRING_SERVICE_NAME, KEYRING_USERNAME)
        logger.debug("Refresh token securely purged from OS keyring.")
    except keyring.errors.PasswordDeleteError:
        pass  # Token was already deleted or never existed
    except Exception as e:
        logger.warning(f"Error while clearing OS keyring: {e}")