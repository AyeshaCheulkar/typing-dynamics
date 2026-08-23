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
