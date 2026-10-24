"""Checks for the report logic. Run from the repo root:  venv\\Scripts\\python prototype_platform\\tests\\test_analysis.py"""
import os
import pathlib
import random
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "research"))

from core import analysis as an        # noqa: E402
from core import db, predict           # noqa: E402
from features import writing_actions   # noqa: E402


def _ev(keys_and_gaps):
    t, out = 0, []
    for k, gap in keys_and_gaps:
        t += gap
        out.append({"event_type": "keydown", "key_value": k, "t_ms": t})
    return out


def test_pauses_are_placed_where_they_fell():
    ev = _ev([("a", 100), ("b", 900), (" ", 100), ("c", 900), (".", 100), (" ", 100), ("D", 900), ("Backspace", 100)])
    a = writing_actions(ev)
    assert a["pauses"]["within_word"]["n"] == 1        # a -> b
    assert a["pauses"]["between_words"]["n"] == 1      # space -> c
    assert a["pauses"]["between_sentences"]["n"] == 1  # ". " -> D
    assert a["additions"] == 7 and a["deletions"] == 1


def test_engagement_is_50_when_every_behaviour_is_average():
    m = an.engagement_model()
    feats = {"behavioural_valid": 1, "mean_iki_ms": 100.0}
    for f, mu in zip(m["features"], m["mean"]):
        if f == "rhythm_cv":
            feats["std_iki_ms"] = mu * 100.0      # cv = std / mean
        else:
            feats[f] = mu
    assert abs(an.engagement(feats)["pct"] - 50) <= 1


def test_engagement_is_none_for_invalid_capture():
    assert an.engagement({"behavioural_valid": 0}) is None


def test_comparison_bars_stay_on_the_scale_and_keyboard_matters():
    f = {"median_iki_ms": 200, "mean_iki_ms": 300, "std_iki_ms": 400, "pause_time_ratio": 0.4,
         "revisions_per_100": 2, "delete_rate": 0.05}
    for kb in ("laptop", "external", None):
        assert all(0 <= b["fill"] <= 100 for b in an.compare(f, kb))
    assert an.compare(f, "laptop")[0]["fill"] != an.compare(f, "external")[0]["fill"]


def test_tips_always_return_something():
    bars = an.compare({"median_iki_ms": 180, "mean_iki_ms": 300, "std_iki_ms": 300, "pause_time_ratio": 0.4,
                       "revisions_per_100": 2, "delete_rate": 0.05}, "laptop")
    assert 1 <= len(an.tips(None, bars)) <= 3


def test_effort_card_compares_model_and_answer():
    est = {"available": True, "predicted_effort": 2.6, "contributions": [("Writing time", 0.2), ("Longest pause", -0.1)]}
    near = an.effort_card({"tlx_effort": 3}, est)
    far = an.effort_card({"tlx_effort": 5}, est)
    assert "within" in near["verdict"] and "higher" in far["verdict"]
    assert 0 <= near["lo"] <= near["pred_pos"] <= near["hi"] <= 100
    assert an.effort_card({}, est)["actual"] is None and an.effort_card({}, {"available": False}) is None


def test_pause_length_buckets_add_up_to_all_pauses():
    a = writing_actions(_ev([("a", 100), ("b", 600), ("c", 1500), ("d", 3000), ("e", 7000)]))
    assert sum(a["length_buckets"].values()) == 4 and a["length_buckets"]["5 s +"] == 1


def test_report_renders_for_a_submitted_session():
    tmp = pathlib.Path(tempfile.mkdtemp()) / "t.db"
    shutil.copy(db.DB_PATH, tmp)
    real, db.DB_PATH = db.DB_PATH, tmp
    try:
        import app as flask_app
        c = flask_app.app.test_client()
        random.seed(2)
        text, t, events = "I remember the day clearly. It was a good one. " * 4, 0, []
        for i, ch in enumerate(text):
            t += random.randint(90, 260) + (1500 if ch == "." else 0)
            events.append({"type": "keydown", "key": ch, "t": t, "caret": i, "caretEnd": i})
        r = c.post("/api/submit", json={"participant_code": "T1", "task_id": "happy_moment", "started_at": 0,
                                        "ended_at": t, "final_text": text, "events": events,
                                        "typing_skill": "touch", "keyboard": "laptop", "self_mood": 4})
        assert r.status_code == 200
        page = c.get("/report/%d" % r.get_json()["session_id"])
        assert page.status_code == 200 and b"pane-emotional" in page.data
        assert page.data.count(b"<h2>Suggestions</h2>") == 2
    finally:
        db.DB_PATH = real


def test_emotion_words_flip_after_negation():
    from core import affect
    r = affect.emotion_words("I was happy and loved the day, but the end was awful and I was not happy about it.", "happy")
    assert r["n_pos"] >= 2 and r["n_neg"] >= 2
    assert "".join(g["t"] for g in r["segments"]).startswith("I was happy")
    assert affect.emotion_words("too short") is None


def test_nrc_finds_feeling_words_and_suggestions_never_empty():
    from core import affect
    r = affect.nrc_emotions("I felt joy and love, but the funeral brought tears and grief for everyone there.")
    assert r is not None and {x["emotion"] for x in r["rows"]} >= {"joy", "sadness"}
    assert affect.nrc_emotions("short") is None
    sug = an.emotional_suggestions([], None, None, None, "happy")
    assert sug and all(x["observed"] and x["tip"] for x in sug)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("ok  ", t.__name__)
    print("%d passed" % len(tests))
