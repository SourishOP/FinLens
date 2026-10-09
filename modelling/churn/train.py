"""Module 5: Customer churn prediction ("potential to leave").

SIMULATED DATA (clearly labelled) — see modelling/common/synthetic_customers.py.
Methodology follows the research consensus for retail-bank churn:
  * LightGBM gradient-boosted trees (research-preferred),
  * leakage-safe train/test split with stratification,
  * probability calibration (isotonic) for trustworthy probabilities,
  * cost-sensitive threshold + cumulative-gains ("top X% captures Y% of churn"),
  * SHAP explainability (regulatory relevance for a bank).

Run:
    python -m modelling.churn.train
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (average_precision_score, brier_score_loss,
                             roc_auc_score)
from sklearn.model_selection import train_test_split

from modelling.common.synthetic_customers import make_customers

_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = _ROOT / "data" / "predictions"

CATEGORICAL = ["geography", "gender"]
TARGET = "churned"
DROP_FOR_FEATURES = ["churned", "opened_new_product"]


def _prepare(df: pd.DataFrame):
    X = df.drop(columns=DROP_FOR_FEATURES)
    X = pd.get_dummies(X, columns=CATEGORICAL, drop_first=True)
    y = df[TARGET].values
    return X, y


def gains_table(y_true: np.ndarray, proba: np.ndarray, bins: int = 10) -> pd.DataFrame:
    """Cumulative gains: sort by predicted risk, see how much churn each decile
    captures. The headline business number comes from here."""
    order = np.argsort(-proba)
    y_sorted = y_true[order]
    total_pos = y_sorted.sum()
    rows = []
    n = len(y_sorted)
    for b in range(1, bins + 1):
        cut = int(n * b / bins)
        captured = y_sorted[:cut].sum()
        rows.append({"top_pct": b * 100 // bins,
                     "customers": cut,
                     "churners_captured": int(captured),
                     "pct_of_all_churn": round(100 * captured / total_pos, 1)})
    return pd.DataFrame(rows)


def train(seed: int = 42) -> dict:
    import lightgbm as lgb

    df = make_customers(seed=seed)
    X, y = _prepare(df)
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.25, stratify=y, random_state=seed)

    base = lgb.LGBMClassifier(
        n_estimators=400, learning_rate=0.03, num_leaves=31,
        subsample=0.8, colsample_bytree=0.8, random_state=seed,
        class_weight="balanced", verbose=-1)
    # Calibrated probabilities (isotonic) via internal CV on the training set.
    model = CalibratedClassifierCV(base, method="isotonic", cv=3)
    model.fit(X_tr, y_tr)

    proba = model.predict_proba(X_te)[:, 1]
    metrics = {
        "ROC_AUC": round(roc_auc_score(y_te, proba), 4),
        "PR_AUC": round(average_precision_score(y_te, proba), 4),
        "Brier": round(brier_score_loss(y_te, proba), 4),
        "churn_rate": round(float(y.mean()), 4),
    }
    gains = gains_table(y_te, proba)

    # Score the full population and persist (feeds App 2 "churn risk list").
    full_proba = model.predict_proba(X)[:, 1]
    scored = df.assign(churn_risk=full_proba.round(4))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    scored.sort_values("churn_risk", ascending=False).to_csv(
        OUT_DIR / "churn_scored.csv", index=False)

    shap_summary = _shap_importance(base, X_tr, X_te)
    return {"metrics": metrics, "gains": gains, "shap": shap_summary,
            "n": len(df), "features": list(X.columns)}


def _shap_importance(base_estimator, X_tr, X_te, top_k: int = 8) -> pd.DataFrame:
    """Mean absolute SHAP value per feature (explainability)."""
    try:
        import shap
        import lightgbm as lgb
        fitted = lgb.LGBMClassifier(**base_estimator.get_params()).fit(
            X_tr, make_customers().loc[X_tr.index, "churned"])
        explainer = shap.TreeExplainer(fitted)
        sv = explainer.shap_values(X_te)
        vals = sv[1] if isinstance(sv, list) else sv
        imp = np.abs(vals).mean(axis=0)
        return (pd.DataFrame({"feature": X_te.columns, "mean_abs_shap": imp})
                .sort_values("mean_abs_shap", ascending=False)
                .head(top_k).reset_index(drop=True))
    except Exception as exc:
        return pd.DataFrame({"note": [f"SHAP skipped: {exc}"]})


if __name__ == "__main__":
    res = train()
    print(f"=== Churn model (SIMULATED data, n={res['n']}) ===")
    print("Metrics:", res["metrics"])
    print("\nCumulative gains (business framing):")
    print(res["gains"].to_string(index=False))
    g = res["gains"]
    row40 = g[g["top_pct"] == 40]
    if not row40.empty:
        print(f"\n>> Targeting the top 40% highest-risk customers captures "
              f"{row40.iloc[0]['pct_of_all_churn']}% of all churners.")
    print("\nTop churn drivers (mean |SHAP|):")
    print(res["shap"].to_string(index=False))
    print(f"\nScored population -> data/predictions/churn_scored.csv")
