"""
model_binary.py — Stage 3 (binary reframe): predict LOW vs HIGH writing effort.

Why a binary target: with a small pilot, learning a full 1-5 scale is very hard
(see model.py — regression lost to the mean). Collapsing effort into two classes
(lower vs higher) is much easier to learn from little data, and it is also the
bridge to the external cognitive-demand datasets (Strategy B), which only label
tasks as low vs high demand.

Primary split (balanced, uses every session):
    effort 1-2  -> LOW effort   (class 0)
    effort 3-5  -> HIGH effort  (class 1)
Robustness split (extremes only, clearer meaning but tiny/imbalanced):
    effort 1-2  -> LOW,  effort 4-5 -> HIGH,  the 3s are dropped.

Same honest test as before: Leave-One-Participant-Out CV, behavioural features
only (never the text). Reports accuracy, balanced accuracy, F1, ROC-AUC and the
confusion matrix, all against a majority-class baseline.
"""

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, f1_score,
                             roc_auc_score, confusion_matrix)

from model import FEATURES, TARGET, GROUP, load


def make_binary(df, threshold_high=3, drop_middle=False):
    """Return (df, y) with effort collapsed to LOW(0)/HIGH(1)."""
    d = df.copy()
    if drop_middle:
        d = d[d[TARGET] != threshold_high].copy()
    y = (d[TARGET] >= threshold_high).astype(int)
    return d.reset_index(drop=True), y.reset_index(drop=True).to_numpy()


def lopo_classify(d, y, model_factory):
    """Leave-One-Participant-Out CV; pool out-of-fold labels + probabilities."""
    X = d[FEATURES].to_numpy()
    groups = d[GROUP].to_numpy()
    logo = LeaveOneGroupOut()
    y_true, y_pred, y_prob = [], [], []
    for tr, te in logo.split(X, y, groups):
        model = model_factory()
        model.fit(X[tr], y[tr])
        y_true.extend(y[te])
        y_pred.extend(model.predict(X[te]))
        # probability of HIGH class, if the model provides one
        if hasattr(model, "predict_proba"):
            classes = list(model.classes_)
            if 1 in classes:
                y_prob.extend(model.predict_proba(X[te])[:, classes.index(1)])
            else:  # training fold had only one class
                y_prob.extend([float(classes[0])] * len(te))
        else:
            y_prob.extend(model.predict(X[te]))
    return np.array(y_true), np.array(y_pred), np.array(y_prob)


def class_means(d, y):
    """Mean of each feature for LOW vs HIGH — a simple, readable signal table."""
    print(f"\n--- Feature means: LOW vs HIGH effort ---")
    print(f"{'feature':>22} {'LOW':>9} {'HIGH':>9}  direction")
    low, high = d[y == 0], d[y == 1]
    for f in FEATURES:
        lo, hi = low[f].mean(), high[f].mean()
        arrow = "higher when HARDER" if hi > lo else "lower when HARDER"
        print(f"{f:>22} {lo:>9.3f} {hi:>9.3f}  {arrow}")


def evaluate(df, label, threshold_high=3, drop_middle=False):
    d, y = make_binary(df, threshold_high, drop_middle)
    n_low, n_high = int((y == 0).sum()), int((y == 1).sum())
    print(f"\n=== {label} ===")
    print(f"sessions: {len(d)}   participants: {d[GROUP].nunique()}   "
          f"LOW={n_low}  HIGH={n_high}")
    if n_low == 0 or n_high == 0 or d[GROUP].nunique() < 3:
        print("  (too few of one class / too few participants — skipping)")
        return

    class_means(d, y)

    models = {
        "Baseline (majority class)": lambda: DummyClassifier(
            strategy="most_frequent"),
        "Logistic Regression": lambda: make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=1000, class_weight="balanced")),
        "Random Forest": lambda: RandomForestClassifier(
            n_estimators=300, min_samples_leaf=2,
            class_weight="balanced", random_state=42),
    }
    print(f"\n--- Leave-One-Participant-Out results ---")
    print(f"{'model':>26} {'Acc':>6} {'BalAcc':>7} {'F1':>6} {'AUC':>6}")
    for name, factory in models.items():
        yt, yp, pr = lopo_classify(d, y, factory)
        acc = accuracy_score(yt, yp)
        bacc = balanced_accuracy_score(yt, yp)
        f1 = f1_score(yt, yp, zero_division=0)
        try:
            auc = roc_auc_score(yt, pr)
        except ValueError:
            auc = float("nan")
        print(f"{name:>26} {acc:>6.3f} {bacc:>7.3f} {f1:>6.3f} {auc:>6.3f}")
        if name == "Random Forest":
            cm = confusion_matrix(yt, yp)
            print(f"      RF confusion matrix [rows=true LOW/HIGH, cols=pred]:\n"
                  f"        {cm.tolist()}")

    # Feature importance from a RF fit on all rows (descriptive)
    rf = RandomForestClassifier(n_estimators=300, min_samples_leaf=2,
                                class_weight="balanced", random_state=42)
    rf.fit(d[FEATURES], y)
    imp = sorted(zip(FEATURES, rf.feature_importances_), key=lambda x: -x[1])
    print("\n--- Random Forest feature importance (most -> least) ---")
    for f, v in imp:
        print(f"{f:>22} {v:>6.3f}")


def main():
    print("#" * 64)
    print("STAGE 3 BINARY MODEL — LOW vs HIGH writing effort")
    print("#" * 64)
    valid = load(valid_only=True)

    evaluate(valid, "PRIMARY: split 1-2 (LOW) vs 3-5 (HIGH), 22 valid sessions",
             threshold_high=3, drop_middle=False)

    evaluate(valid, "ROBUSTNESS: extremes only 1-2 (LOW) vs 4-5 (HIGH), 3s dropped",
             threshold_high=3, drop_middle=True)

    print("\nRead: 'Baseline' always predicts the majority class. A model is only "
          "useful\nif its Balanced Accuracy / AUC clearly beat 0.5 and it tops the "
          "baseline.")


if __name__ == "__main__":
    main()
