"""
db.py — SQLite schema and helper functions for the Typing Dynamics platform.

Two tables:
  sessions   : one row per completed writing task (metadata + label)
  keystrokes : one row per captured event (the raw behavioural layer)

The raw keystrokes layer is the ground truth. Feature extraction (Stage 2)
reads from it. Keep it intact — never delete it after collection.
"""

import json
import sqlite3
from pathlib import Path

# The database lives next to this file as a single portable file.
DB_PATH = Path(__file__).parent / "data.db"


def get_connection():
    """Open a connection with row access by column name and foreign keys on."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """Create tables if they do not exist. Safe to call on every startup."""
    conn = get_connection()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_id TEXT    NOT NULL,      -- who wrote (grouping key for ML CV)
            task_id        TEXT    NOT NULL,      -- which task
            task_prompt    TEXT    NOT NULL,      -- exact prompt shown
            started_at     INTEGER NOT NULL,      -- wall-clock epoch ms at start
            ended_at       INTEGER NOT NULL,      -- wall-clock epoch ms at finish
            duration_ms    INTEGER NOT NULL,      -- ended_at - started_at
            final_text     TEXT    NOT NULL,      -- submitted text
            char_count     INTEGER NOT NULL,      -- length of final_text
            word_count     INTEGER,               -- number of words in final_text
            quality_flags  TEXT,                  -- JSON list of content quality flags (review aid)
            included       INTEGER DEFAULT 1,     -- researcher decision: 1=include in ML, 0=exclude
            effort_rating  INTEGER NOT NULL,      -- SELF-RATED 1..5 (the ML label)
            paste_used     INTEGER NOT NULL,      -- 1 if any paste happened (integrity flag)
            user_agent     TEXT,                  -- browser/device string (remote studies)
            created_at     TEXT    DEFAULT (datetime('now'))  -- server insert time
        );

        CREATE TABLE IF NOT EXISTS keystrokes (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id    INTEGER NOT NULL,
            event_type    TEXT    NOT NULL,       -- 'keydown' | 'keyup' | 'paste'
            key_value     TEXT,                   -- the key (e.g. 'a', 'Backspace') or paste length
            t_ms          INTEGER NOT NULL,       -- ms since session start (monotonic)
            caret_pos     INTEGER,                -- selectionStart at event time (revision detection)
            selection_end INTEGER,                -- selectionEnd; caret_pos != selection_end => a range was selected
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_keystrokes_session ON keystrokes(session_id);
        """
    )
    _migrate(conn)
    conn.commit()
    conn.close()


def _migrate(conn):
    """Add newer columns to an already-existing sessions table (older data.db).

    CREATE TABLE IF NOT EXISTS never alters an existing table, so a database
    created before these columns existed needs them added here. Each ADD COLUMN
    is guarded so this is safe to run on every startup.
    """
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(sessions)")}
    additions = {
        "word_count": "ALTER TABLE sessions ADD COLUMN word_count INTEGER",
        "quality_flags": "ALTER TABLE sessions ADD COLUMN quality_flags TEXT",
        "included": "ALTER TABLE sessions ADD COLUMN included INTEGER DEFAULT 1",
    }
    for col, ddl in additions.items():
        if col not in existing:
            conn.execute(ddl)

    ks_cols = {row["name"] for row in conn.execute("PRAGMA table_info(keystrokes)")}
    if "selection_end" not in ks_cols:
        conn.execute("ALTER TABLE keystrokes ADD COLUMN selection_end INTEGER")


def insert_session(data):
    """
    Insert one completed session plus all its keystroke events atomically.
    `data` is the dict posted from the browser. Returns the new session id.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO sessions
                (participant_id, task_id, task_prompt, started_at, ended_at,
                 duration_ms, final_text, char_count, word_count, quality_flags,
                 included, effort_rating, paste_used, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["participant_id"].strip(),
                data["task_id"],
                data["task_prompt"],
                data["started_at"],
                data["ended_at"],
                data["ended_at"] - data["started_at"],
                data["final_text"],
                len(data["final_text"]),
                data.get("word_count", len(data["final_text"].split())),
                json.dumps(data.get("quality_flags", [])),
                1,  # every session is kept; researcher may exclude later in /admin
                data["effort_rating"],
                1 if data.get("paste_used") else 0,
                data.get("user_agent", ""),
            ),
        )
        session_id = cur.lastrowid

        events = data.get("events", [])
        cur.executemany(
            """
            INSERT INTO keystrokes
                (session_id, event_type, key_value, t_ms, caret_pos, selection_end)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (session_id, e["type"], e.get("key"), e["t"],
                 e.get("caret"), e.get("caretEnd"))
                for e in events
            ],
        )
        conn.commit()
        return session_id
    finally:
        conn.close()


def list_sessions():
    """Return a summary row per session, with its captured event count (for /admin)."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT s.id, s.participant_id, s.task_id, s.started_at, s.ended_at,
               s.duration_ms, s.char_count, s.word_count, s.quality_flags,
               s.included, s.final_text, s.effort_rating, s.paste_used,
               s.created_at,
               COUNT(k.id) AS event_count
        FROM sessions s
        LEFT JOIN keystrokes k ON k.session_id = s.id
        GROUP BY s.id
        ORDER BY s.id DESC
        """
    ).fetchall()
    conn.close()

    sessions = []
    for r in rows:
        d = dict(r)
        # Normalise columns that may be NULL on rows saved before these features.
        d["included"] = 1 if d["included"] is None else d["included"]
        try:
            d["quality_flags"] = json.loads(d["quality_flags"]) if d["quality_flags"] else []
        except (TypeError, ValueError):
            d["quality_flags"] = []
        if d["word_count"] is None:
            d["word_count"] = len((d["final_text"] or "").split())
        sessions.append(d)
    return sessions


def set_included(session_id, included):
    """Researcher toggle: mark a session as included (1) or excluded (0) from ML."""
    conn = get_connection()
    cur = conn.execute(
        "UPDATE sessions SET included = ? WHERE id = ?",
        (1 if included else 0, session_id),
    )
    conn.commit()
    changed = cur.rowcount
    conn.close()
    return changed > 0


def list_all_keystrokes():
    """Every keystroke event across all sessions, with its session context.

    One row per event — this is the full raw behavioural layer, exported so the
    researcher can download/back it up. Stage 2 reads the same data to build the
    feature table.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT k.session_id, s.participant_id, s.task_id,
               k.event_type, k.key_value, k.t_ms, k.caret_pos, k.selection_end
        FROM keystrokes k
        JOIN sessions s ON s.id = k.session_id
        ORDER BY k.session_id, k.t_ms, k.id
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_session_detail(session_id):
    """Return one session's full record plus its events (for verification)."""
    conn = get_connection()
    session = conn.execute(
        "SELECT * FROM sessions WHERE id = ?", (session_id,)
    ).fetchone()
    events = conn.execute(
        "SELECT event_type, key_value, t_ms, caret_pos, selection_end FROM keystrokes "
        "WHERE session_id = ? ORDER BY t_ms, id",
        (session_id,),
    ).fetchall()
    conn.close()
    if session is None:
        return None
    return {"session": dict(session), "events": [dict(e) for e in events]}
