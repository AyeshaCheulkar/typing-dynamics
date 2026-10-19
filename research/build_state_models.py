"""
build_state_models.py — builds the two data-driven pieces the report uses, from public data.

1. engagement model  (data/derived/engagement_model.json)
   Logistic regression on EmoSurv free-text sessions: emotional writing (anger / happy / calm /
   sad) vs neutral writing. Weights are stored as plain numbers, so every reading can be
   explained exactly as  weight x (your value - mean) / spread  per behaviour.
   Cross-validation holds out whole participants; a permutation test checks it beats chance.

2. peer reference  (data/derived/peer_reference.json)
   101-point quantile tables of six typing measures over the valid sessions of the pilot, EmoSurv and
   KeyRecs, so the report can say how a writer compares without reading the raw CSVs at run time.

3. typing norms  (data/derived/typing_norms.json)
   Median key interval of 491 English copy-task sessions (Inputlog corpus), split by laptop and
   desktop, as 101-point quantile tables. Used to say how fast the writer's keys are compared
   with typists on the same kind of computer.

Run:  venv\\Scripts\\python research\\build_state_models.py
"""

import json
import os
import warnings

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, roc_auc_score
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT = os.path.join(ROOT, "data", "external")
OUT = os.path.join(ROOT, "data", "derived")
CORPUS = os.path.join(EXT, "zenodo_5803401", "data", "corpus", "data")

# behaviour -> plain name used in the report
FEATURES = {
    "rhythm_cv": "Typing rhythm variability",
    "pause_time_ratio": "Share of time paused",
    "n_long_pause_per_100": "Long thinking pauses",
    "max_pause_ms": "Longest pause",
    "delete_rate": "Deleting",
    "revisions_per_100": "Revising",
    "median_iki_ms": "Key-to-key speed",
}
C = 0.3            # regularisation, fixed before looking at results
FOLDS, PERMS, SEED = 10, 300, 0


def engagement():
    d = pd.read_csv(os.path.join(EXT, "external_features_emosurv.csv"))
    d = d[d.behavioural_valid == 1].copy()
    d["pid"] = d.external_session.str.split("|").str[0]
    d["rhythm_cv"] = d.std_iki_ms / d.mean_iki_ms
    X, y, g = d[list(FEATURES)].to_numpy(float), (d.emotion != "N").astype(int).to_numpy(), d.pid.to_numpy()

    def model():
        return make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=1000))

    cv = GroupKFold(FOLDS)
    p = cross_val_predict(model(), X, y, groups=g, cv=cv, method="predict_proba")[:, 1]
    auc, bal = roc_auc_score(y, p), balanced_accuracy_score(y, p > 0.5)

    # permutation test: shuffle the labels inside each participant, repeat the same CV
    rng, null = np.random.default_rng(SEED), []
    idx = {k: np.where(g == k)[0] for k in np.unique(g)}
    for _ in range(PERMS):
        yp = y.copy()
        for ix in idx.values():
            yp[ix] = rng.permutation(yp[ix])
        null.append(roc_auc_score(yp, cross_val_predict(model(), X, yp, groups=g, cv=cv, method="predict_proba")[:, 1]))
    perm_p = (1 + sum(n >= auc for n in null)) / (1 + PERMS)

    m = model().fit(X, y)
    sc, lr = m.named_steps["standardscaler"], m.named_steps["logisticregression"]
    return {
        "source": "EmoSurv free-text sessions (Maalej & Kallel), emotional vs neutral writing",
        "n_sessions": int(len(d)), "n_participants": int(len(idx)), "share_emotional": round(float(y.mean()), 3),
        "features": list(FEATURES), "labels": FEATURES,
        "mean": sc.mean_.tolist(), "scale": sc.scale_.tolist(),
        "coef": lr.coef_[0].tolist(), "intercept": float(lr.intercept_[0]),
        "cv": {"folds": FOLDS, "auc": round(auc, 3), "balanced_accuracy": round(bal, 3),
               "permutation_p": round(perm_p, 4), "permutations": PERMS},
    }


def peers():
    frames = []
    for path in (os.path.join(ROOT, "data", "study", "features.csv"),
                 os.path.join(EXT, "external_features_emosurv.csv"),
                 os.path.join(EXT, "external_features_keyrecs.csv")):
        d = pd.read_csv(path)
        frames.append(d[d.behavioural_valid == 1])
    d = pd.concat(frames, ignore_index=True)
    d["rhythm_cv"] = d.std_iki_ms / d.mean_iki_ms
    cols = ["rhythm_cv", "pause_time_ratio", "revisions_per_100", "delete_rate", "n_long_pause_per_100",
            "median_iki_ms"]
    q = np.linspace(0, 100, 101)
    return {"source": "valid sessions: pilot study + EmoSurv + KeyRecs", "n": int(len(d)),
            "quantiles": {c: np.percentile(d[c], q).round(5).tolist() for c in cols}}


def norms():
    s = pd.read_csv(os.path.join(CORPUS, "session.csv"))
    c = pd.read_csv(os.path.join(CORPUS, "components", "sentence.csv"))
    d = s.merge(c[["id", "median"]], on="id")
    d = d[d.computer.isin(["laptop", "desktop"])]
    q = np.linspace(0, 100, 101)
    return {
        "source": "Inputlog copy-task corpus, English subset (Zenodo 5803401, CC-BY-4.0)",
        "n_sessions": int(len(d)),
        "median_iki_ms": {k: np.percentile(v["median"], q).round(1).tolist() for k, v in d.groupby("computer")},
        "counts": d.computer.value_counts().to_dict(),
    }


if __name__ == "__main__":
    eng, nrm = engagement(), norms()
    for name, obj in (("engagement_model.json", eng), ("typing_norms.json", nrm), ("peer_reference.json", peers())):
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=1)
    print("engagement:", eng["cv"], "| n =", eng["n_sessions"], "sessions /", eng["n_participants"], "people")
    for f, w in sorted(zip(eng["features"], eng["coef"]), key=lambda t: -abs(t[1])):
        print("  %-22s %+.3f" % (f, w))
    print("norms:", nrm["counts"], "| median laptop/desktop key interval:",
          nrm["median_iki_ms"]["laptop"][50], nrm["median_iki_ms"]["desktop"][50], "ms")
