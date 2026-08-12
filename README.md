# Typing Dynamics-Based Writing Analytics Platform

MSc research pilot: estimating **perceived writing effort** from behavioural
typing dynamics using machine learning.

> Scope: proof-of-concept research study. It does **not** diagnose stress,
> anxiety, depression, or any medical/psychological condition.

## Project stages
1. **Writing editor + keystroke capture** ← *current stage*
2. Feature extraction (raw keystrokes → feature table)
3. ML pipeline (Linear Regression baseline vs Random Forest; GroupKFold CV)
4. SHAP explainability
5. Researcher analytics dashboard
6. Hosting for remote participants
7. Testing + final research analysis

## Tech
- Front-end: plain HTML + JavaScript (accurate keystroke capture)
- Back-end: Python + Flask
- Storage: SQLite (`data.db`)

## Run (Windows)
```powershell
python -m venv venv                 # first time only
venv\Scripts\python -m pip install -r requirements.txt
venv\Scripts\python app.py
```
Then open:
- **http://127.0.0.1:5000** — the writing platform (participants)
- **http://127.0.0.1:5000/admin** — verify captured sessions (researcher)

## Data model
`sessions` — one row per completed task (metadata + `effort_rating` label).
`keystrokes` — one row per event (`keydown` / `keyup` / `paste`) with a
millisecond timestamp and caret position. This raw layer is the ground truth;
never delete it.
