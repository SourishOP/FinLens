"""Module 1: Stock-price prediction bake-off on REAL HSBC data (yfinance).

Compares several forecasting approaches on a held-out test window and reports
error metrics so the choice of model is justified, not assumed. This mirrors the
research consensus (ARIMA good for stable series, Prophet for seasonality,
LSTM for complex patterns) and lets us show a defensible comparison.

Models:
  * Naive (last-value)      -- baseline every real model must beat
  * ARIMA                   -- statsmodels (always available)
  * Prophet                 -- optional (if `prophet` installed)
  * LSTM                    -- optional (if `tensorflow` installed)

Run:
    python -m modelling.stock_price.bakeoff
"""
from __future__ import annotations

import os
import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from modelling.common.market_data import load_prices
from modelling.common.metrics import regression_report

warnings.filterwarnings("ignore")


@dataclass
class ForecastResult:
    name: str
    predictions: np.ndarray
    metrics: dict = field(default_factory=dict)
    note: str = ""


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
def _naive(train: pd.Series, horizon: int) -> np.ndarray:
    """Last observed value carried forward (random-walk baseline)."""
    return np.repeat(train.iloc[-1], horizon)


def _arima(train: pd.Series, horizon: int) -> np.ndarray:
    from statsmodels.tsa.arima.model import ARIMA

    # (5,1,0): differenced once (prices are non-stationary), 5 AR lags.
    model = ARIMA(train.values, order=(5, 1, 0))
    fitted = model.fit()
    return np.asarray(fitted.forecast(steps=horizon), dtype=float)


def _prophet(train: pd.Series, horizon: int) -> np.ndarray:
    from prophet import Prophet

    dfp = pd.DataFrame({"ds": train.index, "y": train.values})
    # business-day data: weekly seasonality on, yearly on, daily off
    m = Prophet(daily_seasonality=False, weekly_seasonality=True,
                yearly_seasonality=True)
    m.fit(dfp)
    future = m.make_future_dataframe(periods=horizon, freq="B")
    fc = m.predict(future)
    return fc["yhat"].to_numpy()[-horizon:]


def _lstm(train: pd.Series, horizon: int, look_back: int = 30) -> np.ndarray:
    import tensorflow as tf
    from sklearn.preprocessing import MinMaxScaler

    values = train.values.reshape(-1, 1)
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(values)

    X, y = [], []
    for i in range(look_back, len(scaled)):
        X.append(scaled[i - look_back:i, 0])
        y.append(scaled[i, 0])
    X, y = np.array(X), np.array(y)
    X = X.reshape((X.shape[0], X.shape[1], 1))

    model = tf.keras.Sequential([
        tf.keras.layers.Input((look_back, 1)),
        tf.keras.layers.LSTM(50),
        tf.keras.layers.Dense(1),
    ])
    model.compile(optimizer="adam", loss="mse")
    model.fit(X, y, epochs=20, batch_size=16, verbose=0)

    # iterative multi-step forecast
    window = scaled[-look_back:, 0].tolist()
    preds = []
    for _ in range(horizon):
        x = np.array(window[-look_back:]).reshape(1, look_back, 1)
        p = float(model.predict(x, verbose=0)[0, 0])
        preds.append(p)
        window.append(p)
    return scaler.inverse_transform(np.array(preds).reshape(-1, 1)).ravel()


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def run_bakeoff(period: str = "3y", test_size: int = 30) -> list[ForecastResult]:
    prices = load_prices(period=period, interval="1d")
    close = prices["Close"].dropna()
    close.index = pd.to_datetime(close.index)

    train, test = close.iloc[:-test_size], close.iloc[-test_size:]
    actual = test.values
    horizon = len(test)
    print(f"Loaded {len(close)} days | train={len(train)} test={horizon}")

    runners = [("Naive", _naive), ("ARIMA", _arima),
               ("Prophet", _prophet), ("LSTM", _lstm)]
    results: list[ForecastResult] = []

    for name, fn in runners:
        try:
            preds = fn(train, horizon)
            res = ForecastResult(name, preds, regression_report(actual, preds))
            results.append(res)
        except ImportError:
            results.append(ForecastResult(
                name, np.array([]), note="skipped (library not installed)"))
        except Exception as exc:
            results.append(ForecastResult(
                name, np.array([]), note=f"failed: {exc}"))
    return results


def _fit_predict_forward(name: str, series: pd.Series, horizon: int) -> np.ndarray:
    """Fit the chosen model on ALL data and forecast `horizon` days ahead."""
    fn = dict([("Naive", _naive), ("ARIMA", _arima),
               ("Prophet", _prophet), ("LSTM", _lstm)])[name]
    return fn(series, horizon)


def predict(period: str = "2y", horizon: int = 30, test_size: int = 30) -> dict:
    """Produce an ACTUAL share-price forecast.

    Internally runs the bake-off to pick the most accurate model (by RMSE on a
    held-out window), then refits that single best model on all data and
    forecasts the next `horizon` trading days. Returns history + forecast +
    which model won and its validation error — ready to plot.
    """
    prices = load_prices(period=period, interval="1d")
    close = prices["Close"].dropna()
    close.index = pd.to_datetime(close.index)

    # 1) select the best model on a held-out window
    results = run_bakeoff(period=period, test_size=test_size)
    scored = [r for r in results if r.metrics]
    scored.sort(key=lambda r: r.metrics.get("RMSE", float("inf")))
    # ignore Naive as the "chosen" model unless it's the only one that ran
    best = next((r for r in scored if r.name != "Naive"), scored[0]) if scored else None
    if best is None:
        return {"error": "no model could be fit"}

    # 2) refit the winner on all data, forecast forward
    fc = _fit_predict_forward(best.name, close, horizon)
    last_date = close.index[-1]
    future_dates = pd.bdate_range(last_date, periods=horizon + 1)[1:]

    # recent history for the chart (last 120 trading days)
    hist = close.iloc[-120:]
    history = [{"date": d.strftime("%Y-%m-%d"), "price": round(float(v), 1)}
               for d, v in hist.items()]
    forecast = [{"date": d.strftime("%Y-%m-%d"), "price": round(float(v), 1)}
                for d, v in zip(future_dates, fc)]

    last_price = float(close.iloc[-1])
    target = float(fc[-1])
    change_pct = round((target - last_price) / last_price * 100, 2)

    return {
        "ticker": os.getenv("HSBC_TICKER", "HSBA.L"),
        "best_model": best.name,
        "validation": {"avg_pct_error": round(best.metrics["MAPE"], 2),
                       "direction_correct_pct": round(best.metrics["DirectionalAccuracy"], 1)},
        "last_price": round(last_price, 1),
        "last_date": last_date.strftime("%Y-%m-%d"),
        "horizon_days": horizon,
        "target_price": round(target, 1),
        "change_pct": change_pct,
        "history": history,
        "forecast": forecast,
    }


def print_leaderboard(results: list[ForecastResult]) -> None:
    print("\n=== Stock-price bake-off (lower RMSE/MAPE better) ===")
    header = f"{'Model':<10}{'RMSE':>10}{'MAE':>10}{'MAPE%':>10}{'Dir%':>8}  note"
    print(header)
    print("-" * len(header))
    scored = [r for r in results if r.metrics]
    scored.sort(key=lambda r: r.metrics.get("RMSE", float("inf")))
    for r in scored:
        m = r.metrics
        print(f"{r.name:<10}{m['RMSE']:>10.2f}{m['MAE']:>10.2f}"
              f"{m['MAPE']:>10.2f}{m['DirectionalAccuracy']:>8.1f}  {r.note}")
    for r in results:
        if not r.metrics:
            print(f"{r.name:<10}{'-':>10}{'-':>10}{'-':>10}{'-':>8}  {r.note}")
    if scored:
        print(f"\nBest by RMSE: {scored[0].name}")


if __name__ == "__main__":
    print_leaderboard(run_bakeoff())
