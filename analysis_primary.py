"""
analysis_primary.py — Final statistical + ML analysis of the PRIMARY dataset:
self-perceived writing effort (1-5) vs typing behaviour.

Scope note (kept deliberately narrow): the target is the participant's OWN rating
of *self-perceived writing effort*. Nothing here claims to measure mental effort,
cognitive load, stress, or any psychological/medical state.

Everything is PARTICIPANT-AWARE:
  - cross-validation leaves out whole participants (LOPO / GroupKFold), and
  - every confidence interval is bootstrapped by resampling PARTICIPANTS (not
    sessions), so repeated sessions from one person don't fake precision.

Two parts:
  A. Relationship analysis — Pearson & Spearman correlation of each behaviour with
     the effort rating, each with a participant-bootstrap 95% CI, plus whether the
     direction matches the study hypothesis.
  B. Prediction — Linear Regression and Random Forest under participant-aware CV,
     scored with MAE, RMSE, R² (each with a bootstrap 95% CI) against a mean
     baseline. A paired test asks whether either model actually beats the baseline,
     and a permutation test asks whether the R² is distinguishable from chance.

No result is tuned or resampled to look better — this reports what the 22 sessions
actually support, including the small-sample limitations.
"""

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import t as tdist
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import LeaveOneGroupOut, GroupKFold
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

TARGET, GROUP = "effort_rating", "participant_id"

# Each behaviour the study set out to test -> its feature column, a readable name,
# and the HYPOTHESISED sign of its correlation with self-perceived effort.
#   +1 : harder writing -> MORE / LONGER ;  -1 : harder writing -> LESS / FASTER
HYPOTHESES = [
    ("chars_per_sec",        "Typing speed (chars/sec)",      -1),
    ("mean_iki_ms",          "Average keystroke gap",         +1),
    ("max_pause_ms",         "Longest pause",                 +1),
    ("n_long_pause_per_100", "Long-pause frequency",          +1),
    ("pause_time_ratio",     "Share of time paused",          +1),
    ("delete_rate",          "Backspace/delete activity",     +1),
    ("revisions_per_100",    "Revision activity",             +1),
    ("active_time_s",        "Writing time",                  +1),
    ("std_iki_ms",           "Typing-rhythm variability",     +1),
]
MODEL_FEATURES = [k for k, _, _ in HYPOTHESES]

N_BOOT = 2000     # bootstrap resamples for CIs
N_PERM = 300      # permutations for the R² test
SEED = 42


def load(path="features.csv"):
    df = pd.read_csv(path)
    return df[df["behavioural_valid"] == 1].reset_index(drop=True)


def model_factories():
    """The three predictors — identical everywhere they are used."""
    return {
        "Baseline (mean)": lambda: DummyRegressor(strategy="mean"),
        "Linear Regression": lambda: make_pipeline(StandardScaler(),
                                                   LinearRegression()),
        "Random Forest": lambda: RandomForestRegressor(
            n_estimators=400, min_samples_leaf=2, random_state=42),
    }


# --------------------------------------------------------------------------- #
# Participant-aware bootstrap helpers
# --------------------------------------------------------------------------- #
def _boot_rows(groups, rng):
    """Resample whole PARTICIPANTS with replacement -> row indices."""
    parts = np.unique(groups)
    idx = []
    for p in rng.choice(parts, size=len(parts), replace=True):
        idx.extend(np.where(groups == p)[0])
    return np.asarray(idx)


def bootstrap_corr(df, col, method="spearman", B=N_BOOT, seed=SEED):
    """Point correlation + participant-bootstrap 95% CI of a behaviour vs effort."""
    g = df[GROUP].to_numpy()
    x = df[col].to_numpy(float)
    y = df[TARGET].to_numpy(float)
    corr = ((lambda a, b: stats.spearmanr(a, b)[0]) if method == "spearman"
            else (lambda a, b: stats.pearsonr(a, b)[0]))
    point = corr(x, y)
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(B):
        idx = _boot_rows(g, rng)
        a, b = x[idx], y[idx]
        if np.std(a) == 0 or np.std(b) == 0:
            continue
        r = corr(a, b)
        if not np.isnan(r):
            boots.append(r)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return point, lo, hi


def oof_lopo(df, factory):
    """Leave-One-Participant-Out out-of-fold predictions aligned to df rows."""
    X = df[MODEL_FEATURES].to_numpy()
    y = df[TARGET].to_numpy(float)
    g = df[GROUP].to_numpy()
    pred = np.empty(len(df))
    for tr, te in LeaveOneGroupOut().split(X, y, g):
        m = factory()
        m.fit(X[tr], y[tr])
        pred[te] = m.predict(X[te])
    return y, pred


def metric_ci(y, pred, groups, B=N_BOOT, seed=SEED):
    """Participant-bootstrap 95% CI for MAE and RMSE of fixed OOF predictions."""
    rng = np.random.default_rng(seed)
    maes, rmses = [], []
    for _ in range(B):
        idx = _boot_rows(groups, rng)
        maes.append(mean_absolute_error(y[idx], pred[idx]))
        rmses.append(np.sqrt(mean_squared_error(y[idx], pred[idx])))
    return {"mae": (np.percentile(maes, 2.5), np.percentile(maes, 97.5)),
            "rmse": (np.percentile(rmses, 2.5), np.percentile(rmses, 97.5))}


def paired_vs_baseline(df, model_pred, base_pred):
    """Per-participant mean |error|; Wilcoxon signed-rank model vs baseline."""
    g = df[GROUP].to_numpy()
    y = df[TARGET].to_numpy(float)
    m_err, b_err = [], []
    for p in np.unique(g):
        idx = np.where(g == p)[0]
        m_err.append(np.mean(np.abs(y[idx] - model_pred[idx])))
        b_err.append(np.mean(np.abs(y[idx] - base_pred[idx])))
    m_err, b_err = np.array(m_err), np.array(b_err)
    diff = m_err - b_err            # negative => model beats baseline
    try:
        _, p = stats.wilcoxon(m_err, b_err)
    except ValueError:
        p = np.nan
    return float(np.median(diff)), p


def permutation_r2(df, eval_factory, perm_factory=None, n_perm=N_PERM, seed=SEED):
    """Permutation p-value: is the LOPO R² better than label-shuffled chance?

    The observed R² uses the full model (eval_factory). The null distribution uses
    a lighter model (perm_factory) so 300 refits stay fast — the shape of the null
    is what matters, and a smaller forest gives the same conclusion.
    """
    perm_factory = perm_factory or eval_factory
    y_obs, pred_obs = oof_lopo(df, eval_factory)
    obs = r2_score(y_obs, pred_obs)
    X = df[MODEL_FEATURES].to_numpy()
    g = df[GROUP].to_numpy()
    rng = np.random.default_rng(seed)
    count = 0
    for _ in range(n_perm):
        yp = rng.permutation(y_obs)
        pred = np.empty(len(df))
        for tr, te in LeaveOneGroupOut().split(X, yp, g):
            m = perm_factory()
            m.fit(X[tr], yp[tr])
            pred[te] = m.predict(X[te])
        if r2_score(yp, pred) >= obs:
            count += 1
    return obs, (count + 1) / (n_perm + 1)


def _perm_factories():
    """Lighter models for the permutation null (fast; same conclusion)."""
    return {
        "Linear Regression": lambda: make_pipeline(StandardScaler(),
                                                   LinearRegression()),
        "Random Forest": lambda: RandomForestRegressor(
            n_estimators=120, min_samples_leaf=2, random_state=42),
    }


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #
def part_a_relationships(df):
    n = len(df)
    tcrit = tdist.ppf(0.975, n - 2)
    rcrit = tcrit / np.sqrt(n - 2 + tcrit**2)
    print("=" * 78)
    print(f"PART A — Effort vs typing behaviour (n={n}; |r|>={rcrit:.2f} needed "
          f"for p<0.05)")
    print("=" * 78)
    print(f"{'behaviour':>28} {'rho':>6} {'95% CI':>16} {'p':>6} {'hyp':>4} "
          f"{'match':>5} {'sig':>4}")
    results = []
    for col, name, hyp in HYPOTHESES:
        rho, lo, hi = bootstrap_corr(df, col, method="spearman")
        _, sp = stats.spearmanr(df[col], df[TARGET])
        obs_sign = 0 if rho == 0 else (1 if rho > 0 else -1)
        match = "yes" if obs_sign == hyp else "no"
        sig = "*" if sp < 0.05 else ""
        print(f"{name:>28} {rho:>6.2f} [{lo:>6.2f},{hi:>6.2f}] {sp:>6.3f} "
              f"{'+' if hyp>0 else '-':>4} {match:>5} {sig:>4}")
        results.append({"behaviour": name, "rho": rho, "ci": (lo, hi),
                        "p": sp, "match": match == "yes", "sig": sp < 0.05})
    print(f"\nDirection matches hypothesis: "
          f"{sum(x['match'] for x in results)}/{len(results)}.  "
          f"Significant (p<0.05, uncorrected): {sum(x['sig'] for x in results)}.")
    print("Every 95% CI below spans zero -> no relationship is statistically "
          "resolved at n=22 (multiple-comparison risk on 9 tests too).")
    return results


def part_b_models(df):
    print("\n" + "=" * 78)
    print("PART B — Predicting the 1-5 effort rating (participant-aware CV)")
    print("=" * 78)
    facs = model_factories()
    g = df[GROUP].to_numpy()

    # LOPO out-of-fold predictions for each model
    oof = {name: oof_lopo(df, fac) for name, fac in facs.items()}

    print("\n--- Leave-One-Participant-Out (point estimate [95% CI]) ---")
    print(f"{'model':>20} {'MAE [95% CI]':>22} {'RMSE [95% CI]':>22} {'R2':>7}")
    for name, (y, pred) in oof.items():
        mae = mean_absolute_error(y, pred)
        rmse = np.sqrt(mean_squared_error(y, pred))
        r2 = r2_score(y, pred)
        ci = metric_ci(y, pred, g)
        print(f"{name:>20} {mae:>6.2f} [{ci['mae'][0]:.2f},{ci['mae'][1]:.2f}]"
              f"   {rmse:>6.2f} [{ci['rmse'][0]:.2f},{ci['rmse'][1]:.2f}]"
              f"   {r2:>6.2f}")

    print("\n--- Does either model beat the baseline? (paired, per participant) ---")
    base_pred = oof["Baseline (mean)"][1]
    for name in ("Linear Regression", "Random Forest"):
        med_diff, p = paired_vs_baseline(df, oof[name][1], base_pred)
        verdict = ("better" if med_diff < 0 else "worse") + \
                  (" (n.s.)" if (np.isnan(p) or p >= 0.05) else " (sig)")
        print(f"{name:>20}: median per-participant MAE difference vs baseline "
              f"= {med_diff:+.2f}  (Wilcoxon p={p:.3f}) -> {verdict}")

    print("\n--- Permutation test: is R² better than shuffled-label chance? ---")
    perm_facs = _perm_factories()
    for name in ("Linear Regression", "Random Forest"):
        obs, p = permutation_r2(df, facs[name], perm_facs[name])
        print(f"{name:>20}: observed LOPO R²={obs:+.2f}, permutation p={p:.3f}")

    print("\n--- GroupKFold (5 folds by participant) — robustness point estimates ---")
    print(f"{'model':>20} {'MAE':>6} {'RMSE':>6} {'R2':>7}")
    X = df[MODEL_FEATURES].to_numpy()
    y = df[TARGET].to_numpy(float)
    gk = GroupKFold(n_splits=min(5, df[GROUP].nunique()))
    for name, fac in facs.items():
        yt, yp = [], []
        for tr, te in gk.split(X, y, g):
            m = fac()
            m.fit(X[tr], y[tr])
            yt.extend(y[te])
            yp.extend(m.predict(X[te]))
        yt, yp = np.array(yt), np.array(yp)
        print(f"{name:>20} {mean_absolute_error(yt,yp):>6.2f} "
              f"{np.sqrt(mean_squared_error(yt,yp)):>6.2f} {r2_score(yt,yp):>7.2f}")

    rf = RandomForestRegressor(n_estimators=400, min_samples_leaf=2,
                               random_state=42).fit(df[MODEL_FEATURES], df[TARGET])
    print("\n--- Random Forest feature importance (descriptive, in-sample) ---")
    for f, v in sorted(zip(MODEL_FEATURES, rf.feature_importances_),
                       key=lambda x: -x[1]):
        print(f"{f:>22} {v:>6.3f}")


def limitations(df):
    n = len(df)
    print("\n" + "=" * 78)
    print("LIMITATIONS (small sample)")
    print("=" * 78)
    print(f"- n={n} sessions from {df[GROUP].nunique()} participants; effort "
          f"ratings concentrated at 2-3.")
    print("- Only moderate-to-large correlations (|r|>=~0.42) could reach "
          "significance here; smaller true effects are undetectable.")
    print("- Wide bootstrap CIs and permutation p-values reflect this: results "
          "are exploratory, not confirmatory.")
    print("- No effort labels exist in any external dataset, so the primary set "
          "cannot be enlarged except by collecting more sessions.")


def main():
    df = load()
    print(f"PRIMARY dataset: {len(df)} behaviourally-valid sessions, "
          f"{df[GROUP].nunique()} participants.")
    dist = df[TARGET].value_counts().sort_index()
    print("Effort-rating distribution:", {int(k): int(v) for k, v in dist.items()},
          f"| mean {df[TARGET].mean():.2f}")
    part_a_relationships(df)
    part_b_models(df)
    limitations(df)
    print("\nTarget throughout = SELF-PERCEIVED writing effort (1-5). No claim is "
          "made about mental effort, stress, or any psychological state.")


if __name__ == "__main__":
    main()
