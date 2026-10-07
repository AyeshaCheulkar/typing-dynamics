"""
plain_report.py — turns the behaviour measurements into plain-language text for the
participant report. No formulas, no 0-100 scores: each card states what was measured, how
it compares with other writers in the pilot sample (lower / typical / higher), what it can
mean, and how solid the evidence is.

Evidence labels (kept honest):
  measured  - an exact count/rate taken from the keystrokes.
  supported - backed by a validated finding (rhythm steadiness is higher while writing under
              an emotion than in neutral writing, EmoSurv, Holm-corrected).
  exploratory - a reasonable reading that has not been checked against focus or stress
              answers yet.
"""

import behaviour as bh


def _pct(context, feature):
    for c in context:
        if c["feature"] == feature:
            return c["percentile"]
    return None


def _band(pct):
    if pct is None:
        return "typical"
    return "lower" if pct < 34 else "higher" if pct > 66 else "typical"


_WORD = {"lower": "lower than most writers in our sample",
         "typical": "about typical for our sample",
         "higher": "higher than most writers in our sample"}


def _times(n):
    return "once" if n == 1 else "%d times" % n


def cards(feats, context, indices):
    n_kd = float(feats.get("n_keydown") or 0)
    long_n = int(round(float(feats.get("n_long_pause_per_100") or 0) * n_kd / 100))
    revs = int(feats.get("n_revision_bursts") or 0)
    cps = float(feats.get("chars_per_sec") or 0)

    irr = indices["irregularity"] if indices else None
    steady_band = None if irr is None else ("even" if irr < 34 else "uneven" if irr > 66 else "typical")
    steady_text = {"even": "Your typing rhythm was steady and even.",
                   "uneven": "Your typing rhythm was uneven, with bursts and stops.",
                   "typical": "Your typing rhythm was about as even as most writers' in our sample.",
                   None: "There were too few keystrokes to judge your rhythm."}[steady_band]
    steady_chip = {"even": "More even than most", "uneven": "Less even than most",
                   "typical": "Typical", None: "Not enough data"}[steady_band]

    p_pause = _band(_pct(context, "n_long_pause_per_100"))
    p_pace = _band(_pct(context, "chars_per_sec"))
    p_rev = _band(_pct(context, "revisions_per_100"))

    return [
        {"title": "Pace", "evidence": "measured",
         "statement": "You typed about %.1f characters per second." % cps,
         "chip": _WORD[p_pace].capitalize(), "pct": _pct(context, "chars_per_sec"),
         "meaning": "Speed differs a lot between people and keyboards, so it says more about your typing habits than your mood."},
        {"title": "Stopping to think", "evidence": "measured",
         "statement": "You paused for two seconds or longer %s." % _times(long_n),
         "chip": _WORD[p_pause].capitalize(), "pct": _pct(context, "n_long_pause_per_100"),
         "meaning": "Longer pauses often happen when we choose words or recall details. They are neither good nor bad."},
        {"title": "Steadiness", "evidence": "measured",
         "statement": steady_text, "chip": steady_chip, "pct": None,
         "meaning": "Backed by public typing data: people typed more evenly while writing under an emotion than in neutral "
                    "writing, so a steady rhythm often goes with being absorbed in what you write."},
        {"title": "Going back", "evidence": "measured",
         "statement": "You went back to correct or reword %s." % _times(revs),
         "chip": _WORD[p_rev].capitalize(), "pct": _pct(context, "revisions_per_100"),
         "meaning": "Going back to fix or rephrase is a normal part of writing."},
    ]


def overview(feats, context, indices):
    p_pause = _band(_pct(context, "n_long_pause_per_100"))
    irr = indices["irregularity"] if indices else None
    steady = irr is not None and irr < 34
    uneven = irr is not None and irr > 66
    if steady and p_pause != "higher":
        line = "Overall, your writing flowed steadily with few long stops."
    elif uneven and p_pause == "higher":
        line = "Overall, your writing had a stop-and-start feel, with several long pauses."
    elif p_pause == "higher":
        line = "Overall, your writing had more long pauses than most, with an otherwise typical rhythm."
    elif uneven:
        line = "Overall, your typing rhythm was a little uneven, with a typical number of pauses."
    else:
        line = "Overall, your typing pattern was fairly typical for our sample."
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


def compare(indices, s):
    """Your own answers next to what the typing looked like. Plain, cautious."""
    if not indices:
        return []
    rows = []
    sf, ss = s.get("self_focus"), s.get("self_stress")
    focus_idx = indices["focus"]
    if sf:
        typing = "steady" if focus_idx >= 60 else "stop-and-start" if focus_idx <= 40 else "mixed"
        said = "focused" if sf >= 4 else "distracted" if sf <= 2 else "somewhat focused"
        fit = (sf >= 4 and typing == "steady") or (sf <= 2 and typing == "stop-and-start") or \
              (2 < sf < 4 and typing == "mixed")
        rows.append({"topic": "Focus",
                     "said": "You said you felt %s (%d of 5)." % (said, sf),
                     "typing": "Your typing looked %s." % typing,
                     "verdict": "These fit together." if fit else
                                "These differ, which is common: pauses are not the same as losing focus."})
    tension_idx = indices["mind_space"]
    if ss:
        typing = "strained" if tension_idx >= 60 else "relaxed" if tension_idx <= 40 else "in between"
        said = "tense" if ss >= 4 else "not tense" if ss <= 2 else "a little tense"
        fit = (ss >= 4 and typing == "strained") or (ss <= 2 and typing == "relaxed") or \
              (2 < ss < 4 and typing == "in between")
        rows.append({"topic": "Tension",
                     "said": "You said you felt %s (%d of 5)." % (said, ss),
                     "typing": "Your typing pattern looked %s." % typing,
                     "verdict": "These fit together." if fit else
                                "These differ. Typing patterns are only a rough guide to how tense someone feels."})
    return rows


EVIDENCE = {
    "solid": ["The counts above come straight from your keystrokes, so they are exact.",
              "In public typing data, a steadier rhythm went with writing under an emotion, compared with neutral writing."],
    "exploratory": ["Reading your typing as focus or tension is still being checked against participants' own answers, "
                    "so treat it as a gentle hint."],
    "cannot": ["Typing alone cannot tell a happy memory from a sad one.",
               "None of this is a diagnosis or a measure of mental health."],
}
