from typing import List
from pydantic import BaseModel
from loguru import logger

# Git's empty SHA-1 used for branch creations and deletions
ZERO_OID = "0000000000000000000000000000000000000000"

class ParsedRef(BaseModel):
    """Structured representation of a Git push reference."""
    local_ref: str
    local_sha: str
    remote_ref: str
    remote_sha: str
    is_new_branch: bool
    is_delete: bool
    is_tag: bool

def parse_refs(raw_lines: List[str]) -> List[ParsedRef]:
    """
    Parses Git's stdin payload during a pre-push hook.
    Format per line: <local ref> SP <local sha1> SP <remote ref> SP <remote sha1> LF
    """
    parsed_refs = []
    
    for line in raw_lines:
        parts = line.strip().split()
        
        # Guard against malformed input from older Git clients
        if len(parts) != 4:
            logger.warning(f"Skipping malformed ref line from Git: {line}")
            continue
            
        local_ref, local_sha, remote_ref, remote_sha = parts
        
        # Classify the Git operation
        is_new_branch = (remote_sha == ZERO_OID)
        is_delete = (local_sha == ZERO_OID)
        is_tag = local_ref.startswith("refs/tags/") or remote_ref.startswith("refs/tags/")
        
        ref_obj = ParsedRef(
            local_ref=local_ref,
            local_sha=local_sha,
            remote_ref=remote_ref,
            remote_sha=remote_sha,
            is_new_branch=is_new_branch,
            is_delete=is_delete,
            is_tag=is_tag
        )
        
        parsed_refs.append(ref_obj)
        logger.debug(f"Parsed Git Ref: {local_ref} (New: {is_new_branch}, Delete: {is_delete})")
        
    return parsed_refs