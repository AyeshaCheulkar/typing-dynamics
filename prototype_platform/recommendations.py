"""
recommendations.py — writing-process suggestions that are TIED TO OBSERVED
BEHAVIOUR, never to the effort score (self-rated or predicted).

Design rules (from PLATFORM_DESIGN.md §6):
  - a suggestion fires only when a measured behaviour crosses a threshold defined
    RELATIVE TO THE TRAINING DISTRIBUTION (quartiles of the study's valid sessions);
  - no generic advice ("read books", "study harder") — each names its behaviour;
  - at most 3 suggestions; if none fire, one neutral message.

Thresholds come from the shared research feature table (../features.csv), read
ONLY. This module never writes anything and never touches the Stage-1 system.
"""

import os
import numpy as np
import pandas as pd

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_FEATURES_CSV = os.path.join(_ROOT, "features.csv")

# Behaviours shown in the report with a "compared to typical" context label.
DISPLAY_FEATURES = [
    ("chars_per_sec", "Typing speed"),
    ("active_time_s", "Writing time"),
    ("n_long_pause_per_100", "Long pauses"),
    ("pause_time_ratio", "Time spent paused"),
    ("delete_rate", "Backspace/delete activity"),
    ("revisions_per_100", "Revision activity"),
]

_DIST = None


def _dist():
    """Load the training distribution (valid sessions) once; column -> sorted array."""
    global _DIST
    if _DIST is None:
        df = pd.read_csv(_FEATURES_CSV)
        df = df[df["behavioural_valid"] == 1]
        num = df.select_dtypes(include="number")
        _DIST = {c: np.sort(num[c].to_numpy(float)) for c in num.columns}
        _DIST["_word_count_median"] = float(np.median(df["word_count"]))
    return _DIST


def _q(col, p):
    return float(np.percentile(_dist()[col], p))


def _percentile_of(col, value):
    arr = _dist()[col]
    return float((arr <= value).mean() * 100)


def _display(col, v):
    """Human-friendly formatting of a behaviour value."""
    if col == "chars_per_sec":
        return f"{v:.1f} characters/sec"
    if col == "active_time_s":
        m, s = int(v // 60), int(v % 60)
        return f"{m}m {s}s" if m else f"{s}s"
    if col == "n_long_pause_per_100":
        return f"{v:.1f} long pauses per 100 keystrokes"
    if col == "pause_time_ratio":
        return f"{v * 100:.0f}% of the time paused"
    if col == "delete_rate":
        return f"{v * 100:.0f}% of keystrokes were delete/backspace"
    if col == "revisions_per_100":
        return f"{v:.1f} revision bursts per 100 keystrokes"
    return f"{v:.2f}"


def context_labels(features):
    """For the report: each display behaviour vs the typical range (Q25–Q75)."""
    out = []
    for col, label in DISPLAY_FEATURES:
        if col not in _dist():
            continue
        v = float(features.get(col, 0))
        lo, hi = _q(col, 25), _q(col, 75)
        if v < lo:
            band = "lower than most sessions"
        elif v > hi:
            band = "higher than most sessions"
        else:
            band = "within the typical range"
        out.append({"feature": col, "label": label, "value": v,
                    "display": _display(col, v),
                    "band": band, "percentile": round(_percentile_of(col, v))})
    return out


def _rec(behaviour, title, observed, strategy, resources):
    return {"behaviour": behaviour, "title": title, "observed": observed,
            "strategy": strategy, "text": strategy, "resources": resources}


# General writing-process tips shown ONLY when no behaviour trigger fires. They
# are explicitly generic (not derived from this session or the effort score).
GENERAL_TIPS = [
    "Outline 2–3 key points before you start writing.",
    "Draft first, then edit — separate 'getting ideas down' from 'polishing'.",
    "Read widely in the style you want to write; note how strong writers structure ideas.",
    "Build typing fluency with free tools such as keybr.com or typing.com.",
]


def recommend(features):
    """Behaviour-tied suggestions (never triggered by the effort score).

    Each item has: behaviour, title, observed (what was measured), strategy
    (what to try), resources (concrete ways to build the skill), and text.
    """
    recs = []
    f = features

    def hi(col):   # in the top quartile of the study sample
        return f.get(col, 0) >= _q(col, 75)

    def lo(col):   # in the bottom quartile of the study sample
        return f.get(col, 1e9) <= _q(col, 25)

    # 1. Excessive revision -> planning-before-drafting.
    if hi("revisions_per_100") or hi("delete_rate"):
        recs.append(_rec(
            "revision", "Frequent revisions",
            "Higher-than-typical backspace / revision activity was observed — you "
            "edited while composing rather than after.",
            "Try planning the sentence in your head (or a few words) before typing "
            "it, so you rewrite less.",
            ["Write a rough first draft without deleting, then edit in a second pass.",
             "Practise 5 minutes of free-writing (no backspace) to build flow.",
             "Read on drafting: Anne Lamott's 'Bird by Bird' (the 'first drafts' chapter)."]))

    # 2. Many long (thinking) pauses -> plan/outline first.
    if hi("n_long_pause_per_100") or hi("pause_time_ratio"):
        recs.append(_rec(
            "pauses", "Long thinking pauses",
            "Several extended pauses occurred during the session — planning appears "
            "to have happened mid-draft.",
            "Briefly outline your main points before starting, to move some planning "
            "up front.",
            ["Jot a 3-bullet outline before writing the first sentence.",
             "Try a quick 'brain-dump', then organise the points.",
             "Online: a simple bullet list or a mind-map tool (e.g. MindMup)."]))

    # 3. Uneven typing rhythm -> separate planning from typing.
    if hi("std_iki_ms"):
        recs.append(_rec(
            "rhythm", "Uneven typing rhythm",
            "Your keystroke timing was uneven (bursts of typing separated by stalls), "
            "more variable than most sessions.",
            "This often reflects planning while typing; deciding the next sentence "
            "before you start it can smooth the rhythm.",
            ["Think the full sentence first, then type it in one go.",
             "Draft in short complete sentences rather than half-phrases.",
             "Read your point aloud in your head before committing it."]))

    # 4. One very long single pause -> unblock and move on.
    if hi("max_pause_ms"):
        recs.append(_rec(
            "longpause", "A very long single pause",
            "One notably long pause occurred — often a sign of getting stuck on a "
            "particular idea or wording.",
            "When stuck, jot a keyword or placeholder and move on; return to it "
            "afterwards rather than stalling.",
            ["Use a placeholder like [example?] and keep writing.",
             "Write the easy part of the answer first to build momentum.",
             "Set a 30-second 'move on' rule when a sentence won't come."]))

    # 5. Frequent micro-hesitations -> write in fuller units.
    if hi("n_short_pause_per_100"):
        recs.append(_rec(
            "hesitation", "Frequent short hesitations",
            "Many brief hesitations occurred between words — writing progressed in "
            "small stop-start steps.",
            "Try composing a whole clause or sentence before pausing, rather than "
            "word-by-word.",
            ["Aim to type a full sentence, then pause to think.",
             "Read the prompt once more so the direction is clear before you start.",
             "Practise free-writing to build continuous flow."]))

    # 6. Slow typing -> typing fluency (framed as fluency, never ability).
    if lo("chars_per_sec"):
        recs.append(_rec(
            "speed", "Typing fluency",
            "Typing pace was slower than most sessions, which can make it harder to "
            "keep up with your ideas.",
            "Short, regular typing practice can help you get thoughts down faster.",
            ["Practise touch-typing ~10 min/day at keybr.com or typing.com.",
             "Try monkeytype.com to track speed and accuracy over time.",
             "Prioritise accuracy first — speed tends to follow."]))

    # 7. Long time for little output -> timebox.
    if hi("active_time_s") and f.get("word_count", 1e9) <= _dist()["_word_count_median"]:
        recs.append(_rec(
            "time", "Time vs output",
            "The session took longer than most for the amount written.",
            "Timeboxing a first draft, then editing, can help you use the time "
            "more efficiently.",
            ["Set a short timer (e.g. 10 min) for a first draft, then edit.",
             "Try the Pomodoro technique (25-min focused blocks).",
             "Decide a rough word target before you begin."]))

    # 8. Short response -> develop points further.
    if lo("word_count"):
        recs.append(_rec(
            "length", "Shorter response",
            "The response was shorter than most sessions for this task.",
            "Developing each point with a reason or a concrete example usually "
            "strengthens the writing.",
            ["Add a 'because…' or 'for example…' to each main point.",
             "Use the classic point → explain → example structure.",
             "Re-read the prompt and check every part is addressed."]))

    # 9. Very little editing -> a quick proofread pass (neutral/positive).
    if lo("revisions_per_100") and lo("delete_rate"):
        recs.append(_rec(
            "clean", "Clean first pass",
            "Very little editing or backspacing was observed — you wrote in a mostly "
            "continuous pass.",
            "That is efficient; a single quick re-read at the end can still catch "
            "small slips.",
            ["Do one proofreading pass for typos and missing words.",
             "Read the final sentence-to-sentence flow once.",
             "Check the opening and closing sentences match your point."]))

    # 10. Steady flow -> positive reinforcement (behavioural, not effort).
    if lo("n_long_pause_per_100") and f.get("chars_per_sec", 0) >= _q("chars_per_sec", 50):
        recs.append(_rec(
            "flow", "Steady writing flow",
            "You kept up a steady output with few long pauses — a sign of fluent, "
            "continuous composition.",
            "Keep using whatever preparation worked here; it supported a smooth "
            "writing process.",
            ["Note what helped (a clear idea, an outline) and repeat it.",
             "Steady flow pairs well with a final proofread pass.",
             "Challenge yourself with a Moderate prompt to extend the skill."]))

    recs = recs[:5]
    if not recs:
        recs.append(_rec(
            "none", "Balanced process",
            "Writing-process measures were within the typical range.",
            "Nothing specific stands out to change.", []))
    return recs


if __name__ == "__main__":
    # High-revision + slow example should trigger the revision & speed suggestions.
    demo = {"revisions_per_100": 9.0, "delete_rate": 0.20, "n_long_pause_per_100": 0.1,
            "pause_time_ratio": 0.3, "chars_per_sec": 0.9, "active_time_s": 60,
            "word_count": 200}
    print("thresholds — revisions Q75:", round(_q("revisions_per_100", 75), 2),
          "| chars_per_sec Q25:", round(_q("chars_per_sec", 25), 2))
    for r in recommend(demo):
        print(f"  [{r['behaviour']}] {r['text']}")
    print("neutral case:")
    for r in recommend({"revisions_per_100": 3, "delete_rate": 0.05,
                        "n_long_pause_per_100": 1, "pause_time_ratio": 0.4,
                        "chars_per_sec": 2.5, "active_time_s": 100, "word_count": 200}):
        print(f"  [{r['behaviour']}] {r['text']}")
