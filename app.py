"""
app.py — Flask backend for the Typing Dynamics Writing Analytics Platform.

Stage 1 responsibilities:
  - Serve the writing editor page
  - Provide the list of writing tasks
  - Receive a completed session (metadata + keystrokes + effort rating) and store it
  - Provide a simple admin/verification view so we can confirm data is captured correctly

Run:
    venv/Scripts/python app.py
Then open http://127.0.0.1:5000
"""

import csv
import io
import os
import re
from functools import wraps

from flask import Flask, render_template, request, jsonify, abort, Response

import db

app = Flask(__name__)

# Create tables on import. Locally this also runs from __main__, but on a WSGI
# host (PythonAnywhere) __main__ never executes, so the DB must be initialised
# here or the first request would hit a missing table. init_db is idempotent.
db.init_db()

# ---------------------------------------------------------------------------
# Admin protection.
# The participant pages ("/", "/api/session") stay public — friends need them.
# But /admin, the CSV export and include/exclude expose ALL responses and must
# be password-protected once the app is on the public internet.
#
# Set these as environment variables on the host (see pythonanywhere_wsgi.py):
#     ADMIN_USER      (optional, default "admin")
#     ADMIN_PASSWORD  (required to unlock admin when hosted)
#
# For LOCAL development the password can be left unset: admin is then reachable
# only from your own machine (127.0.0.1) and blocked for everyone else.
# ---------------------------------------------------------------------------
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if ADMIN_PASSWORD is None:
            # No password configured: allow only from the local machine.
            if request.remote_addr in ("127.0.0.1", "::1"):
                return view(*args, **kwargs)
            return Response(
                "Admin is locked. Set the ADMIN_PASSWORD environment variable "
                "on the host to enable it.", 503)
        auth = request.authorization
        if not auth or auth.username != ADMIN_USER or auth.password != ADMIN_PASSWORD:
            return Response(
                "Authentication required.", 401,
                {"WWW-Authenticate": 'Basic realm="Typing Dynamics admin"'})
        return view(*args, **kwargs)
    return wrapper

# Minimum words for a submission not to be flagged as too short. The prompts ask
# for 120–180 words, so 50 is a lenient floor — enough to catch one-liners and
# empty-ish answers without penalising genuinely brief writers.
MIN_WORDS = 50

# Participant IDs must match this AFTER normalisation (see normalize_pid).
# Permissive on purpose: it rejects blanks/garbage but accepts any reasonable
# scheme (P01, P001, PART-1, S12_A …). It never enforces a single fixed format.
PID_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9_-]{1,19}$")


def normalize_pid(raw):
    """
    Canonicalise a participant ID so the SAME person always maps to the SAME
    grouping key. Without this, 'p01', 'P01' and ' P 01 ' would be treated as
    three different participants and silently break participant-level CV
    (GroupKFold / leave-one-participant-out) in Stage 3.

    Rule: drop all whitespace, then upper-case. 'p 01' -> 'P01'.
    """
    return re.sub(r"\s+", "", str(raw)).upper()


def assess_quality(text, prompt):
    """
    Heuristic content-quality check. Returns a list of flag strings.

    IMPORTANT: these are *review aids only* — the app never rejects a session
    on their basis. They exist so the researcher can quickly spot submissions
    that may not be genuine on-topic writing (gibberish, keyboard-mashing,
    copies of the prompt, one-liners) and decide whether to exclude them from
    the ML dataset. Content *relevance* is deliberately left to human judgement.
    """
    flags = []
    words = text.split()
    n_words = len(words)

    # 1. Too short to be a real attempt at a 120–180 word task.
    if n_words < MIN_WORDS:
        flags.append("too_short")

    # 2. Long runs of one repeated character, e.g. "aaaaaaaa" (keyboard mashing).
    if re.search(r"(.)\1{5,}", text):
        flags.append("keyboard_mashing")

    # 3. Very low word variety — the same few words over and over.
    if n_words >= 12:
        unique_ratio = len({w.lower() for w in words}) / n_words
        if unique_ratio < 0.4:
            flags.append("repetitive")

    # 4. Gibberish: most "words" have no vowel (real English words almost always
    #    contain one). Only meaningful once there are a few tokens to judge.
    alpha = re.findall(r"[A-Za-z]+", text)
    if len(alpha) >= 5:
        with_vowel = sum(1 for w in alpha if re.search(r"[aeiouy]", w.lower()))
        if with_vowel / len(alpha) < 0.6:
            flags.append("gibberish")

    # 5. Copied prompt: a 6-word run of the prompt appears verbatim in the answer.
    p_tokens = re.findall(r"[A-Za-z']+", prompt.lower())
    answer_lc = " ".join(re.findall(r"[A-Za-z']+", text.lower()))
    for i in range(len(p_tokens) - 5):
        if " ".join(p_tokens[i:i + 6]) in answer_lc:
            flags.append("copied_prompt")
            break

    return flags

# ---------------------------------------------------------------------------
# Writing tasks — TWO difficulty levels only (Easy, Moderate).
#
# Each level holds a POOL of prompt variations. When a participant starts, one
# variation is picked from the chosen level's pool. Keeping several variations
# per level matters for the study: a participant does repeated sessions, and
# reusing the exact same prompt would let them memorise/repeat it. Variations
# keep the writing fresh while holding the difficulty level constant.
#
#   Easy     — short everyday/personal writing (routine, favourites, weekend…).
#   Moderate — describe a scene from an image (each variation shows a picture).
#
# To add an image variation: drop a .jpg/.png/.svg into static/images/ and add
# an entry under the "moderate" pool with its filename and an "image_alt".
# ---------------------------------------------------------------------------
LEVELS = [
    {
        "id": "easy",
        "title": "Everyday writing",
        "difficulty": "Easy",
        "blurb": "A short, familiar topic about your own life — nothing to research.",
        "variations": [
            {"id": "easy_routine",
             "prompt": "Describe your typical morning routine, from waking up to "
                       "starting your day. About 120–180 words."},
            {"id": "easy_food",
             "prompt": "Describe your favourite food or meal. What is it, and why "
                       "do you love it? Try to make the reader hungry. "
                       "About 120–180 words."},
            {"id": "easy_place",
             "prompt": "Describe your favourite place to relax. Where is it, and "
                       "how does it make you feel? About 120–180 words."},
            {"id": "easy_weekend",
             "prompt": "Describe how you like to spend an ideal weekend. "
                       "About 120–180 words."},
            {"id": "easy_hobby",
             "prompt": "Describe a hobby or activity you enjoy and explain what "
                       "you like about it. About 120–180 words."},
            {"id": "easy_person",
             "prompt": "Describe a person you admire and explain why they matter "
                       "to you. About 120–180 words."},
        ],
    },
    {
        "id": "moderate",
        "title": "Describe & explain",
        "difficulty": "Moderate",
        "blurb": "A topic that needs a bit of structure, reflection or reasoning.",
        "variations": [
            {"id": "mod_journey",
             "prompt": "Describe a memorable journey or trip you have taken. Where "
                       "did you go, what happened, and what made it stand out? "
                       "About 150–200 words."},
            {"id": "mod_technology",
             "prompt": "Explain how a piece of technology has changed the way you "
                       "live, study or work. Give specific examples of what is "
                       "different now. About 150–200 words."},
            {"id": "mod_challenge",
             "prompt": "Describe a challenge or difficult situation you faced and "
                       "explain how you dealt with it and what you learned. "
                       "About 150–200 words."},
            {"id": "mod_compare",
             "prompt": "Compare two things you know well — for example two cities, "
                       "two seasons, or two hobbies — and explain which you prefer "
                       "and why. About 150–200 words."},
            {"id": "mod_career",
             "prompt": "Describe what your ideal job or career would look like and "
                       "explain why it appeals to you and how you might get there. "
                       "About 150–200 words."},
            {"id": "mod_tradition",
             "prompt": "Explain a tradition, festival or custom that is important "
                       "in your family or culture, and why it matters to you. "
                       "About 150–200 words."},
        ],
    },
]

# Flatten every variation into a lookup keyed by its id, carrying its level
# metadata along. task_id stored in the DB is the *variation* id (e.g.
# "easy_food"), which is descriptive and needs no schema change.
TASKS_BY_ID = {}
for _lvl in LEVELS:
    for _v in _lvl["variations"]:
        TASKS_BY_ID[_v["id"]] = {
            "prompt": _v["prompt"],
            "image": _v.get("image"),
            "image_alt": _v.get("image_alt"),
            "level_id": _lvl["id"],
            "level_title": _lvl["title"],
            "difficulty": _lvl["difficulty"],
        }

# Compact map (variation id -> friendly label + difficulty) for the admin view.
TASK_META = {
    tid: {"label": meta["level_title"], "difficulty": meta["difficulty"]}
    for tid, meta in TASKS_BY_ID.items()
}


@app.route("/")
def index():
    """The participant-facing writing platform."""
    return render_template("index.html", levels=LEVELS)


@app.route("/api/session", methods=["POST"])
def save_session():
    """Receive one completed writing session and persist it to SQLite."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"ok": False, "error": "No JSON body received."}), 400

    # --- Validation: reject anything that would corrupt the dataset ---------
    required = ["participant_id", "task_id", "started_at", "ended_at",
                "final_text", "effort_rating"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"ok": False, "error": f"Missing fields: {missing}"}), 400

    pid = normalize_pid(data["participant_id"])
    if not pid:
        return jsonify({"ok": False, "error": "Participant ID is empty."}), 400
    if not PID_PATTERN.match(pid):
        return jsonify({"ok": False, "error":
                        "Participant ID must be 2–20 letters/numbers "
                        "(e.g. P01)."}), 400
    data["participant_id"] = pid   # store the normalised, canonical form

    if data["task_id"] not in TASKS_BY_ID:
        return jsonify({"ok": False, "error": "Unknown task_id."}), 400

    try:
        rating = int(data["effort_rating"])
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "effort_rating must be a number."}), 400
    if rating < 1 or rating > 5:
        return jsonify({"ok": False, "error": "effort_rating must be 1..5."}), 400
    data["effort_rating"] = rating

    # Attach the authoritative prompt text from the server (not the client).
    data["task_prompt"] = TASKS_BY_ID[data["task_id"]]["prompt"]
    data["user_agent"] = request.headers.get("User-Agent", "")

    # Compute content-quality flags (review aids — never used to reject).
    text = str(data["final_text"])
    data["word_count"] = len(text.split())
    data["quality_flags"] = assess_quality(text, data["task_prompt"])

    session_id = db.insert_session(data)
    return jsonify({"ok": True, "session_id": session_id,
                    "quality_flags": data["quality_flags"]})


@app.route("/api/session/<int:session_id>/include", methods=["POST"])
@require_admin
def set_included(session_id):
    """Researcher action: include/exclude a session from the ML dataset."""
    body = request.get_json(silent=True) or {}
    if "included" not in body:
        return jsonify({"ok": False, "error": "Missing 'included'."}), 400
    ok = db.set_included(session_id, bool(body["included"]))
    if not ok:
        abort(404)
    return jsonify({"ok": True, "included": 1 if body["included"] else 0})


@app.route("/admin")
@require_admin
def admin():
    """Researcher view: list all captured sessions with event counts + summary."""
    sessions = db.list_sessions()
    return render_template(
        "admin.html",
        sessions=sessions,
        stats=_summarise(sessions),
        per_participant=_per_participant(sessions),
        task_meta=TASK_META,
    )


def _per_participant(sessions):
    """One row per participant: how much has been collected so far.

    Lets the researcher track progress against the ~10 participants × 3–4 tasks
    target and spot anyone with too few (or excluded-heavy) sessions.
    """
    by_pid = {}
    for s in sessions:
        p = by_pid.setdefault(s["participant_id"], {
            "participant_id": s["participant_id"],
            "sessions": 0, "tasks": set(), "included": 0,
            "flagged": 0, "effort_sum": 0,
        })
        p["sessions"] += 1
        p["tasks"].add(s["task_id"])
        p["included"] += 1 if s["included"] else 0
        p["flagged"] += 1 if s["quality_flags"] else 0
        p["effort_sum"] += s["effort_rating"]
    rows = []
    for p in by_pid.values():
        rows.append({
            "participant_id": p["participant_id"],
            "sessions": p["sessions"],
            "distinct_tasks": len(p["tasks"]),
            "included": p["included"],
            "flagged": p["flagged"],
            "avg_effort": round(p["effort_sum"] / p["sessions"], 2),
        })
    rows.sort(key=lambda r: r["participant_id"])
    return rows


@app.route("/admin/export.csv")
@require_admin
def export_csv():
    """Download all sessions as a flat CSV for Stage 2 / spreadsheet review."""
    sessions = db.list_sessions()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "id", "participant_id", "task_id", "difficulty", "started_at",
        "ended_at", "duration_ms", "word_count", "char_count", "event_count",
        "effort_rating", "paste_used", "quality_flags", "included", "created_at",
    ])
    for s in sessions:
        meta = TASK_META.get(s["task_id"], {"difficulty": "?"})
        writer.writerow([
            s["id"], s["participant_id"], s["task_id"], meta["difficulty"],
            s["started_at"], s["ended_at"], s["duration_ms"], s["word_count"],
            s["char_count"], s["event_count"], s["effort_rating"],
            s["paste_used"], "|".join(s["quality_flags"]), s["included"],
            s["created_at"],
        ])
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=sessions.csv"},
    )


def _summarise(sessions):
    """Compute headline numbers for the admin dashboard cards."""
    n = len(sessions)
    if n == 0:
        return {"total": 0, "participants": 0, "avg_effort": 0,
                "avg_duration_s": 0, "paste_flags": 0, "flagged": 0,
                "included": 0, "effort_dist": {}}
    participants = {s["participant_id"] for s in sessions}
    effort_dist = {r: 0 for r in range(1, 6)}
    for s in sessions:
        effort_dist[s["effort_rating"]] = effort_dist.get(s["effort_rating"], 0) + 1
    return {
        "total": n,
        "participants": len(participants),
        "avg_effort": round(sum(s["effort_rating"] for s in sessions) / n, 2),
        "avg_duration_s": round(sum(s["duration_ms"] for s in sessions) / n / 1000, 1),
        "paste_flags": sum(1 for s in sessions if s["paste_used"]),
        "flagged": sum(1 for s in sessions if s["quality_flags"]),
        "included": sum(1 for s in sessions if s["included"]),
        "effort_dist": effort_dist,
    }


@app.route("/api/session/<int:session_id>")
@require_admin
def session_detail(session_id):
    """Full detail of one session (metadata + all events) for verification."""
    detail = db.get_session_detail(session_id)
    if detail is None:
        abort(404)
    return jsonify(detail)


if __name__ == "__main__":
    db.init_db()
    # host=0.0.0.0 lets other devices on your network reach it during testing.
    app.run(host="0.0.0.0", port=5000, debug=True)
