import sqlite3
import json
import os
import firebase_admin
from firebase_admin import credentials, firestore

# 1. Initialize Firebase Admin
cred_path = "serviceAccountKey.json"
if not os.path.exists(cred_path):
    print(f"Error: Could not find Firebase service account key at '{cred_path}'.")
    exit(1)

cred = credentials.Certificate(cred_path)
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

# 2. Find 'preflight.db' automatically
def find_db():
    for root, dirs, files in os.walk("."):
        if "preflight.db" in files:
            return os.path.join(root, "preflight.db")
    return None

def sync_reports():
    db_path = find_db()
    if not db_path:
        print("Error: Could not find 'preflight.db' anywhere in the project.")
        return

    print(f"Found database at: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Inspect available tables in SQLite
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row["name"] for row in cursor.fetchall()]
    print(f"Available SQLite tables: {tables}")

    if not tables:
        print("Error: No tables found in the SQLite database yet. Run a git push to generate reports.")
        conn.close()
        return

    # Pick the most likely table name
    target_table = "reports" if "reports" in tables else tables[0]
    print(f"Reading from table: '{target_table}'...")

    try:
        cursor.execute(f"SELECT * FROM {target_table} ORDER BY timestamp DESC LIMIT 20")
        rows = cursor.fetchall()
    except Exception as e:
        print(f"Error querying table {target_table}: {e}")
        conn.close()
        return

    print(f"Found {len(rows)} local report(s). Syncing to Firestore...")

    for row in rows:
        report_data = dict(row)
        report_id = str(report_data.get("report_id") or report_data.get("id") or "unknown-id")

        # Safely parse JSON fields if stored as strings
        for field in ["popup_payload", "popup", "meta"]:
            if field in report_data and isinstance(report_data[field], str):
                try:
                    report_data[field] = json.loads(report_data[field])
                except:
                    pass

        # Push to Firestore collection 'reports'
        doc_ref = db.collection("reports").document(report_id)
        doc_ref.set(report_data, merge=True)
        print(f"Synced report {report_id} -> Firestore")

    conn.close()
    print("Sync complete!")

if __name__ == "__main__":
    sync_reports()