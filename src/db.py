"""
db.py - small helpers shared by the SQL-related scripts.
"""
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_FILE = ROOT / "data" / "northfield.db"
SQL_DIR = ROOT / "sql"


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def now() -> str:
    return datetime.now().replace(microsecond=0).isoformat(sep=" ")


def audit(conn, raw_row, actor, action, detail=""):
    """Write one line in the audit diary."""
    conn.execute(
        "INSERT INTO audit_log (ts, raw_row, actor, action, detail) VALUES (?, ?, ?, ?, ?)",
        (now(), raw_row, actor, action, detail),
    )


def run_sql_file(path: Path, conn=None, title_prefix="-- Q"):
    """Split a .sql file of '-- Q1: title' blocks and return [(title, columns, rows)]."""
    own = conn is None
    conn = conn or connect()
    blocks, title, lines = [], None, []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(title_prefix):
            if title and "".join(lines).strip():
                blocks.append((title, "\n".join(lines)))
            title, lines = line[3:].strip(), []
        elif title:
            lines.append(line)
    if title and "".join(lines).strip():
        blocks.append((title, "\n".join(lines)))
    results = []
    for t, q in blocks:
        cur = conn.execute(q)
        results.append((t, [d[0] for d in cur.description], cur.fetchall(), q.strip()))
    if own:
        conn.close()
    return results
