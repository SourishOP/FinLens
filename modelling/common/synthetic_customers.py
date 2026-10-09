"""Generate a realistic SIMULATED retail-banking customer dataset.

CLEARLY LABELLED SIMULATED DATA. HSBC's real per-customer data is confidential;
this mirrors the structure of the public "Bank Customer Churn" benchmark
(ChurnModelling.csv) used in the research, so the churn/acquisition methodology is
validated on data of the right shape and ready to point at real data later.

Churn and acquisition labels are generated from a transparent logistic process so
the models have genuine (not random) signal to learn, and so feature importance is
interpretable and defensible.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def make_customers(n: int = 10_000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    credit_score = rng.normal(650, 95, n).clip(350, 850)
    age = rng.normal(39, 11, n).clip(18, 92).round()
    tenure_years = rng.integers(0, 11, n)
    balance = np.where(rng.random(n) < 0.25, 0.0,
                       rng.normal(78_000, 55_000, n).clip(0, 260_000))
    num_products = rng.integers(1, 5, n)
    has_credit_card = rng.integers(0, 2, n)
    is_active_member = rng.integers(0, 2, n)
    estimated_salary = rng.normal(100_000, 50_000, n).clip(10_000, 220_000)
    txns_last_year = rng.poisson(45, n) + (is_active_member * rng.poisson(30, n))
    txn_value_last_year = (txns_last_year * rng.normal(220, 60, n)).clip(0)
    complaints_last_year = rng.poisson(0.3, n)
    geography = rng.choice(["Hong Kong", "UK", "UAE", "Singapore"], n,
                           p=[0.4, 0.35, 0.1, 0.15])
    gender = rng.choice(["F", "M"], n)

    df = pd.DataFrame({
        "credit_score": credit_score.round(),
        "geography": geography,
        "gender": gender,
        "age": age,
        "tenure_years": tenure_years,
        "balance": balance.round(2),
        "num_products": num_products,
        "has_credit_card": has_credit_card,
        "is_active_member": is_active_member,
        "estimated_salary": estimated_salary.round(2),
        "txns_last_year": txns_last_year,
        "txn_value_last_year": txn_value_last_year.round(2),
        "complaints_last_year": complaints_last_year,
    })

    # ---- Churn label: transparent logistic process -------------------------
    # Drivers (matching the research): low activity, few products, complaints,
    # older age, and (classic benchmark quirk) higher balance churns more.
    z = (-1.6
         - 1.3 * df["is_active_member"]
         - 0.45 * (df["num_products"] - 1)
         + 0.8 * (df["complaints_last_year"] > 0)
         + 0.015 * (df["age"] - 39)
         + 0.0000035 * (df["balance"] - 78_000)
         - 0.004 * (df["txns_last_year"] - 60)
         + rng.normal(0, 0.5, n))
    churn_prob = 1 / (1 + np.exp(-z))
    df["churned"] = (rng.random(n) < churn_prob).astype(int)

    # ---- Acquisition label: propensity to OPEN an additional product -------
    # Drivers: active, higher salary, more transactions, younger, has card.
    za = (-1.9
          + 1.0 * df["is_active_member"]
          + 0.0000075 * (df["estimated_salary"] - 100_000)
          + 0.006 * (df["txns_last_year"] - 60)
          - 0.012 * (df["age"] - 39)
          + 0.5 * df["has_credit_card"]
          + rng.normal(0, 0.5, n))
    acq_prob = 1 / (1 + np.exp(-za))
    df["opened_new_product"] = (rng.random(n) < acq_prob).astype(int)

    return df


if __name__ == "__main__":
    d = make_customers()
    print(d.head())
    print(f"\nrows: {len(d)}")
    print(f"churn rate:       {d['churned'].mean():.1%}")
    print(f"acquisition rate: {d['opened_new_product'].mean():.1%}")
