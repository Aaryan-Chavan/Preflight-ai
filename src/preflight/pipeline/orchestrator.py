import time
import uuid
from typing import List
from datetime import datetime, timezone
from loguru import logger

from preflight.core.models import (
    ChangeSet, Report, ReportMetadata, 
    Decision, PushOutcome, RiskLevel, PopupPayload
)
from preflight.git.ref_parser import ParsedRef
from preflight.git.diff_extractor import extract_file_changes
from preflight.git.repo_info import get_repo_name, get_author_email, get_repo_root
from preflight.storage.repositories import PushReportDAO
from preflight.config.settings import settings

def execute_pipeline(refs: List[ParsedRef]) -> int:
    """
    Executes the main Pre-Flight AI analysis pipeline.
    Returns the process exit code: 0 to allow the push, 1 to cancel it.
    """
    start_time = time.time()
    logger.info("Initializing AI Analysis Pipeline...")

    # For MVP, we only analyze the first valid reference being pushed.
    # (Handling multiple branches in a single push is a v2 feature).
    active_ref = next((r for r in refs if not r.is_delete and not r.is_tag), None)
    
    if not active_ref:
        logger.info("No actionable refs found (only deletions or tags). Allowing push.")
        return 0

    # -------------------------------------------------------------------------
    # 1. Tier 0: Data Extraction
    # -------------------------------------------------------------------------
    logger.debug(f"Tier 0: Extracting diffs for {active_ref.local_ref}...")
    file_changes = extract_file_changes(active_ref)
    
    if not file_changes:
        logger.info("No supported files changed. Allowing push.")
        return 0

    # Assemble the master ChangeSet object
    change_set = ChangeSet(
        repository_name=get_repo_name(),
        branch=active_ref.local_ref.replace("refs/heads/", ""),
        author_email=get_author_email(),
        files=file_changes
    )

    # -------------------------------------------------------------------------
    # 2. Tier 1 & 2: AI Analysis (Gracefully mocked during development)
    # -------------------------------------------------------------------------
    try:
        from preflight.pipeline.llm_engine import analyze_changeset
        
        logger.info(f"Tier 1/2: Sending {len(file_changes)} files to Ollama ({settings.llm_model_name})...")
        popup_payload, detailed_md = analyze_changeset(change_set)
        
    except ImportError:
        logger.warning("[Development] LLM Engine not yet built. Generating dummy report.")
        # Dummy data so the pipeline can continue while we build the app
        popup_payload = PopupPayload(
            risk_level=RiskLevel.LOW,
            confidence_percentage=95,
            summary="Development Mode: LLM Engine missing. Code looks good!",
            key_concerns=["Build the LLM module next!"]
        )
        detailed_md = "# Development Mode\nThe AI engine is not fully assembled yet."

    # -------------------------------------------------------------------------
    # 3. Report Assembly & Storage
    # -------------------------------------------------------------------------
    report_id = uuid.uuid4()
    analysis_ms = int((time.time() - start_time) * 1000)
    
    meta = ReportMetadata(
        report_id=report_id,
        repo_name=change_set.repository_name,
        branch=change_set.branch,
        local_sha=active_ref.local_sha,
        remote_sha=active_ref.remote_sha,
        timestamp=datetime.now(timezone.utc),
        decision=Decision.PENDING, 
        outcome=PushOutcome.PENDING,
        analysis_ms=analysis_ms,
        pipeline_version="1.0.0"
    )
    
    report = Report(
        meta=meta,
        popup=popup_payload,
        detailed_markdown=detailed_md
    )

    logger.debug("Saving pending report to local SQLite database...")
    PushReportDAO.save_report(report)

    # -------------------------------------------------------------------------
    # 4. User Interface & Decision
    # -------------------------------------------------------------------------
    try:
        from preflight.ui.terminal_app import show_review_ui
        
        logger.info("Triggering interactive UI...")
        # This blocks until the user clicks 'Continue' or 'Cancel'
        decision = show_review_ui(report)
        
    except ImportError:
        logger.warning("[Development] UI module not yet built. Auto-approving.")
        decision = Decision.CONTINUE

    # -------------------------------------------------------------------------
    # 5. Final Outcome & Cleanup
    # -------------------------------------------------------------------------
    if decision == Decision.CANCEL:
        logger.info("Developer cancelled the push. Updating DB.")
        PushReportDAO.update_decision_and_outcome(str(report_id), decision, PushOutcome.CANCELLED)
        return 1
    
    else:
        logger.info("Developer approved the push. Spawning background watcher...")
        try:
            from preflight.git.push_watcher import spawn_watcher
            spawn_watcher(
                report_id=str(report_id),
                repo_path=get_repo_root(),
                branch=active_ref.local_ref,
                expected_sha=active_ref.local_sha
            )
        except ImportError:
            pass # Failsafe during dev
            
        return 0