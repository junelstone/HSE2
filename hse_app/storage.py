"""SQLite storage for inspections and corrective actions.

The database file defaults to ``data/inspections.db`` and can be changed with
the ``HSE_DB_PATH`` environment variable.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

from . import scoring

DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "inspections.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS inspections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    inspection_date TEXT,
    site TEXT,
    installation TEXT,
    inspectors TEXT,
    department TEXT,
    stage_id TEXT,
    lang TEXT,
    comments TEXT,
    score REAL,
    critical_nc INTEGER,
    pdf BLOB
);
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inspection_id INTEGER NOT NULL REFERENCES inspections(id) ON DELETE CASCADE,
    item_id TEXT NOT NULL,
    section_id TEXT,
    item_text TEXT,
    criticality TEXT,
    status TEXT,
    observation TEXT,
    action TEXT,
    owner TEXT,
    due_date TEXT,
    priority TEXT,
    action_closed INTEGER NOT NULL DEFAULT 0,
    closed_at TEXT,
    closed_by TEXT,
    closing_note TEXT
);
CREATE TABLE IF NOT EXISTS drafts (
    id TEXT PRIMARY KEY,
    updated_at TEXT NOT NULL,
    data TEXT NOT NULL
);
"""

# Columns added after the first release: added to older databases on connect.
MIGRATIONS = {"results": {"closed_by": "TEXT", "closing_note": "TEXT"}}


def _migrate(conn) -> None:
    for table, columns in MIGRATIONS.items():
        existing = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        for name, kind in columns.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {kind}")


def db_path() -> Path:
    return Path(os.environ.get("HSE_DB_PATH", DEFAULT_DB))


@contextmanager
def connect(path: Path | str | None = None):
    path = Path(path) if path else db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.executescript(SCHEMA)
        _migrate(conn)
        yield conn
        conn.commit()
    finally:
        conn.close()


def save_inspection(inspection: dict, sections: list, pdf: bytes, path=None) -> int:
    results = inspection.get("results", {})
    total = scoring.overall(sections, results)
    critical = scoring.critical_findings(sections, results)
    lang = inspection.get("lang", "fr")
    with connect(path) as conn:
        cur = conn.execute(
            "INSERT INTO inspections (created_at, inspection_date, site, installation, inspectors,"
            " department, stage_id, lang, comments, score, critical_nc, pdf)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (datetime.now().isoformat(timespec="seconds"), inspection.get("date"), inspection.get("site"),
             inspection.get("installation"), inspection.get("inspectors"), inspection.get("department"),
             inspection.get("stage_id"), lang, inspection.get("comments"), total.percent,
             len(critical), pdf),
        )
        inspection_id = cur.lastrowid
        for section in sections:
            for item in section.items:
                res = results.get(item.id) or {}
                conn.execute(
                    "INSERT INTO results (inspection_id, item_id, section_id, item_text, criticality,"
                    " status, observation, action, owner, due_date, priority)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (inspection_id, item.id, section.id, item.label(lang), item.criticality,
                     res.get("status"), res.get("observation"), res.get("action"), res.get("owner"),
                     res.get("due"), res.get("priority")),
                )
    return inspection_id


def list_inspections(path=None) -> list:
    with connect(path) as conn:
        rows = conn.execute(
            "SELECT id, inspection_date, site, installation, inspectors, stage_id, score, critical_nc"
            " FROM inspections ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


def get_pdf(inspection_id: int, path=None) -> bytes | None:
    with connect(path) as conn:
        row = conn.execute("SELECT pdf FROM inspections WHERE id = ?", (inspection_id,)).fetchone()
    return bytes(row["pdf"]) if row and row["pdf"] is not None else None


def open_actions(path=None, today: date | None = None) -> list:
    today = (today or date.today()).isoformat()
    with connect(path) as conn:
        rows = conn.execute(
            "SELECT r.id, r.inspection_id, i.site, r.item_id, r.item_text, r.criticality, r.action,"
            " r.owner, r.due_date, r.priority,"
            " CASE WHEN r.due_date IS NOT NULL AND r.due_date <> '' AND r.due_date < ? THEN 1 ELSE 0 END"
            " AS overdue"
            " FROM results r JOIN inspections i ON i.id = r.inspection_id"
            " WHERE r.status = ? AND r.action_closed = 0"
            " ORDER BY overdue DESC, r.due_date IS NULL, r.due_date, r.id",
            (today, scoring.NON_CONFORM)).fetchall()
    return [dict(r) for r in rows]


def close_action(result_id: int, path=None, closed_by: str = "", note: str = "") -> None:
    """Close a corrective action, recording who closed it and how."""
    with connect(path) as conn:
        conn.execute("UPDATE results SET action_closed = 1, closed_at = ?, closed_by = ?, closing_note = ?"
                     " WHERE id = ?",
                     (datetime.now().isoformat(timespec="seconds"), closed_by, note, result_id))


def closed_actions(path=None, limit: int = 50) -> list:
    with connect(path) as conn:
        rows = conn.execute(
            "SELECT r.inspection_id, i.site, r.item_id, r.item_text, r.action, r.owner, r.closed_at,"
            " r.closed_by, r.closing_note"
            " FROM results r JOIN inspections i ON i.id = r.inspection_id"
            " WHERE r.action_closed = 1 ORDER BY r.closed_at DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def all_results(path=None) -> list:
    """Every checklist answer with its inspection header, for the Excel export."""
    with connect(path) as conn:
        rows = conn.execute(
            "SELECT i.id AS inspection_id, i.inspection_date, i.site, i.installation, i.inspectors,"
            " i.stage_id, r.section_id, r.item_id, r.item_text, r.criticality, r.status, r.observation,"
            " r.action, r.owner, r.due_date, r.priority, r.action_closed, r.closed_at, r.closed_by,"
            " r.closing_note"
            " FROM results r JOIN inspections i ON i.id = r.inspection_id"
            " ORDER BY i.id DESC, r.id").fetchall()
    return [dict(r) for r in rows]


def known_sites(path=None) -> tuple[list, list]:
    """Sites and installations used before, most recent first, for quick picking."""
    with connect(path) as conn:
        sites = [r[0] for r in conn.execute(
            "SELECT site FROM inspections WHERE site <> '' GROUP BY site ORDER BY MAX(id) DESC")]
        installs = [r[0] for r in conn.execute(
            "SELECT installation FROM inspections WHERE installation <> ''"
            " GROUP BY installation ORDER BY MAX(id) DESC")]
    return sites, installs


# Drafts: an inspection in progress, kept so a refresh or lost signal does not lose it.

def save_draft(draft_id: str, data: dict, path=None) -> None:
    with connect(path) as conn:
        conn.execute("INSERT INTO drafts (id, updated_at, data) VALUES (?,?,?)"
                     " ON CONFLICT(id) DO UPDATE SET updated_at = excluded.updated_at, data = excluded.data",
                     (draft_id, datetime.now().isoformat(timespec="seconds"), json.dumps(data)))


def load_draft(draft_id: str, path=None) -> dict | None:
    with connect(path) as conn:
        row = conn.execute("SELECT data FROM drafts WHERE id = ?", (draft_id,)).fetchone()
    return json.loads(row["data"]) if row else None


def delete_draft(draft_id: str, path=None) -> None:
    with connect(path) as conn:
        conn.execute("DELETE FROM drafts WHERE id = ?", (draft_id,))
