import sys
import json
import time
import requests
import subprocess
from loguru import logger

from preflight.storage.repositories import SyncOutboxDAO
from preflight.auth.token_store import get_credentials
from preflight.storage.db import get_connection
from preflight.config.settings import settings

def _get_full_report_payload(report_id: str) -> tuple:
    with get_connection() as conn:
        cursor = conn.execute('''
            SELECT p.*, r.popup_json, r.detailed_md, rep.path as repo_path 
            FROM pushes p 
            JOIN reports r ON p.report_id = r.report_id 
            JOIN repositories rep ON p.repo_id = rep.id
            WHERE p.report_id = ?
        ''', (report_id,))
        row = cursor.fetchone()
        
        if not row:
            return {}, ""
            
        payload = {
            "report_id": row["report_id"],
            "repo_id": row["repo_id"],
            "branch": row["branch"],
            "timestamp": row["timestamp"],
            "decision": row["decision"],
            "outcome": row["outcome"],
            "popup": json.loads(row["popup_json"]),
            "detailed_md": row["detailed_md"]
        }
        return payload, row["repo_path"]

def _get_fresh_id_token(refresh_token: str) -> str:
    """Exchanges the secure long-lived refresh token for a 1-hour ID token."""
    api_key = "AIzaSyB4eLLKNuOu-GUIgSNMEX0Wwicyg0Aowys" 
    url = f"https://securetoken.googleapis.com/v1/token?key={api_key}"
    payload = {"grant_type": "refresh_token", "refresh_token": refresh_token}
    
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()["id_token"]

def format_for_firestore(data: dict) -> dict:
    fields = {}
    for k, v in data.items():
        if isinstance(v, str): fields[k] = {"stringValue": v}
        elif isinstance(v, bool): fields[k] = {"booleanValue": v}
        elif isinstance(v, int): fields[k] = {"integerValue": str(v)}
        elif isinstance(v, float): fields[k] = {"doubleValue": float(v)}
        elif isinstance(v, (dict, list)): fields[k] = {"stringValue": json.dumps(v)}
        elif v is None: fields[k] = {"nullValue": None}
        else: fields[k] = {"stringValue": str(v)}
    return {"fields": fields}

def _upload_to_firestore(report_id: str, payload: dict, uid: str, id_token: str) -> bool:
    payload["userId"] = uid
    firestore_payload = format_for_firestore(payload)
    url = f"https://firestore.googleapis.com/v1/projects/{settings.firebase_project_id}/databases/(default)/documents/reports?documentId={report_id}"
    
    headers = {
        "Authorization": f"Bearer {id_token}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(url, headers=headers, json=firestore_payload, timeout=15)
        if response.status_code == 200:
            return True
        logger.warning(f"Cloud upload failed: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        logger.warning(f"Network error during cloud sync: {e}")
    return False

def process_outbox():
    pending_reports = SyncOutboxDAO.get_pending_reports(limit=10)
    if not pending_reports:
        return

    logger.info(f"Sync worker started. {len(pending_reports)} reports pending.")

    for report_id in pending_reports:
        payload, repo_path = _get_full_report_payload(report_id)
        if not payload:
            SyncOutboxDAO.mark_status(report_id, "failed", "Missing from DB")
            continue

        credentials = get_credentials(repo_path)
        if not credentials:
            logger.info(f"Skipping report {report_id}: No auth for repo {repo_path}")
            continue

        try:
            # Generate temporary token for upload
            id_token = _get_fresh_id_token(credentials["refresh_token"])
            success = _upload_to_firestore(report_id, payload, credentials["uid"], id_token)
            
            if success:
                SyncOutboxDAO.mark_status(report_id, "synced")
                logger.info(f"✅ Synced {report_id}")
            else:
                SyncOutboxDAO.mark_status(report_id, "failed", "Network/Auth Error")
        except Exception as e:
            logger.error(f"Token refresh failed for {report_id}: {e}")
            SyncOutboxDAO.mark_status(report_id, "failed", "Auth token expiration")
            
        time.sleep(1)

def trigger_sync_worker():
    cmd = [sys.executable, "-m", "preflight.cloud.sync_worker"]
    kwargs = {"creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP} if sys.platform == "win32" else {"start_new_session": True, "stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    try: subprocess.Popen(cmd, **kwargs)
    except Exception as e: logger.error(f"Spawn failed: {e}")

if __name__ == "__main__":
    process_outbox()