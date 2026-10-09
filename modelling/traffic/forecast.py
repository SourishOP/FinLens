"""Module 3: User-traffic forecasting on GA4 data (REAL from our own app).

Forecasts daily sessions from raw.ga4_sessions (GA4 export, or simulated via
bigquery/ga4_ingest.py). Prophet is the right tool here — unlike daily stock
prices, web/app traffic has strong weekly seasonality (weekend dips), exactly
what Prophet models well. This is the mirror image of the stock bake-off finding.

Run:
    python -m modelling.traffic.forecast
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from bigquery.warehouse import get_warehouse
from modelling.common.metrics import regression_report


def load_daily_sessions() -> pd.Series:
    wh = get_warehouse()
    df = wh.query("SELECT session_date, sessions FROM hsbc_raw.ga4_sessions")
    if df.empty:
        raise RuntimeError("No GA4 data. Run: python -m bigquery.ga4_ingest")
    daily = (df.groupby("session_date")["sessions"].sum()
             .rename_axis("ds").rename("y"))
    daily.index = pd.to_datetime(daily.index)
    return daily.sort_index()


def forecast(horizon: int = 14, test_size: int = 14) -> dict:
    s = load_daily_sessions()
    train, test = s.iloc[:-test_size], s.iloc[-test_size:]

    results = {}
    # Prophet (primary)
    try:
        from prophet import Prophet
        dfp = pd.DataFrame({"ds": train.index, "y": train.values})
        m = Prophet(daily_seasonality=False, weekly_seasonality=True,
                    yearly_seasonality=False)
        m.fit(dfp)
        fc = m.predict(m.make_future_dataframe(periods=test_size, freq="D"))
        preds = fc["yhat"].to_numpy()[-test_size:]
        results["prophet"] = {"metrics": regression_report(test.values, preds),
                              "predictions": preds.round(0).tolist()}
    except Exception as exc:
        results["prophet"] = {"error": str(exc)}

    # Seasonal-naive baseline (last week repeated)
    base = train.values[-7:]
    snaive = np.array([base[i % 7] for i in range(test_size)])
    results["seasonal_naive"] = {
        "metrics": regression_report(test.values, snaive),
        "predictions": snaive.round(0).tolist()}

    # Forward forecast with Prophet on all data
    forward = None
    try:
        from prophet import Prophet
        dfp = pd.DataFrame({"ds": s.index, "y": s.values})
        m = Prophet(daily_seasonality=False, weekly_seasonality=True,
                    yearly_seasonality=False)
        m.fit(dfp)
        fc = m.predict(m.make_future_dataframe(periods=horizon, freq="D"))
        tail = fc[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(horizon)
        forward = [{"date": r.ds.strftime("%Y-%m-%d"),
                    "sessions": round(r.yhat), "lower": round(r.yhat_lower),
                    "upper": round(r.yhat_upper)} for r in tail.itertuples()]
    except Exception:
        pass

    return {"module": "traffic", "n_days": int(len(s)),
            "test_size": test_size, "actual": test.values.tolist(),
            "results": results, "forward": forward}


if __name__ == "__main__":
    r = forecast()
    print(f"=== Traffic forecast (GA4, {r['n_days']} days) ===")
    for name, res in r["results"].items():
        if "metrics" in res:
            print(f"{name:<16} MAPE={res['metrics']['MAPE']:.2f}%  "
                  f"RMSE={res['metrics']['RMSE']:.0f}")
    if r["forward"]:
        print("\nNext 14 days (Prophet, with interval):")
        for row in r["forward"][:7]:
            print(f"  {row['date']}: {row['sessions']} "
                  f"[{row['lower']}-{row['upper']}]")
