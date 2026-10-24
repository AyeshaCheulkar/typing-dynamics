"""paths.py — every file location the prototype uses, in one place.

  repo/
    data/
      databases/         prototype.db (live sessions)
      study/             the study CSVs                          [read-only]
      external/          public datasets (EmoSurv, KeyRecs)      [read-only]
      derived/           reference stats, validation JSON, trained models
    research/            study pipeline + offline builders (features.py, explain.py, scripts/)
    prototype_platform/  the app (core/ is this package)
"""
import os

CORE = os.path.dirname(os.path.abspath(__file__))
PROTO = os.path.dirname(CORE)                       # prototype_platform/
REPO = os.path.dirname(PROTO)

DATA = os.path.join(REPO, "data")
DB_FILE = os.path.join(DATA, "databases", "prototype.db")
DERIVED = os.path.join(DATA, "derived")
REFERENCE_STATS = os.path.join(DERIVED, "reference_stats.json")
EMOTION_MODEL = os.path.join(DERIVED, "emotion_model.pkl")
EMOTION_VALIDATION = os.path.join(DERIVED, "emotion_validation.json")
LITERATURE_VALIDATION = os.path.join(DERIVED, "literature_validation.json")

RESEARCH = os.path.join(REPO, "research")           # features.py, explain.py
EFFORT_MODEL = os.path.join(DERIVED, "effort_model.pkl")
STUDY = os.path.join(DATA, "study")
FEATURES_CSV = os.path.join(STUDY, "features.csv")
EXPORT_CSV = os.path.join(STUDY, "server_export.csv")
KEYSTROKES_CSV = os.path.join(STUDY, "server_keystrokes.csv")
ENGAGEMENT_MODEL = os.path.join(DERIVED, "engagement_model.json")
PEER_REFERENCE = os.path.join(DERIVED, "peer_reference.json")
TYPING_NORMS = os.path.join(DERIVED, "typing_norms.json")
NRC_LEXICON = os.path.join(DATA, "external", "nrc_emotion_lexicon.json")
EMOSURV_CSV = os.path.join(DATA, "external", "external_features_emosurv.csv")
