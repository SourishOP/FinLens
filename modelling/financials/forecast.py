"""Module 2: Financials forecasting on REAL HSBC Data Pack series.

Forecasts headline group metrics (e.g. net operating income / "revenue", PBT) from
the quarterly series extracted by parsers/datapack_parser.py.

IMPORTANT modelling judgement (interview-defensible):
  We have only ~8 quarterly observations. With a sample this small, deep models
  (LSTM) and even heavily-parameterised SARIMA will overfit. The correct, honest
  choices are:
    * a Naive/seasonal-naive baseline,
    * a simple linear trend (OLS on time),
    * Holt's linear exponential smoothing,
  and we report uncertainty, not a false-precision point forecast. We state this
  limitation openly rather than dress up a fragile model.

When more history is available (add more packs to the scraper registry), SARIMA
with (p,d,q)(P,D,Q,4) can be enabled via `method='sarima'`.

Run:
    python -m modelling.financials.forecast
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from modelling.common.metrics import regression_report

_ROOT = Path(__file__).resolve().parents[2]
SERIES_CSV = _ROOT / "data" / "financials" / "group_income_statement_long.csv"


def load_series(metric: str = "net_operating_income") -> pd.Series:
    if not SERIES_CSV.exists():
        raise FileNotFoundError(
            f"{SERIES_CSV} not found. Run the scraper + parser first "
            "(python -m scrapers.hsbc_financials_scraper; "
            "python -m parsers.datapack_parser).")
    df = pd.read_csv(SERIES_CSV)
    s = (df[df["metric"] == metric]
         .assign(period_end=lambda d: pd.to_datetime(d["period_end"]))
         .sort_values("period_end")
         .set_index("period_end")["value_m"])
    s.name = metric
    return s


# ---------------------------------------------------------------------------
# Lightweight, small-sample-appropriate forecasters
# ---------------------------------------------------------------------------
def _seasonal_naive(train: pd.Series, horizon: int, season: int = 4) -> np.ndarray:
    """Repeat the value from one year (4 quarters) ago; fall back to last value."""
    if len(train) >= season:
        base = train.values[-season:]
        return np.array([base[i % season] for i in range(horizon)])
    return np.repeat(train.values[-1], horizon)


def _linear_trend(train: pd.Series, horizon: int) -> np.ndarray:
    t = np.arange(len(train))
    coeffs = np.polyfit(t, train.values, 1)
    future_t = np.arange(len(train), len(train) + horizon)
    return np.polyval(coeffs, future_t)


def _holt(train: pd.Series, horizon: int) -> np.ndarray:
    from statsmodels.tsa.holtwinters import Holt
    model = Holt(train.values, initialization_method="estimated").fit()
    return np.asarray(model.forecast(horizon), dtype=float)


def _sarima(train: pd.Series, horizon: int) -> np.ndarray:
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    model = SARIMAX(train.values, order=(1, 1, 0),
                    seasonal_order=(0, 1, 0, 4),
                    enforce_stationarity=False,
                    enforce_invertibility=False).fit(disp=False)
    return np.asarray(model.forecast(horizon), dtype=float)


METHODS = {
    "seasonal_naive": _seasonal_naive,
    "linear_trend": _linear_trend,
    "holt": _holt,
    "sarima": _sarima,
}


def backtest(metric: str = "net_operating_income", test_size: int = 2) -> dict:
    """Hold out the last `test_size` quarters; compare methods."""
    series = load_series(metric)
    if len(series) <= test_size + 2:
        test_size = 1  # keep at least a couple of training points
    train, test = series.iloc[:-test_size], series.iloc[-test_size:]

    scored = {}
    for name, fn in METHODS.items():
        try:
            preds = fn(train, len(test))
            scored[name] = {"metrics": regression_report(test.values, preds),
                            "predictions": preds.tolist()}
        except Exception as exc:
            scored[name] = {"error": str(exc)}
    return {"metric": metric, "n_obs": int(len(series)),
            "train": int(len(train)), "test": int(len(test)),
            "test_periods": [d.strftime("%Y-%m-%d") for d in test.index],
            "actual": test.values.tolist(), "results": scored}


def forecast_forward(metric: str = "net_operating_income",
                     horizon: int = 4, method: str = "holt") -> pd.DataFrame:
    """Forecast the next `horizon` quarters using the chosen method on all data."""
    series = load_series(metric)
    preds = METHODS[method](series, horizon)
    last = series.index[-1]
    future_idx = pd.date_range(last, periods=horizon + 1, freq="QE")[1:]
    return pd.DataFrame({"period_end": future_idx,
                         "metric": metric, "method": method,
                         "forecast_m": preds})


if __name__ == "__main__":
    for metric in ["net_operating_income", "profit_before_tax"]:
        bt = backtest(metric)
        print(f"\n=== {metric}  (n={bt['n_obs']}, test={bt['test']} "
              f"quarters: {bt['test_periods']}) ===")
        print(f"actual: {[round(a) for a in bt['actual']]}")
        rows = [(n, r['metrics']['MAPE']) for n, r in bt['results'].items()
                if 'metrics' in r]
        rows.sort(key=lambda x: (np.isnan(x[1]), x[1]))
        for name, mape in rows:
            preds = [round(p) for p in bt['results'][name]['predictions']]
            print(f"  {name:<16} MAPE={mape:6.2f}%  preds={preds}")
        best = rows[0][0] if rows else "holt"
        fwd = forecast_forward(metric, horizon=4, method=best)
        print(f"  -> next 4Q forecast ({best}):")
        for _, r in fwd.iterrows():
            print(f"       {r['period_end'].strftime('%Y-%m-%d')}: "
                  f"{r['forecast_m']:,.0f} $m")
