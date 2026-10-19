# Typing Dynamics Writing Analytics

MSc research project: what a person's typing behaviour can tell us about how they wrote, and how it
relates to self-reported emotional intensity, cognitive load and flow. It does **not** diagnose
stress, anxiety, depression or any condition.

## Repository layout
```
prototype_platform/   The app (Flask, port 5001). Start here.
  app.py              Routes: participant flow (/, /test, /report/<id>) and researcher admin (/admin)
  core/               Application logic (paths.py holds every file location)
    tasks.py            writing prompts
    questionnaire.py    SAM / NASA-TLX / Flow Short Scale scoring (ground-truth labels)
    analysis.py         the participant report: comparisons, engagement reading, pauses, tips
    behaviour.py        typing indices (focus, hesitation, correction, mind-space, processing)
    affect.py           text tone, EmoSurv model, live correlation analysis
    measures.py         content of the researcher's Model research page (formulas, sources, datasets)
    findings.py         research summary and hypotheses shown on the admin dashboard
    plain_report.py     wording for the emotional tab (answers vs typing)
    predict.py          typing features, timeline; pilot effort model + SHAP (researcher side only)
    recommendations.py  pilot session reports (researcher side)
    research_data.py    read-only access to the pilot dataset (admin pages)
    db.py               prototype SQLite layer
  tests/              test_analysis.py (run it directly with python)
  templates/          base.html, participant/ (landing, write, report), admin/
  static/             css/, js/, img/, vendor/
  deploy/             prototype_wsgi.py (PythonAnywhere), run_prototype_online.bat (Cloudflare tunnel)
data/                 Everything that is data
  databases/          prototype.db (new sessions; git-ignored) and a dated backup of the earlier test sessions
  study/              The 25-session pilot CSVs (features, sessions, keystrokes)
  external/           Public datasets and their features (EmoSurv, KeyRecs, Inputlog copy task, Freihaut stress study)
  derived/            reference stats, validation JSON, engagement_model.json, typing_norms.json, effort/emotion models (.pkl)
research/             Everything that produces the numbers
  features.py, train_model.py, explain.py, analysis_primary.py   study pipeline
  build_state_models.py   engagement model + typing norms -> data/derived/
  scripts/            build_emotion_validation.py, validate_literature_formulas.py
  docs/               ANALYSIS_PRIMARY.md, LITERATURE.md, FORMULAS.md
app.py, db.py, data.db, templates/, static/, requirements.txt, pythonanywhere_wsgi.py
                      Stage-1 data-collection app (deployed from the repo root; not used by the prototype)
```

## Run the prototype (Windows)
```powershell
python -m venv venv                                          # first time only
venv\Scripts\python -m pip install -r prototype_platform\requirements.txt
venv\Scripts\python prototype_platform\app.py
```
- Participants: http://127.0.0.1:5001/
- Researcher: http://127.0.0.1:5001/admin (default login `admin` / `admin`; set `PROTO_ADMIN_USER`, `PROTO_ADMIN_PASSWORD`)

`prototype_platform\deploy\run_prototype_online.bat` starts the same server and a Cloudflare tunnel;
`prototype_platform\deploy\prototype_wsgi.py` is the PythonAnywhere configuration.

The prototype never writes to the Stage-1 files, the study CSVs or the external datasets. Its only
database is `data/databases/prototype.db`, created on first run.

## Rebuild derived files (optional)
```powershell
venv\Scripts\python research\features.py                          # data/study/*.csv -> features.csv
venv\Scripts\python research\train_model.py                       # features.csv -> data\derived\effort_model.pkl
venv\Scripts\python research\build_state_models.py                # engagement model + typing norms
venv\Scripts\python research\scripts\build_emotion_validation.py
venv\Scripts\python research\scripts\validate_literature_formulas.py
```

## Tests
```powershell
venv\Scripts\python prototype_platform\tests\test_analysis.py
```

## Stage-1 app (data collection only)
`venv\Scripts\python app.py` serves the original collection site on port 5000. Do not move or change it:
it is deployed from this repository root.
