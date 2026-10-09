"""Module 6: Account/product acquisition propensity ("likely to open new product").

SIMULATED DATA (clearly labelled). Research framing: lead-scoring / propensity.
We follow the recommended pattern:
  * Logistic Regression as the interpretable baseline (maps to score percentiles),
  * LightGBM as the stronger model,
  * decile lead-scoring table so a "campaign list" is directly actionable
    (Next-Best-Action: target the highest-propensity customers first).

Run:
    python -m modelling.acquisition.train
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from modelling.common.synthetic_customers import make_customers

_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = _ROOT / "data" / "predictions"

CATEGORICAL = ["geography", "gender"]
TARGET = "opened_new_product"
DROP = ["churned", "opened_new_product"]


def _prepare(df: pd.DataFrame):
    X = pd.get_dummies(df.drop(columns=DROP), columns=CATEGORICAL, drop_first=True)
    return X, df[TARGET].values


def lead_score_table(y_true, proba, bins: int = 10) -> pd.DataFrame:
    order = np.argsort(-proba)
    ys = y_true[order]
    total = ys.sum()
    base_rate = y_true.mean()
    n = len(ys)
    rows = []
    for b in range(1, bins + 1):
        cut = int(n * b / bins)
        decile_slice = ys[int(n * (b - 1) / bins):cut]
        rows.append({
            "decile": b,
            "customers": len(decile_slice),
            "conversion_rate": round(decile_slice.mean(), 3),
            "lift_vs_base": round(decile_slice.mean() / base_rate, 2),
            "cum_pct_of_converters": round(100 * ys[:cut].sum() / total, 1),
        })
    return pd.DataFrame(rows)


def train(seed: int = 42) -> dict:
    import lightgbm as lgb

    df = make_customers(seed=seed)
    X, y = _prepare(df)
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.25, stratify=y, random_state=seed)

    # Interpretable baseline
    logit = make_pipeline(StandardScaler(),
                          LogisticRegression(max_iter=1000, class_weight="balanced"))
    logit.fit(X_tr, y_tr)
    p_logit = logit.predict_proba(X_te)[:, 1]

    # Stronger model
    gbm = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.03, num_leaves=31,
                             subsample=0.8, colsample_bytree=0.8,
                             class_weight="balanced", random_state=seed, verbose=-1)
    gbm.fit(X_tr, y_tr)
    p_gbm = gbm.predict_proba(X_te)[:, 1]

    metrics = {
        "LogReg": {"ROC_AUC": round(roc_auc_score(y_te, p_logit), 4),
                   "PR_AUC": round(average_precision_score(y_te, p_logit), 4)},
        "LightGBM": {"ROC_AUC": round(roc_auc_score(y_te, p_gbm), 4),
                     "PR_AUC": round(average_precision_score(y_te, p_gbm), 4)},
        "base_rate": round(float(y.mean()), 4),
    }

    # Score full population with the better model -> campaign list
    best_model = gbm if metrics["LightGBM"]["ROC_AUC"] >= metrics["LogReg"]["ROC_AUC"] else logit
    full_p = best_model.predict_proba(X)[:, 1]
    scored = df.assign(acquisition_propensity=full_p.round(4))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    scored.sort_values("acquisition_propensity", ascending=False).to_csv(
        OUT_DIR / "acquisition_scored.csv", index=False)

    return {"metrics": metrics,
            "lead_table": lead_score_table(y_te, p_gbm),
            "n": len(df)}


if __name__ == "__main__":
    res = train()
    print(f"=== Acquisition propensity (SIMULATED data, n={res['n']}) ===")
    print(f"base conversion rate: {res['metrics']['base_rate']:.1%}")
    print(f"LogReg (baseline): {res['metrics']['LogReg']}")
    print(f"LightGBM         : {res['metrics']['LightGBM']}")
    print("\nLead-scoring table (decile 1 = highest propensity):")
    print(res["lead_table"].to_string(index=False))
    top = res["lead_table"].iloc[0]
    print(f"\n>> Top decile converts at {top['conversion_rate']:.1%} "
          f"({top['lift_vs_base']}x the base rate) — the priority campaign list.")
    print("Scored population -> data/predictions/acquisition_scored.csv")
