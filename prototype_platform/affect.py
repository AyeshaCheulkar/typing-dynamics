"""
affect.py — the emotion-writing extension: ties together
  1. text emotion      (VADER sentiment model + first-person-pronoun rate),
  2. behaviour indices (behaviour.py — transparent equal-weight formulas),
  3. external-data model (Random Forest trained on EmoSurv; exploratory),
  4. self-report comparison (mood / focus / stress ratings).

Every part degrades gracefully: if vaderSentiment or emotion_model.pkl is missing
the corresponding card is simply hidden — the rest of the report still works.
"""

import json
import os
import re

import behaviour as bh

_HERE = os.path.dirname(os.path.abspath(__file__))

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _VADER = SentimentIntensityAnalyzer()
except Exception:               # optional dependency
    _VADER = None

_EMO_MODEL = None
_EMO_MODEL_TRIED = False

_FIRST_PERSON = {"i", "me", "my", "mine", "myself", "i'm", "i've", "i'd", "i'll"}
_WORD_RE = re.compile(r"[A-Za-z']+")
_SENT_RE = re.compile(r"(?<=[.!?])\s+|\n+")


# ---------------------------------------------------------------- text emotion
def text_emotion(text):
    """Sentiment + simple style markers of the written passage (None if unavailable)."""
    if _VADER is None or not text or len(text.split()) < 8:
        return None
    sents = [s.strip() for s in _SENT_RE.split(text) if len(s.strip()) > 2]
    sent_scores = [_VADER.polarity_scores(s)["compound"] for s in sents] or [0.0]
    whole = _VADER.polarity_scores(text)
    words = [w.lower() for w in _WORD_RE.findall(text)]
    pos_w = sum(1 for w in words if _VADER.lexicon.get(w, 0) >= 1.5)
    neg_w = sum(1 for w in words if _VADER.lexicon.get(w, 0) <= -1.5)
    n = len(words) or 1
    mean_comp = sum(sent_scores) / len(sent_scores)
    if mean_comp >= 0.15:
        tone = "Positive"
    elif mean_comp <= -0.15:
        tone = "Negative"
    else:
        tone = "Mixed / neutral"
    return {
        "tone": tone,
        "compound": round(mean_comp, 3),             # mean sentence compound, -1..1
        "pos_share": round(whole["pos"], 3),
        "neg_share": round(whole["neg"], 3),
        "neu_share": round(whole["neu"], 3),
        "pos_words_pct": round(100 * pos_w / n, 1),
        "neg_words_pct": round(100 * neg_w / n, 1),
        "first_person_pct": round(100 * sum(w in _FIRST_PERSON for w in words) / n, 1),
        "lexical_diversity": round(len(set(words)) / n, 2),
        "n_sentences": len(sents),
    }


# ----------------------------------------------------- external-data (EmoSurv) model
def _emo_model():
    global _EMO_MODEL, _EMO_MODEL_TRIED
    if not _EMO_MODEL_TRIED:
        _EMO_MODEL_TRIED = True
        path = os.path.join(_HERE, "emotion_model.pkl")
        if os.path.exists(path):
            try:
                import joblib
                _EMO_MODEL = joblib.load(path)
            except Exception:
                _EMO_MODEL = None
    return _EMO_MODEL


def external_model(feats):
    """Happy-like vs sad-like typing pattern from the EmoSurv-trained model."""
    art = _emo_model()
    if art is None or not feats.get("behavioural_valid", 1):
        return None
    X = [[float(feats.get(f) or 0) for f in art["features"]]]
    p_sad = float(art["model"].predict_proba(X)[0][1])
    return {"p_sad_like": round(p_sad, 3), "p_happy_like": round(1 - p_sad, 3),
            "label": "sad-like" if p_sad >= 0.5 else "happy-like"}


# ------------------------------------------------------------------- the bundle
def analyse(feats, text, emotion):
    """Compute everything stored with a session (JSON-serialisable)."""
    return {
        "emotion": emotion,
        "text": text_emotion(text),
        "indices": bh.compute_indices(feats),
        "external": external_model(feats),
    }


def dumps(d):
    return json.dumps(d)


def rhythm_shift(feats, base_feats):
    """Compare this emotional passage with the SAME person's neutral baseline.
    Primary measure: rhythm variability (CV of the inter-key interval) — the one
    within-person effect that survived length-matching on EmoSurv. Pause/speed values
    are returned as descriptive context only (they are sensitive to passage length)."""
    if not feats.get("behavioural_valid", 1) or not base_feats.get("behavioural_valid", 1):
        return None
    cv, bcv = bh.rhythm_cv(feats), bh.rhythm_cv(base_feats)
    if bcv <= 0:
        return None
    n, bn = feats.get("n_keydown") or 0, base_feats.get("n_keydown") or 0
    ratio = n / bn if bn else None
    delta_pct = 100 * (cv - bcv) / bcv
    if delta_pct <= -10:
        reading = "more even than your baseline"
    elif delta_pct >= 10:
        reading = "less even than your baseline"
    else:
        reading = "about the same as your baseline"
    ratio_cv = cv / bcv
    if ratio_cv <= 0.90:
        state = "Engagement-like shift: steadier rhythm than your baseline"
    elif ratio_cv >= 1.10:
        state = "Less steady than your baseline"
    else:
        state = "No clear shift from your baseline"
    return {
        "cv": round(cv, 2), "base_cv": round(bcv, 2), "delta_pct": round(delta_pct),
        "reading": reading, "state": state, "length_ratio": round(ratio, 2) if ratio else None,
        "length_matched": bool(ratio and 0.6 < ratio < 1.67),
        "context": [
            {"label": "Typing speed (chars/s)", "now": feats.get("chars_per_sec"), "base": base_feats.get("chars_per_sec")},
            {"label": "Long pauses per 100 keys", "now": feats.get("n_long_pause_per_100"), "base": base_feats.get("n_long_pause_per_100")},
            {"label": "Time paused", "now": round(100 * (feats.get("pause_time_ratio") or 0)), "base": round(100 * (base_feats.get("pause_time_ratio") or 0)), "unit": "%"},
        ],
    }


def replication_test(sessions):
    """H1 on OUR data: is CV lower in emotional writing than in each person's own
    baseline? Wilcoxon signed-rank on (emotional CV - baseline CV), reported on all pairs
    and on length-matched pairs. Hypothesis was derived from EmoSurv, so this is a
    prospective replication."""
    from scipy import stats
    by_id = {s["id"]: s for s in sessions}
    deltas, matched = [], []
    for s in sessions:
        b = by_id.get(s.get("baseline_id"))
        if not b or s.get("emotion") not in ("happy", "sad"):
            continue
        sh = rhythm_shift(s["features"], b["features"])
        if not sh:
            continue
        d = sh["cv"] - sh["base_cv"]
        deltas.append(d)
        if sh["length_matched"]:
            matched.append(d)

    def summ(ds):
        if len(ds) < MIN_N:
            return {"n": len(ds), "ready": False}
        nz = [x for x in ds if x != 0]
        p = stats.wilcoxon(ds).pvalue if len(nz) >= 5 else None
        ds_sorted = sorted(ds)
        return {"n": len(ds), "ready": True, "median": round(ds_sorted[len(ds) // 2], 3),
                "share_lower": round(sum(x < 0 for x in ds) / len(ds), 2),
                "p": round(float(p), 4) if p is not None else None}
    return {"all": summ(deltas), "matched": summ(matched), "n_pairs": len(deltas)}


def _level(score):
    return 1 + min(4, int(score // 20))     # 0-100 -> 1..5


def compare_self_report(indices, s):
    """Self-reported focus / stress next to the matching typing-based index.
    Descriptive only — agreement on one session proves nothing."""
    if not indices:
        return []
    out = []
    if s.get("self_focus"):
        out.append({"label": "Focus", "self": s["self_focus"],
                    "index_name": "Focus index", "index": indices["focus"],
                    "index_level": _level(indices["focus"])})
    if s.get("self_stress"):
        out.append({"label": "Stress / anxiety", "self": s["self_stress"],
                    "index_name": "Mind-space load", "index": indices["mind_space"],
                    "index_level": _level(indices["mind_space"])})
    for r in out:
        d = abs(r["self"] - r["index_level"])
        r["agreement"] = ("Close match" if d <= 1 else
                          "Partly different" if d == 2 else "Quite different")
    return out


# ------------------------------------------------- live validation (admin page)
MIN_N = 8       # fewest sessions before a correlation is shown at all


def _spearman(xs, ys):
    from scipy import stats
    if len(xs) < MIN_N or len(set(xs)) < 2 or len(set(ys)) < 2:
        return None
    r, p = stats.spearmanr(xs, ys)
    return {"n": len(xs), "rho": round(float(r), 2), "p": round(float(p), 3)}


def live_validation(sessions):
    """Aggregate the live (emotion-writing) sessions: do the formulas and the
    external model line up with what people reported / the condition they chose?
    Returns only what the data supports; sections stay None until n is large enough."""
    rows = [s for s in sessions
            if s.get("affect") and s["affect"].get("indices")
            and s.get("emotion") in ("happy", "sad")]
    out = {"n": len(rows), "min_n": MIN_N, "pairs": [], "by_emotion": [],
           "external": None, "text": None, "replication": replication_test(sessions)}
    if not rows:
        return out
    pair_defs = [("self_focus", "focus", "Self-rated focus ↔ Focus index"),
                 ("self_stress", "mind_space", "Self-rated stress ↔ Mind-space load"),
                 ("self_stress", "hesitation", "Self-rated stress ↔ Hesitation"),
                 ("self_mood", "focus", "Self-rated mood ↔ Focus index")]
    for col, idx, label in pair_defs:
        pts = [(s[col], s["affect"]["indices"][idx]) for s in rows if s.get(col)]
        res = _spearman([a for a, _ in pts], [b for _, b in pts])
        out["pairs"].append({"label": label, "n": len(pts), "result": res})
    for emo in ("happy", "sad"):
        g = [s for s in rows if s["emotion"] == emo]
        if not g:
            continue
        def med(vals):
            vals = sorted(v for v in vals if v is not None)
            return round(vals[len(vals) // 2], 1) if vals else None
        out["by_emotion"].append({
            "emotion": emo.capitalize(), "n": len(g),
            "mood": med([s.get("self_mood") for s in g]),
            "focus_self": med([s.get("self_focus") for s in g]),
            "stress_self": med([s.get("self_stress") for s in g]),
            "focus_idx": med([s["affect"]["indices"]["focus"] for s in g]),
            "mind_idx": med([s["affect"]["indices"]["mind_space"] for s in g]),
            "sentiment": med([(s["affect"].get("text") or {}).get("compound") for s in g]),
        })
    ext = [s for s in rows if s["affect"].get("external")]
    if ext:
        hit = sum(1 for s in ext
                  if (s["affect"]["external"]["label"] == "sad-like") == (s["emotion"] == "sad"))
        out["external"] = {"n": len(ext), "hits": hit,
                           "accuracy": round(hit / len(ext), 2)}
    txt = [s for s in rows if s["affect"].get("text")]
    if txt:
        hit = sum(1 for s in txt
                  if (s["affect"]["text"]["compound"] < 0) == (s["emotion"] == "sad"))
        out["text"] = {"n": len(txt), "hits": hit, "accuracy": round(hit / len(txt), 2)}
    return out


def load_validation_json():
    try:
        with open(os.path.join(_HERE, "emotion_validation.json"), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None
