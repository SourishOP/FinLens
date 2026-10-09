"""Module 7a (market-risk part): Value-at-Risk & volatility on REAL HSBC stock.

Three industry-standard VaR methods plus a GARCH volatility forecast. All computed
on real HSBC share-price returns from yfinance, so every number is defensible.

Definitions used:
  * Returns     : daily log returns of the adjusted close.
  * VaR (alpha) : the loss threshold such that, with (1-alpha) confidence, the
                  one-day loss will not exceed it. Reported as a POSITIVE number
                  (e.g. VaR 0.021 = a 2.1% one-day loss at the chosen confidence).
  * CVaR / ES   : expected shortfall = average loss *beyond* the VaR threshold.

Run:
    python -m modelling.risk.market_risk
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from modelling.common.market_data import load_prices


@dataclass
class VaRResult:
    method: str
    confidence: float
    var: float          # one-day VaR as a positive fraction of portfolio value
    cvar: float         # expected shortfall (positive fraction)

    def as_pct(self) -> str:
        return (f"{self.method:<16} {int(self.confidence * 100)}%  "
                f"VaR={self.var * 100:6.2f}%  CVaR={self.cvar * 100:6.2f}%")


def log_returns(period: str = "3y") -> pd.Series:
    close = load_prices(period=period, interval="1d")["Close"].dropna()
    rets = np.log(close / close.shift(1)).dropna()
    rets.name = "log_return"
    return rets


def historical_var(returns: pd.Series, confidence: float = 0.95) -> VaRResult:
    """Non-parametric: read VaR straight off the empirical return distribution."""
    q = np.quantile(returns, 1 - confidence)
    tail = returns[returns <= q]
    cvar = -tail.mean() if len(tail) else -q
    return VaRResult("Historical", confidence, var=-q, cvar=float(cvar))


def parametric_var(returns: pd.Series, confidence: float = 0.95) -> VaRResult:
    """Variance-covariance (Gaussian) VaR."""
    mu, sigma = returns.mean(), returns.std()
    z = stats.norm.ppf(1 - confidence)
    var = -(mu + z * sigma)
    # closed-form Gaussian expected shortfall
    es = -(mu - sigma * stats.norm.pdf(z) / (1 - confidence))
    return VaRResult("Parametric", confidence, var=float(var), cvar=float(es))


def monte_carlo_var(returns: pd.Series, confidence: float = 0.95,
                    sims: int = 50_000, seed: int = 42) -> VaRResult:
    """Simulate one-day returns from the fitted normal and read off the quantile."""
    rng = np.random.default_rng(seed)
    sim = rng.normal(returns.mean(), returns.std(), sims)
    q = np.quantile(sim, 1 - confidence)
    cvar = -sim[sim <= q].mean()
    return VaRResult("MonteCarlo", confidence, var=float(-q), cvar=float(cvar))


def garch_volatility_forecast(returns: pd.Series, horizon: int = 5) -> dict:
    """Forecast next-`horizon`-day volatility with a GARCH(1,1) model.

    Returns annualised vols so they're easy to read. Falls back to a rolling-std
    estimate if the `arch` package is unavailable.
    """
    try:
        from arch import arch_model
    except ImportError:
        roll = returns.rolling(21).std().iloc[-1] * np.sqrt(252)
        return {"method": "rolling-std (arch not installed)",
                "annualised_vol": float(roll)}

    # arch prefers percentage returns for numerical stability
    am = arch_model(returns * 100, vol="GARCH", p=1, q=1, mean="constant")
    fitted = am.fit(disp="off")
    fc = fitted.forecast(horizon=horizon, reindex=False)
    daily_var = fc.variance.values[-1]            # variance per day (in %^2)
    daily_vol = np.sqrt(daily_var) / 100.0        # back to fraction
    return {
        "method": "GARCH(1,1)",
        "daily_vol_forecast": [float(v) for v in daily_vol],
        "annualised_vol_next_day": float(daily_vol[0] * np.sqrt(252)),
    }


def full_report(period: str = "3y",
                confidences=(0.95, 0.99)) -> dict:
    rets = log_returns(period=period)
    results = []
    for c in confidences:
        results.append(historical_var(rets, c))
        results.append(parametric_var(rets, c))
        results.append(monte_carlo_var(rets, c))
    return {
        "observations": int(len(rets)),
        "ann_volatility": float(rets.std() * np.sqrt(252)),
        "var_results": results,
        "garch": garch_volatility_forecast(rets),
    }


if __name__ == "__main__":
    rep = full_report()
    print(f"HSBC market-risk report  |  {rep['observations']} daily returns")
    print(f"Annualised volatility: {rep['ann_volatility'] * 100:.1f}%\n")
    print("One-day Value-at-Risk / Expected Shortfall:")
    for r in rep["var_results"]:
        print("  " + r.as_pct())
    g = rep["garch"]
    print(f"\nVolatility forecast ({g['method']}):")
    if "annualised_vol_next_day" in g:
        print(f"  next-day annualised vol: {g['annualised_vol_next_day'] * 100:.1f}%")
    else:
        print(f"  annualised vol: {g['annualised_vol'] * 100:.1f}%")
