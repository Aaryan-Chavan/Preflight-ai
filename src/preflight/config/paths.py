import os
from pathlib import Path
from platformdirs import PlatformDirs

# Initialize platform-specific directory paths for Pre-Flight AI
_dirs = PlatformDirs(appname="preflight-ai", appauthor=False)

# -----------------------------------------------------------------------------
# Base Directories
# -----------------------------------------------------------------------------
CONFIG_DIR = Path(_dirs.user_config_dir)
DATA_DIR = Path(_dirs.user_data_dir)
LOG_DIR = Path(_dirs.user_log_dir)

# -----------------------------------------------------------------------------
# Specific Application Paths
# -----------------------------------------------------------------------------
# Where the global Git hooks shim will be installed
GLOBAL_HOOKS_DIR = CONFIG_DIR / "hooks"

# SQLite local database path
DB_PATH = DATA_DIR / "preflight.db"

# Local cache for downloaded ML model artifacts (XGBoost JSON, thresholds)
MODELS_DIR = DATA_DIR / "models"

# User configuration and state tracking
CONFIG_FILE = CONFIG_DIR / "config.json"
INSTALL_ID_FILE = CONFIG_DIR / "install_id"

def ensure_directories() -> None:
    """
    Ensure all required application directories exist before the pipeline runs.
    This is called during 'preflight setup' and daemon startup.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    GLOBAL_HOOKS_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)