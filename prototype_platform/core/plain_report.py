"""
plain_report.py — turns measurements and questionnaire answers into the plain-language text of
the participant report: the one-line overview, tone of the words, behavioural state (what the
participant reported next to what their typing suggests), practical insight and use cases.
No formulas or raw scores in the main text; the scoring lives in questionnaire.py / behaviour.py.
"""

from core import questionnaire as qn


def overview(feats, context, indices):
    """One-line headline, consistent with the Focus reading (same index, same cut-offs)."""
    if not indices:
        return "There were too few keystrokes to describe your typing pattern."
    f = indices["focus"]
    if f >= 60:
        line = "Overall, your writing flowed steadily with few long stops."
    elif f <= 40:
        line = "Overall, your writing had a stop-and-start feel, with several long pauses."
    else:
        line = "Overall, your writing had some steady stretches and some stops, which is typical."
    return line + " This describes how you typed in this one session."


def tone(text_aff, emotion):
    if not text_aff:
        return None
    t = text_aff["tone"]
    pos, neg = text_aff["pos_words_pct"], text_aff["neg_words_pct"]
    if t == "Positive":
        read = "Your passage reads as mostly positive"
    elif t == "Negative":
        read = "Your passage reads as mostly negative"
    else:
        read = "Your passage reads as mixed or neutral in tone"
    fits = None
    if emotion == "happy":
        fits = ("This matches the happy moment you chose." if t == "Positive" else
                "You chose a happy moment, though the wording reads %s. Memories are often more than one feeling."
                % ("mixed" if t != "Negative" else "somber"))
    elif emotion == "sad":
        fits = ("This matches the sad moment you chose." if t == "Negative" else
                "You chose a sad moment, though the wording reads %s. Hard memories often hold warmth too."
                % ("mixed" if t != "Positive" else "positive"))
    return {"headline": read + " (about %s%% of your words were positive and %s%% negative)." % (pos, neg),
            "fits": fits, "pos": pos, "neg": neg}


EVIDENCE = {
    "solid": ["The counts in section 1 come straight from your keystrokes, so they are exact.",
              "Your answers come from short versions of published questionnaires (SAM, NASA-TLX, Flow Short Scale)."],
    "exploratory": ["Reading cognitive load, flow and emotional intensity from typing is being checked in our study "
                    "by correlating typing with these answers. Treat the typing side as a hint, not a measurement."],
    "cannot": ["Typing alone cannot tell a happy memory from a sad one.",
               "None of this is a diagnosis or a measure of mental health."],
}


_LVL_WORD = {"low": "Low", "mid": "Moderate", "high": "High"}
_LVL_IDX = {"low": 0, "mid": 1, "high": 2}

# what each typing reading is built from: (index key, plain label, phrase when high / low)
_DRIVERS = {
    "load": [("hesitation", "Hesitation", "more and longer pauses than most", "fewer and shorter pauses than most"),
             ("correction", "Self-correction", "more deleting and rewording than most", "less deleting and rewording than most"),
             ("irregularity", "Rhythm", "a less even rhythm than most", "a more even rhythm than most")],
    "intensity": [("hesitation", "Pausing", "more and longer pauses than most", "fewer and shorter pauses than most"),
                  ("correction", "Deleting", "more deleting and rewording than most", "less deleting and rewording than most")],
    "flow": [("focus", "Continuity", "steady, continuous typing", "a stop-and-start pattern")],
}


def _agree(a, b):
    d = abs(_LVL_IDX[a] - _LVL_IDX[b])
    return ("match", "Match") if d == 0 else ("partly", "Close") if d == 1 else ("differs", "Different")


def states(row, indices):
    """Behavioural state: for each of emotional intensity / cognitive load / flow, what the
    participant reported (published questionnaire) next to what their typing indicates."""
    mine = qn.self_states(row)
    out = []
    for k in qn.STATE_ORDER:
        meta = qn.STATES[k]
        s = mine.get(k)
        typ = indices.get(meta["typing"]) if indices else None
        item = {"key": k, "label": meta["label"], "source": meta["source"], "formula": meta["formula"],
                "typing_label": meta["typing_label"], "self": None, "typing": None, "agree": None,
                "drivers": [], "sentence": None}
        if s:
            lv = qn.level(s["pct"])
            item["self"] = {"score": s["score"], "pct": s["pct"], "level": _LVL_WORD[lv],
                            "lv": lv, "text": meta[lv]}
        if typ is not None:
            lv = qn.level(typ)
            item["typing"] = {"pct": round(typ), "level": _LVL_WORD[lv], "lv": lv}
            if k == "flow":
                item["typing"]["level"] = {"low": "Stop-and-start", "mid": "Mixed", "high": "Steady"}[lv]
            for key, lab, hi, lo in _DRIVERS[k]:
                v = indices.get(key)
                if v is None:
                    continue
                t = qn.level(v)
                if k == "flow":
                    phrase = hi if t == "high" else lo if t == "low" else "a mix of steady stretches and stops"
                else:
                    phrase = hi if t == "high" else lo if t == "low" else "about typical"
                item["drivers"].append({"label": lab, "text": phrase, "lv": t})
        if item["self"] and item["typing"]:
            cls, word = _agree(item["self"]["lv"], item["typing"]["lv"])
            item["agree"] = {"cls": cls, "word": word}
            item["sentence"] = {
                "match": "Your answers and your typing point the same way.",
                "partly": "Your answers and your typing are close but not identical.",
                "differs": "Your answers and your typing differ. That is common, and it is one of the things this study measures.",
            }[cls]
        out.append(item)
    return out


def insight(sts, emotion):
    """Plain read-across of the three states: what the combination can mean."""
    by = {s["key"]: s for s in sts}
    inten, load = by["intensity"], by["load"]
    lines = []
    if inten["self"] and load["self"]:
        hi_i, hi_l = inten["self"]["lv"] == "high", load["self"]["lv"] == "high"
        if hi_i and hi_l:
            lines.append("You described a strong emotional experience that also took real mental effort. Writing about an "
                         "emotional event often feels like this while the memory is being put into words.")
        elif hi_i:
            lines.append("You felt the moment strongly, but the writing itself did not feel heavy.")
        elif hi_l:
            lines.append("The writing took a lot of mental effort without a very strong emotional pull. The effort may come from "
                         "finding words more than from the feeling.")
        else:
            lines.append("This was a light session: neither the emotion nor the effort ran high.")
    if inten["typing"] and inten["typing"]["lv"] == "high":
        lines.append("Your typing combined pausing and deleting more than most writers do. This is the pattern we are testing as a "
                     "sign of emotional processing; one session cannot confirm it.")
    flow = by["flow"]
    if flow["self"] and flow["self"]["lv"] == "high":
        lines.append("You reported a strong sense of flow while writing.")
    return lines


USES = [
    {"title": "Emotional reflection",
     "text": "Writing about emotional events is a long-used therapeutic technique (Pennebaker & Beall, 1986). "
             "Typing hesitation and self-correction could one day show how someone is working through a memory, "
             "without asking them to rate it."},
    {"title": "Fatigue and strain monitoring",
     "text": "Typing rhythm, pauses and corrections change when people are tired or under strain (Epp et al., 2011; "
             "Vizer et al., 2009). Short reflective writing at work or in study could flag hidden fatigue early."},
    {"title": "Writing support",
     "text": "The same measures show when a writer is stuck or fluent, so tools can offer help at the right time."},
]
