"""
model.py — Stage 3 (primary model): can typing dynamics estimate writing effort?

Reads  : features.csv  (one row per session: behavioural features + effort label)
Trains : a mean-baseline, Linear Regression, and Random Forest to predict the
         self-rated effort (1-5) from typing behaviour ONLY (not the text).
Tested : with Leave-One-Participant-Out cross-validation (LOPO) — every fold
         trains on some people and is tested on a person it has NEVER seen, so
         the score reflects generalisation to new writers, not memorisation.
Reports: MAE, RMSE, R² for each model, a feature<->effort correlation table, and
         Random-Forest feature importances (which behaviours matter most).

Why LOPO: several participants did more than one session. Ordinary k-fold could
put the same person in train and test and inflate the score (data leakage). LOPO
(GroupKFold by participant) is the honest test for a study like this.

This script deliberately uses BEHAVIOURAL features only (speed, pauses, deletion,
revision, writing time) — NOT word/character counts — because the research
question is whether *how* someone types (not how much they wrote) tracks effort.
"""

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Behavioural feature set — the "typing dynamics". No text-volume columns.
FEATURES = [
    "chars_per_sec",        # typing speed
    "median_iki_ms",        # rhythm: typical gap between keys
    "std_iki_ms",           # rhythm variability
    "n_short_pause_per_100",  # frequency of brief hesitations
    "n_long_pause_per_100",   # frequency of long (thinking) pauses
    "pause_time_ratio",     # share of time spent paused
    "delete_rate",          # correcting as you go
    "revisions_per_100",    # how often editing bursts happen
    "active_time_s",        # total active writing time
]
TARGET = "effort_rating"
GROUP = "participant_id"


def load(valid_only=True, path="features.csv"):
    df = pd.read_csv(path)
    if valid_only:
        df = df[df["behavioural_valid"] == 1].copy()
    return df.reset_index(drop=True)


def describe(df, label):
    print(f"\n=== Dataset: {label} ===")
    print(f"sessions: {len(df)}   participants: {df[GROUP].nunique()}")
    dist = df[TARGET].value_counts().sort_index()
    print("effort rating distribution:",
          {int(k): int(v) for k, v in dist.items()})
    print(f"mean effort: {df[TARGET].mean():.2f}  (std {df[TARGET].std():.2f})")


def correlations(df):
    """Pearson & Spearman correlation of each feature with the effort rating."""
    print("\n--- Feature <-> effort correlation (all valid sessions) ---")
    print(f"{'feature':>22} {'Pearson r':>10} {'p':>7} {'Spearman':>9} {'p':>7}")
    rows = []
    for f in FEATURES:
        pr, pp = stats.pearsonr(df[f], df[TARGET])
        sr, sp = stats.spearmanr(df[f], df[TARGET])
        rows.append((f, pr, pp, sr, sp))
        star = " *" if (pp < 0.05 or sp < 0.05) else ""
        print(f"{f:>22} {pr:>10.3f} {pp:>7.3f} {sr:>9.3f} {sp:>7.3f}{star}")
    return rows


def lopo_scores(df, model_factory):
    """Leave-One-Participant-Out CV; return pooled out-of-fold predictions."""
    X = df[FEATURES].to_numpy()
    y = df[TARGET].to_numpy(dtype=float)
    groups = df[GROUP].to_numpy()
    logo = LeaveOneGroupOut()
    y_true, y_pred = [], []
    for tr, te in logo.split(X, y, groups):
        model = model_factory()
        model.fit(X[tr], y[tr])
        y_true.extend(y[te])
        y_pred.extend(model.predict(X[te]))
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    return {"MAE": mae, "RMSE": rmse, "R2": r2,
            "y_true": y_true, "y_pred": y_pred}


def evaluate(df, label):
    describe(df, label)
    correlations(df)

    models = {
        "Baseline (predict mean)": lambda: DummyRegressor(strategy="mean"),
        "Linear Regression": lambda: make_pipeline(
            StandardScaler(), LinearRegression()),
        "Random Forest": lambda: RandomForestRegressor(
            n_estimators=300, min_samples_leaf=2, random_state=42),
    }
    print(f"\n--- Leave-One-Participant-Out results ({label}) ---")
    print(f"{'model':>26} {'MAE':>6} {'RMSE':>6} {'R2':>7}")
    results = {}
    for name, factory in models.items():
        s = lopo_scores(df, factory)
        results[name] = s
        print(f"{name:>26} {s['MAE']:>6.3f} {s['RMSE']:>6.3f} {s['R2']:>7.3f}")

    # Random-Forest feature importance (fit once on all valid data — descriptive)
    rf = RandomForestRegressor(n_estimators=300, min_samples_leaf=2,
                               random_state=42)
    rf.fit(df[FEATURES], df[TARGET])
    imp = sorted(zip(FEATURES, rf.feature_importances_),
                 key=lambda x: -x[1])
    print("\n--- Random Forest feature importance (most -> least) ---")
    for f, v in imp:
        print(f"{f:>22} {v:>6.3f}")
    return results


def main():
    print("#" * 64)
    print("STAGE 3 PRIMARY MODEL — typing dynamics -> writing effort (1-5)")
    print("#" * 64)

    valid = load(valid_only=True)
    evaluate(valid, "22 behaviourally-valid sessions (PRIMARY)")

    # Sensitivity check: does including the 3 flagged sessions change the story?
    allrows = load(valid_only=False)
    evaluate(allrows, "all 25 included sessions (SENSITIVITY CHECK)")

    print("\nNote: with a pilot this small, R² is unstable and often near or "
          "below 0.\nThe honest read is the model-vs-baseline gap (MAE/RMSE) and "
          "which\nbehaviours correlate with effort — not a single headline R².")


if __name__ == "__main__":
    main()
