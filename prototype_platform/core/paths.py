"""paths.py — every file location the prototype uses, in one place.

  repo/
    research/            shared study pipeline (features.py, explain.py, model)  [read-only]
    data/study/          the study CSVs                                          [read-only]
    prototype_platform/
      core/              this package
      data/              prototype's own database, reference stats, validation JSON, EmoSurv model
"""
import os

CORE = os.path.dirname(os.path.abspath(__file__))
PROTO = os.path.dirname(CORE)                       # prototype_platform/
REPO = os.path.dirname(PROTO)

DATA = os.path.join(PROTO, "data")
DB_FILE = os.path.join(DATA, "prototype.db")
REFERENCE_STATS = os.path.join(DATA, "reference_stats.json")
EMOTION_MODEL = os.path.join(DATA, "emotion_model.pkl")
EMOTION_VALIDATION = os.path.join(DATA, "emotion_validation.json")
LITERATURE_VALIDATION = os.path.join(DATA, "literature_validation.json")

RESEARCH = os.path.join(REPO, "research")           # features.py, explain.py, effort_model.pkl
EFFORT_MODEL = os.path.join(RESEARCH, "effort_model.pkl")
STUDY = os.path.join(REPO, "data", "study")
FEATURES_CSV = os.path.join(STUDY, "features.csv")
EXPORT_CSV = os.path.join(STUDY, "server_export.csv")
KEYSTROKES_CSV = os.path.join(STUDY, "server_keystrokes.csv")
EMOSURV_CSV = os.path.join(REPO, "data", "external", "external_features_emosurv.csv")
