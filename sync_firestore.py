import sqlite3
import json
import os
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# 1. Initialize Firebase Admin
# Make sure you have downloaded your service account JSON from Firebase Console 
# and saved it as 'serviceAccountKey.json' in your root folder.
cred_path = "serviceAccountKey.json"
if not os.path.exists(cred_path):
    print(f"Error: Could not find Firebase service account key at '{cred_path}'.")
    print("Please download it from your Firebase Project Settings -> Service Accounts.")
    exit(1)

cred = credentials.Certificate(cred_path)
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

def sync_reports():
    conn = sqlite3.connect("preflight.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Fetch reports from local SQLite database
    try:
        cursor.execute("SELECT * FROM reports ORDER BY timestamp DESC LIMIT 20")
        rows = cursor.fetchall()
    except Exception as e:
        print(f"Error reading SQLite database: {e}")
        return

    print(f"Found {len(rows)} local report(s). Syncing to Firestore...")

    for row in rows:
        report_data = dict(row)
        report_id = str(report_data.get("report_id"))

        # Convert JSON strings back to dicts if stored as text
        if "popup_payload" in report_data and isinstance(report_data["popup_payload"], str):
            try:
                report_data["popup_payload"] = json.loads(report_data["popup_payload"])
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