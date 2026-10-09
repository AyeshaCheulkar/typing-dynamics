# Typing Dynamics Writing Analytics

MSc research project: what a person's typing behaviour can tell us about how they wrote, and how it
relates to self-reported emotional intensity, cognitive load and flow. It does **not** diagnose
stress, anxiety, depression or any condition.

## Repository layout
```
prototype_platform/   The final prototype (Flask app, port 5001). Start here.
  app.py              Routes: participant flow (/, /test, /report/<id>) and researcher admin (/admin)
  core/               Application logic
    paths.py            every file location in one place
    tasks.py            writing prompts
    questionnaire.py    SAM / NASA-TLX / Flow Short Scale scoring (ground-truth labels)
    behaviour.py        typing indices (focus, hesitation, correction, mind-space, processing)
    affect.py           text tone, EmoSurv model, live correlation analysis
    plain_report.py     plain-language report text
    predict.py          typing features, experimental effort estimate, SHAP
    recommendations.py  behaviour-based writing suggestions
    research_data.py    read-only access to the study dataset (admin pages)
    db.py               prototype SQLite layer
  templates/          base.html, participant/ (landing, write, report), admin/
  static/             css/, js/, img/, vendor/
  data/               prototype.db, reference stats, validation JSON, EmoSurv model
  scripts/            offline builders for the validation files
research/             Study pipeline: features.py, train_model.py, explain.py, analysis_primary.py, effort_model.pkl
data/study/           The 25-session study CSVs (features, sessions, keystrokes)
data/external/        External datasets (EmoSurv features, KeyRecs, free-text typing)
docs/                 ANALYSIS_PRIMARY.md, LITERATURE.md, FORMULAS.md
app.py, db.py, data.db, templates/, static/, pythonanywhere_wsgi.py
                      Stage-1 data-collection app (deployed separately; not used by the prototype)
```

## Run the prototype (Windows)
```powershell
python -m venv venv                                          # first time only
venv\Scripts\python -m pip install -r prototype_platform\requirements.txt
venv\Scripts\python prototype_platform\app.py
```
- Participants: http://127.0.0.1:5001/
- Researcher: http://127.0.0.1:5001/admin (default login `admin` / `admin`; set `PROTO_ADMIN_USER`, `PROTO_ADMIN_PASSWORD`)

`run_prototype_online.bat` starts the same server and a Cloudflare tunnel; `prototype_wsgi.py` is the
PythonAnywhere configuration.

## Rebuild derived files (optional)
```powershell
venv\Scripts\python research\features.py                          # data/study/*.csv -> features.csv
venv\Scripts\python research\train_model.py                       # features.csv -> research\effort_model.pkl
venv\Scripts\python prototype_platform\scripts\build_emotion_validation.py
venv\Scripts\python prototype_platform\scripts\validate_literature_formulas.py
```

## Stage-1 app (data collection only)
`venv\Scripts\python app.py` serves the original collection site on port 5000. Do not change it: it is
deployed from this repository.
