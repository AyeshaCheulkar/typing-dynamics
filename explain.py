"""
explain.py — Stage B: SHAP explainability for the effort model.

Produces:
  - a GLOBAL picture: which typing behaviours the Random Forest relies on most
    (SHAP mean|impact|), saved as shap_summary.png;
  - a PER-SESSION explanation function `explain_session(features)` that the future
    prototype platform will reuse to tell a writer, in plain language, which of
    their behaviours pushed the effort estimate up or down;
  - a cross-check against the Linear Regression's standardised coefficients.

Honest framing (printed and written into EXPLAINABILITY.md): the effort model does
NOT beat a mean baseline on this pilot, so SHAP here explains WHAT THE MODEL DOES,
not a validated causal driver of effort. Treat as descriptive/experimental.
"""

import os
import joblib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import shap

from train_model import train, READABLE
from analysis_primary import MODEL_FEATURES


def load_artifact(path="effort_model.pkl"):
    if not os.path.exists(path):
        train(out=path)
    return joblib.load(path)


def _explainer(artifact):
    return shap.TreeExplainer(artifact["rf"])


def global_summary(artifact, out="shap_summary.png"):
    """SHAP global importance (bar of mean|impact|) + return values for the doc."""
    expl = _explainer(artifact)
    sv = expl.shap_values(artifact["X_train"])
    labels = [READABLE[f] for f in MODEL_FEATURES]

    plt.figure(figsize=(8, 5))
    shap.summary_plot(sv, artifact["X_train"], feature_names=labels,
                      plot_type="bar", show=False, color="#0072B2")
    plt.title("SHAP global importance — Random Forest effort model\n"
              "(descriptive: model does not beat baseline)", fontsize=10)
    plt.tight_layout()
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()

    mean_abs = np.abs(sv).mean(axis=0)
    ranking = sorted(zip(MODEL_FEATURES, mean_abs), key=lambda t: -t[1])
    return ranking


def explain_session(artifact, feats):
    """Explain ONE session. `feats` = dict feature->value. Returns a dict the
    platform can render directly (predicted effort + ranked contributions +
    plain-language sentences)."""
    expl = _explainer(artifact)
    x = np.array([[float(feats[f]) for f in MODEL_FEATURES]], float)
    sv = expl.shap_values(x)[0]
    base = float(np.ravel(expl.expected_value)[0])
    pred = float(artifact["rf"].predict(x)[0])

    contribs = sorted(zip(MODEL_FEATURES, sv), key=lambda t: -abs(t[1]))
    sentences = []
    for f, v in contribs[:4]:
        if abs(v) < 1e-3:
            continue
        verb = "raised" if v > 0 else "lowered"
        sentences.append(f"{READABLE[f]} {verb} the effort estimate ({v:+.2f}).")
    return {"predicted_effort": round(pred, 2),
            "baseline_effort": round(base, 2),
            "contributions": [(READABLE[f], round(float(v), 3)) for f, v in contribs],
            "explanations": sentences}


def linear_coefficients(artifact):
    """Standardised LR coefficients — a simple linear cross-check on SHAP."""
    lr = artifact["lr"]
    coefs = lr.named_steps["linearregression"].coef_
    return sorted(zip(MODEL_FEATURES, coefs), key=lambda t: -abs(t[1]))


if __name__ == "__main__":
    art = load_artifact()
    print(f"Model: RF + LR on {art['n_sessions']} sessions, "
          f"{art['n_participants']} participants. "
          f"Baseline mean effort = {art['train_mean_effort']:.2f}\n")

    ranking = global_summary(art)
    print("SHAP global importance (mean|impact| on predicted effort):")
    for f, v in ranking:
        print(f"  {READABLE[f]:>26} {v:.3f}")

    print("\nLinear Regression standardised coefficients (cross-check):")
    for f, c in linear_coefficients(art):
        print(f"  {READABLE[f]:>26} {c:+.3f}")

    # Example per-session explanation on the highest-effort training session.
    import pandas as pd
    df = pd.read_csv("features.csv")
    df = df[df["behavioural_valid"] == 1]
    row = df.sort_values("effort_rating", ascending=False).iloc[0]
    feats = {f: row[f] for f in MODEL_FEATURES}
    ex = explain_session(art, feats)
    print(f"\nExample session (participant {row['participant_id']}, "
          f"self-rated effort {int(row['effort_rating'])}):")
    print(f"  predicted effort = {ex['predicted_effort']} "
          f"(model baseline {ex['baseline_effort']})")
    for s in ex["explanations"]:
        print("   -", s)
    print("\nsaved shap_summary.png")
