"""Module 7a (credit-risk part): forecast Expected Credit Losses on REAL data.

Uses the ECL series extracted from HSBC Data Packs (parsers/datapack_parser.py).
ECL (loan impairment charges) is the headline credit-risk metric: rising ECL
signals deteriorating credit quality. We forecast upcoming-quarter ECL and flag
whether it is trending up.

Small-sample honesty: as with the financials module, ~8 quarters means we use
simple, transparent methods (trailing average / linear trend / Holt) and report
the trend direction rather than over-precise point values.

Run:
    python -m modelling.risk.credit_risk
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from modelling.financials.forecast import load_series


def ecl_series() -> pd.Series:
    """ECL as a positive magnitude of charge ($m)."""
    s = load_series("expected_credit_losses").abs()
    s.name = "ecl_charge_m"
    return s


def forecast_ecl(horizon: int = 2) -> dict:
    s = ecl_series()
    # Holt linear trend if enough points, else trailing mean.
    try:
        from statsmodels.tsa.holtwinters import Holt
        preds = Holt(s.values, initialization_method="estimated").fit().forecast(horizon)
    except Exception:
        preds = np.repeat(s.values[-4:].mean(), horizon)

    recent, prior = s.values[-4:].mean(), s.values[-8:-4].mean() if len(s) >= 8 else s.values[:-4].mean()
    trend = "rising" if recent > prior else "falling"
    future_idx = pd.date_range(s.index[-1], periods=horizon + 1, freq="QE")[1:]
    return {
        "history": {d.strftime("%Y-%m-%d"): float(v) for d, v in s.items()},
        "forecast": {d.strftime("%Y-%m-%d"): round(float(p), 1)
                     for d, p in zip(future_idx, preds)},
        "recent_4q_avg": round(float(recent), 1),
        "prior_4q_avg": round(float(prior), 1),
        "trend": trend,
    }


if __name__ == "__main__":
    r = forecast_ecl()
    print("=== HSBC credit-risk: Expected Credit Losses forecast (REAL data) ===")
    print("History ($m charge):")
    for d, v in r["history"].items():
        print(f"  {d}: {v:,.0f}")
    print(f"\nTrend: ECL {r['trend']} "
          f"(recent 4Q avg {r['recent_4q_avg']:,} vs prior {r['prior_4q_avg']:,})")
    print("Forecast ($m):")
    for d, v in r["forecast"].items():
        print(f"  {d}: {v:,.0f}")
