import json
import uuid
import platform
from loguru import logger

from preflight.config.paths import INSTALL_ID_FILE

def _gather_system_metadata() -> dict:
    """Collects basic OS and hardware metadata to associate with this installation."""
    return {
        "os_system": platform.system(),
        "os_release": platform.release(),
        "os_version": platform.version(),
        "hostname": platform.node(),
        "architecture": platform.machine(),
    }

def generate_and_save_install_id() -> str:
    """
    Generates a unique Installation ID for this specific machine if one does not exist.
    Persists it to the local configuration directory.
    Returns the Installation ID string.
    """
    # 1. Idempotency Check: Return existing ID if already installed
    if INSTALL_ID_FILE.exists():
        try:
            with open(INSTALL_ID_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                install_id = data.get("install_id")
                if install_id:
                    logger.debug(f"Loaded existing Installation ID: {install_id}")
                    return install_id
        except Exception as e:
            logger.warning(f"Corrupted install_id file detected. Regenerating. Error: {e}")

    # 2. Generate a new unique ID (Format: DEV-XXXXXXXX)
    short_uuid = uuid.uuid4().hex[:8].upper()
    new_install_id = f"DEV-{short_uuid}"
    
    # 3. Build the payload
    payload = {
        "install_id": new_install_id,
        "metadata": _gather_system_metadata()
    }
    
    # 4. Save to disk securely
    try:
        with open(INSTALL_ID_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4)
        logger.info(f"Generated new Installation ID: {new_install_id}")
    except Exception as e:
        logger.error(f"Failed to save Installation ID: {e}")
        raise RuntimeError(f"Could not persist installation identity: {e}")

    return new_install_id

def get_install_id() -> str:
    """
    Retrieves the current Installation ID. 
    Defaults to 'DEV-UNKNOWN' if setup hasn't been run yet.
    """
    if INSTALL_ID_FILE.exists():
        try:
            with open(INSTALL_ID_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("install_id", "DEV-UNKNOWN")
        except Exception:
            return "DEV-UNKNOWN"
    return "DEV-UNKNOWN"