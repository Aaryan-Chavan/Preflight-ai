import sys
import time
import argparse
import subprocess
from pathlib import Path
from loguru import logger

# -----------------------------------------------------------------------------
# Background Worker Logic
# -----------------------------------------------------------------------------
def _check_remote_sha(repo_path: str, branch: str) -> str:
    """Queries the remote Git server to see what SHA is currently on the branch."""
    try:
        # ls-remote is fast and doesn't require downloading objects
        result = subprocess.run(
            ["git", "ls-remote", "origin", branch],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.stdout:
            # Output format: <sha> \t <ref>
            return result.stdout.strip().split()[0]
    except Exception as e:
        logger.debug(f"Remote check failed (network issue?): {e}")
    return ""

def _update_outcome(report_id: str, outcome_value: str) -> None:
    """Directly updates the SQLite database from the background thread."""
    try:
        from preflight.storage.db import get_connection
        with get_connection() as conn:
            conn.execute(
                "UPDATE pushes SET outcome = ? WHERE report_id = ?", 
                (outcome_value, report_id)
            )
            # Re-queue the report so Firebase gets the updated outcome
            conn.execute(
                "UPDATE sync_outbox SET status = 'pending' WHERE report_id = ?", 
                (report_id,)
            )
            conn.commit()
            logger.info(f"Database updated: Report {report_id} -> {outcome_value}")
    except Exception as e:
        logger.error(f"Watcher failed to update database: {e}")

def watch_push(report_id: str, repo_path: str, branch: str, expected_sha: str, max_retries: int = 12):
    """
    Polls the remote repository every 5 seconds.
    If the expected SHA appears, the push succeeded.
    """
    # Configure a private log file for the background worker inside the repo's .git folder
    log_file = Path(repo_path) / ".git" / "preflight_watcher.log"
    logger.add(log_file, rotation="1 MB", level="DEBUG")
    
    logger.info(f"Watcher started for report {report_id}. Waiting for {expected_sha[:8]} on {branch}...")

    # Wait 3 seconds before the first poll to give the Git upload time to finish
    time.sleep(3)

    for attempt in range(max_retries):
        remote_sha = _check_remote_sha(repo_path, branch)
        
        if remote_sha == expected_sha:
            logger.info(f"✅ Push confirmed! {expected_sha[:8]} is live on remote.")
            _update_outcome(report_id, "success")
            return
            
        logger.debug(f"Attempt {attempt + 1}/{max_retries}: Remote is at {remote_sha[:8]}, still waiting...")
        time.sleep(5)

    # If we exhaust retries, we assume the push was rejected or timed out
    logger.warning(f"❌ Watcher timed out. {expected_sha[:8]} never reached remote.")
    _update_outcome(report_id, "failed")

# -----------------------------------------------------------------------------
# Subprocess Spawner
# -----------------------------------------------------------------------------
def spawn_watcher(report_id: str, repo_path: str, branch: str, expected_sha: str) -> None:
    """
    Spawns this exact script as a fully detached background process.
    Called by the main pipeline right before the hook exits.
    """
    cmd = [
        sys.executable,
        "-m", "preflight.git.push_watcher",
        "--report-id", report_id,
        "--repo-path", repo_path,
        "--branch", branch,
        "--sha", expected_sha
    ]
    
    kwargs = {}
    if sys.platform == "win32":
        # CRITICAL for Windows: This flag completely decouples the child process 
        # from the developer's terminal so it doesn't freeze their command prompt.
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        # POSIX equivalent
        kwargs["start_new_session"] = True
        kwargs["stdin"] = subprocess.DEVNULL
        kwargs["stdout"] = subprocess.DEVNULL
        kwargs["stderr"] = subprocess.DEVNULL

    try:
        subprocess.Popen(cmd, **kwargs)
        logger.debug("Background push watcher successfully spawned.")
    except Exception as e:
        logger.error(f"Failed to spawn push watcher: {e}")

# -----------------------------------------------------------------------------
# CLI Entrypoint for the Background Worker
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pre-Flight AI Background Watcher")
    parser.add_argument("--report-id", required=True)
    parser.add_argument("--repo-path", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--sha", required=True)
    
    args = parser.parse_args()
    watch_push(args.report_id, args.repo_path, args.branch, args.sha)