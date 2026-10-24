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


_NEGATORS = {"not", "no", "never", "hardly", "without", "cannot"}
_MIN_EMO_WORDS = 3


def emotion_words(text, emotion=None):
    """The words that carry feeling, found with the VADER word list (|score| >= 1.5).
    A feeling word with not/never/n't in the three words before it is counted the other way round.
    Returns the passage cut into segments (for highlighting), the top words and a verdict."""
    if _VADER is None or not text or len(text.split()) < 8:
        return None
    segs, counts, pos_n, neg_n, last, recent = [], {"pos": {}, "neg": {}}, 0, 0, 0, []
    for m in _WORD_RE.finditer(text):
        if m.start() > last:
            segs.append({"t": text[last:m.start()], "c": ""})
        last = m.end()
        w = m.group().lower()
        v = _VADER.lexicon.get(w, 0)
        cls = ""
        if abs(v) >= 1.5:
            if any(r in _NEGATORS or r.endswith("n't") for r in recent[-3:]):
                v = -v
            cls = "pos" if v > 0 else "neg"
            counts[cls][w] = counts[cls].get(w, 0) + 1
            pos_n, neg_n = pos_n + (cls == "pos"), neg_n + (cls == "neg")
        segs.append({"t": m.group(), "c": cls})
        recent.append(w)
    if last < len(text):
        segs.append({"t": text[last:], "c": ""})
    top = lambda d: sorted(d.items(), key=lambda kv: -kv[1])[:5]
    total = pos_n + neg_n
    if total < _MIN_EMO_WORDS:
        lean, verdict = "few", "Only %d feeling word%s found, too few to say what the words show." % (total, "" if total == 1 else "s")
    else:
        share = pos_n / total
        lean = "pos" if share >= 0.65 else "neg" if share <= 0.35 else "mixed"
        verdict = {"pos": "Most of your feeling words are positive (%d of %d)." % (pos_n, total),
                   "neg": "Most of your feeling words are negative (%d of %d)." % (neg_n, total),
                   "mixed": "Your feeling words are mixed: %d positive and %d negative." % (pos_n, neg_n)}[lean]
        want = {"happy": "pos", "sad": "neg"}.get(emotion)
        if want:
            verdict += (" This supports the %s moment you chose." % emotion if lean == want else
                        " This does not clearly match the %s moment you chose." % emotion)
    return {"segments": segs, "pos": top(counts["pos"]), "neg": top(counts["neg"]),
            "n_pos": pos_n, "n_neg": neg_n, "lean": lean, "verdict": verdict}


_NRC = None
_NRC_TRIED = False
_NRC_EMOTIONS = ["joy", "trust", "anticipation", "surprise", "sadness", "fear", "anger", "disgust"]


def _nrc():
    """NRC Emotion Lexicon (Mohammad & Turney, 2013): word -> list of emotions. None if the file is absent."""
    global _NRC, _NRC_TRIED
    if not _NRC_TRIED:
        _NRC_TRIED = True
        try:
            with open(paths.NRC_LEXICON, "r", encoding="utf-8") as fh:
                _NRC = json.load(fh)
        except (OSError, ValueError):
            _NRC = None
    return _NRC


def _nrc_forms(w):
    """The word, then simple endings removed (loved -> love, tears -> tear)."""
    yield w
    for suf, add in (("ing", ""), ("ing", "e"), ("ed", ""), ("ed", "e"), ("ly", ""), ("es", ""), ("s", "")):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            yield w[:-len(suf)] + add


def nrc_emotions(text):
    """Count the words tied to eight emotions in the NRC lexicon. None if the lexicon or the text is missing.
    One word can count for several emotions. Negation is not handled (the lexicon has no notion of it)."""
    lex = _nrc()
    if not lex or not text or len(text.split()) < 8:
        return None
    counts = {e: 0 for e in _NRC_EMOTIONS}
    words = {e: {} for e in _NRC_EMOTIONS}
    hit = 0
    for m in _WORD_RE.finditer(text):
        w = m.group().lower()
        emos = next((lex[f] for f in _nrc_forms(w) if f in lex), None)
        if not emos:
            continue
        hit += 1
        for e in emos:
            counts[e] += 1
            words[e][w] = words[e].get(w, 0) + 1
    rows = [{"emotion": e, "n": counts[e], "words": sorted(words[e], key=lambda k: -words[e][k])[:4]}
            for e in _NRC_EMOTIONS if counts[e]]
    rows.sort(key=lambda r: -r["n"])
    top = rows[0]["n"] if rows else 1
    for r in rows:
        r["width"] = round(100 * r["n"] / top)
    if hit < _MIN_EMO_WORDS:
        text_out = "Only %d word%s from the NRC list found, too few to say which feelings stand out." % (hit, "" if hit == 1 else "s")
    else:
        lead = [r for r in rows if r["n"] >= max(2, 0.6 * rows[0]["n"])][:2]
        text_out = "Feelings that stand out: %s." % " and ".join("%s (%d words)" % (r["emotion"], r["n"]) for r in lead)
    return {"rows": rows, "hit": hit, "text": text_out, "lead": rows[0]["emotion"] if hit >= _MIN_EMO_WORDS and rows else None}


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
           "external": None, "text": None}
    if not rows:
        return out
    # questionnaire scores (1-5) and fresh typing indices for every row (older sessions lack "processing")
    for s in rows:
        for k in qn.STATE_ORDER:
            s["q_" + k] = qn.score(s, k)
        s["_idx"] = bh.compute_indices(s["features"]) or s["affect"]["indices"]
    # (questionnaire score, typing index, label, expected sign, hypothesis key)
    pair_defs = [("q_load", "mind_space", "Cognitive load (NASA-TLX) ↔ Mind-space load", +1, "load"),
                 ("q_flow", "focus", "Flow (Flow Short Scale) ↔ Focus index", +1, "flow"),
                 ("q_intensity", "processing", "Emotional intensity (SAM) ↔ Emotional-processing load", +1, "intensity"),
                 ("q_load", "hesitation", "Cognitive load (NASA-TLX) ↔ Hesitation", +1, None),
                 ("q_flow", "irregularity", "Flow (Flow Short Scale) ↔ Rhythm irregularity", -1, None),
                 ("q_intensity", "correction", "Emotional intensity (SAM) ↔ Self-correction", +1, None),
                 ("self_mood", "focus", "Valence (SAM) ↔ Focus index", None, None),
                 ("tlx_frustration", "mind_space", "Frustration (NASA-TLX) ↔ Mind-space load", +1, None)]
    for col, idx, label, expected, hyp in pair_defs:
        pts = [(s[col], s["_idx"][idx]) for s in rows if s.get(col)]
        res = _spearman([a for a, _ in pts], [b for _, b in pts])
        adj = _adjusted_spearman([(s[col], s["_idx"][idx],
                                   s.get("typing_skill"), s.get("keyboard"))
                                  for s in rows if s.get(col)])
        out["pairs"].append({"label": label, "n": len(pts), "result": res, "adjusted": adj,
                             "expected": expected, "hypothesis": hyp})
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
