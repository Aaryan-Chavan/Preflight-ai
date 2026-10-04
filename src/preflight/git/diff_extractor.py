import subprocess
import re
from typing import List, Optional, Tuple
from loguru import logger

from preflight.core.models import FileChange, Hunk, ChangeKind, Language
from preflight.git.ref_parser import ParsedRef, ZERO_OID
from preflight.config.settings import settings

# -----------------------------------------------------------------------------
# Configuration & Constants
# -----------------------------------------------------------------------------
# Exclude files that are too large, generated, or irrelevant for AI review
EXCLUDED_EXTENSIONS = {".lock", ".min.js", ".min.css", ".map", ".pyc", ".png", ".jpg", ".exe"}
EXCLUDED_DIRS = {"node_modules/", "venv/", ".env/", "dist/", "build/", "vendor/"}

# Regex to parse Git's Unified Diff (U0) headers: @@ -old,lines +new,lines @@
HUNK_HEADER_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

# -----------------------------------------------------------------------------
# Git Subprocess Helpers
# -----------------------------------------------------------------------------
def _run_git(cmd: List[str]) -> str:
    """Executes a Git command safely and returns its stdout."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Git command failed: {' '.join(cmd)}\n{e.stderr}")
        raise RuntimeError(f"Git extraction failed: {e.stderr}")

def _get_default_branch() -> str:
    """Finds the default remote branch (e.g., origin/main or origin/master)."""
    try:
        # Ask Git what it thinks the default branch is for origin
        out = _run_git(["git", "rev-parse", "--abbrev-ref", "origin/HEAD"])
        return out if out else "origin/main"
    except RuntimeError:
        return "origin/main" # Safe fallback

def _determine_diff_range(ref: ParsedRef) -> str:
    """
    Calculates the exact commit range to diff.
    Handles the edge case where the remote branch doesn't exist yet (ZERO_OID).
    """
    if ref.is_new_branch:
        default_branch = _get_default_branch()
        logger.debug(f"New branch detected. Finding merge-base with {default_branch}")
        merge_base = _run_git(["git", "merge-base", ref.local_sha, default_branch])
        return f"{merge_base}..{ref.local_sha}"
    else:
        return f"{ref.remote_sha}..{ref.local_sha}"

# -----------------------------------------------------------------------------
# Parsing Helpers
# -----------------------------------------------------------------------------
def _detect_language(filepath: str) -> Language:
    """Basic extension matching to determine the language for Tree-sitter later."""
    ext = filepath.lower().split('.')[-1]
    lang_map = {
        "py": Language.PYTHON,
        "js": Language.JAVASCRIPT,
        "jsx": Language.JAVASCRIPT,
        "ts": Language.TYPESCRIPT,
        "tsx": Language.TYPESCRIPT,
        "java": Language.JAVA,
        "cpp": Language.CPP,
        "cc": Language.CPP,
        "hpp": Language.CPP,
        "h": Language.CPP,
        "c": Language.CPP
    }
    return lang_map.get(ext, Language.UNKNOWN)

def _is_excluded(filepath: str) -> bool:
    """Checks if a file should be skipped to save Time Budgets."""
    if any(filepath.endswith(ext) for ext in EXCLUDED_EXTENSIONS):
        return True
    if any(d in filepath for d in EXCLUDED_DIRS):
        return True
    return False

def _parse_hunks(diff_text: str) -> List[Hunk]:
    """
    Parses a unified diff into structured Pydantic Hunk objects.
    Extracts the exact line numbers that changed.
    """
    hunks = []
    current_hunk = None
    lines_buffer = []

    for line in diff_text.splitlines():
        match = HUNK_HEADER_RE.match(line)
        if match:
            # Save the previous hunk if we have one
            if current_hunk:
                current_hunk.content = "\n".join(lines_buffer)
                hunks.append(current_hunk)
                lines_buffer = []
            
            # Parse the new hunk header
            old_start = int(match.group(1))
            old_lines = int(match.group(2)) if match.group(2) else 1
            new_start = int(match.group(3))
            new_lines = int(match.group(4)) if match.group(4) else 1
            
            current_hunk = Hunk(
                old_start=old_start, 
                old_lines=old_lines, 
                new_start=new_start, 
                new_lines=new_lines, 
                content=""
            )
        elif current_hunk:
            lines_buffer.append(line)

    # Catch the final hunk
    if current_hunk:
        current_hunk.content = "\n".join(lines_buffer)
        hunks.append(current_hunk)

    return hunks

# -----------------------------------------------------------------------------
# Main Extractor
# -----------------------------------------------------------------------------
def extract_file_changes(ref: ParsedRef) -> List[FileChange]:
    """
    Extracts a strictly typed list of files and their hunks for the push.
    This fulfills the Tier 0 Time Budget requirements.
    """
    if ref.is_delete or ref.is_tag:
        return []

    diff_range = _determine_diff_range(ref)
    logger.info(f"Extracting diff for range: {diff_range}")
    
    # 1. Get the list of files and their statuses (Added, Modified, Deleted, Renamed)
    # Using -z for safe parsing of paths with spaces
    name_status_raw = _run_git(["git", "diff", "--name-status", "-M", "-z", diff_range])
    
    if not name_status_raw:
        return []

    # Git -z output splits everything by null bytes
    parts = name_status_raw.split('\0')
    file_changes: List[FileChange] = []
    
    i = 0
    while i < len(parts) - 1: # -1 because the last element might be empty
        status_code = parts[i][0] # A, M, D, R, etc.
        
        old_path = None
        new_path = None
        change_kind = ChangeKind.MODIFIED
        
        if status_code == 'R':
            # Renames consume 3 parts: status, old_name, new_name
            change_kind = ChangeKind.RENAMED
            old_path = parts[i+1]
            new_path = parts[i+2]
            i += 3
        else:
            # A, M, D consume 2 parts: status, name
            path = parts[i+1]
            if status_code == 'A':
                change_kind = ChangeKind.ADDED
                new_path = path
            elif status_code == 'D':
                change_kind = ChangeKind.DELETED
                old_path = path
            else:
                change_kind = ChangeKind.MODIFIED
                old_path = path
                new_path = path
            i += 2

        active_path = new_path if new_path else old_path
        
        if _is_excluded(active_path):
            continue

        language = _detect_language(active_path)
        is_test = "test" in active_path.lower() or "spec" in active_path.lower()
        
        file_change = FileChange(
            old_path=old_path,
            new_path=new_path,
            change_kind=change_kind,
            language=language,
            is_test_file=is_test,
            hunks=[],
            symbols=[]
        )

        # 2. Extract specific Hunks (only for Added/Modified files)
        if change_kind in (ChangeKind.ADDED, ChangeKind.MODIFIED, ChangeKind.RENAMED) and new_path:
            # We use -U0 to only get the exact changed lines (no surrounding context lines)
            diff_text = _run_git(["git", "diff", "-U0", diff_range, "--", new_path])
            file_change.hunks = _parse_hunks(diff_text)
            
        file_changes.append(file_change)

    logger.info(f"Extracted {len(file_changes)} valid source files for analysis.")
    return file_changes