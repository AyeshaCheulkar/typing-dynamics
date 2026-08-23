"""
train_model.py — fit the FINAL effort models on all 22 valid sessions and save a
single reusable artifact (`effort_model.pkl`).

This artifact is the shared hand-off point:
  - Stage B (explain.py) loads it to compute SHAP explanations.
  - The future prototype platform (separate prototype_platform/ folder) will load
    the SAME artifact to score a new session and build its report — it never
    retrains and never imports the Stage-1 data-collection app.

Honesty note: these models do NOT beat a mean baseline on this pilot (see
ANALYSIS_PRIMARY.md). They are fit here so the pipeline is complete and
explainable end-to-end; predicted effort must be treated as EXPERIMENTAL.
"""

import joblib
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from analysis_primary import load, MODEL_FEATURES, HYPOTHESES, TARGET

READABLE = {k: name for k, name, _ in HYPOTHESES}
HYP_SIGN = {k: s for k, _, s in HYPOTHESES}


def train(path="features.csv", out="effort_model.pkl"):
    df = load(path)
    X = df[MODEL_FEATURES].to_numpy(float)
    y = df[TARGET].to_numpy(float)

    rf = RandomForestRegressor(n_estimators=400, min_samples_leaf=2,
                               random_state=42).fit(X, y)
    lr = make_pipeline(StandardScaler(), LinearRegression()).fit(X, y)

    artifact = {
        "rf": rf,
        "lr": lr,
        "features": MODEL_FEATURES,       # order matters — platform must match
        "readable": READABLE,             # feature -> human label
        "hyp_sign": HYP_SIGN,             # hypothesised direction (+1/-1)
        "X_train": X,                     # background for SHAP + percentile context
        "y_train": y,
        "train_mean_effort": float(y.mean()),   # the baseline predictor
        "n_sessions": int(len(df)),
        "n_participants": int(df["participant_id"].nunique()),
    }
    joblib.dump(artifact, out)
    print(f"saved {out}: RF + LinearRegression fit on {len(df)} sessions, "
          f"{len(MODEL_FEATURES)} features. Baseline mean effort = "
          f"{artifact['train_mean_effort']:.2f}.")
    return artifact


if __name__ == "__main__":
    train()
