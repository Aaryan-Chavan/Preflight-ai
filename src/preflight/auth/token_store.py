import json
import keyring
import hashlib
from typing import Optional, Dict
from loguru import logger

from preflight.config.paths import CONFIG_DIR

AUTH_CONFIG_FILE = CONFIG_DIR / "auth.json"
KEYRING_SERVICE_BASE = "preflight-ai"

def _get_project_key(repo_path: str) -> str:
    """Creates a unique hash for the specific git repository path."""
    return hashlib.md5(repo_path.encode('utf-8')).hexdigest()

def save_credentials(repo_path: str, uid: str, email: str, refresh_token: str) -> None:
    project_key = _get_project_key(repo_path)
    
    # 1. Save Public Identity mapping
    auth_data = {}
    if AUTH_CONFIG_FILE.exists():
        try:
            with open(AUTH_CONFIG_FILE, "r", encoding="utf-8") as f:
                auth_data = json.load(f)
        except Exception:
            pass
            
    auth_data[project_key] = {"uid": uid, "email": email, "repo_path": repo_path}
    with open(AUTH_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(auth_data, f, indent=4)

    # 2. Save Sensitive Refresh Token bound to this specific project hash
    service_name = f"{KEYRING_SERVICE_BASE}-{project_key}"
    try:
        keyring.set_password(service_name, "refresh_token_holder", refresh_token)
        logger.debug(f"Refresh token encrypted for project {project_key}.")
    except Exception as e:
        logger.error(f"Failed to access OS keyring: {e}")
        raise RuntimeError("OS Keyring is required for secure token storage.")

def get_credentials(repo_path: str) -> Optional[Dict[str, str]]:
    project_key = _get_project_key(repo_path)
    if not AUTH_CONFIG_FILE.exists():
        return None
    
    try:
        with open(AUTH_CONFIG_FILE, "r", encoding="utf-8") as f:
            auth_data = json.load(f)
    except Exception:
        return None

    project_auth = auth_data.get(project_key)
    if not project_auth:
        return None

    service_name = f"{KEYRING_SERVICE_BASE}-{project_key}"
    try:
        refresh_token = keyring.get_password(service_name, "refresh_token_holder")
        if not refresh_token:
            return None
        project_auth["refresh_token"] = refresh_token
        return project_auth
    except Exception as e:
        logger.warning(f"Failed to retrieve token from OS keyring: {e}")
        return None

def clear_credentials(repo_path: str) -> None:
    project_key = _get_project_key(repo_path)
    if AUTH_CONFIG_FILE.exists():
        try:
            with open(AUTH_CONFIG_FILE, "r", encoding="utf-8") as f:
                auth_data = json.load(f)
            if project_key in auth_data:
                del auth_data[project_key]
                with open(AUTH_CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(auth_data, f, indent=4)
        except Exception:
            pass

    service_name = f"{KEYRING_SERVICE_BASE}-{project_key}"
    try:
        keyring.delete_password(service_name, "refresh_token_holder")
    except Exception:
        pass