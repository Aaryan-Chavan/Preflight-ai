"""Main Pre-Flight pipeline: diff -> AI review -> report -> developer decision -> push outcome.

The return value is the hook's exit code: 0 lets the push continue, 1 cancels it.

Everything except the developer's own decision is fail-soft: a broken stage is logged with its
traceback and replaced by a safe default, so a bug in Pre-Flight never blocks a push.

Place at: src/preflight/pipeline/orchestrator.py
"""
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, List, Tuple

from loguru import logger

from preflight.config.settings import settings
from preflight.core.models import (
    ChangeSet,
    Decision,
    PopupPayload,
    PushOutcome,
    Report,
    ReportMetadata,
)
from preflight.git.diff_extractor import extract_file_changes
from preflight.git.ref_parser import ParsedRef
from preflight.git.repo_info import get_repo_name, get_repo_root
from preflight.pipeline.fallback import build_unavailable_payload
from preflight.storage.repositories import PushReportDAO


def _install_id() -> str:
    return str(getattr(settings, "install_id", "") or "local-dev")


def _store(description: str, action: Callable[..., Any], *args: Any) -> bool:
    """Run a local-database action. A storage failure is logged but must never stop the push."""
    try:
        action(*args)
        return True
    except Exception:
        logger.opt(exception=True).error(f"Local storage failed while {description}. Continuing without it.")
        return False


def _analyze(change_set: ChangeSet) -> Tuple[PopupPayload, str]:
    """Run the AI review, degrading to a complete 'unavailable' report on any problem."""
    try:
        from preflight.pipeline.llm_engine import analyze_changeset
    except ImportError as exc:
        logger.warning(f"[Development] LLM engine missing or failed to import: {exc}")
        return build_unavailable_payload(change_set, "LLM engine is not available")

    try:
        logger.info(f"Tier 1/2: Sending {len(change_set.files)} file(s) to Ollama ({settings.llm_model_name})...")
        return analyze_changeset(change_set)
    except Exception as exc:
        logger.opt(exception=True).error("AI analysis crashed unexpectedly.")
        return build_unavailable_payload(change_set, f"internal error ({type(exc).__name__})")


def _ask_developer(report: Report) -> Decision:
    """Show the review UI and return CONTINUE or CANCEL. Fails open if the UI is missing or broken."""
    try:
        from preflight.ui.terminal_app import show_review_ui
    except ImportError as exc:
        logger.warning(f"[Development] Review UI missing or failed to import: {exc}. Auto-approving.")
        return Decision.CONTINUE

    try:
        decision = show_review_ui(report)  # blocks until the developer chooses
    except Exception:
        logger.opt(exception=True).error("Review UI failed. Failing open: the push will continue.")
        return Decision.CONTINUE

    if decision not in (Decision.CONTINUE, Decision.CANCEL):
        logger.warning(f"Review UI returned {decision!r}; treating it as CONTINUE.")
        return Decision.CONTINUE
    return decision


def _start_watcher(report_id: str, ref: ParsedRef) -> None:
    """Start the background process that records whether the push really succeeded."""
    try:
        from preflight.git.push_watcher import spawn_watcher
    except ImportError as exc:
        logger.warning(f"[Development] Push watcher missing or failed to import: {exc}")
        return

    try:
        spawn_watcher(
            report_id=report_id,
            repo_path=get_repo_root(),
            branch=ref.local_ref,
            expected_sha=ref.local_sha,
        )
    except Exception:
        logger.opt(exception=True).error("Could not start the push watcher; the outcome will stay PENDING.")


def execute_pipeline(refs: List[ParsedRef]) -> int:
    """Run the full pipeline for one push. Returns 0 to allow the push, 1 to cancel it."""
    started = time.monotonic()
    logger.info("Initializing AI Analysis Pipeline...")

    actionable = [r for r in refs if not r.is_delete and not r.is_tag]
    if not actionable:
        logger.info("No actionable refs found (only deletions or tags). Allowing push.")
        return 0
    if len(actionable) > 1:
        logger.warning(
            f"{len(actionable)} branches pushed at once; analyzing only {actionable[0].local_ref} "
            "(multi-branch support is planned)."
        )
    active_ref = actionable[0]

    # ---- Tier 0: data extraction -------------------------------------------
    logger.debug(f"Tier 0: Extracting diffs for {active_ref.local_ref}...")
    file_changes = extract_file_changes(active_ref)
    if not file_changes:
        logger.info("No supported files changed. Allowing push.")
        return 0

    display_branch = active_ref.local_ref.removeprefix("refs/heads/")
    change_set = ChangeSet(
        repo_name=get_repo_name(),
        repo_path=get_repo_root(),
        branch=display_branch,
        local_sha=active_ref.local_sha,
        remote_sha=active_ref.remote_sha,
        files=file_changes,
    )

    # ---- Tier 1/2: AI review -----------------------------------------------
    popup_payload, detailed_md = _analyze(change_set)

    # ---- Report assembly and storage ---------------------------------------
    report_id = uuid.uuid4()
    analysis_ms = int((time.monotonic() - started) * 1000)  # excludes the time the human spends deciding

    meta = ReportMetadata(
        report_id=report_id,
        install_id=_install_id(),
        repo_name=change_set.repo_name,
        branch=display_branch,
        local_sha=active_ref.local_sha,
        remote_sha=active_ref.remote_sha,
        timestamp=datetime.now(timezone.utc),
        decision=Decision.PENDING,
        outcome=PushOutcome.PENDING,
        analysis_ms=analysis_ms,
        pipeline_version="1.0.0",
    )
    report = Report(meta=meta, popup=popup_payload, detailed_markdown=detailed_md)

    logger.debug("Saving pending report to local SQLite database...")
    saved = _store("saving the pending report", PushReportDAO.save_report, report)

    # ---- Developer decision ------------------------------------------------
    logger.info("Triggering interactive UI...")
    decision = _ask_developer(report)

    # ---- Final outcome -----------------------------------------------------
    if decision == Decision.CANCEL:
        logger.info("Developer cancelled the push.")
        if saved:
            _store("recording the cancellation", PushReportDAO.update_decision_and_outcome,
                   str(report_id), decision, PushOutcome.CANCELLED)
        return 1

    logger.info("Developer approved the push.")
    if saved:
        # Record the decision now; the watcher fills in the real push outcome later.
        _store("recording the decision", PushReportDAO.update_decision_and_outcome,
               str(report_id), Decision.CONTINUE, PushOutcome.PENDING)
        _start_watcher(str(report_id), active_ref)
    else:
        logger.warning("Report was not saved, so the push watcher was not started.")
    return 0