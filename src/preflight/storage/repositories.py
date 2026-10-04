import json
from typing import Optional, List
from loguru import logger

from preflight.core.models import Report, ReportMetadata, PopupPayload, Decision, PushOutcome
from preflight.storage.db import get_connection

class PushReportDAO:
    """
    Data Access Object for managing Git Push Reports in SQLite.
    Handles the 'repositories', 'pushes', 'reports', and 'sync_outbox' tables.
    """

    @staticmethod
    def _get_or_create_repo(conn, path: str, name: str, remote_url: str = "") -> int:
        """Resolves a repository path to its SQLite primary key ID."""
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO repositories (path, name, remote_url)
            VALUES (?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET 
                name=excluded.name, 
                remote_url=excluded.remote_url
            """,
            (path, name, remote_url)
        )
        cursor.execute("SELECT id FROM repositories WHERE path = ?", (path,))
        return cursor.fetchone()["id"]

    @classmethod
    def save_report(cls, report: Report) -> None:
        """
        Saves a complete Report object to the database across multiple tables.
        Wraps everything in a transaction.
        """
        with get_connection() as conn:
            try:
                # 1. Resolve Repo ID
                repo_id = cls._get_or_create_repo(
                    conn, 
                    path=report.meta.repo_name, # Using name as path placeholder for now
                    name=report.meta.repo_name,
                    remote_url=""
                )

                # 2. Insert into Pushes (Searchable Metadata)
                conn.execute(
                    """
                    INSERT INTO pushes (
                        report_id, repo_id, branch, local_sha, remote_sha, 
                        timestamp, risk_level, risk_prob, confidence, 
                        decision, outcome, analysis_ms, pipeline_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(report_id) DO UPDATE SET
                        decision=excluded.decision,
                        outcome=excluded.outcome
                    """,
                    (
                        str(report.meta.report_id),
                        repo_id,
                        report.meta.branch,
                        report.meta.local_sha,
                        report.meta.remote_sha,
                        report.meta.timestamp.isoformat(),
                        report.popup.risk_level.value,
                        0.0, # risk_prob (placeholder until ML)
                        report.popup.confidence_percentage / 100.0,
                        report.meta.decision.value,
                        report.meta.outcome.value,
                        report.meta.analysis_ms,
                        report.meta.pipeline_version
                    )
                )

                # 3. Insert into Reports (Heavy JSON/Markdown content)
                conn.execute(
                    """
                    INSERT INTO reports (report_id, popup_json, detailed_md)
                    VALUES (?, ?, ?)
                    ON CONFLICT(report_id) DO UPDATE SET
                        popup_json=excluded.popup_json,
                        detailed_md=excluded.detailed_md
                    """,
                    (
                        str(report.meta.report_id),
                        report.popup.model_dump_json(),
                        report.detailed_markdown
                    )
                )

                # 4. Queue for Cloud Sync
                conn.execute(
                    """
                    INSERT OR IGNORE INTO sync_outbox (report_id, status)
                    VALUES (?, 'pending')
                    """,
                    (str(report.meta.report_id),)
                )

                conn.commit()
                logger.debug(f"Successfully saved report {report.meta.report_id} to SQLite.")
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to save report to SQLite: {e}")
                raise

    @classmethod
    def update_decision_and_outcome(cls, report_id: str, decision: Decision, outcome: PushOutcome) -> None:
        """Fast update for when the developer clicks Continue/Cancel or the watcher confirms the push."""
        with get_connection() as conn:
            conn.execute(
                "UPDATE pushes SET decision = ?, outcome = ? WHERE report_id = ?",
                (decision.value, outcome.value, report_id)
            )
            # Re-queue for sync since the data changed
            conn.execute(
                "UPDATE sync_outbox SET status = 'pending' WHERE report_id = ?",
                (report_id,)
            )
            conn.commit()


class SyncOutboxDAO:
    """Manages the background synchronization queue to Firebase Firestore."""
    
    @staticmethod
    def get_pending_reports(limit: int = 50) -> List[str]:
        """Returns a list of report_ids that need to be uploaded."""
        with get_connection() as conn:
            cursor = conn.execute(
                "SELECT report_id FROM sync_outbox WHERE status = 'pending' OR status = 'failed' LIMIT ?",
                (limit,)
            )
            return [row["report_id"] for row in cursor.fetchall()]

    @staticmethod
    def mark_status(report_id: str, status: str, error: Optional[str] = None) -> None:
        """Marks a sync attempt as 'sent' or 'failed'."""
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE sync_outbox 
                SET status = ?, last_error = ?, attempts = attempts + 1, next_try = CURRENT_TIMESTAMP
                WHERE report_id = ?
                """,
                (status, error, report_id)
            )
            conn.commit()