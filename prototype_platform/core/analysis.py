"""
analysis.py — everything the participant report says about HOW a person wrote, computed from their
keystrokes and compared with reference data:

  compare()      speed / rhythm / pausing / revising / deleting against other writers
                 (key speed against typists on the same kind of computer)
  engagement()   how much the rhythm resembles emotional vs neutral writing, with per-behaviour drivers
  tips()         2-3 suggestions tied to the strongest drivers and what the person actually did
  headlines()    three plain sentences for the top of the report
  over_time()    characters per minute across the session
  pause_view()   where the pauses fell
  tone_vs_feeling()  text tone against the person's own valence answer

Formulas, sources and test results are shown on the researcher's Model research page, not here.
"""

import json
import math

import numpy as np

from core import behaviour as bh
from core import paths

_REF = None
_ENG = None
_NORMS = None


def _json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def engagement_model():
    global _ENG
    if _ENG is None:
        _ENG = _json(paths.ENGAGEMENT_MODEL)
    return _ENG


def norms():
    global _NORMS
    if _NORMS is None:
        _NORMS = _json(paths.TYPING_NORMS)
    return _NORMS


def reference():
    """Pilot + public free-text sessions (valid streams only): measure -> 101-point quantile table, and n.
    Built by research/build_state_models.py."""
    global _REF
    if _REF is None:
        r = _json(paths.PEER_REFERENCE)
        _REF = {"vals": {c: np.array(v) for c, v in r["quantiles"].items()}, "n": r["n"]}
    return _REF


def _pct(sorted_vals, v):
    """Percentile rank 0-100 (mid-rank for ties)."""
    lo, hi = np.searchsorted(sorted_vals, v, "left"), np.searchsorted(sorted_vals, v, "right")
    return float(100 * (lo + hi) / 2 / len(sorted_vals))


def _word(p, hi, lo, mid="were about typical"):
    return hi if p >= 66 else lo if p <= 33 else mid


# ------------------------------------------------------------------ compare
def compare(feats, keyboard=None):
    """Bars comparing this writer with others. fill = share of reference writers/typists beaten
    (speed) or the measure's own percentile (the rest). Returns (bars, note)."""
    ref = reference()
    bars = []

    # Copy-typing is faster than composing, so the copy-task data is used only for the laptop vs
    # desktop shift; the person is then ranked against free-text writers on the device-adjusted value.
    iki = float(feats.get("median_iki_ms") or 0)
    med = {k: v[50] for k, v in norms()["median_iki_ms"].items()}
    overall = sum(med.values()) / len(med)
    factor = med["laptop"] / overall if keyboard == "laptop" else med["desktop"] / overall if keyboard == "external" else 1.0
    adj = iki / factor
    faster = 100 - _pct(ref["vals"]["median_iki_ms"], adj)
    where = {"laptop": "on a laptop keyboard", "external": "on a desktop or external keyboard"}.get(keyboard, "")
    bars.append({"label": "Key-to-key speed", "fill": round(faster),
                 "value": "%d ms between keys" % round(iki),
                 "phrase": "were faster than %d%% of writers%s" % (round(faster), " (allowing for typing " + where + ")" if where else ""),
                 "group": "%d writers, adjusted for keyboard type using 491 typists (Inputlog corpus)" % ref["n"]})

    cv = bh.rhythm_cv(feats)
    spec = (("Typing rhythm", "rhythm_cv", cv, "%.2f variability" % cv,
             "less even than most writers", "more even than most writers"),
            ("Time spent paused", "pause_time_ratio", feats.get("pause_time_ratio", 0),
             "%d%% of the time" % round(100 * feats.get("pause_time_ratio", 0)),
             "paused more than most writers", "paused less than most writers"),
            ("Revising", "revisions_per_100", feats.get("revisions_per_100", 0),
             "%.1f revisions per 100 keys" % feats.get("revisions_per_100", 0),
             "revised more than most writers", "revised less than most writers"),
            ("Deleting", "delete_rate", feats.get("delete_rate", 0),
             "%.1f%% of keystrokes" % (100 * feats.get("delete_rate", 0)),
             "deleted more than most writers", "deleted less than most writers"))
    for label, key, v, val, hi, lo in spec:
        p = _pct(ref["vals"][key], float(v))
        bars.append({"label": label, "fill": round(p), "value": val,
                     "phrase": _word(p, hi, lo, "were about typical for writers"),
                     "group": "%d writers (pilot + public free-text studies)" % ref["n"]})
    return bars


# ------------------------------------------------------------------ engagement
def engagement(feats):
    """Resemblance to emotional writing (0-100; 50 = no evidence either way) + drivers, or None."""
    if not feats.get("behavioural_valid", 1):
        return None
    m = engagement_model()
    vals = {"rhythm_cv": bh.rhythm_cv(feats), **{k: float(feats.get(k) or 0) for k in m["features"]
                                                  if k != "rhythm_cv"}}
    drivers = []
    for f, mu, sd, w in zip(m["features"], m["mean"], m["scale"], m["coef"]):
        z = max(-3.0, min(3.0, (vals[f] - mu) / sd))        # cap so one extreme value cannot dominate
        drivers.append({"key": f, "label": m["labels"][f], "effect": w * z, "z": z})
    total = sum(d["effect"] for d in drivers)
    pct = round(100 / (1 + math.exp(-total)))
    top = max(abs(d["effect"]) for d in drivers) or 1
    for d in drivers:
        d["width"] = round(100 * abs(d["effect"]) / top)
        d["dir"] = "toward emotional" if d["effect"] > 0 else "toward neutral"
    drivers.sort(key=lambda d: -abs(d["effect"]))
    level = ("Resembles emotional writing" if pct >= 58 else
             "Resembles neutral writing" if pct <= 42 else "Between emotional and neutral")
    return {"pct": pct, "level": level, "drivers": drivers}


# ------------------------------------------------------------------ pauses / actions
_WHERE = {"within_word": "inside words", "between_words": "between words",
          "between_sentences": "between sentences"}


def pause_view(acts):
    """Counts and typical length of pauses by where they fell."""
    rows = []
    for k, label in _WHERE.items():
        b = acts["pauses"][k]
        rows.append({"label": label, "n": b["n"],
                     "avg_s": round(b["total_ms"] / b["n"] / 1000, 1) if b["n"] else 0,
                     "longest_s": round(b["longest_ms"] / 1000, 1)})
    total = sum(r["n"] for r in rows)
    for r in rows:
        r["share"] = round(100 * r["n"] / total) if total else 0
    return {"rows": rows, "total": total}


def pause_lengths(acts):
    """How long the pauses were: counts per length band."""
    b = acts["length_buckets"]
    return {"labels": list(b), "values": list(b.values())}


def over_time(events, bins=10):
    """Characters typed per minute in equal slices of the session."""
    t = sorted(e["t"] for e in events if e.get("type") == "keydown" and len(e.get("key") or "") == 1)
    if len(t) < 20:
        return None
    t0, span = t[0], max(t[-1] - t[0], 1)
    width = span / bins
    counts = [0] * bins
    for x in t:
        counts[min(bins - 1, int((x - t0) / width))] += 1
    label = lambda ms: "%d:%02d" % divmod(int(ms / 1000), 60)
    return {"labels": [label(width * (i + 0.5)) for i in range(bins)],
            "values": [round(c / (width / 60000.0)) for c in counts]}


def pace_story(ot):
    """Plain sentences about how the pace changed through the session."""
    if not ot:
        return None
    v, n = ot["values"], len(ot["values"])
    k = max(1, n // 3)
    first, last = sum(v[:k]) / k, sum(v[-k:]) / k
    change = 100 * (last - first) / first if first else 0
    slow, fast = min(range(n), key=v.__getitem__), max(range(n), key=v.__getitem__)
    trend = ("You sped up as you went, which often happens once the ideas are flowing." if change > 15 else
             "You slowed toward the end, which is common as a passage nears its conclusion or attention tires."
             if change < -15 else "Your pace stayed level from start to finish.")
    return ["You began at about %d characters a minute and finished at about %d. %s" % (first, last, trend),
            "Your fastest stretch was around %s (%d characters a minute) and your slowest around %s (%d)."
            % (ot["labels"][fast], v[fast], ot["labels"][slow], v[slow])]


# Leave-one-participant-out mean error of the pilot Random Forest (research/docs/ANALYSIS_PRIMARY.md).
EFFORT_MAE = 1.1


def effort_card(row, estimate):
    """Model's effort estimate (as a range) next to the person's own answer, with what drove it."""
    if not estimate or not estimate.get("available"):
        return None
    p = estimate["predicted_effort"]
    lo, hi = max(1.0, p - EFFORT_MAE), min(5.0, p + EFFORT_MAE)
    if row.get("tlx_effort"):
        actual, src = row["tlx_effort"], "your effort answer"
    elif row.get("self_rated_effort"):
        actual, src = row["self_rated_effort"], "your effort rating"
    else:
        actual, src = None, None
    scale = lambda x: round((x - 1) / 4 * 100, 1)
    if actual is None:
        verdict = "You did not rate your effort, so there is nothing to compare the estimate with."
    elif abs(actual - p) <= EFFORT_MAE:
        verdict = "%s (%d) is within the model's usual error of its estimate (%.1f), so your typing and your own sense of effort agree."
        verdict = verdict % (src.capitalize(), actual, p)
    else:
        verdict = ("You rated the effort %s than the model expected (%d against %.1f). That gap is larger than the model's usual "
                   "error, so how hard the writing felt was not visible in your typing." %
                   ("higher" if actual > p else "lower", actual, p))
    top = estimate["contributions"][:5]
    big = max(abs(v) for _, v in top) or 1
    return {"pred": p, "lo": scale(lo), "hi": scale(hi), "pred_pos": scale(p), "actual": actual, "src": src,
            "actual_pos": scale(actual) if actual else None, "verdict": verdict, "mae": EFFORT_MAE,
            "drivers": [{"name": n, "up": v > 0, "width": round(100 * abs(v) / big)} for n, v in top]}


# ------------------------------------------------------------------ words
def headlines(feats, acts, bars):
    """Three plain sentences about how the person wrote."""
    by = {b["label"]: b for b in bars}
    pv = pause_view(acts)
    long_n = int(round(feats.get("n_long_pause_per_100", 0) / 100 * feats.get("n_keydown", 0)))
    p = by["Time spent paused"]["fill"]
    r = by["Typing rhythm"]["fill"]
    if r <= 33 and p <= 50:
        one = "You wrote in a steady, even rhythm with few stops."
    elif r >= 66 and p >= 50:
        one = "You wrote in bursts with real stops in between: fast stretches, then time to think."
    elif r >= 66:
        one = "Your typing came in uneven bursts rather than one steady pace."
    elif p >= 66:
        one = "You wrote at an even pace but spent a lot of the time paused."
    else:
        one = "You wrote at a fairly steady pace with a normal amount of stopping."
    if pv["total"]:
        top = max(pv["rows"], key=lambda x: x["n"])
        two = ("You paused %d times for half a second or more (%d of them for 2 seconds or longer); most fell %s, "
               "and the longest lasted %.1f seconds." % (pv["total"], long_n, top["label"],
                                                         feats.get("max_pause_ms", 0) / 1000))
    else:
        two = "You did not pause for more than half a second at any point."
    rev = by["Revising"]["phrase"]
    three = ("You typed %d characters and deleted %d, and %s." %
             (acts["additions"], acts["deletions"], rev if "typical" not in rev else "revised about as much as most writers"))
    return [one, two, three]


_TIPS = {
    "rhythm_cv": (
        "hi", "Your typing came in uneven bursts",
        "Try drafting in short timed sprints of about ten minutes without stopping to fix anything, then edit once the sprint ends."),
    "pause": (
        "hi", "You spent a lot of the session paused",
        "Spend two minutes listing your three main points before you start. Pauses shrink when the next idea is already decided."),
    "revise": (
        "hi", "You went back and corrected a lot while typing",
        "Leave a quick mark such as [fix] where something feels wrong and keep going. Fixing everything after the draft keeps the flow."),
    "revise_lo": (
        "lo", "You rarely went back to change anything",
        "Read the passage through once after you finish. A short second pass catches the rough spots a steady draft leaves behind."),
    "rhythm_lo": (
        "lo", "Your rhythm was very even",
        "That is a strong base for drafting. Add a deliberate pause at the end of each paragraph to check that you are still heading the right way."),
}
_TIP_FOR = {"rhythm_cv": ("rhythm_cv", "rhythm_lo"), "pause_time_ratio": ("pause", None),
            "n_long_pause_per_100": ("pause", None), "max_pause_ms": ("pause", None),
            "revisions_per_100": ("revise", "revise_lo"), "delete_rate": ("revise", "revise_lo")}


def tips(eng, bars, skill=None):
    """Up to three suggestions, picked in order of how strongly a behaviour drove the reading."""
    by = {b["label"]: b["fill"] for b in bars}
    pct = {"rhythm_cv": by["Typing rhythm"], "pause_time_ratio": by["Time spent paused"],
           "n_long_pause_per_100": by["Time spent paused"], "max_pause_ms": by["Time spent paused"],
           "revisions_per_100": by["Revising"], "delete_rate": by["Revising"]}
    out, seen = [], set()
    for d in (eng["drivers"] if eng else []):
        if d["key"] not in _TIP_FOR:
            continue
        hi_key, lo_key = _TIP_FOR[d["key"]]
        p = pct[d["key"]]
        key = hi_key if p >= 66 else lo_key if p <= 33 else None
        if key and key not in seen:
            seen.add(key)
            out.append({"observed": _TIPS[key][1], "tip": _TIPS[key][2]})
    if skill == "hunt" and by["Key-to-key speed"] <= 33:
        out.append({"observed": "You look at the keys while typing, so each key takes longer",
                    "tip": "Short daily touch-typing practice is the biggest single speed-up; the pauses in this report are partly "
                           "the cost of searching for keys."})
    return out[:3] or [{"observed": "Your pattern was close to typical on every measure",
                        "tip": "Nothing stands out to change. Keep this approach, and compare it with how you write under time pressure."}]


# ------------------------------------------------------------------ text tone vs feeling
_FEEL = ["very unpleasant", "unpleasant", "neutral", "pleasant", "very pleasant"]


def tone_vs_feeling(row, text_aff):
    """The person's own valence answer (1-5) against the tone of their words."""
    mood = row.get("self_mood")
    if not mood or not text_aff:
        return None
    tone5 = max(1, min(5, round(3 + 2 * text_aff["compound"])))
    gap = abs(tone5 - mood)
    verdict = ("Your words and your feeling point the same way." if gap <= 1 else
               "Your words read %s, but you said you felt %s. People often write more gently, or more harshly, than they feel."
               % (_FEEL[tone5 - 1], _FEEL[mood - 1]))
    return {"felt": _FEEL[mood - 1], "felt_pos": (mood - 1) * 25, "words": _FEEL[tone5 - 1],
            "words_pos": (tone5 - 1) * 25, "verdict": verdict}
