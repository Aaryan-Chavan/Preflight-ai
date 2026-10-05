import sqlite3
from contextlib import contextmanager
from typing import Generator
from loguru import logger

from preflight.config.paths import DB_PATH

# -----------------------------------------------------------------------------
# Connection Factory
# -----------------------------------------------------------------------------
@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager yielding a highly optimized SQLite connection.
    Enables WAL mode for concurrent reads/writes and enforces foreign keys.
    """
    # Ensure the parent directory exists before connecting
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    
    # Return rows as dictionary-like objects instead of plain tuples
    conn.row_factory = sqlite3.Row
    
    try:
        # High-performance pragmas for concurrent pipeline execution
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA temp_store=MEMORY;")
        yield conn
    finally:
        conn.close()

# -----------------------------------------------------------------------------
# Schema & Migrations Engine
# -----------------------------------------------------------------------------
def _run_migrations(conn: sqlite3.Connection):
    """
    Reads the PRAGMA user_version and applies sequential schema updates.
    """
    current_version = conn.execute("PRAGMA user_version;").fetchone()[0]
    
    if current_version < 1:
        logger.info("Initializing SQLite database schema (Version 1)...")
        _migrate_v0_to_v1(conn)
        conn.execute("PRAGMA user_version = 1;")
        conn.commit()

def _migrate_v0_to_v1(conn: sqlite3.Connection):
    """
    V1 Schema Definition based on Blueprint Section 4.
    """
    cursor = conn.cursor()
    
    # 1. Metadata Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            schema_version INTEGER NOT NULL,
            install_id TEXT NOT NULL,
            uid TEXT
        );
    """)

    # 2. Repositories Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS repositories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            remote_url TEXT,
            enabled BOOLEAN DEFAULT 1
        );
    """)

    # 3. Pushes Table (The core report tracking)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pushes (
            report_id TEXT PRIMARY KEY,
            repo_id INTEGER NOT NULL,
            branch TEXT NOT NULL,
            local_sha TEXT NOT NULL,
            remote_sha TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            risk_level TEXT,
            risk_prob REAL,
            confidence REAL,
            decision TEXT,
            outcome TEXT,
            analysis_ms INTEGER,
            pipeline_version TEXT,
            model_version TEXT,
            FOREIGN KEY(repo_id) REFERENCES repositories(id) ON DELETE CASCADE
        );
    """)

    # 4. Reports Content Table (Separated for fast list queries on pushes)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            report_id TEXT PRIMARY KEY,
            popup_json TEXT NOT NULL,
            detailed_md TEXT,
            detailed_status TEXT DEFAULT 'pending',
            FOREIGN KEY(report_id) REFERENCES pushes(report_id) ON DELETE CASCADE
        );
    """)

    # 5. Cloud Sync Outbox
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_outbox (
            report_id TEXT PRIMARY KEY,
            status TEXT DEFAULT 'pending', 
            attempts INTEGER DEFAULT 0,
            next_try DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_error TEXT,
            FOREIGN KEY(report_id) REFERENCES pushes(report_id) ON DELETE CASCADE
        );
    """)

    # 6. LLM Content Cache (Speeds up repeated analyses of unchanged code)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS llm_cache (
            hunk_hash TEXT PRIMARY KEY,
            prompt_version TEXT NOT NULL,
            output TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)

def initialize_database():
    """
    Bootstraps the database. 
    Called by `preflight setup` to ensure tables exist before the first push.
    """
    # Ensure the parent directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with get_connection() as conn:
        _run_migrations(conn)

if __name__ == "__main__":
    initialize_database()