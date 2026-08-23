"""
external_data.py — Step 4: run EXTERNAL keystroke datasets through the SAME
feature extractor as our own data (features.py), so external and own features
live in one shared feature space (the requirement for Strategy A / B).

The problem every external dataset poses: it stores keystrokes in its own column
layout. This module normalises any such layout into our generic event stream
    (event_type, key_value, t_ms)
and then calls the very same `extract_features()` used on our data. Nothing about
the feature definitions changes — only the plumbing that feeds them.

How to use once you have downloaded a dataset:
    1. Look at the file's real header row.
    2. Pick/adjust a PRESET below so the column names match.
    3. build_external_features("Free_Text.csv", EMOSURV, "external_features.csv")

Presets are pre-filled from each dataset's *documented* columns, but you MUST
confirm them against the actual downloaded header (they occasionally differ).
"""

import csv

from features import extract_features  # the SAME extractor used on our own data
from model import FEATURES              # the SAME behavioural feature list

# --- Key-code -> key name mapping ------------------------------------------
# Control/navigation keys must come out with the SAME names features.py knows
# (Backspace/Delete = deletions; Shift/Enter/... = non-character), so the
# deletion and character counts are computed correctly.
_CONTROL_CODES = {
    8: "Backspace", 46: "Delete", 13: "Enter", 9: "Tab", 16: "Shift",
    17: "Control", 18: "Alt", 20: "CapsLock", 27: "Escape",
    37: "ArrowLeft", 38: "ArrowUp", 39: "ArrowRight", 40: "ArrowDown",
    36: "Home", 35: "End", 33: "PageUp", 34: "PageDown", 45: "Insert",
}


def keycode_to_key(code):
    """Turn a numeric key code into a key_value string."""
    try:
        code = int(float(code))
    except (TypeError, ValueError):
        return "Unidentified"
    if code in _CONTROL_CODES:
        return _CONTROL_CODES[code]
    if 32 <= code <= 126:            # printable ASCII -> the character itself
        return chr(code)
    return "Unidentified"


# --- Dataset presets: map a dataset's columns to our generic fields ---------
# Each preset says which columns identify ONE session (session_keys), and where
# the key, the key-down time and the key-up time live. `key_is_code` says the
# key column holds a numeric code (use keycode_to_key) vs. a literal character.
# `label_col` (optional) carries any external label through for reference.
EMOSURV = {
    "session_keys": ["User Id", "Emotion Index"],  # one typing block per emotion
    "key_col": "Key Code",   "key_is_code": True,
    "down_col": "key Down",  "up_col": "key Up",   # ms timestamps
    "label_col": "Emotion Index",                  # 5 induced emotions (NOT effort)
    "label_name": "emotion",
}

AALTO = {
    "session_keys": ["PARTICIPANT_ID", "TEST_SECTION_ID"],  # one sentence transcribed
    "key_col": "LETTER",     "key_is_code": False,
    "down_col": "PRESS_TIME", "up_col": "RELEASE_TIME",
    "label_col": None,
    "label_name": None,
}


def _rows_to_events(rows, spec):
    """Convert the raw rows of ONE session into our sorted event stream."""
    kd = spec["down_col"]
    events = []
    for r in rows:
        try:
            down = float(r[kd])
            up = float(r[spec["up_col"]]) if r.get(spec["up_col"]) not in (None, "") else down
        except (TypeError, ValueError):
            continue
        key = (keycode_to_key(r[spec["key_col"]]) if spec["key_is_code"]
               else (r[spec["key_col"]] or "").strip() or "Unidentified")
        events.append((down, "keydown", key))
        events.append((up, "keyup", key))
    if not events:
        return [], 0
    t0 = min(t for t, _, _ in events)          # normalise so session starts at 0
    stream = [{"event_type": et, "key_value": k, "t_ms": t - t0,
               "caret_pos": None, "selection_end": None}
              for (t, et, k) in sorted(events)]
    # char_count = number of character-producing keydowns (single-char, not space-only edit)
    char_count = sum(1 for e in stream
                     if e["event_type"] == "keydown" and len(e["key_value"]) == 1)
    return stream, char_count


def build_external_features(in_csv, spec, out_csv="external_features.csv"):
    """Read an external keystroke CSV -> per-session features in OUR columns."""
    # group rows into sessions
    sessions = {}
    with open(in_csv, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            key = tuple(r.get(c, "") for c in spec["session_keys"])
            sessions.setdefault(key, []).append(r)

    out_rows = []
    for skey, rows in sessions.items():
        events, char_count = _rows_to_events(rows, spec)
        feats = extract_features(events, char_count)
        row = {"external_session": "|".join(map(str, skey))}
        if spec.get("label_col"):
            row[spec["label_name"]] = rows[0].get(spec["label_col"], "")
        row.update(feats)
        out_rows.append(row)

    out_rows.sort(key=lambda r: r["external_session"])
    fieldnames = list(out_rows[0].keys())
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(out_rows)
    return out_rows


# ---------------------------------------------------------------------------
# EmoSurv (real file) loader.
#
# The downloaded "Free Text Typing Dataset.csv" is ';'-delimited with ','-decimals
# (European locale) and, crucially, its absolute keyDown/keyUp columns were rounded
# to 6-figure scientific notation (Excel) and are UNUSABLE. We therefore rebuild
# each session's keydown timeline from the intact D1D2 (down-to-down interval)
# column, then feed the SAME extract_features(). keyCode is stored as a literal
# escape string ('\\b', '\\u0010', 'v', ' ').
# ---------------------------------------------------------------------------
def _decode_keycode(s):
    """Turn EmoSurv's escaped keyCode string into a key_value features.py knows."""
    if s is None:
        return "Unidentified"
    if s == r"\b":
        return "Backspace"
    if s == r"\t":
        return "Tab"
    if s in (r"\n", r"\r"):
        return "Enter"
    if s.startswith(r"\u") and len(s) == 6:
        try:
            code = int(s[2:], 16)
        except ValueError:
            return "Unidentified"
        if code == 8:
            return "Backspace"
        if 32 <= code <= 126:
            return chr(code)
        return "Unidentified"        # control chars (Shift/Ctrl etc.) -> non-character
    if len(s) == 1:
        return s
    return "Unidentified"


def _emo_num(x):
    x = (x or "").strip().replace(",", ".")
    try:
        return float(x)
    except ValueError:
        return None


def build_emosurv_features(in_csv="Free Text Typing Dataset.csv",
                           out_csv="external_features_emosurv.csv",
                           min_keydowns=40):
    """Reconstruct EmoSurv sessions from D1D2 intervals -> OUR feature columns."""
    with open(in_csv, newline="", encoding="utf-8-sig") as f:
        rd = csv.reader(f, delimiter=";")
        header = next(rd)
        Hh = {c: i for i, c in enumerate(header)}
        raw = [r for r in rd if len(r) == len(header)]

    # group into sessions and keep source order (by 'index')
    sessions = {}
    for r in raw:
        key = (r[Hh["userid"]], r[Hh["emotionIndex"]])
        sessions.setdefault(key, []).append(r)

    out_rows = []
    for (uid, emo), rws in sessions.items():
        rws.sort(key=lambda r: int(r[Hh["index"]]))
        t = 0.0
        events = []
        for i, r in enumerate(rws):
            gap = _emo_num(r[Hh["D1D2"]])
            if i > 0 and gap is not None and 0 <= gap < 60000:
                t += gap                       # rebuild time from inter-key gaps
            key = _decode_keycode(r[Hh["keyCode"]])
            events.append({"event_type": "keydown", "key_value": key,
                           "t_ms": t, "caret_pos": None, "selection_end": None})
        char_count = sum(1 for e in events if len(e["key_value"]) == 1)
        feats = extract_features(events, char_count)
        out_rows.append({"external_session": f"{uid}|{emo}",
                         "emotion": emo, **feats})

    out_rows.sort(key=lambda r: r["external_session"])
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    valid = [r for r in out_rows if r["behavioural_valid"] == 1]
    print(f"EmoSurv -> {out_csv}: {len(out_rows)} sessions, "
          f"{len(valid)} behaviourally valid (>= {min_keydowns} keydowns).")
    return out_rows


# ---------------------------------------------------------------------------
# KeyRecs (real file) loader — a SECOND independent feature-validation set.
#
# KeyRecs free-text.csv stores one row per DIGRAPH (consecutive key pair) with
# latencies in SECONDS. The down-to-down column DD.key1.key2 is the inter-key
# interval, so — exactly as for EmoSurv — we rebuild each session's keydown
# timeline by cumulatively summing it, then feed the SAME extract_features().
# Named keys ('Space','Backspace','Shift',arrows...) map onto features.py's
# vocabulary. No effort/difficulty label exists here: validation only.
# ---------------------------------------------------------------------------
def _keyrecs_key(name):
    if name == "Space":
        return " "
    if name in ("Backspace", "Delete", "Shift", "Control", "Alt", "Enter",
                "CapsLock", "Tab", "ArrowLeft", "ArrowRight", "ArrowUp",
                "ArrowDown", "Home", "End", "PageUp", "PageDown", "NumLock",
                "Escape"):
        return name
    if len(name) == 1:
        return name
    return "Unidentified"      # Dead, OS, AltGraph, MediaTrackNext, Fn, ...


def build_keyrecs_features(in_csv="keyrecs_freetext.csv",
                           out_csv="external_features_keyrecs.csv",
                           min_keydowns=40):
    """Reconstruct KeyRecs sessions from DD.key1.key2 -> OUR feature columns."""
    with open(in_csv, newline="", encoding="utf-8") as f:
        rd = csv.reader(f)
        header = [h.strip() for h in next(rd)]
        Hh = {c: i for i, c in enumerate(header)}
        raw = [r for r in rd if len(r) > Hh["DD.key1.key2"]]

    sessions = {}
    for r in raw:                       # preserve digraph order within a session
        sessions.setdefault((r[Hh["participant"]], r[Hh["session"]]), []).append(r)

    out_rows = []
    for (pid, sid), rws in sessions.items():
        t = 0.0
        events = [{"event_type": "keydown", "key_value": _keyrecs_key(rws[0][Hh["key1"]]),
                   "t_ms": 0.0, "caret_pos": None, "selection_end": None}]
        for r in rws:
            try:
                gap = float(r[Hh["DD.key1.key2"]]) * 1000.0   # seconds -> ms
            except ValueError:
                gap = 0.0
            if not (0 <= gap < 60000):
                gap = 0.0                # clamp rollover-negatives / outliers
            t += gap
            events.append({"event_type": "keydown",
                           "key_value": _keyrecs_key(r[Hh["key2"]]),
                           "t_ms": t, "caret_pos": None, "selection_end": None})
        char_count = sum(1 for e in events if len(e["key_value"]) == 1)
        feats = extract_features(events, char_count)
        out_rows.append({"external_session": f"{pid}|{sid}", **feats})

    out_rows.sort(key=lambda r: r["external_session"])
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    valid = [r for r in out_rows if r["behavioural_valid"] == 1]
    print(f"KeyRecs -> {out_csv}: {len(out_rows)} sessions, "
          f"{len(valid)} behaviourally valid.")
    return out_rows


# ---------------------------------------------------------------------------
# PLUMBING TEST (not real data): a 6-keystroke fixture in EmoSurv's documented
# column layout, only to prove external rows flow through the SAME extractor and
# come out in the SAME feature columns. Replace with the real download to model.
# ---------------------------------------------------------------------------
def _self_test():
    fixture = "scratch_external_fixture.csv"
    with open(fixture, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["User Id", "Emotion Index", "Key Code", "key Down", "key Up"])
        # user U1, emotion 0: types "hi", pauses, backspaces, retypes
        seq = [(104, 1000, 1080), (105, 1200, 1270),      # h, i
               (8, 3600, 3660),                           # long pause then Backspace
               (105, 3900, 3970), (32, 4100, 4160),       # i, space
               (98, 4300, 4380)]                          # b
        for code, d, u in seq:
            w.writerow(["U1", 0, code, d, u])
    rows = build_external_features(fixture, EMOSURV, "scratch_external_features.csv")
    print("PLUMBING TEST — external rows through the SAME extractor:")
    r = rows[0]
    for col in ["external_session", "emotion", "n_keydown", "char_count",
                "active_time_s", "chars_per_sec", "n_long_pause_per_100",
                "delete_rate", "n_revision_bursts", "behavioural_valid"]:
        print(f"  {col:>22} = {r[col]}")
    print(f"\nOutput columns match our feature set: "
          f"{all(fc in r for fc in FEATURES)}  ({len(FEATURES)} features)")


if __name__ == "__main__":
    _self_test()
