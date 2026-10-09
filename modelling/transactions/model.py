"""Module 4: Transaction analytics on GA4 data (REAL from our own app).

Two parts:
  (1) Volume forecast — daily completed-transaction count (Prophet).
  (2) Conversion analysis — completion rate (transactions / sessions) by
      platform and geography, i.e. which channel converts best. This mirrors
      real digital-banking funnel analytics.

Data: raw.ga4_sessions (from bigquery/ga4_ingest.py).

Run:
    python -m modelling.transactions.model
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from bigquery.warehouse import get_warehouse
from modelling.common.metrics import regression_report


def _load() -> pd.DataFrame:
    wh = get_warehouse()
    df = wh.query("SELECT * FROM hsbc_raw.ga4_sessions")
    if df.empty:
        raise RuntimeError("No GA4 data. Run: python -m bigquery.ga4_ingest")
    return df


def conversion_by_channel() -> pd.DataFrame:
    df = _load()
    g = (df.groupby("platform")
         .agg(sessions=("sessions", "sum"),
              transactions=("transactions", "sum"),
              txn_value=("txn_value", "sum")).reset_index())
    g["conversion_rate"] = (g["transactions"] / g["sessions"]).round(3)
    g["avg_txn_value"] = (g["txn_value"] / g["transactions"]).round(2)
    return g


def conversion_by_geo() -> pd.DataFrame:
    df = _load()
    g = (df.groupby("geo")
         .agg(sessions=("sessions", "sum"),
              transactions=("transactions", "sum")).reset_index())
    g["conversion_rate"] = (g["transactions"] / g["sessions"]).round(3)
    return g.sort_values("conversion_rate", ascending=False)


def volume_forecast(horizon: int = 14, test_size: int = 14) -> dict:
    df = _load()
    daily = (df.groupby("session_date")["transactions"].sum())
    daily.index = pd.to_datetime(daily.index)
    daily = daily.sort_index()
    train, test = daily.iloc[:-test_size], daily.iloc[-test_size:]

    out = {}
    try:
        from prophet import Prophet
        dfp = pd.DataFrame({"ds": train.index, "y": train.values})
        m = Prophet(weekly_seasonality=True, daily_seasonality=False,
                    yearly_seasonality=False)
        m.fit(dfp)
        fc = m.predict(m.make_future_dataframe(periods=test_size, freq="D"))
        preds = fc["yhat"].to_numpy()[-test_size:]
        out["prophet"] = regression_report(test.values, preds)
    except Exception as exc:
        out["prophet"] = {"error": str(exc)}

    base = train.values[-7:]
    snaive = np.array([base[i % 7] for i in range(test_size)])
    out["seasonal_naive"] = regression_report(test.values, snaive)
    return {"n_days": int(len(daily)), "metrics": out}


if __name__ == "__main__":
    print("=== Transaction conversion by channel (GA4) ===")
    print(conversion_by_channel().to_string(index=False))
    print("\n=== Conversion by geography ===")
    print(conversion_by_geo().to_string(index=False))
    print("\n=== Transaction volume forecast backtest ===")
    vf = volume_forecast()
    for name, m in vf["metrics"].items():
        if "MAPE" in m:
            print(f"  {name:<16} MAPE={m['MAPE']:.2f}%  RMSE={m['RMSE']:.1f}")
