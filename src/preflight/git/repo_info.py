import subprocess
from pathlib import Path
from loguru import logger

def _run_git(cmd: list[str]) -> str:
    """Executes a Git command safely and returns its stdout."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.debug(f"Git command silently failed: {' '.join(cmd)}. Reason: {e.stderr.strip()}")
        return ""

def get_repo_root() -> str:
    """Gets the absolute path to the root of the Git repository."""
    path = _run_git(["git", "rev-parse", "--show-toplevel"])
    return path if path else str(Path.cwd())

def get_repo_name() -> str:
    """Derives the repository name from the root directory."""
    root = get_repo_root()
    return Path(root).name if root else "unknown_repo"

def get_remote_url() -> str:
    """Gets the fetch URL for the 'origin' remote."""
    return _run_git(["git", "config", "--get", "remote.origin.url"])

def get_current_branch() -> str:
    """
    Gets the name of the currently checked-out branch.
    Useful as a fallback if the pre-push stdin ref parsing fails.
    """
    return _run_git(["git", "rev-parse", "--abbrev-ref", "HEAD"])

def get_author_email() -> str:
    """Gets the Git user's configured email address."""
    return _run_git(["git", "config", "user.email"])

def get_author_name() -> str:
    """Gets the Git user's configured name."""
    return _run_git(["git", "config", "user.name"])

def get_commit_message(sha: str = "HEAD") -> str:
    """Extracts the exact commit message for a specific Git SHA."""
    try:
        # Pass the exact SHA to git log instead of relying on HEAD
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=%B", sha], 
            capture_output=True, 
            text=True, 
            check=True
        )
        return result.stdout.strip()
    except Exception as e:
        logger.debug(f"Failed to extract commit message for {sha}: {e}")
        return "Commit details unavailable"