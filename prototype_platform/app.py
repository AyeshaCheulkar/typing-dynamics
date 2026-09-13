"""
app.py — the PROTOTYPE Writing Analytics Platform (Flask).

Separate from the Stage-1 data-collection app: own port, own database
(prototype.db), and it reuses ../features.py, ../explain.py, ../effort_model.pkl
and the study CSVs READ-ONLY. It never imports or writes the Stage-1 app.

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

import db
import predict
import recommendations as recs
import research_data as rd
from tasks import LEVELS, TASKS_BY_ID

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
    return render_template("landing.html")


@app.route("/test")
def test():
    return render_template("write.html", levels=LEVELS)


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
    estimate = predict.estimate_and_explain(features)
    predicted = estimate["predicted_effort"] if estimate["available"] else None
    meta = {
        "participant_code": code, "task_id": data["task_id"],
        "difficulty": TASKS_BY_ID[data["task_id"]]["difficulty"],
        "started_at": int(data["started_at"]), "ended_at": int(data["ended_at"]),
        "final_text": final_text,
        "self_rated_effort": (int(data["self_rated_effort"])
                              if data.get("self_rated_effort") else None),
    }
    sid = db.insert_session(meta, events, features, predicted)
    return jsonify({"ok": True, "session_id": sid,
                    "report_url": url_for("report", session_id=sid)})


_BAND_OBS = {"lower than most sessions": "Lower than typical",
             "within the typical range": "Within typical range",
             "higher than most sessions": "Higher than typical"}
_PROFILE_MAP = {"chars_per_sec": "Speed", "pause_time_ratio": "Pausing",
                "active_time_s": "Writing time", "revisions_per_100": "Revisions",
                "delete_rate": "Deletions"}
_GLANCE_MAP = {"chars_per_sec": "Typing", "pause_time_ratio": "Pausing",
               "revisions_per_100": "Revisions", "active_time_s": "Writing time"}


def _fmt_time(sec):
    sec = int(round(sec))
    return "%dm %02ds" % (sec // 60, sec % 60) if sec >= 60 else "%ds" % sec


def _hjoin(items):
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


# Phrasing for the radar interpretation box (percentile vs the study sample).
_PROFILE_PHRASE = {
    "Speed":        ("faster typing", "slower typing", "typing speed"),
    "Pausing":      ("more pausing", "less pausing", "pausing"),
    "Writing time": ("longer writing time", "shorter writing time", "writing time"),
    "Revisions":    ("more frequent revisions", "little revision", "revision activity"),
    "Deletions":    ("more deletion activity", "little deletion activity", "deletion activity"),
}


def _profile_interpretation(profile):
    """Plain-language summary of the radar (percentiles vs the study sample)."""
    above, below, avg = [], [], []
    for label, pct in zip(profile["labels"], profile["values"]):
        hi, lo, noun = _PROFILE_PHRASE.get(label, (label, label, label))
        if pct >= 66:
            above.append(hi)
        elif pct <= 33:
            below.append(lo)
        else:
            avg.append(noun)
    verb = "was" if len(avg) == 1 else "were"
    text = "Compared with other study sessions, "
    if above and below:
        body = "your writing involved " + _hjoin(above) + ", with " + _hjoin(below) + ". "
    elif above:
        body = "your writing involved " + _hjoin(above) + ". "
    elif below:
        body = "your writing involved " + _hjoin(below) + ". "
    else:
        body = ""
    if body:
        text += body
        if avg:
            text += "Your " + _hjoin(avg) + " " + verb + " closer to the study average."
    elif avg:
        text += "your " + _hjoin(avg) + " " + verb + " closer to the study average."
    else:
        text += "your writing pattern was broadly in line with the study sample."
    return text.strip()


@app.route("/report/<int:session_id>")
def report(session_id):
    s = db.get_session(session_id)
    if s is None:
        abort(404)
    feats = s["features"]
    estimate = predict.estimate_and_explain(feats)
    context = recs.context_labels(feats)
    recommendations = recs.recommend(feats)

    metrics = [
        {"value": s["word_count"], "label": "Words"},
        {"value": _fmt_time(feats.get("active_time_s", 0)), "label": "Writing time"},
        {"value": "%.1f" % feats.get("chars_per_sec", 0), "label": "Characters/sec"},
        {"value": int(feats.get("n_keydown", 0)), "label": "Keystrokes"},
        {"value": "%d%%" % round(feats.get("pause_time_ratio", 0) * 100), "label": "Time paused"},
    ]
    profile = {"labels": [], "values": []}
    glance = []
    for c in context:
        if c["feature"] in _PROFILE_MAP:
            profile["labels"].append(_PROFILE_MAP[c["feature"]])
            profile["values"].append(c["percentile"])
        if c["feature"] in _GLANCE_MAP:
            glance.append({"area": _GLANCE_MAP[c["feature"]],
                           "obs": _BAND_OBS.get(c["band"], c["band"])})

    contrib_view = None
    if estimate["available"] and estimate["contributions"]:
        top = estimate["contributions"][:5]
        maxabs = max(abs(v) for _, v in top) or 1
        contrib_view = [{"name": n, "val": v, "dir": "up" if v > 0 else "down",
                         "pct": round(abs(v) / maxabs * 100)} for n, v in top]

    timeline = predict.timeline_from_events(db.get_keystrokes(session_id))
    has_rec = recommendations and recommendations[0]["behaviour"] != "none"

    return render_template(
        "report.html", s=s, feats=feats, estimate=estimate, context=context,
        recommendations=recommendations, has_rec=has_rec,
        general_tips=recs.GENERAL_TIPS,
        task=TASKS_BY_ID.get(s["task_id"], {}), metrics=metrics, profile=profile,
        profile_interpretation=_profile_interpretation(profile),
        glance=glance, contrib_view=contrib_view, timeline=timeline)


# ===================== Researcher auth =====================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if (request.form.get("username") == ADMIN_USER and
                request.form.get("password") == ADMIN_PASSWORD):
            session["admin"] = True
            return redirect(url_for("admin"))
        return render_template("login.html", error="Incorrect username or password.")
    if session.get("admin"):
        return redirect(url_for("admin"))
    return render_template("login.html")


@app.route("/admin/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("home"))


# ===================== Researcher analytics (study data) =====================
@app.route("/admin")
@login_required
def admin():
    return render_template(
        "overview.html", active="overview",
        kpis=rd.study_kpis(), signals=rd.research_signals(),
        model=MODEL_RESULTS, live_count=len(db.list_sessions()),
        charts={"effort_dist": rd.effort_distribution(),
                "feature_vs_effort": rd.feature_vs_effort()})


@app.route("/admin/participants")
@login_required
def participants_page():
    return render_template("participants.html", active="participants",
                           participants=rd.participants())


@app.route("/admin/participants/<code>")
@login_required
def participant_profile(code):
    prof = rd.participant_profile(code)
    if prof is None:
        abort(404)
    return render_template("participant_profile.html", active="participants",
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
        "session_report.html", active="participants",
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
            "avg_effort": round(_avg([x["self_rated_effort"] for x in g]), 1),
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
        "avg_effort": round(_avg([x["self_rated_effort"] for x in g]), 1),
        "avg_speed": round(_avg(col("chars_per_sec")), 2),
        "avg_time": round(_avg(col("active_time_s"))),
        "avg_pause_ratio": round(_avg(col("pause_time_ratio")) * 100),
        "avg_revisions": round(_avg(col("revisions_per_100")), 1),
    }
    sessions = [{
        "id": x["id"],
        "level_title": TASKS_BY_ID.get(x["task_id"], {}).get("level_title", x["difficulty"]),
        "difficulty": x["difficulty"],
        "effort": x["self_rated_effort"] or 0,
        "speed": round(x["features"].get("chars_per_sec", 0), 2),
        "pauses": int(round(x["features"].get("n_long_pause_per_100", 0))),
        "revisions": int(x["features"].get("n_revision_bursts", 0)),
        "time_s": int(round(x["features"].get("active_time_s", 0))),
        "words": x["word_count"], "valid": x["behavioural_valid"],
    } for x in g]
    trend = {
        "labels": ["S%d" % (i + 1) for i in range(len(g))],
        "effort": [x["self_rated_effort"] for x in g],
        "speed": [round(x["features"].get("chars_per_sec", 0), 2) for x in g],
        "pauses": [round(x["features"].get("n_long_pause_per_100", 0), 1) for x in g],
        "revisions": [round(x["features"].get("revisions_per_100", 0), 1) for x in g],
    }
    return {"code": code, "snapshot": snap, "sessions": sessions,
            "trend": trend, "enough_trend": len(g) >= 3}


@app.route("/admin/live")
@login_required
def live_page():
    sessions = db.list_sessions()
    summary = {
        "sessions": len(sessions),
        "participants": len({x["participant_code"] for x in sessions}),
        "mean_self_rated": round(_avg([x["self_rated_effort"] for x in sessions]), 2),
        "mean_predicted": round(_avg([x["predicted_effort"] for x in sessions]), 2),
    }
    return render_template("live.html", active="live", sessions=sessions,
                           summary=summary,
                           participants=_live_participants(sessions))


@app.route("/admin/live/participants/<code>")
@login_required
def live_profile(code):
    prof = _live_profile(code)
    if prof is None:
        abort(404)
    return render_template("live_profile.html", active="live", p=prof)


@app.route("/admin/live/clear", methods=["POST"])
@login_required
def live_clear():
    db.clear_all()
    return redirect(url_for("live_page"))


@app.route("/admin/methodology")
@login_required
def methodology_page():
    return render_template("methodology.html", active="methodology",
                           kpis=rd.study_kpis())


@app.route("/admin/model-card")
@login_required
def model_card_page():
    return render_template("model_card.html", active="modelcard",
                           kpis=rd.study_kpis(), model=MODEL_RESULTS)


@app.route("/admin/research")
@login_required
def research_page():
    return render_template("research.html", active="research",
                           kpis=rd.study_kpis(), signals=rd.research_signals(),
                           model=MODEL_RESULTS)


@app.route("/admin/export.csv")
@login_required
def export_csv():
    v = rd.valid().to_dict("records") if hasattr(rd.valid(), "to_dict") else []
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


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
