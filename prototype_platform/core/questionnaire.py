"""
questionnaire.py — the post-writing questions, taken from published instruments, and the
formulas that turn the answers into three self-reported states. These are the GROUND-TRUTH
labels the keystroke readings are checked against (correlation analysis on the admin page).

All items use a 1-5 response scale (the published scales use 7-, 9- or 21-point versions;
the shortening is ours and is stated wherever the scores are shown).

  Emotional intensity   Self-Assessment Manikin (Bradley & Lang, 1994): valence + arousal,
                        plus one item on how strongly the moment was felt while writing.
      intensity_score = mean(felt, arousal)                         (1-5)
      valence is kept separate (pleasant <-> unpleasant); it is not intensity.

  Cognitive load        Raw NASA-TLX (Hart, 2006; Hart & Staveland, 1988), the three
                        subscales most tied to thinking effort.
      load_score = mean(mental demand, effort, frustration)         (1-5)

  Flow state            Flow Short Scale (Rheinberg, Vollmeyer & Engeser, 2003), four items:
                        fluency (smooth flow), concentration, absorption, time distortion.
      flow_score = mean(fluent, concentrate, absorbed, time)        (1-5)

Typing-side counterparts (behaviour.py): cognitive load <- mind-space index, flow <- focus
index, emotional intensity <- emotional-processing index.
"""

# key (as sent by the browser) -> database column
ITEM_COLUMNS = {
    "felt": "self_relive", "valence": "self_mood", "arousal": "self_arousal",
    "tlx_mental": "tlx_mental", "tlx_effort": "tlx_effort", "tlx_frustration": "tlx_frustration",
    "flow_fluent": "flow_fluent", "flow_concentrate": "flow_concentrate",
    "flow_absorbed": "flow_absorbed", "flow_time": "flow_time",
}

STATES = {
    "intensity": {"label": "Emotional intensity", "items": ["self_relive", "self_arousal"],
                  "typing": "processing", "typing_label": "Emotional-processing load",
                  "source": "Self-Assessment Manikin (Bradley & Lang, 1994)",
                  "formula": "mean(felt strongly, arousal)",
                  "low": "a mild emotional experience", "mid": "a moderate emotional experience",
                  "high": "a strong emotional experience"},
    "load": {"label": "Cognitive load",
             "items": ["tlx_mental", "tlx_effort", "tlx_frustration"],
             "typing": "mind_space", "typing_label": "Mind-space load",
             "source": "Raw NASA-TLX (Hart, 2006)",
             "formula": "mean(mental demand, effort, frustration)",
             "low": "light mental effort", "mid": "moderate mental effort",
             "high": "heavy mental effort"},
    "flow": {"label": "Flow state",
             "items": ["flow_fluent", "flow_concentrate", "flow_absorbed", "flow_time"],
             "typing": "focus", "typing_label": "Typing flow",
             "source": "Flow Short Scale (Rheinberg et al., 2003)",
             "formula": "mean(fluent, concentrated, absorbed, lost track of time)",
             "low": "little sense of flow", "mid": "some sense of flow",
             "high": "a strong sense of flow"},
}
STATE_ORDER = ["intensity", "load", "flow"]


def score(row, key):
    """Mean of the answered items for one state, 1-5 (None if none were answered)."""
    vals = [row.get(c) for c in STATES[key]["items"] if row.get(c)]
    return round(sum(vals) / len(vals), 2) if vals else None


def to_100(s):
    """Map a 1-5 score onto 0-100 so it can sit next to a typing index."""
    return None if s is None else round((s - 1) / 4 * 100, 1)


def level(score100):
    """low / mid / high on a 0-100 scale (same cut-offs as the typing indices)."""
    return "low" if score100 < 34 else "high" if score100 > 66 else "mid"


def self_states(row):
    """{state: {score (1-5), pct (0-100)}} for every state that was answered."""
    out = {}
    for k in STATE_ORDER:
        s = score(row, k)
        if s is not None:
            out[k] = {"score": s, "pct": to_100(s)}
    return out
