"""
predict.py — orchestration that REUSES the shared research code, read-only:
  - ../features.py     -> extract_features()  (the exact study feature pipeline)
  - ../explain.py      -> load_artifact(), explain_session()  (SHAP)
  - ../effort_model.pkl (loaded by explain.load_artifact; NEVER retrained here)

Nothing in this file trains or modifies the model. It only:
  1. turns captured keystroke events into behavioural features, and
  2. produces the EXPERIMENTAL estimated writing effort + its SHAP explanation.
"""

import os
import sys

# Make the shared repo-root modules importable WITHOUT copying or editing them.
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from features import extract_features            # shared, read-only
from explain import load_artifact, explain_session  # shared, read-only

# Load the trained artifact once (read-only). Kept module-level so the Flask app
# and SHAP explainer are initialised a single time.
_ARTIFACT = None


def artifact():
    global _ARTIFACT
    if _ARTIFACT is None:
        _ARTIFACT = load_artifact(os.path.join(_ROOT, "effort_model.pkl"))
    return _ARTIFACT


def compute_features(events, final_text):
    """Captured events (type/key/t/caret/caretEnd) -> behavioural feature dict."""
    conv = [{
        "event_type": e.get("type"),
        "key_value": e.get("key"),
        "t_ms": e.get("t"),
        "caret_pos": e.get("caret"),
        "selection_end": e.get("caretEnd"),
    } for e in events]
    return extract_features(conv, len(final_text or ""))


_PAUSE_MS = 2000
_DELETE = {"Backspace", "Delete"}


def timeline_from_events(events):
    """Segment captured keydowns into typing / pause / revision spans for the
    writing-timeline visual. Uses the real captured timestamps only."""
    kd = sorted([e for e in events if e.get("type") == "keydown"],
                key=lambda e: e.get("t", 0))
    if len(kd) < 3:
        return {"insufficient": True, "segments": [], "n_pause": 0,
                "longest_pause_s": 0}
    t = [e.get("t", 0) for e in kd]
    keys = [str(e.get("key")) for e in kd]
    t0 = t[0]
    segs, n_pause, longest = [], 0, 0
    for i in range(1, len(t)):
        gap = t[i] - t[i - 1]
        if gap >= _PAUSE_MS:
            cls = "pause"; n_pause += 1; longest = max(longest, gap)
        elif keys[i] in _DELETE or keys[i - 1] in _DELETE:
            cls = "revision"
        else:
            cls = "type"
        a, b = t[i - 1] - t0, t[i] - t0
        if segs and segs[-1]["cls"] == cls:
            segs[-1]["t1"] = b; segs[-1]["n"] += 1; segs[-1]["last_gap"] = gap
        else:
            segs.append({"cls": cls, "t0": a, "t1": b, "n": 1, "last_gap": gap})
    total = (t[-1] - t0) or 1
    for s in segs:
        s["pct"] = round(100 * (s["t1"] - s["t0"]) / total, 3)
        s["dur_s"] = round((s["t1"] - s["t0"]) / 1000, 1)
        s["gap_ms"] = int(s["last_gap"])
    segs = [s for s in segs if s["pct"] >= 0.4] or segs
    return {"insufficient": False, "segments": segs, "n_pause": n_pause,
            "longest_pause_s": round(longest / 1000, 1)}


def _band(pred, baseline):
    if pred < baseline - 0.5:
        return "Lower than average"
    if pred > baseline + 0.5:
        return "Higher than average"
    return "Around average"


def estimate_and_explain(features):
    """Return the EXPERIMENTAL estimate + SHAP explanation for one session.

    If the keystroke capture is insufficient (behavioural_valid == 0) the estimate
    is SUPPRESSED rather than shown as a misleading number.
    """
    art = artifact()
    if not features.get("behavioural_valid", 0):
        return {"available": False,
                "reason": "Keystroke capture was insufficient for an estimate "
                          "(too few keystrokes or an unsupported keyboard)."}
    ex = explain_session(art, features)
    baseline = float(art["train_mean_effort"])
    pred = max(1.0, min(5.0, float(ex["predicted_effort"])))   # clip to 1-5
    return {
        "available": True,
        "predicted_effort": round(pred, 2),
        "band": _band(pred, baseline),
        "baseline_effort": round(baseline, 2),
        "contributions": ex["contributions"],   # [(readable name, signed value), ...]
        "explanations": ex["explanations"],      # plain-language sentences
    }


if __name__ == "__main__":
    # smoke test: fabricate a short keystroke stream and run the full path.
    evs, t = [], 0
    for ch in ("the quick brown fox " * 30):
        t += 180
        evs.append({"type": "keydown", "key": ch, "t": t, "caret": 0, "caretEnd": 0})
    feats = compute_features(evs, "the quick brown fox " * 30)
    print("behavioural_valid:", feats["behavioural_valid"],
          "| chars_per_sec:", feats["chars_per_sec"])
    out = estimate_and_explain(feats)
    print("estimate available:", out["available"])
    if out["available"]:
        print("experimental estimated effort:", out["predicted_effort"],
              "->", out["band"], "(baseline", out["baseline_effort"], ")")
        for s in out["explanations"]:
            print("  -", s)
