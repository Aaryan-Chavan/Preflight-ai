import sqlite3
import json
import uuid
from datetime import datetime

conn = sqlite3.connect("preflight.db")
cursor = conn.cursor()

# 1. Create the table that your orchestrator forgot to commit
cursor.execute('''
CREATE TABLE IF NOT EXISTS reports (
    report_id TEXT PRIMARY KEY,
    timestamp TEXT,
    branch TEXT,
    decision TEXT,
    outcome TEXT,
    analysis_ms INTEGER,
    popup_payload TEXT
)
''')

# 2. Inject your exact pipeline results from your last successful push
mock_id = str(uuid.uuid4())
popup_data = json.dumps({
    "repo_name": "preflight-ai",
    "branch": "main",
    "risk_level": "LOW",
    "confidence_percentage": 98,
    "files_modified_count": 3,
    "critical_functions": [],
    "impact_summary": ["ML risk score and confidence embedded.", "Low-risk commits bypass LLM review."],
    "verification_checklist": ["Verify that serviceAccountKey.json is not present", "Confirm dynamic SQL query uses parameterized statements"],
    "ai_recommendation": "Commit is structurally sound and low risk. Proceed with push."
})

cursor.execute('''
INSERT INTO reports (report_id, timestamp, branch, decision, outcome, analysis_ms, popup_payload)
VALUES (?, ?, ?, ?, ?, ?, ?)
''', (mock_id, datetime.now().isoformat(), "main", "PASSED", "SUCCESS", 57632, popup_data))

# 3. THIS is the line your DAO is missing!
conn.commit()
conn.close()

print("✅ Table created and pipeline record securely committed to SQLite!")