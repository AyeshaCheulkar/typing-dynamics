"""
research_data.py — read-only access to the STUDY dataset for the researcher
dashboard. It reads the shared research files at the repo root and NEVER writes
them or the Stage-1 system:
    ../features.csv          (per-session behavioural features + effort label)
    ../server_export.csv     (session metadata incl. created_at)
    ../server_keystrokes.csv (raw keystroke events — for the typing timeline)

Nothing here changes the methodology, features, model, analysis or statistics.
It only aggregates the existing study data for presentation. All numbers shown
are computed from the real data — none are invented.
"""

import os
from functools import lru_cache

import numpy as np
import pandas as pd
from scipy import stats

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_FEATURES = os.path.join(_ROOT, "features.csv")
_EXPORT = os.path.join(_ROOT, "server_export.csv")
_KEYS = os.path.join(_ROOT, "server_keystrokes.csv")

PAUSE_MS = 2000
DELETE_KEYS = {"Backspace", "Delete"}

LEVEL_TITLE = {"Easy": "Everyday writing", "Moderate": "Describe & explain"}

# behaviours shown as "Research Signals" (Spearman vs self-rated effort)
SIGNAL_FEATURES = [
    ("pause_time_ratio", "Pausing", "share of time paused"),
    ("chars_per_sec", "Typing speed", "characters per second"),
    ("revisions_per_100", "Revisions", "revision bursts per 100 keys"),
    ("n_long_pause_per_100", "Long pauses", "long pauses per 100 keys"),
    ("delete_rate", "Deletions", "backspace/delete rate"),
    ("std_iki_ms", "Rhythm variability", "variation in keystroke timing"),
]


@lru_cache(maxsize=1)
def _study():
    f = pd.read_csv(_FEATURES)
    e = pd.read_csv(_EXPORT)[["id", "created_at"]].rename(columns={"id": "session_id"})
    df = f.merge(e, on="session_id", how="left")
    df["level_title"] = df["difficulty"].map(LEVEL_TITLE).fillna(df["difficulty"])
    return df


def valid(df=None):
    df = _study() if df is None else df
    return df[df["behavioural_valid"] == 1]


# --------------------------------------------------------------------------- #
# Overview
# --------------------------------------------------------------------------- #
def study_kpis():
    v = valid()
    return {
        "participants": int(v["participant_id"].nunique()),
        "valid_sessions": int(len(v)),
        "included_sessions": int(len(_study())),
        "mean_effort": round(float(v["effort_rating"].mean()), 2),
        "mean_writing_time": round(float(v["active_time_s"].mean())),
        "mean_speed": round(float(v["chars_per_sec"].mean()), 2),
        "mean_pause_ratio": round(float(v["pause_time_ratio"].mean()) * 100),
    }


def research_signals():
    v = valid()
    out = []
    for col, name, desc in SIGNAL_FEATURES:
        rho, p = stats.spearmanr(v[col], v["effort_rating"])
        mag = abs(rho)
        strength = ("Moderate" if mag >= 0.2 else "Weak" if mag >= 0.1 else "Negligible")
        tendency = ("higher-effort tendency" if rho > 0 else "lower-effort tendency")
        out.append({"name": name, "desc": desc, "rho": round(float(rho), 2),
                    "p": round(float(p), 3), "strength": strength,
                    "direction": "up" if rho > 0 else "down",
                    "tendency": tendency})
    out.sort(key=lambda r: -abs(r["rho"]))
    return out


def effort_distribution():
    v = valid()
    return [int((v["effort_rating"] == i).sum()) for i in range(1, 6)]


def feature_vs_effort():
    """Points for the switchable primary chart: effort (x) vs behaviour (y)."""
    v = valid()
    feats = {"speed": "chars_per_sec", "pauses": "pause_time_ratio",
             "revisions": "revisions_per_100", "time": "active_time_s"}
    data = {}
    for key, col in feats.items():
        data[key] = [{"x": int(r["effort_rating"]), "y": round(float(r[col]), 3)}
                     for _, r in v.iterrows()]
    return data


# --------------------------------------------------------------------------- #
# Participants
# --------------------------------------------------------------------------- #
def _fmt_date(s):
    try:
        return pd.to_datetime(s).strftime("%b %d")
    except Exception:
        return "—"


def participants():
    df = _study().sort_values("session_id")
    rows = []
    for code, g in df.groupby("participant_id"):
        gv = g[g["behavioural_valid"] == 1]
        if gv.empty:
            continue  # study cohort = participants with >=1 behaviourally-valid session
        rows.append({
            "code": code,
            "sessions": int(len(g)),
            "valid": int(len(gv)),
            "levels": int(g["difficulty"].nunique()),
            "avg_effort": round(float(g["effort_rating"].mean()), 1),
            "avg_speed": round(float(g["chars_per_sec"].mean()), 2),
            "avg_pauses": round(float(g["n_long_pause_per_100"].mean()), 1),
            "avg_time": round(float(g["active_time_s"].mean())),
            "avg_revisions": round(float(g["revisions_per_100"].mean()), 1),
            "last": _fmt_date(g["created_at"].dropna().max() if g["created_at"].notna().any() else None),
        })
    rows.sort(key=lambda r: r["code"])
    return rows


def participant_profile(code):
    df = _study()
    g = df[df["participant_id"] == code].sort_values("session_id")
    if g.empty:
        return None
    sessions = [_session_summary(r) for _, r in g.iterrows()]
    snap = {
        "sessions": int(len(g)),
        "valid": int((g["behavioural_valid"] == 1).sum()),
        "levels": int(g["difficulty"].nunique()),
        "avg_effort": round(float(g["effort_rating"].mean()), 1),
        "avg_speed": round(float(g["chars_per_sec"].mean()), 2),
        "avg_time": round(float(g["active_time_s"].mean())),
        "avg_pause_ratio": round(float(g["pause_time_ratio"].mean()) * 100),
        "avg_revisions": round(float(g["revisions_per_100"].mean()), 1),
    }
    trend = {
        "labels": ["S%d" % (i + 1) for i in range(len(g))],
        "effort": [int(x) for x in g["effort_rating"]],
        "speed": [round(float(x), 2) for x in g["chars_per_sec"]],
        "pauses": [round(float(x), 1) for x in g["n_long_pause_per_100"]],
        "revisions": [round(float(x), 1) for x in g["revisions_per_100"]],
    }
    return {"code": code, "snapshot": snap, "sessions": sessions,
            "trend": trend, "enough_trend": len(g) >= 3}


def _session_summary(r):
    return {
        "id": int(r["session_id"]),
        "participant": r["participant_id"],
        "task_id": r["task_id"],
        "difficulty": r["difficulty"],
        "level_title": r["level_title"],
        "effort": int(r["effort_rating"]),
        "speed": round(float(r["chars_per_sec"]), 2),
        "pauses": int(round(float(r["n_long_pause_per_100"]))),
        "revisions": int(r["n_revision_bursts"]),
        "time_s": int(round(float(r["active_time_s"]))),
        "words": int(r["word_count"]),
        "valid": int(r["behavioural_valid"]),
    }


# --------------------------------------------------------------------------- #
# One session (detailed report)
# --------------------------------------------------------------------------- #
def percentile(col, value):
    """Percentile rank (0–100) of a value within the valid-session distribution."""
    v = valid()
    if col not in v.columns:
        return 0
    arr = v[col].to_numpy(float)
    return int(round(100 * (arr <= float(value)).mean()))


def session_row(session_id):
    df = _study()
    m = df[df["session_id"] == session_id]
    if m.empty:
        return None
    return m.iloc[0]


def session_features(session_id):
    """Return the feature dict (as the model/recommendations expect)."""
    r = session_row(session_id)
    if r is None:
        return None
    d = {c: (float(r[c]) if isinstance(r[c], (int, float, np.floating, np.integer)) else r[c])
         for c in r.index}
    d["behavioural_valid"] = int(r["behavioural_valid"])
    d["word_count"] = int(r["word_count"])
    return d


@lru_cache(maxsize=1)
def _keys_by_session():
    df = pd.read_csv(_KEYS)
    df = df[df["event_type"] == "keydown"].sort_values(["session_id", "t_ms"])
    return {int(sid): g for sid, g in df.groupby("session_id")}


def typing_timeline(session_id):
    """Segment the session into typing / pause / revision spans from real keys."""
    g = _keys_by_session().get(int(session_id))
    if g is None or len(g) < 3:
        return {"insufficient": True, "segments": [], "total_ms": 0,
                "n_pause": 0, "longest_pause_s": 0}
    t = g["t_ms"].to_numpy(dtype=float)
    keys = g["key_value"].astype(str).to_numpy()
    t0 = t[0]
    segs = []
    n_pause = 0
    longest = 0.0
    for i in range(1, len(t)):
        gap = t[i] - t[i - 1]
        if gap >= PAUSE_MS:
            cls = "pause"; n_pause += 1; longest = max(longest, gap)
        elif keys[i] in DELETE_KEYS or keys[i - 1] in DELETE_KEYS:
            cls = "revision"
        else:
            cls = "type"
        a, b = t[i - 1] - t0, t[i] - t0
        if segs and segs[-1]["cls"] == cls:
            segs[-1]["t1"] = b
            segs[-1]["n"] += 1
        else:
            segs.append({"cls": cls, "t0": a, "t1": b, "n": 1})
    total = (t[-1] - t0) or 1
    for s in segs:
        s["pct"] = round(100 * (s["t1"] - s["t0"]) / total, 3)
        s["dur_s"] = round((s["t1"] - s["t0"]) / 1000, 1)
    # drop invisibly thin segments by merging into neighbour
    segs = [s for s in segs if s["pct"] >= 0.4] or segs
    return {"insufficient": False, "segments": segs, "total_ms": int(total),
            "n_pause": n_pause, "longest_pause_s": round(longest / 1000, 1)}
