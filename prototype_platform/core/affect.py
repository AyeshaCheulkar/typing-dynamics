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

from core import behaviour as bh
from core import questionnaire as qn

from core import paths

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
        path = paths.EMOTION_MODEL
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
    deltas, matched, relive, skill = [], [], [], {}
    n_interrupted = 0
    for s in sessions:
        b = by_id.get(s.get("baseline_id"))
        if not b or s.get("emotion") not in ("happy", "sad"):
            continue
        if s.get("interrupted") == 1:          # quality control: drop interrupted sessions
            n_interrupted += 1
            continue
        sh = rhythm_shift(s["features"], b["features"])
        if not sh:
            continue
        d = sh["cv"] - sh["base_cv"]
        deltas.append(d)
        if s.get("self_relive"):
            relive.append((s["self_relive"], d))
        if s.get("typing_skill"):
            skill.setdefault(s["typing_skill"], []).append(d)
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
    names = {"touch": "Touch typist", "some": "Some looking at keys", "hunt": "Hunt-and-peck"}
    by_skill = [{"label": names[k], "n": len(v), "median": round(sorted(v)[len(v) // 2], 3)}
                for k, v in skill.items() if k in names]
    return {"all": summ(deltas), "matched": summ(matched), "n_pairs": len(deltas),
            "n_interrupted": n_interrupted, "by_skill": by_skill,
            "relive": _spearman([a for a, _ in relive], [b for _, b in relive])
                      if relive else None,
            "n_relive": len(relive)}


# ------------------------------------------------- live validation (admin page)
MIN_N = 8       # fewest sessions before a correlation is shown at all


def _spearman(xs, ys):
    from scipy import stats
    if len(xs) < MIN_N or len(set(xs)) < 2 or len(set(ys)) < 2:
        return None
    r, p = stats.spearmanr(xs, ys)
    return {"n": len(xs), "rho": round(float(r), 2), "p": round(float(p), 3)}


def _adjusted_spearman(rows):
    """Spearman between x and y after removing differences explained by typing style and
    keyboard (both are regressed out of x and y; Spearman is taken on the residuals).
    rows = [(x, y, typing_skill, keyboard)]. p is approximate (residualising uses up
    degrees of freedom), so it is reported as indicative only."""
    import numpy as np
    from scipy import stats
    rows = [r for r in rows if r[2] and r[3]]
    if len(rows) < MIN_N:
        return None
    cols = []
    for k in (2, 3):
        levels = sorted({r[k] for r in rows})
        for lv in levels[1:]:
            cols.append([1.0 if r[k] == lv else 0.0 for r in rows])
    if not cols:
        return None
    D = np.column_stack([np.ones(len(rows))] + cols)
    if len(rows) <= D.shape[1] + 2:
        return None
    out = []
    for j in (0, 1):
        v = np.array([float(r[j]) for r in rows])
        beta, *_ = np.linalg.lstsq(D, v, rcond=None)
        out.append(v - D @ beta)
    if np.std(out[0]) == 0 or np.std(out[1]) == 0:
        return None
    r, p = stats.spearmanr(out[0], out[1])
    return {"n": len(rows), "rho": round(float(r), 2), "p": round(float(p), 3)}


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
    # questionnaire scores (1-5) and fresh typing indices for every row (older sessions lack "processing")
    for s in rows:
        for k in qn.STATE_ORDER:
            s["q_" + k] = qn.score(s, k)
        s["_idx"] = bh.compute_indices(s["features"]) or s["affect"]["indices"]
    pair_defs = [("q_load", "mind_space", "Cognitive load (NASA-TLX) ↔ Mind-space load"),
                 ("q_load", "hesitation", "Cognitive load (NASA-TLX) ↔ Hesitation"),
                 ("q_flow", "focus", "Flow (Flow Short Scale) ↔ Focus index (expect positive)"),
                 ("q_flow", "irregularity", "Flow (Flow Short Scale) ↔ Rhythm irregularity (expect negative)"),
                 ("q_intensity", "processing", "Emotional intensity (SAM) ↔ Emotional-processing load"),
                 ("q_intensity", "correction", "Emotional intensity (SAM) ↔ Self-correction"),
                 ("self_mood", "focus", "Valence (SAM) ↔ Focus index"),
                 ("tlx_frustration", "mind_space", "Frustration (NASA-TLX) ↔ Mind-space load")]
    for col, idx, label in pair_defs:
        pts = [(s[col], s["_idx"][idx]) for s in rows if s.get(col)]
        res = _spearman([a for a, _ in pts], [b for _, b in pts])
        adj = _adjusted_spearman([(s[col], s["_idx"][idx],
                                   s.get("typing_skill"), s.get("keyboard"))
                                  for s in rows if s.get(col)])
        out["pairs"].append({"label": label, "n": len(pts), "result": res, "adjusted": adj})
    skill_names = {"touch": "Touch typist", "some": "Mixed", "hunt": "Hunt-and-peck"}
    kb_names = {"laptop": "Laptop", "external": "External"}
    out["composition"] = {
        "skill": [{"label": skill_names[k], "n": sum(1 for s in rows if s.get("typing_skill") == k)}
                  for k in skill_names],
        "keyboard": [{"label": kb_names[k], "n": sum(1 for s in rows if s.get("keyboard") == k)}
                     for k in kb_names]}
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
            "intensity_self": med([s.get("q_intensity") for s in g]),
            "load_self": med([s.get("q_load") for s in g]),
            "flow_self": med([s.get("q_flow") for s in g]),
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
        with open(paths.EMOTION_VALIDATION, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def load_literature_validation():
    try:
        with open(paths.LITERATURE_VALIDATION, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None
