"""
app.py — the PROTOTYPE Writing Analytics Platform (Flask).

Separate from the Stage-1 data-collection app: own port, own database
(data/databases/prototype.db), and it reuses research/features.py, research/explain.py,
data/derived/effort_model.pkl and the study CSVs in data/study/ READ-ONLY. It never imports or writes the Stage-1 app.

Two experiences:
  • Participant  — landing (/), writing test (/test), live report (/report/<id>)
    stored in prototype.db.
  • Researcher   — a full analytics system over the STUDY dataset (read-only):
    Overview → Participants → Participant profile → Session → detailed report,
    plus a paper-style Research results page.

Methodology, features, model, SHAP, analysis, disclaimers and the
measured / self-rated / experimental separation are unchanged. No statistic is
invented — every figure is computed from the real study data.
"""

import csv
import io
import os
from functools import wraps

from flask import (Flask, render_template, request, jsonify, abort, Response,
                   url_for, redirect, session)

from core import affect, db, predict
from core import analysis as an
from core import measures as ms
from core import questionnaire as qn
from core import behaviour as bh
from core import findings as fd
from core import plain_report as pr
from core import recommendations as recs
from core import research_data as rd
from core.tasks import MOMENTS, TASKS_BY_ID

app = Flask(__name__)
app.secret_key = os.environ.get("PROTO_SECRET", "prototype-dev-secret-change-me")
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0   # dev: never cache static (JS/CSS)
db.init_db()
predict.artifact()

ADMIN_USER = os.environ.get("PROTO_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("PROTO_ADMIN_PASSWORD", "admin")

MODEL_RESULTS = {
    "n_sessions": 22, "n_participants": 17,
    "rows": [
        ("Baseline (predict mean)", "0.94 [0.65, 1.24]", "1.17", "-0.12"),
        ("Linear Regression", "1.99 [1.42, 2.63]", "2.49", "-4.08"),
        ("Random Forest", "1.10 [0.72, 1.50]", "1.44", "-0.70"),
    ],
    "notes": [
        "Neither model beats the mean baseline (paired Wilcoxon: RF p=0.045, LR p<0.001).",
        "Permutation tests: LR R² p=0.85, RF R² p=0.99 — not distinguishable from chance.",
        "Every behaviour↔effort correlation 95% CI spans zero at n=22.",
        "Promising direction, but the experimental estimate is NOT a reliable measure — sample-size limited.",
    ],
}


def login_required(view):
    @wraps(view)
    def wrapper(*a, **k):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return view(*a, **k)
    return wrapper


# ===================== Participant experience =====================
@app.route("/")
def home():
    return render_template("participant/landing.html")


def research_mode():
    """Research mode collects the participant's own ratings (effort, mood, focus,
    stress) as validation labels. The default PARTICIPANT mode is label-free: it asks
    for nothing and reports only what the validated rules and models infer from
    behaviour and text. Enable research mode with /test?mode=research or the env var
    PROTO_RESEARCH_MODE=1."""
    return (request.args.get("mode") == "research"
            or os.environ.get("PROTO_RESEARCH_MODE") == "1")


@app.route("/test")
def test():
    return render_template("participant/write.html", levels=MOMENTS,
                           research_mode=research_mode())


@app.route("/api/submit", methods=["POST"])
def submit():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"ok": False, "error": "No data."}), 400
    required = ["participant_code", "task_id", "started_at", "ended_at",
                "final_text", "events"]
    if [f for f in required if f not in data]:
        return jsonify({"ok": False, "error": "Missing fields."}), 400
    if data["task_id"] not in TASKS_BY_ID:
        return jsonify({"ok": False, "error": "Unknown task."}), 400

    code = "".join(str(data["participant_code"]).split()).upper()
    final_text = str(data["final_text"])
    events = data["events"] or []
    features = predict.compute_features(events, final_text)
    features["word_count"] = len(final_text.split())
    emotion = TASKS_BY_ID[data["task_id"]]["level_id"]
    emotion = emotion if emotion in ("happy", "sad") else None
    affect_data = affect.analyse(features, final_text, emotion)

    def _likert(key):
        try:
            v = int(data.get(key))
            return v if 1 <= v <= 5 else None
        except (TypeError, ValueError):
            return None

    meta = {
        "participant_code": code, "task_id": data["task_id"],
        "difficulty": TASKS_BY_ID[data["task_id"]]["difficulty"],
        "emotion": emotion, "self_mood": _likert("self_mood"),
        "self_focus": _likert("self_focus"), "self_stress": _likert("self_stress"),
        "self_relive": _likert("self_relive"), "self_arousal": _likert("self_arousal"),
        "self_wander": _likert("self_wander"),
        **{c: _likert(c) for c in ("tlx_mental", "tlx_effort", "tlx_frustration",
                                   "flow_fluent", "flow_concentrate", "flow_absorbed",
                                   "flow_time")},
        "interrupted": (1 if data.get("interrupted") in (1, True, "1", "yes") else
                        0 if data.get("interrupted") in (0, False, "0", "no") else None),
        "typing_skill": (data.get("typing_skill") if data.get("typing_skill")
                         in ("touch", "some", "hunt") else None),
        "keyboard": (data.get("keyboard") if data.get("keyboard")
                     in ("laptop", "external") else None),
        "started_at": int(data["started_at"]), "ended_at": int(data["ended_at"]),
        "final_text": final_text,
        "self_rated_effort": (int(data["self_rated_effort"])
                              if data.get("self_rated_effort") else None),
    }
    sid = db.insert_session(meta, events, features, None, affect_data)
    return jsonify({"ok": True, "session_id": sid,
                    "report_url": url_for("report", session_id=sid)})


def _fmt_time(sec):
    sec = int(round(sec))
    return "%dm %02ds" % (sec // 60, sec % 60) if sec >= 60 else "%ds" % sec


@app.route("/report/<int:session_id>")
def report(session_id):
    s = db.get_session(session_id)
    if s is None:
        abort(404)
    feats, emotion = s["features"], s.get("emotion")
    events = db.get_keystrokes(session_id)
    acts = predict.actions(events)
    bars = an.compare(feats, s.get("keyboard"))
    eng = an.engagement(feats)

    pauses = an.pause_view(acts)
    metrics = [
        {"value": s["word_count"], "label": "Words"},
        {"value": _fmt_time(feats.get("active_time_s", 0)), "label": "Writing time"},
        {"value": "%.1f" % feats.get("chars_per_sec", 0), "label": "Characters/sec"},
        {"value": pauses["total"], "label": "Pauses"},
        {"value": acts["additions"], "label": "Characters typed"},
        {"value": acts["deletions"], "label": "Deletions"},
    ]

    # emotional tab (older sessions get their text analysis computed on the fly)
    aff = s.get("affect") or affect.analyse(feats, s["final_text"], emotion)
    idx = bh.compute_indices(feats)
    sts = pr.states(s, idx)
    plain = {"states": sts, "insight": pr.insight(sts, emotion), "tone": pr.tone(aff.get("text"), emotion)}
    val = affect.load_validation_json()
    mine = None
    _mine = bh.compute_indices(feats, bh.load_reference("emosurv"))
    if _mine and val:
        pos = lambda v: "lower than most" if v < 34 else "higher than most" if v > 66 else "about typical"
        mine = [{"key": k, "label": bh.INDEX_META[k]["label"], "value": round(_mine[k]), "pos": pos(_mine[k])}
                for k in bh.INDEX_ORDER]

    return render_template(
        "participant/report.html", s=s, plain=plain, mine=mine, val=val,
        metrics=metrics, bars=bars, pauses=pauses, eng=eng,
        eng_n=an.engagement_model()["n_sessions"],
        headlines=an.headlines(feats, acts, bars), tips=an.tips(eng, bars, s.get("typing_skill")),
        over_time=an.over_time(events), timeline=predict.timeline_from_events(events),
        tone_feel=an.tone_vs_feeling(s, aff.get("text")),
        skill_word={"touch": "touch typist", "some": "mixed typing", "hunt": "looks at the keys"}.get(
            s.get("typing_skill"), "typing style not given"),
        keyboard_word={"laptop": "laptop keyboard", "external": "external keyboard"}.get(
            s.get("keyboard"), "keyboard not given"))


# ===================== Researcher auth =====================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if (request.form.get("username") == ADMIN_USER and
                request.form.get("password") == ADMIN_PASSWORD):
            session["admin"] = True
            return redirect(url_for("admin"))
        return render_template("admin/login.html", error="Incorrect username or password.")
    if session.get("admin"):
        return redirect(url_for("admin"))
    return render_template("admin/login.html")


@app.route("/admin/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("home"))


# ===================== Researcher analytics (study data) =====================
def _research_context():
    """Everything the researcher pages need: study KPIs, external validation, live data, findings."""
    kpis, signals = rd.study_kpis(), rd.research_signals()
    ext, lit = affect.load_validation_json(), affect.load_literature_validation()
    live = affect.live_validation(db.list_sessions())
    found, hyps = fd.build(kpis, signals, MODEL_RESULTS, ext, lit, live)
    return dict(kpis=kpis, signals=signals, model=MODEL_RESULTS, ext=ext, lit=lit, live=live,
                findings=found, hyps=hyps, meta=bh.INDEX_META, order=bh.INDEX_ORDER,
                status_label=fd.STATUS_LABEL)


@app.route("/admin")
@login_required
def admin():
    return render_template(
        "admin/overview.html", active="overview", live_count=len(db.list_sessions()),
        charts={"effort_dist": rd.effort_distribution(),
                "feature_vs_effort": rd.feature_vs_effort()},
        **_research_context())


@app.route("/admin/participants")
@login_required
def participants_page():
    sessions = db.list_sessions()
    for x in sessions:
        x["scores"] = {k: qn.score(x, k) for k in qn.STATE_ORDER}
    summary = {"sessions": len(sessions), "participants": len({x["participant_code"] for x in sessions})}
    return render_template("admin/participants.html", active="participants",
                           participants=rd.participants(), sessions=sessions, summary=summary,
                           live_participants=_live_participants(sessions))


@app.route("/admin/participants/<code>")
@login_required
def participant_profile(code):
    prof = rd.participant_profile(code)
    if prof is None:
        abort(404)
    return render_template("admin/participant_profile.html", active="participants",
                           p=prof)


@app.route("/admin/session/<int:session_id>")
@login_required
def session_report(session_id):
    feats = rd.session_features(session_id)
    if feats is None:
        abort(404)
    row = rd.session_row(session_id)
    estimate = predict.estimate_and_explain(feats)
    _profile = [
        ("Typing", "%.2f" % feats["chars_per_sec"], "chars/s", "chars_per_sec"),
        ("Pauses", int(round(feats["n_short_pause_per_100"] / 100 * feats["n_keydown"])), "total", "n_long_pause_per_100"),
        ("Longest pause", "%.1f" % (feats["max_pause_ms"] / 1000), "s", "max_pause_ms"),
        ("Revisions", int(feats["n_revision_bursts"]), "bursts", "revisions_per_100"),
        ("Writing time", int(round(feats["active_time_s"])), "s", "active_time_s"),
        ("Words", int(feats["word_count"]), "words", "word_count"),
    ]
    profile = [{"label": lab, "value": val, "unit": unit,
                "pct": rd.percentile(col, feats.get(col, 0))}
               for lab, val, unit, col in _profile]
    recommendations = recs.recommend(feats)
    has_rec = recommendations and recommendations[0]["behaviour"] != "none"
    return render_template(
        "admin/session_report.html", active="participants",
        sid=session_id, row=row, feats=feats, estimate=estimate,
        profile=profile, timeline=rd.typing_timeline(session_id),
        context=recs.context_labels(feats),
        recommendations=recommendations, has_rec=has_rec,
        general_tips=recs.GENERAL_TIPS,
        level_title=rd.LEVEL_TITLE.get(row["difficulty"], row["difficulty"]))


def _avg(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else 0


def _live_participants(sessions):
    """Aggregate live sessions into per-participant cards (latest first)."""
    by = {}
    for s in sessions:
        by.setdefault(s["participant_code"], []).append(s)
    rows = []
    for code, g in by.items():
        rows.append({
            "code": code, "sessions": len(g),
            "valid": sum(1 for x in g if x["behavioural_valid"]),
            "avg_load": round(_avg([qn.score(x, "load") for x in g]), 1),
            "avg_speed": round(_avg([x["features"].get("chars_per_sec") for x in g]), 2),
            "avg_pauses": round(_avg([x["features"].get("n_long_pause_per_100") for x in g]), 1),
            "last": max((x["created_at"] or "") for x in g)[:16],
        })
    rows.sort(key=lambda r: r["code"])
    return rows


def _live_profile(code):
    g = db.list_for_participant(code)   # ascending order
    if not g:
        return None
    def col(k):
        return [x["features"].get(k) or 0 for x in g]
    snap = {
        "sessions": len(g),
        "valid": sum(1 for x in g if x["behavioural_valid"]),
        "levels": len({x["difficulty"] for x in g}),
        "avg_load": round(_avg([qn.score(x, "load") for x in g]), 1),
        "avg_speed": round(_avg(col("chars_per_sec")), 2),
        "avg_time": round(_avg(col("active_time_s"))),
        "avg_pause_ratio": round(_avg(col("pause_time_ratio")) * 100),
        "avg_revisions": round(_avg(col("revisions_per_100")), 1),
    }
    sessions = [{
        "id": x["id"],
        "level_title": TASKS_BY_ID.get(x["task_id"], {}).get("level_title", x["difficulty"]),
        "difficulty": x["difficulty"],
        "load": qn.score(x, "load") or 0,
        "speed": round(x["features"].get("chars_per_sec", 0), 2),
        "pauses": int(round(x["features"].get("n_long_pause_per_100", 0))),
        "revisions": int(x["features"].get("n_revision_bursts", 0)),
        "time_s": int(round(x["features"].get("active_time_s", 0))),
        "words": x["word_count"], "valid": x["behavioural_valid"],
    } for x in g]
    trend = {
        "labels": ["S%d" % (i + 1) for i in range(len(g))],
        "effort": [qn.score(x, "load") for x in g], "effort_label": "Cognitive load",
        "speed": [round(x["features"].get("chars_per_sec", 0), 2) for x in g],
        "pauses": [round(x["features"].get("n_long_pause_per_100", 0), 1) for x in g],
        "revisions": [round(x["features"].get("revisions_per_100", 0), 1) for x in g],
    }
    return {"code": code, "snapshot": snap, "sessions": sessions,
            "trend": trend, "enough_trend": len(g) >= 3}


@app.route("/admin/live/participants/<code>")
@login_required
def live_profile(code):
    prof = _live_profile(code)
    if prof is None:
        abort(404)
    return render_template("admin/live_profile.html", active="participants", p=prof)


@app.route("/admin/live/clear", methods=["POST"])
@login_required
def live_clear():
    db.clear_all()
    return redirect(url_for("participants_page") + "#new")


@app.route("/admin/behaviour")
@login_required
def behaviour_page():
    return render_template("admin/behaviour_research.html", active="behaviour",
                           **_research_context())


@app.route("/admin/model-research")
@login_required
def model_research_page():
    ctx = _research_context()
    return render_template(
        "admin/model_research.html", active="model", measures=ms.measure_cards(ctx["lit"]),
        eng_card=ms.engagement_card(), norms=an.norms(), set_aside=ms.SET_ASIDE, datasets=ms.DATASETS,
        rejected=ms.REJECTED, questionnaires=ms.QUESTIONNAIRES, sources=list(ms.SOURCES.values()), **ctx)


@app.route("/admin/export.csv")
@login_required
def export_csv():
    buf = io.StringIO()
    w = csv.writer(buf)
    cols = ["session_id", "participant_id", "task_id", "difficulty", "effort_rating",
            "behavioural_valid", "chars_per_sec", "active_time_s",
            "n_long_pause_per_100", "pause_time_ratio", "delete_rate",
            "revisions_per_100", "word_count"]
    w.writerow(cols)
    for r in rd._study().to_dict("records"):
        w.writerow([r.get(c) for c in cols])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=study_sessions.csv"})


@app.route("/admin/export-live.csv")
@login_required
def export_live_csv():
    cols = ["id", "participant_code", "emotion", "typing_skill", "keyboard", "self_mood", "behavioural_valid",
            "word_count", "created_at"]
    feats = ["chars_per_sec", "median_iki_ms", "pause_time_ratio", "n_long_pause_per_100", "delete_rate",
             "revisions_per_100"]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(cols + ["score_" + k for k in qn.STATE_ORDER] + feats)
    for x in db.list_sessions():
        w.writerow([x.get(c) for c in cols] + [qn.score(x, k) for k in qn.STATE_ORDER]
                   + [x["features"].get(f) for f in feats])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=live_sessions.csv"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
