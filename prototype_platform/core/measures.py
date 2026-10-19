"""
measures.py — the content of the researcher's "Model research" page: every typing measure with its
formula, why it was chosen, the paper it comes from and how it held up; the datasets used and set aside;
and the models tried. Numbers that exist in a data file are read from it (literature_validation.json,
engagement_model.json), so this page cannot drift from the analysis. Verification flags:
  [V] abstract or page opened and checked   [S] record seen in search results only   [M] from memory

Plain text only; the participant report never shows any of this.
"""

from core import analysis as an

V, S, M = "verified", "search only", "from memory"

# Epp 2011 etc. are listed once in SOURCES and referenced by key from the measures.
SOURCES = {
    "epp": ("Epp, Lippold & Mandryk (2011). Identifying emotional states using keystroke dynamics. CHI.", V),
    "lee": ("Lee, Tsui & Hsiao (2015). The influence of emotion on keyboard typing: auditory stimuli. PLoS ONE 10(6):e0129056.", V),
    "kol": ("Kolakowska & Landowska (2021). Keystroke dynamics patterns while writing positive and negative opinions. Sensors 21(17):5963.", V),
    "zul": ("Zulueta et al. (2018). Predicting mood disturbance severity with mobile phone keystroke metadata. JMIR 20(7):e241.", V),
    "con19": ("Conijn, Roeser & van Zaanen (2019). Understanding the keystroke log: the effect of writing task on keystroke features. Reading & Writing.", V),
    "con21": ("Conijn, Dux Speltz & Chukharev-Hudilainen (2021). Automated extraction of revision events from keystroke data. Reading & Writing.", S),
    "tian": ("Tian, Kim & Crossley (2024). P-bursts as a fluency indicator. J. Writing Research 15(3).", V),
    "viz": ("Vizer, Zhou & Sears (2009). Automated stress detection using keystroke and linguistic features. Int. J. Human-Computer Studies 67(10).", S),
    "bix": ("Bixler & D'Mello (2013). Detecting boredom and engagement during writing with keystroke analysis. IUI.", S),
    "schutz": ("Schutz et al. (2026). Typing behavior in human-LLM interaction. arXiv:2606.28090 (preprint).", V),
    "lei": ("Leijten & Van Waes (2013). Keystroke logging in writing research: Inputlog. Written Communication 30(3).", S),
}

QUESTIONNAIRES = [
    ("Self-Assessment Manikin", "Bradley & Lang (1994)", "valence, arousal", M),
    ("Raw NASA-TLX", "Hart & Staveland (1988); Hart (2006)", "mental demand, effort, frustration", M),
    ("Flow Short Scale", "Rheinberg, Vollmeyer & Engeser (2003)", "fluency, concentration, absorption, time distortion", M),
]

# key, plain name, formula, why, sources, other evidence, verdict, verdict class
MEASURES = [
    dict(key="rhythm_cv", lit="rhythm_cv", name="Rhythm variability",
         formula="standard deviation of the gap between keystrokes / its mean",
         why="How even the typing pace is. The strongest, most consistent signal across the emotion studies.",
         sources=["epp", "kol"], extra="Freihaut stress study (53 paired): no difference between high and low stress. Largest weight in the engagement model.",
         verdict="Supported within a person", cls="supported"),
    dict(key="speed", lit="median_iki_ms", name="Key-to-key speed",
         formula="median gap between keystrokes (ms)",
         why="How fast the keys are hit. Mostly a trait of the typist, not of the task, so it is compared with writers on the same kind of keyboard.",
         sources=["con19", "zul", "epp"], extra="Inputlog corpus (491 typists): the median interval shifts by about 20 ms between laptop and desktop and about 60 ms between slow and fast typists. Freihaut stress study: keys were about 13 ms slower under high stress (p = 0.017, uncorrected).",
         verdict="A trait of the typist; used for comparison", cls="mixed"),
    dict(key="long_pause", lit="long_pause_100", name="Long thinking pauses",
         formula="gaps of 2 seconds or more, per 100 keystrokes",
         why="Stops long enough to plan the next idea; the standard boundary for a burst of production.",
         sources=["tian", "con19", "lei"], extra="Pause counts grow with passage length (EmoSurv's neutral passages were about 1.8x longer), so they are only fair when length is matched.",
         verdict="Not supported once length is controlled", cls="not-supported"),
    dict(key="pause_share", lit="pause_ratio", name="Share of time paused",
         formula="total time in gaps of 0.5 s or more / total writing time",
         why="How much of the session was spent stopped.",
         sources=["viz", "zul"], extra="Same pattern as long pauses: a length effect.",
         verdict="Not supported once length is controlled", cls="not-supported"),
    dict(key="longest", lit=None, name="Longest pause",
         formula="the largest gap between two keystrokes",
         why="A single long stop, often a break rather than thinking.",
         sources=["lei"], extra="Used inside the hesitation index only.", verdict="Descriptive", cls="mixed"),
    dict(key="delete", lit="backspace_ratio", name="Deleting",
         formula="backspace and delete presses / all keystrokes",
         why="How much the writer takes back what they typed.",
         sources=["zul", "viz", "kol"], extra="Kolakowska & Landowska: backspace and delete not significant between positive and negative writing.",
         verdict="Not supported", cls="not-supported"),
    dict(key="revise", lit="revision_100", name="Revising",
         formula="separate runs of deletions (one editing act each) per 100 keystrokes",
         why="How often the writer goes back to change something, rather than how many keys were deleted.",
         sources=["con19", "con21"], extra="Revision events can be detected more precisely (Conijn 2021); not yet implemented.",
         verdict="Not supported", cls="not-supported"),
    dict(key="pause_where", lit=None, name="Where pauses fall",
         formula="pauses of 0.5 s or more, split into inside a word, between words and between sentences",
         why="Pauses inside words reflect spelling and key search; pauses between words and sentences reflect planning (Conijn 2019).",
         sources=["con19"], extra="Shown in the participant report as a description. Not yet tested against a state label.",
         verdict="Descriptive", cls="mixed"),
    dict(key="focus", lit="focus", name="Focus index (composite)",
         formula="100 - mean(percentile of time paused, rhythm variability, long pauses)",
         why="One 0-100 reading of steady, continuous typing. Paired with the Flow Short Scale.",
         sources=["bix"], extra="Built from the same measures as above, so it adds no new information beyond them.",
         verdict="Proxy, being tested against Flow answers", cls="mixed"),
    dict(key="hesitation", lit="hesitation", name="Hesitation index (composite)",
         formula="mean(percentile of long pauses, longest pause, time paused)",
         why="More and longer thinking pauses.", sources=["tian", "viz"], extra="",
         verdict="Proxy", cls="mixed"),
    dict(key="mind", lit="mind_space", name="Mind-space load (composite)",
         formula="mean(hesitation, self-correction, rhythm irregularity)",
         why="Strain-like typing: pausing, correcting and an uneven rhythm together. Paired with NASA-TLX load.",
         sources=["viz", "schutz"], extra="Schutz et al. (preprint): harder tasks gave slower typing, more pauses and higher NASA-TLX.",
         verdict="Proxy, being tested against NASA-TLX", cls="mixed"),
]

DATASETS = [
    ("Pilot study (primary)", "25 sessions included, 22 valid, 17 people", "Keystrokes + self-rated writing effort (1-5)",
     "Writing-pattern comparisons; the effort model that was tested and set aside", "Own data, frozen"),
    ("EmoSurv", "190 usable free-text sessions, 81 people", "Induced emotion: neutral, anger, happy, calm, sad",
     "Engagement model; checks on every measure", "IEEE DataPort, doi:10.21227/eae6-pk42"),
    ("KeyRecs", "197 free-text sessions, 99 people", "None (demographics only)",
     "Reference ranges for free-text typing", "Zenodo 7886742, open access"),
    ("Inputlog copy-task corpus", "491 English sessions", "Typing speed, laptop or desktop, familiarity",
     "Why typing skill and keyboard matter; the laptop vs desktop shift in key speed", "Zenodo 5803401, CC-BY-4.0"),
    ("Freihaut & Goritz stress study", "53 people paired (lab); 924 people (online)", "High vs low stress condition, SAM, heart rate, skin conductance",
     "Stress check on rhythm and speed", "Zenodo 4445197 (feature tables only)"),
    ("Our live study (new)", "collecting", "Happy or sad moment, SAM, NASA-TLX, Flow Short Scale",
     "Tests the questionnaire-vs-typing hypotheses H2-H4", "Own data"),
]

REJECTED = [
    ("Inputlog EFL revision set", "PDF reports only, no timing data"),
    ("Audio-description scriptwriting set", "Phase durations only, no keystroke timing"),
    ("KEasyLogger", "Digraph timings only, 17 people, no state labels"),
    ("Kaggle writing-process data", "Needs a Kaggle login"),
    ("DUX emotion dataset", "Inside a 4.2 GB reproduction kit; labels not checked"),
    ("ScholaWrite", "No keystroke timing in the public release"),
    ("TypeState", "35 sessions from about 8 phones, copy task, no participant IDs"),
]

# tests of models that did not make it into the participant report
SET_ASIDE = [
    ("Writing effort from typing (pilot)", "22 sessions, held-out participants",
     "Random Forest and Linear Regression do not beat predicting the average; as a classifier AUC 0.13-0.32",
     "No signal. Predictions stayed near 2.6 because that is the best the data allows."),
    ("Stress from typing (Freihaut online)", "924 people, 10-fold by person",
     "AUC 0.51-0.58 for high vs low stress",
     "Typing carries almost no stress information in this task."),
    ("Happy vs sad from typing (EmoSurv)", "61 sessions, 52 people, leave-one-person-out",
     "Balanced accuracy 0.69, permutation p = 0.34",
     "Not distinguishable from chance."),
]


def measure_cards(lit):
    """MEASURES with the live EmoSurv numbers and resolved source citations attached."""
    rows = {r["feature"]: r for r in (lit["paired_per_person"] if lit else [])}
    out = []
    for m in MEASURES:
        c = dict(m)
        r = rows.get(m["lit"])
        c["emosurv"] = ("Emotional vs neutral writing, same person (n = %d): median change %+.3g, Holm-corrected p = %.3f."
                        % (r["n"], r["median_delta"], r["p_holm"])) if r else None
        c["cites"] = [SOURCES[k] for k in m["sources"]]
        out.append(c)
    return out


def engagement_card():
    """Weights and test results of the engagement model, from its own JSON."""
    m = an.engagement_model()
    w = sorted(zip(m["features"], m["coef"]), key=lambda t: -abs(t[1]))
    return {"source": m["source"], "n": m["n_sessions"], "people": m["n_participants"],
            "weights": [(m["labels"][f], round(c, 3)) for f, c in w], "cv": m["cv"], "intercept": round(m["intercept"], 3)}
