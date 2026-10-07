# Writing Analytics Platform — Prototype

A **separate** prototype that lets a participant write, captures keystroke
behaviour, and produces an explainable report with an **experimental** estimated
writing-effort score. It is fully isolated from the Stage-1 research
data-collection app.

## What it does NOT touch
- `../app.py`, `../db.py`, `../data.db`, `../templates/`, `../static/` — the live
  Stage-1 data-collection system. This prototype never imports or writes them.

## What it reuses (read-only)
- `../features.py` — the study's feature extraction.
- `../explain.py` + `../effort_model.pkl` — the trained model + SHAP (never
  retrained here).
- `../features.csv` — read only, for recommendation thresholds.

## Concept separation (important)
- **Measured behaviour** (green) — objective facts from keystrokes.
- **Self-rated writing effort** (blue) — the participant's own 1–5 rating.
- **Experimental estimated writing effort** (amber) — the model's output; shown
  only as experimental. Never described as mental effort, stress, intelligence, or
  any psychological state.

## Run locally
From the repository root:

```bash
# 1. (once) make sure the shared artifact exists
python train_model.py            # creates ../effort_model.pkl if missing

# 2. install prototype deps (ideally in the project venv)
pip install -r prototype_platform/requirements.txt

# 3. start the prototype (its own port 5001; Stage-1 uses 5000)
python prototype_platform/app.py
```

Then open:
- Participant page: http://127.0.0.1:5001/
- Researcher dashboard: http://127.0.0.1:5001/admin
  (local machine is allowed without a password; to require one, set
  `PROTO_ADMIN_PASSWORD`.)

Data is stored in `prototype_platform/prototype.db` (created on first run; separate
from `../data.db`).

## Files
- `app.py` — Flask routes (own port, own DB)
- `db.py` — prototype SQLite layer (`prototype.db`)
- `predict.py` — features + experimental estimate + SHAP (reuses shared code)
- `recommendations.py` — behaviour-tied suggestions (thresholds from `../features.csv`)
- `tasks.py` — writing prompts (copied, decoupled from Stage 1)
- `templates/` — `write.html`, `report.html`, `dashboard.html`, `history.html`
- `static/` — `capture.js`, `style.css`, result images


## Emotion-writing extension (happy / sad moment)
Participants now choose to write about **a happy or a sad moment**, then rate
effort, mood, focus and stress. The report adds an *Emotion & mind-space* section:
- **Text emotion** — VADER sentiment + first-person word rate (`affect.py`).
- **Behavioural indices** — focus, hesitation, self-correction, rhythm irregularity,
  mind-space load; transparent equal-weight percentile formulas (`behaviour.py`).
- **External validation** — EmoSurv (via the shared feature extractor): index medians
  by emotion and an exploratory happy-like vs sad-like Random Forest.
- **Self-report check** — ratings vs indices per session, and Spearman across sessions
  on the researcher page `/admin/behaviour`.

One-off build (reads `../external_features_emosurv.csv` and `../features.csv`, read-only):

```bash
python prototype_platform/build_emotion_validation.py
```

This writes `reference_stats.json`, `emotion_validation.json` and `emotion_model.pkl`
(the pkl is git-ignored like `effort_model.pkl`; regenerate it on a new server — the
page hides the external-model card if it is missing). Indices are research proxies,
not clinical measures.

### Baseline step and within-person test (headline hypothesis)
Every participant first writes a neutral, length-matched **baseline passage**
("describe the room you are in"), then the happy/sad passage. The emotional session is
linked to the baseline (`baseline_id`), and the report shows the **rhythm shift** (CV of the
inter-key interval) against the person's own baseline.

H1 (derived from EmoSurv, tested prospectively on our data): rhythm variability is lower in
emotional writing than in the same person's baseline. On EmoSurv it holds on 108 pairs
(median ΔCV −0.35, p < 0.0001), after length matching (n=38, p=0.02) and per participant
(n=67, p=0.002). Pause-count effects did not survive length matching, and a baseline-
normalised classifier did not beat raw features, so neither is claimed. The test runs on
`/admin/behaviour` once ≥ 8 baseline+emotional pairs exist.

### Label-free participant mode vs research mode
- **Participant mode (default):** no questionnaires. The report is inferred only from typing
  and text, using rules/models validated in the research phase.
- **Research mode** (`/test?mode=research` or `PROTO_RESEARCH_MODE=1`): additionally asks for
  effort, mood, focus and stress ratings, used only to validate the readings.

**Engagement-shift rule** (the prototype's validated "mind-state" algorithm): the passage with
the lower rhythm CV than the person's baseline is the emotional one. On EmoSurv it picks the
emotional passage in 73% of paired comparisons (95% CI 63–82%), 68% length-matched; a
multi-feature logistic model does no better (70%). It is a two-alternative test — single-passage
specificity cannot be estimated from EmoSurv. Focus index and mind-space load are shown as
unvalidated proxies. Numbers come from `emotion_validation.json`
(`python prototype_platform/build_emotion_validation.py --only-shift` refreshes them).
