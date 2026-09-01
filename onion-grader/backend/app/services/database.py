"""SQLite persistence (development). Production swaps to Supabase/PostgreSQL
by migrating these statements to SQLAlchemy — the schema is identical.

Privacy: we store analysis facts + small processed thumbnails ONLY.
No usernames, no phone numbers, no personal identifiers. The onion is the
only subject of this database.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone

from app.core.config import DATA_DIR

DB_PATH = DATA_DIR / "onion.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS analyses (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    filename TEXT, format TEXT, img_w INTEGER, img_h INTEGER,
    onion_found INTEGER NOT NULL,
    quality_score INTEGER, grade TEXT, rule_version TEXT,
    defects_json TEXT, reasons_json TEXT, breakdown_json TEXT,
    analysis_confidence REAL, diameter_px REAL, circularity REAL,
    recommendation TEXT, onion_count INTEGER DEFAULT 1,
    thumb_b64 TEXT, annotated_b64 TEXT
);
CREATE TABLE IF NOT EXISTS batch_runs (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    total_onions INTEGER, analysed_ok INTEGER,
    grade_a_pct REAL, grade_b_pct REAL, grade_c_pct REAL, urs_pct REAL,
    undetermined INTEGER, avg_score REAL,
    summary_json TEXT
);
CREATE TABLE IF NOT EXISTS eval_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    actual TEXT, predicted TEXT, confidence REAL,
    correct INTEGER, score INTEGER, grade TEXT, filename TEXT
);
"""


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(SCHEMA)


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ------------------------------------------------------------------ #
def save_analysis(row: dict) -> None:
    with _connect() as conn:
        conn.execute(
            """INSERT INTO analyses (id, created_at, filename, format, img_w, img_h,
               onion_found, quality_score, grade, rule_version, defects_json,
               reasons_json, breakdown_json, analysis_confidence, diameter_px,
               circularity, recommendation, onion_count, thumb_b64, annotated_b64)
               VALUES (:id,:created_at,:filename,:format,:img_w,:img_h,:onion_found,
               :quality_score,:grade,:rule_version,:defects_json,:reasons_json,
               :breakdown_json,:analysis_confidence,:diameter_px,:circularity,
               :recommendation,:onion_count,:thumb_b64,:annotated_b64)""",
            row,
        )


def get_analysis(analysis_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM analyses WHERE id=?", (analysis_id,)).fetchone()
    return dict(row) if row else None


def recent_analyses(limit: int = 10) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            """SELECT id, created_at, filename, onion_found, quality_score, grade,
                      defects_json, analysis_confidence, diameter_px
               FROM analyses ORDER BY created_at DESC LIMIT ?""", (limit,)
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["defects"] = json.loads(d.pop("defects_json") or "[]")
        d["defects"] = [x["label"] for x in d["defects"] if x.get("status") == "detected"]
        out.append(d)
    return out


def save_batch(row: dict) -> None:
    with _connect() as conn:
        conn.execute(
            """INSERT INTO batch_runs (id, created_at, total_onions, analysed_ok,
               grade_a_pct, grade_b_pct, grade_c_pct, urs_pct, undetermined,
               avg_score, summary_json)
               VALUES (:id,:created_at,:total_onions,:analysed_ok,:grade_a_pct,
               :grade_b_pct,:grade_c_pct,:urs_pct,:undetermined,:avg_score,:summary_json)""",
            row,
        )


def get_batch(batch_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM batch_runs WHERE id=?", (batch_id,)).fetchone()
    return dict(row) if row else None


def save_eval(row: dict) -> None:
    with _connect() as conn:
        conn.execute(
            """INSERT INTO eval_results (created_at, actual, predicted, confidence,
               correct, score, grade, filename)
               VALUES (:created_at,:actual,:predicted,:confidence,:correct,
               :score,:grade,:filename)""", row)


def all_eval_results(limit: int = 200) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM eval_results ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


init_db()   # create tables at import time (cheap, idempotent)
