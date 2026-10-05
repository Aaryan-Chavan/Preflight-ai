"""Safe "AI unavailable" report, used whenever the LLM stage cannot produce a real review.

It lives in its own module so the orchestrator and the LLM engine build exactly the same
payload and cannot drift apart when PopupPayload changes (the cause of the last few crashes).

Place at: src/preflight/pipeline/fallback.py
"""
from typing import Tuple

from pydantic import ValidationError

from preflight.core.models import ChangeSet, PopupPayload, RiskLevel

_MAX_REASON_CHARS = 200


def _unavailable_risk_level() -> RiskLevel:
    """Prefer an explicit UNKNOWN level so 'no analysis' is never displayed as 'Low risk'."""
    for name in ("UNKNOWN", "UNAVAILABLE"):
        if hasattr(RiskLevel, name):
            return getattr(RiskLevel, name)
    return RiskLevel.LOW


def _coerce_fields(fields: dict, error: ValidationError) -> bool:
    """Fix only the fields Pydantic rejected for being a str where a list is expected, or the reverse.

    Returns True if anything was changed. This keeps the fallback working if PopupPayload's
    field types change later, without guessing the type of fields that are already valid.
    """
    changed = False
    for err in error.errors():
        key = err["loc"][0] if err.get("loc") else None
        if key not in fields:
            continue
        value = fields[key]
        if err["type"] == "list_type" and isinstance(value, str):
            fields[key] = [value]
            changed = True
        elif err["type"] == "string_type" and isinstance(value, list):
            fields[key] = " ".join(str(item) for item in value)
            changed = True
    return changed


def _build_popup(fields: dict) -> PopupPayload:
    for _ in range(3):
        try:
            return PopupPayload(**fields)
        except ValidationError as error:
            if not _coerce_fields(fields, error):
                raise
    return PopupPayload(**fields)


def build_unavailable_payload(change_set: ChangeSet, reason: str) -> Tuple[PopupPayload, str]:
    """Return (popup, detailed_markdown) for a push that could not be reviewed by the AI."""
    reason = " ".join(str(reason).split())[:_MAX_REASON_CHARS] or "unknown reason"

    fields = dict(
        risk_level=_unavailable_risk_level(),
        confidence_percentage=0,
        repo_name=change_set.repo_name,
        branch=change_set.branch,
        files_modified_count=len(change_set.files),
        critical_functions=[],
        impact_summary=[f"AI analysis unavailable: {reason}"],  # list of strings in PopupPayload
        verification_checklist=["Review the diff manually before pushing"],
        ai_recommendation="Automated review did not run. Review the changes manually before pushing.",  # plain string
    )
    popup = _build_popup(fields)

    markdown = "\n".join(
        [
            "# AI Analysis Unavailable",
            "",
            f"**Repository:** {change_set.repo_name} | **Branch:** {change_set.branch}",
            f"**Files modified:** {len(change_set.files)}",
            "",
            f"The local AI review did not run: {reason}",
            "",
            "## What to check",
            "- Is Ollama running? Try `ollama ps`.",
            "- Is the model installed? Try `ollama list`.",
            "- Review the diff manually before pushing.",
        ]
    )
    return popup, markdown