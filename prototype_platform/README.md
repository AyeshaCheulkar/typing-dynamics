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
See the repository `README.md` for the layout and run commands. Short version, from the repo root:

```bash
pip install -r prototype_platform/requirements.txt
python prototype_platform/app.py        # http://127.0.0.1:5001  (admin: /admin)
```

Data is stored in `prototype_platform/data/prototype.db` (created on first run; separate from the
Stage-1 `data.db`).

## Folders
- `app.py` — Flask routes only
- `core/` — logic (`paths`, `tasks`, `questionnaire`, `behaviour`, `affect`, `plain_report`, `predict`,
  `recommendations`, `research_data`, `db`)
- `templates/participant/`, `templates/admin/` — pages; `static/css|js|img|vendor/`
- `data/` — database, reference stats, validation JSON, EmoSurv model (`emotion_model.pkl`, git-ignored)
- `scripts/` — `build_emotion_validation.py`, `validate_literature_formulas.py` (offline, not run by the app)

## Post-writing questions
Ten short items from published instruments, scored in `core/questionnaire.py`: Self-Assessment Manikin
(emotional intensity), NASA-TLX (cognitive load) and Flow Short Scale. The admin page `/admin/behaviour`
correlates them with the typing indices. Research mode (`/test?mode=research`) adds perceived effort.

## Emotion-writing extension (happy / sad moment)
Participants choose a happy or sad moment. The report has four sections: writing dynamics, behavioural
state (self-reported vs typing-suggested), practical insight, evidence and method.
- **Text emotion** — VADER sentiment + first-person word rate (`core/affect.py`).
- **Behavioural indices** — equal-weight percentile formulas (`core/behaviour.py`).
- **External validation** — EmoSurv index medians by mood and an exploratory happy-like vs sad-like model.

Offline build (reads `data/external/external_features_emosurv.csv` and `data/study/features.csv`):

```bash
python prototype_platform/scripts/build_emotion_validation.py
```

It writes `data/reference_stats.json`, `data/emotion_validation.json` and `data/emotion_model.pkl`.
Indices are research proxies, not clinical measures.

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

### Participant mode vs research mode
- **Participant mode (default):** after writing, everyone answers a few short questions
  (relive, mood, energy, focus, mind-wandering, tension, interrupted). No perceived-effort
  question. These answers are the labels used to validate the focus / mind-space readings.
- **Research mode** (`/test?mode=research` or `PROTO_RESEARCH_MODE=1`): the same questions plus
  perceived writing effort.

**Engagement-shift rule** (the prototype's validated "mind-state" algorithm): the passage with
the lower rhythm CV than the person's baseline is the emotional one. On EmoSurv it picks the
emotional passage in 73% of paired comparisons (95% CI 63–82%), 68% length-matched; a
multi-feature logistic model does no better (70%). It is a two-alternative test — single-passage
specificity cannot be estimated from EmoSurv. Focus index and mind-space load are shown as
unvalidated proxies. Numbers come from `emotion_validation.json`
(`python prototype_platform/build_emotion_validation.py --only-shift` refreshes them).
