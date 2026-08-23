"""
analysis_plots.py — one figure summarising the PRIMARY effort analysis, now with
participant-bootstrap 95% confidence intervals shown as whiskers.
  (left)  Spearman correlation of each behaviour with self-perceived effort, with
          its 95% CI; the grey band marks the not-significant region at n=22.
  (right) Leave-One-Participant-Out prediction error (MAE) per model with its 95%
          CI, against the mean baseline. Lower is better.
Colours: Okabe-Ito (colourblind-safe); identity also carried by order/labels.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import t as tdist
from sklearn.metrics import mean_absolute_error

from analysis_primary import (load, HYPOTHESES, bootstrap_corr, oof_lopo,
                              metric_ci, model_factories, TARGET, GROUP)

BLUE, GREEN, VERM, GREY = "#0072B2", "#009E73", "#D55E00", "#8A8A8A"

df = load()
n = len(df)
tcrit = tdist.ppf(0.975, n - 2)
rcrit = tcrit / np.sqrt(n - 2 + tcrit**2)

# --- Panel A: Spearman rho + 95% CI per behaviour, sorted ------------------
rows = []
for col, name, _ in HYPOTHESES:
    rho, lo, hi = bootstrap_corr(df, col, method="spearman")
    rows.append((name, rho, lo, hi))
rows.sort(key=lambda r: r[1])
names = [r[0] for r in rows]
rhos = np.array([r[1] for r in rows])
los = np.array([r[2] for r in rows])
his = np.array([r[3] for r in rows])
colors = [BLUE if r > 0 else VERM for r in rhos]
xerr = np.vstack([rhos - los, his - rhos])

# --- Panel B: LOPO MAE + 95% CI per model ----------------------------------
g = df[GROUP].to_numpy()
facs = model_factories()
mae_pt, mae_err = [], [[], []]
for name, fac in facs.items():
    y, pred = oof_lopo(df, fac)
    mae = mean_absolute_error(y, pred)
    ci = metric_ci(y, pred, g)
    mae_pt.append(mae)
    mae_err[0].append(mae - ci["mae"][0])
    mae_err[1].append(ci["mae"][1] - mae)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.8, 5.4))
fig.suptitle("Self-perceived writing effort vs typing dynamics — primary data "
             f"(n={n} sessions, {df[GROUP].nunique()} participants)",
             fontsize=13, fontweight="bold")

# Panel A
ax1.axvspan(-rcrit, rcrit, color="#EDEDED", zorder=0)
ax1.axvline(0, color="#333333", lw=1)
ax1.barh(names, rhos, color=colors, height=0.6, zorder=3)
ax1.errorbar(rhos, np.arange(len(names)), xerr=xerr, fmt="none",
             ecolor="#444444", elinewidth=1.2, capsize=3, zorder=4)
ax1.set_xlim(-1, 1)
ax1.set_xlabel("Spearman correlation with effort rating  (bars = 95% CI)")
ax1.set_title("Relationship to effort  (grey = not significant; every CI spans 0)",
              fontsize=10.5)
ax1.grid(axis="x", color="#ECECEC", zorder=1)
for s in ("top", "right"):
    ax1.spines[s].set_visible(False)

# Panel B
x = np.arange(len(facs))
bar_colors = [GREY, BLUE, GREEN]
ax2.bar(x, mae_pt, 0.6, color=bar_colors, zorder=3)
ax2.errorbar(x, mae_pt, yerr=mae_err, fmt="none", ecolor="#444444",
             elinewidth=1.2, capsize=4, zorder=4)
for xi, v in zip(x, mae_pt):
    ax2.text(xi, v + 0.02, f"{v:.2f}", ha="center", fontsize=9, color="#222222")
ax2.axhline(mae_pt[0], color=GREY, ls="--", lw=1.1, zorder=2)
ax2.text(len(facs) - 0.5, mae_pt[0] + 0.03, "baseline (lower is better ↓)",
         ha="right", fontsize=8, color="#555555")
ax2.set_xticks(x)
ax2.set_xticklabels(["Baseline", "Linear Reg.", "Random Forest"])
ax2.set_ylabel("MAE, effort points (bars = 95% CI)")
ax2.set_ylim(0, max(mae_pt) + max(mae_err[1]) + 0.4)
ax2.set_title("Prediction error vs baseline (Leave-One-Participant-Out)",
              fontsize=10.5)
ax2.grid(axis="y", color="#ECECEC", zorder=1)
for s in ("top", "right"):
    ax2.spines[s].set_visible(False)

fig.tight_layout(rect=(0, 0, 1, 0.95))
fig.savefig("analysis_primary.png", dpi=150, bbox_inches="tight")
print("saved analysis_primary.png")
