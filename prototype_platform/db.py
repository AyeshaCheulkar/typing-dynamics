"""
db.py — the PROTOTYPE's own SQLite layer. Completely separate from the Stage-1
research database: this writes only to prototype_platform/prototype.db and never
opens ../data.db.

Tables (prefixed pt_ to make the separation unmistakable):
  pt_sessions   — one row per writing session
  pt_keystrokes — one row per captured keystroke event

Note the DELIBERATE separation of the three concepts as separate columns:
  self_rated_effort   (the participant's own 1-5 label)
  predicted_effort    (the EXPERIMENTAL model estimate; nullable)
"""

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "prototype.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS pt_sessions (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_code  TEXT    NOT NULL,
            task_id           TEXT    NOT NULL,
            difficulty        TEXT,
            started_at        INTEGER NOT NULL,
            ended_at          INTEGER NOT NULL,
            duration_ms       INTEGER NOT NULL,
            final_text        TEXT    NOT NULL,
            char_count        INTEGER NOT NULL,
            word_count        INTEGER NOT NULL,
            self_rated_effort INTEGER,           -- participant's own 1-5 label
            predicted_effort  REAL,              -- EXPERIMENTAL estimate (nullable)
            behavioural_valid INTEGER DEFAULT 1,
            features_json     TEXT,              -- full feature dict for the dashboard
            created_at        TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS pt_keystrokes (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id    INTEGER NOT NULL,
            event_type    TEXT    NOT NULL,
            key_value     TEXT,
            t_ms          INTEGER NOT NULL,
            caret_pos     INTEGER,
            selection_end INTEGER,
            FOREIGN KEY (session_id) REFERENCES pt_sessions(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_pt_ks_session ON pt_keystrokes(session_id);
        """
    )
    conn.commit()
    conn.close()


def insert_session(meta, events, features, predicted_effort):
    """Store one session + its keystrokes. Returns the new session id."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO pt_sessions
                (participant_code, task_id, difficulty, started_at, ended_at,
                 duration_ms, final_text, char_count, word_count,
                 self_rated_effort, predicted_effort, behavioural_valid,
                 features_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                meta["participant_code"], meta["task_id"], meta.get("difficulty"),
                meta["started_at"], meta["ended_at"],
                meta["ended_at"] - meta["started_at"],
                meta["final_text"], len(meta["final_text"]),
                len(meta["final_text"].split()),
                meta.get("self_rated_effort"),
                predicted_effort,
                int(features.get("behavioural_valid", 1)),
                json.dumps(features),
            ),
        )
        sid = cur.lastrowid
        cur.executemany(
            """
            INSERT INTO pt_keystrokes
                (session_id, event_type, key_value, t_ms, caret_pos, selection_end)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (sid, e.get("type"), e.get("key"), e.get("t"),
                 e.get("caret"), e.get("caretEnd"))
                for e in events
            ],
        )
        conn.commit()
        return sid
    finally:
        conn.close()


def get_session(session_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM pt_sessions WHERE id = ?",
                       (session_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    d = dict(row)
    d["features"] = json.loads(d["features_json"]) if d["features_json"] else {}
    return d


def list_sessions():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM pt_sessions ORDER BY id DESC").fetchall()
    conn.close()
    out = []
    for r in rows:
        d = dict(r)
        d["features"] = json.loads(d["features_json"]) if d["features_json"] else {}
        out.append(d)
    return out


def get_keystrokes(session_id):
    """Return this session's captured events (for the writing timeline)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT event_type, key_value, t_ms, caret_pos, selection_end "
        "FROM pt_keystrokes WHERE session_id = ? ORDER BY t_ms, id",
        (session_id,)).fetchall()
    conn.close()
    return [{"type": r["event_type"], "key": r["key_value"], "t": r["t_ms"],
             "caret": r["caret_pos"], "caretEnd": r["selection_end"]} for r in rows]


def list_for_participant(code):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM pt_sessions WHERE participant_code = ? ORDER BY id ASC",
        (code,)).fetchall()
    conn.close()
    out = []
    for r in rows:
        d = dict(r)
        d["features"] = json.loads(d["features_json"]) if d["features_json"] else {}
        out.append(d)
    return out


def clear_all():
    """Wipe all live platform submissions (sessions + keystrokes). Start afresh."""
    conn = get_connection()
    conn.execute("DELETE FROM pt_keystrokes")
    conn.execute("DELETE FROM pt_sessions")
    conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('pt_sessions','pt_keystrokes')")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"initialised {DB_PATH}")
