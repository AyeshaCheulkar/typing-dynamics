"""
external_experiment.py — Step 4/5: a SEPARATE experiment on the external EmoSurv
data, kept strictly apart from our writing-effort question.

EmoSurv's own labels are induced EMOTIONS (N neutral, H happy, S sad, C calm,
A angry) — a psychological state, NOT writing effort. We never mix these with our
1-5 effort ratings. This script simply asks EmoSurv's native question with OUR
feature pipeline: do the same typing-dynamics features carry an emotional-state
signal in an independent 81-participant dataset?

Value for the thesis: it validates that the extractor produces a usable,
state-related signal at scale (Strategy A), and demonstrates the whole method on
far more data than our pilot — without ever conflating emotion with effort.

Same honesty as our own models: Leave-One-Participant-Out CV, behavioural
features only, every score compared to a majority-class baseline.
"""

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import balanced_accuracy_score, f1_score, accuracy_score

from model import FEATURES

EMO_NAME = {"N": "Neutral", "H": "Happy", "S": "Sad", "C": "Calm", "A": "Angry"}


def load(path="external_features_emosurv.csv"):
    df = pd.read_csv(path)
    df = df[df["behavioural_valid"] == 1].copy()
    df["userid"] = df["external_session"].str.split("|").str[0]
    return df.reset_index(drop=True)


def feature_means_by_emotion(df):
    print("\n--- Feature medians by emotion (descriptive) ---")
    order = ["N", "H", "S", "C", "A"]
    present = [e for e in order if e in set(df["emotion"])]
    head = "".join(f"{EMO_NAME[e][:7]:>9}" for e in present)
    print(f"{'feature':>22}{head}")
    for f in FEATURES:
        line = "".join(f"{df[df['emotion']==e][f].median():>9.2f}" for e in present)
        print(f"{f:>22}{line}")


def lopo(df, y, factory):
    X = df[FEATURES].to_numpy()
    groups = df["userid"].to_numpy()
    logo = LeaveOneGroupOut()
    yt, yp = [], []
    for tr, te in logo.split(X, y, groups):
        m = factory()
        m.fit(X[tr], y[tr])
        yt.extend(y[te])
        yp.extend(m.predict(X[te]))
    return np.array(yt), np.array(yp)


def run_task(df, y, title):
    print(f"\n=== {title} ===")
    print(f"sessions: {len(df)}  participants: {df['userid'].nunique()}  "
          f"classes: {dict(pd.Series(y).value_counts())}")
    models = {
        "Baseline (majority)": lambda: DummyClassifier(strategy="most_frequent"),
        "Random Forest": lambda: RandomForestClassifier(
            n_estimators=400, min_samples_leaf=2,
            class_weight="balanced", random_state=42),
    }
    print(f"{'model':>22} {'Acc':>6} {'BalAcc':>7} {'MacroF1':>8}")
    for name, factory in models.items():
        yt, yp = lopo(df, y, factory)
        acc = accuracy_score(yt, yp)
        bacc = balanced_accuracy_score(yt, yp)
        mf1 = f1_score(yt, yp, average="macro", zero_division=0)
        print(f"{name:>22} {acc:>6.3f} {bacc:>7.3f} {mf1:>8.3f}")


def main():
    print("#" * 64)
    print("EXTERNAL EXPERIMENT (EmoSurv) — typing dynamics -> EMOTION")
    print("(separate from our writing-effort question; labels never mixed)")
    print("#" * 64)
    df = load()
    feature_means_by_emotion(df)

    # Task 1: full 5-way emotion
    run_task(df, df["emotion"].to_numpy(),
             "5-way emotion (N/H/S/C/A)")

    # Task 2: neutral vs any induced emotion (balanced, easier, clearer)
    y_bin = np.where(df["emotion"].to_numpy() == "N", "Neutral", "Emotion")
    run_task(df, y_bin, "Neutral vs Emotion-induced (binary)")

    print("\nNote: this is EmoSurv's emotion question, run with OUR feature "
          "pipeline\non 190 sessions / 81 people. It is NOT the writing-effort "
          "model and its\nlabels are never combined with our 1-5 effort ratings.")


if __name__ == "__main__":
    main()
