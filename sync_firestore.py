import sqlite3
import json
import os
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from platformdirs import PlatformDirs

# 1. Initialize Firebase
cred_path = os.path.abspath("serviceAccountKey.json")
if not os.path.exists(cred_path):
    print(f"Error: Could not find '{cred_path}'.")
    exit(1)

cred = credentials.Certificate(cred_path)
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()

def sync_reports():
    # 2. Match your app's exact path logic
    dirs = PlatformDirs(appname="preflight-ai", appauthor=False)
    db_path = os.path.join(dirs.user_data_dir, "preflight.db")
    
    print(f"Connecting to database at: {db_path}")
    
    if not os.path.exists(db_path):
        print("Error: Database not found. Run a git push first!")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 3. Read pending reports from the 3-table normalized schema
    query = """
        SELECT 
            p.report_id, p.branch, p.timestamp, p.risk_level, 
            p.confidence, p.decision, p.outcome, p.analysis_ms,
            r.popup_json, r.detailed_md
        FROM pushes p
        JOIN reports r ON p.report_id = r.report_id
        JOIN sync_outbox s ON p.report_id = s.report_id
        WHERE s.status = 'pending'
        ORDER BY p.timestamp ASC
    """
    
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
    except Exception as e:
        print(f"Error reading tables: {e}")
        conn.close()
        return

    if not rows:
        print("No pending reports found in the outbox. You are fully synced!")
        conn.close()
        return

    print(f"Found {len(rows)} pending report(s). Syncing to Firestore...")

    for row in rows:
        report_data = dict(row)
        report_id = report_data["report_id"]

        # Parse JSON payload so Firestore stores it as an object
        if report_data.get("popup_json"):
            try:
                report_data["popup"] = json.loads(report_data.pop("popup_json"))
            except Exception:
                pass
                
        # Convert SQLite text string to a native Firestore Timestamp
        if report_data.get("timestamp"):
            try:
                report_data["timestamp"] = datetime.fromisoformat(report_data["timestamp"])
            except Exception as e:
                print(f"Timestamp error for {report_id}: {e}")

        # Sync to Firestore
        doc_ref = db.collection("reports").document(report_id)
        doc_ref.set(report_data, merge=True)
        print(f"Synced report {report_id} -> Firestore")

        # Mark as synced locally
        cursor.execute("UPDATE sync_outbox SET status = 'synced' WHERE report_id = ?", (report_id,))

    conn.commit()
    conn.close()
    print("Sync queue cleared successfully!")

if __name__ == "__main__":
    sync_reports()