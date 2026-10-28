"""SQLite storage for audit runs and findings."""
import json
import sqlite3
from pathlib import Path

DB_PATH = Path("data/audits.db")


def get_connection(db_path=None):
    path = Path(db_path) if db_path else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(db_path=None):
    with get_connection(db_path) as connection:
        connection.execute("""CREATE TABLE IF NOT EXISTS audit_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            website_url TEXT NOT NULL,
            started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            page_count INTEGER NOT NULL DEFAULT 0,
            issue_count INTEGER NOT NULL DEFAULT 0,
            summary_json TEXT NOT NULL DEFAULT '{}'
        )""")
        connection.execute("""CREATE TABLE IF NOT EXISTS audit_findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_run_id INTEGER NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
            url TEXT NOT NULL,
            finding_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL
        )""")
        connection.execute("""CREATE TABLE IF NOT EXISTS lighthouse_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_run_id INTEGER NOT NULL REFERENCES audit_runs(id) ON DELETE CASCADE,
            category TEXT NOT NULL,
            score REAL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(audit_run_id, category)
        )""")


def create_audit_run(website_url, page_count, issue_count, summary, db_path=None):
    initialize_database(db_path)
    with get_connection(db_path) as connection:
        cursor = connection.execute(
            "INSERT INTO audit_runs (website_url,page_count,issue_count,summary_json) VALUES (?,?,?,?)",
            (website_url, page_count, issue_count, json.dumps(summary)),
        )
        return cursor.lastrowid


def save_findings(audit_run_id, findings, db_path=None):
    with get_connection(db_path) as connection:
        connection.executemany(
            "INSERT INTO audit_findings (audit_run_id,url,finding_type,severity,message) VALUES (?,?,?,?,?)",
            [(audit_run_id, f.get("url", ""), f.get("type", "unknown"),
              f.get("severity", "low"), f.get("message", "")) for f in findings],
        )


def list_runs(limit=20, db_path=None):
    initialize_database(db_path)
    with get_connection(db_path) as connection:
        rows = connection.execute(
            "SELECT * FROM audit_runs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]
