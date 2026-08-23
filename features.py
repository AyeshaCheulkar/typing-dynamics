"""
features.py — Stage 2: turn the RAW keystroke layer into a per-session feature
table for the writing-effort model.

Input  : server_export.csv      (one row per session: metadata + effort label)
         server_keystrokes.csv  (one row per keystroke event)
Output : features.csv           (one row per session: behavioural features + label)

Design principle: THE SAME extractor must run on external keystroke datasets too
(Strategy A/B). So it depends only on a generic event stream of
    (session_id, event_type, key_value, t_ms, caret_pos, selection_end)
and never on anything specific to our platform. Any dataset reshaped to those
columns can be fed through `extract_features`.

Feature groups (the behavioural constructs the project set out to measure):
  - Writing time   : how long the session actively ran
  - Typing speed   : characters / keystrokes per second, inter-key interval (IKI)
  - Pauses         : how often and how long the writer stopped (thinking pauses)
  - Deletion       : backspace/delete usage
  - Revision       : how many separate editing bursts occurred
Plus data-quality columns so unusable behavioural streams can be filtered:
  - unid_rate         : fraction of keydowns whose key could not be identified
  - behavioural_valid : 1 if the keystroke stream can yield trustworthy features
"""

import csv
import statistics

# --- Tunable thresholds (documented so they can be justified in the thesis) ---
# Pause thresholds in ms. 500ms ~ a brief hesitation; 2000ms ~ a genuine
# thinking/planning pause. Both are common cut-offs in keystroke-logging research.
PAUSE_SHORT_MS = 500
PAUSE_LONG_MS = 2000

# Keys that do NOT produce a text character but are still meaningful.
DELETE_KEYS = {"Backspace", "Delete"}
# Non-character control/navigation keys to ignore when counting "typed characters".
NON_CHAR_KEYS = {
    "Shift", "CapsLock", "Control", "Alt", "Meta", "Tab", "Enter",
    "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End",
    "PageUp", "PageDown", "NumLock", "Escape", "F1", "F2", "F3", "F4",
    "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12", "Insert",
}

# Behavioural-validity rule: below this many keydowns, or above this Unidentified
# fraction, the keystroke stream cannot be trusted for typing-dynamics features
# (e.g. mobile/IME keyboards that emit "Unidentified" or paste-like autofill).
MIN_KEYDOWNS = 40
MAX_UNID_RATE = 0.30


def _safe(fn, default=0.0):
    try:
        return fn()
    except (ValueError, statistics.StatisticsError, ZeroDivisionError):
        return default


def extract_features(events, char_count):
    """Compute the behavioural feature dict for ONE session.

    `events`     : list of dicts with keys event_type, key_value, t_ms,
                   caret_pos, selection_end (t_ms already ms-since-start).
    `char_count` : length of the final submitted text (from the session row).
    """
    keydowns = [e for e in events if e["event_type"] == "keydown"]
    keydowns.sort(key=lambda e: e["t_ms"])

    n_kd = len(keydowns)
    unid = sum(1 for e in keydowns if e["key_value"] == "Unidentified")
    unid_rate = unid / n_kd if n_kd else 1.0

    # --- Writing time: span of the keystroke stream (ms) --------------------
    if n_kd >= 2:
        active_ms = keydowns[-1]["t_ms"] - keydowns[0]["t_ms"]
    else:
        active_ms = 0
    active_s = active_ms / 1000.0

    # --- Inter-key intervals (gaps between consecutive keydowns) ------------
    ikis = [keydowns[i]["t_ms"] - keydowns[i - 1]["t_ms"] for i in range(1, n_kd)]

    # --- Typing speed -------------------------------------------------------
    chars_per_sec = char_count / active_s if active_s > 0 else 0.0
    keys_per_sec = n_kd / active_s if active_s > 0 else 0.0

    median_iki = _safe(lambda: statistics.median(ikis))
    mean_iki = _safe(lambda: statistics.fmean(ikis))
    std_iki = _safe(lambda: statistics.pstdev(ikis)) if len(ikis) > 1 else 0.0

    # --- Pauses (IKIs above the thresholds are "pauses") --------------------
    short_pauses = [g for g in ikis if g >= PAUSE_SHORT_MS]
    long_pauses = [g for g in ikis if g >= PAUSE_LONG_MS]
    total_pause_ms = sum(short_pauses)
    pause_time_ratio = total_pause_ms / active_ms if active_ms > 0 else 0.0
    max_pause_ms = max(ikis) if ikis else 0
    # normalise pause counts per 100 keystrokes so long/short sessions compare
    n_short_per_100 = 100 * len(short_pauses) / n_kd if n_kd else 0.0
    n_long_per_100 = 100 * len(long_pauses) / n_kd if n_kd else 0.0

    # --- Deletion -----------------------------------------------------------
    n_delete = sum(1 for e in keydowns if e["key_value"] in DELETE_KEYS)
    delete_rate = n_delete / n_kd if n_kd else 0.0

    # --- Revision bursts: maximal runs of delete keys = one editing act -----
    revision_bursts = 0
    prev_del = False
    for e in keydowns:
        is_del = e["key_value"] in DELETE_KEYS
        if is_del and not prev_del:
            revision_bursts += 1
        prev_del = is_del
    revisions_per_100 = 100 * revision_bursts / n_kd if n_kd else 0.0

    behavioural_valid = 1 if (n_kd >= MIN_KEYDOWNS and unid_rate <= MAX_UNID_RATE) else 0

    return {
        "n_keydown": n_kd,
        "char_count": char_count,
        "active_time_s": round(active_s, 2),
        # speed
        "chars_per_sec": round(chars_per_sec, 3),
        "keys_per_sec": round(keys_per_sec, 3),
        "median_iki_ms": round(median_iki, 1),
        "mean_iki_ms": round(mean_iki, 1),
        "std_iki_ms": round(std_iki, 1),
        # pauses
        "n_short_pause_per_100": round(n_short_per_100, 2),
        "n_long_pause_per_100": round(n_long_per_100, 2),
        "pause_time_ratio": round(pause_time_ratio, 3),
        "max_pause_ms": max_pause_ms,
        # deletion / revision
        "n_delete": n_delete,
        "delete_rate": round(delete_rate, 3),
        "n_revision_bursts": revision_bursts,
        "revisions_per_100": round(revisions_per_100, 2),
        # data quality
        "unid_rate": round(unid_rate, 3),
        "behavioural_valid": behavioural_valid,
    }


def load_events_by_session(keystrokes_csv):
    """Group raw keystroke rows by session_id -> list of event dicts."""
    by_sess = {}
    with open(keystrokes_csv, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            by_sess.setdefault(r["session_id"], []).append({
                "event_type": r["event_type"],
                "key_value": r["key_value"],
                "t_ms": int(r["t_ms"]),
                "caret_pos": r["caret_pos"],
                "selection_end": r["selection_end"],
            })
    return by_sess


def build(sessions_csv="server_export.csv",
          keystrokes_csv="server_keystrokes.csv",
          out_csv="features.csv",
          included_only=True):
    """Build the per-session feature table and write it to `out_csv`."""
    events_by_sess = load_events_by_session(keystrokes_csv)

    rows_out = []
    with open(sessions_csv, newline="", encoding="utf-8") as f:
        for s in csv.DictReader(f):
            if included_only and s["included"] != "1":
                continue
            events = events_by_sess.get(s["id"], [])
            feats = extract_features(events, int(s["char_count"]))
            row = {
                # identity / grouping / label first
                "session_id": int(s["id"]),
                "participant_id": s["participant_id"],
                "task_id": s["task_id"],
                "difficulty": s["difficulty"],
                "word_count": int(s["word_count"]),
                "effort_rating": int(s["effort_rating"]),   # <-- ML target
                "paste_used": int(s["paste_used"]),
                **feats,
            }
            rows_out.append(row)

    rows_out.sort(key=lambda r: r["session_id"])
    fieldnames = list(rows_out[0].keys())
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows_out)

    return rows_out


if __name__ == "__main__":
    rows = build()
    valid = [r for r in rows if r["behavioural_valid"] == 1]
    print(f"Wrote features.csv: {len(rows)} sessions "
          f"({len(valid)} behaviourally valid, "
          f"{len(rows) - len(valid)} flagged).")
    dropped = [r for r in rows if r["behavioural_valid"] == 0]
    if dropped:
        print("Flagged (unusable keystroke stream):")
        for r in dropped:
            print(f"  session {r['session_id']:>3} ({r['participant_id']}): "
                  f"n_keydown={r['n_keydown']}, unid_rate={r['unid_rate']}")
