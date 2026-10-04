import sys
import json
import time
import base64
import requests
import subprocess
from loguru import logger

from preflight.storage.repositories import SyncOutboxDAO
from preflight.auth.token_store import get_credentials
from preflight.storage.db import get_connection
from preflight.config.settings import settings

def _get_full_report_payload(report_id: str) -> dict:
    """Fetches the complete, joined report data from SQLite."""
    with get_connection() as conn:
        cursor = conn.execute('''
            SELECT p.*, r.popup_json, r.detailed_md 
            FROM pushes p 
            JOIN reports r ON p.report_id = r.report_id 
            WHERE p.report_id = ?
        ''', (report_id,))
        row = cursor.fetchone()
        
        if not row:
            return {}
        
        return {
            "report_id": row["report_id"],
            "repo_id": row["repo_id"],
            "branch": row["branch"],
            "timestamp": row["timestamp"],
            "decision": row["decision"],
            "outcome": row["outcome"],
            "popup": json.loads(row["popup_json"]),
            "detailed_md": row["detailed_md"]
        }

def format_for_firestore(data: dict) -> dict:
    """Converts standard Python dicts to Firestore's strict REST API format."""
    fields = {}
    for k, v in data.items():
        if isinstance(v, str): 
            fields[k] = {"stringValue": v}
        elif isinstance(v, bool): 
            fields[k] = {"booleanValue": v}
        elif isinstance(v, int): 
            fields[k] = {"integerValue": str(v)}
        elif isinstance(v, float): 
            fields[k] = {"doubleValue": float(v)}
        elif isinstance(v, dict) or isinstance(v, list):
            # Flatten nested JSON like the popup object into a string for easy storage
            fields[k] = {"stringValue": json.dumps(v)}
        elif v is None:
            fields[k] = {"nullValue": None}
        else: 
            fields[k] = {"stringValue": str(v)}
    return {"fields": fields}

def _upload_to_firestore(report_id: str, payload: dict, id_token: str) -> bool:
    """
    Pushes the data securely to Firestore using the free REST API.
    Bypasses the need for a Firebase Cloud Function.
    """
    try:
        # Extract UID from the JWT token to bind it to the report
        payload_b64 = id_token.split('.')[1]
        payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
        token_data = json.loads(base64.b64decode(payload_b64).decode('utf-8'))
        uid = token_data.get("user_id") or token_data.get("sub")
    except Exception as e:
        logger.error(f"Failed to decode token for UID: {e}")
        return False

    # 1. Bind the user ID so the Security Rules accept it
    payload["userId"] = uid

    # 2. Format the payload for Google's REST API
    firestore_payload = format_for_firestore(payload)
    
    # 3. Hit the free Firestore Database endpoint directly
    url = f"https://firestore.googleapis.com/v1/projects/{settings.firebase_project_id}/databases/(default)/documents/reports?documentId={report_id}"
    
    headers = {
        "Authorization": f"Bearer {id_token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, headers=headers, json=firestore_payload, timeout=15)
        if response.status_code == 200:
            return True
        else:
            logger.warning(f"Cloud upload failed: {response.status_code} - {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        logger.warning(f"Network error during cloud sync: {e}")
        return False

def process_outbox():
    """
    Main loop for the background sync worker.
    Processes up to 10 pending reports per execution to prevent long-running ghost processes.
    """
    credentials = get_credentials()
    if not credentials or not credentials.get("refresh_token"):
        logger.info("Sync skipped: User is not logged in.")
        return

    id_token = credentials.get("id_token", "dev-placeholder-token")

    pending_reports = SyncOutboxDAO.get_pending_reports(limit=10)
    
    if not pending_reports:
        logger.debug("Sync worker exiting: No pending reports.")
        return

    logger.info(f"Sync worker started. {len(pending_reports)} reports in outbox.")

    for report_id in pending_reports:
        payload = _get_full_report_payload(report_id)
        if not payload:
            SyncOutboxDAO.mark_status(report_id, "failed", "Report missing from database")
            continue

        success = _upload_to_firestore(report_id, payload, id_token)
        
        if success:
            SyncOutboxDAO.mark_status(report_id, "synced")
            logger.info(f"✅ Report {report_id} successfully synced to cloud.")
        else:
            SyncOutboxDAO.mark_status(report_id, "failed", "Network error")
            
        # 1-second delay between uploads to be polite to the network
        time.sleep(1)

def trigger_sync_worker():
    """
    Spawns this exact script as a fully detached background process.
    Called by the push_watcher once the outcome is finalized.
    """
    cmd = [sys.executable, "-m", "preflight.cloud.sync_worker"]
    
    kwargs = {}
    if sys.platform == "win32":
        # Completely decouples the child process from the Windows terminal
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        # POSIX equivalent
        kwargs["start_new_session"] = True
        kwargs["stdin"] = subprocess.DEVNULL
        kwargs["stdout"] = subprocess.DEVNULL
        kwargs["stderr"] = subprocess.DEVNULL

    try:
        subprocess.Popen(cmd, **kwargs)
        logger.debug("Background sync worker successfully spawned.")
    except Exception as e:
        logger.error(f"Failed to spawn sync worker: {e}")

if __name__ == "__main__":
    process_outbox()