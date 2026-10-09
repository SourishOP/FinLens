# Modelling layer — 7 prediction modules

Run everything from the project root with the venv active.

```powershell
.\.venv\Scripts\Activate.ps1
```

## Status

| # | Module | Command | Data | Status |
|---|---|---|---|---|
| 1 | Stock price bake-off | `python -m modelling.stock_price.bakeoff` | yfinance HSBA.L | DONE (REAL) |
| 7a | Market risk (VaR/GARCH) | `python -m modelling.risk.market_risk` | yfinance HSBA.L | DONE (REAL) |
| 2 | Financials forecast | `python -m modelling.financials.forecast` | Data Packs | DONE (REAL) |
| 3 | User traffic | `python -m modelling.traffic.forecast` | GA4 (ingest first) | DONE (REAL/our app) |
| 4 | Transactions | `python -m modelling.transactions.model` | GA4 (ingest first) | DONE (REAL/our app) |
| 5 | Churn | `python -m modelling.churn.train` | benchmark/sim | DONE (SIMULATED) |
| 6 | Acquisition propensity | `python -m modelling.acquisition.train` | benchmark/sim | DONE (SIMULATED) |
| 7a | Credit risk (ECL) | `python -m modelling.risk.credit_risk` | Data Packs | DONE (REAL) |
| 7b | Optimization | `python -m modelling.optimization.capital_allocation` | Data Pack segments | DONE (REAL-shaped) |

## Module 2 — Financials forecast
~8 quarterly points only, so we use small-sample-appropriate methods (seasonal-naive,
linear trend, Holt) and report the backtest honestly. **Seasonal-naive wins** because
HSBC quarters are strongly seasonal (weak Q4, strong Q1) — a trend line can't capture
that on 8 points. Interview point: matching model complexity to data size.

## Module 5 — Churn (SIMULATED data)
LightGBM + isotonic calibration + SHAP + cumulative-gains. Verified: ROC-AUC ~0.71,
top 40% highest-risk captures ~68% of churners (the business framing). SHAP recovers
the true drivers (activity, products, transactions, complaints).

## Module 6 — Acquisition propensity (SIMULATED data)
LogReg baseline + LightGBM, decile lead-scoring table. Top decile converts ~1.8x the
base rate = the priority campaign list (Next-Best-Action framing).

## Module 7a — Credit risk (ECL, REAL data)
Forecasts Expected Credit Losses from the real Data Pack ECL series + trend direction.
Market-risk VaR/GARCH is in `modelling/risk/market_risk.py` (Task 2).

## Module 7b — Optimization (REAL-shaped segment data)
PuLP LP: allocate RWA budget across the 4 segments to maximise return on RWA under
concentration limits. Decision-support on public figures — NOT HSBC internal policy.
Replace `SEGMENTS` with values parsed from a Data Pack segment page for fully-real inputs.
Requires PuLP 2.x (4.0 is an incompatible rewrite).

## Module 1 — Stock-price bake-off

Compares Naive (baseline), ARIMA, Prophet, and LSTM (optional) on a 30-day
held-out window; prints a leaderboard sorted by RMSE.

- **ARIMA / Prophet** work out of the box.
- **LSTM** activates automatically if you `pip install tensorflow`.
- **Interview point:** on daily stock prices ARIMA beats Prophet, because prices
  behave like a near-random-walk, not a seasonal series. Prophet's strength
  (seasonality/holidays) pays off in the *traffic* module instead. Showing you
  know *why* a model wins is the point of the bake-off.

## Module 7a — Market risk

Computes one-day Value-at-Risk and Expected Shortfall (CVaR) three ways
(Historical, Parametric/Gaussian, Monte Carlo) at 95% and 99%, plus a GARCH(1,1)
volatility forecast (falls back to rolling-std if `arch` is missing).

- **Interview point:** the Historical 99% VaR is fatter than the Parametric one —
  real HSBC returns have heavier tails than a normal distribution. That's exactly
  why banks don't rely on Gaussian VaR alone.

## Notes

- Share-price data is cached under `data/cache/` after first fetch, so modules
  still run offline once primed.
- LSTM is intentionally optional: `pip install tensorflow` to enable it.

## Module 3 — Traffic forecast (GA4)
Prophet forecasts daily sessions. **Prophet wins here** (MAPE ~5% vs seasonal-naive
~8.5%) because app/web traffic has strong weekly seasonality — the exact mirror of
the stock bake-off where Prophet lost. First run `python -m bigquery.ga4_ingest`.

## Module 4 — Transactions (GA4)
Daily transaction-volume forecast (Prophet beats naive ~6.6% vs 11.7% MAPE) plus
conversion-rate analysis by channel (mobile vs web) and geography. First run
`python -m bigquery.ga4_ingest`.

---
### Full pipeline
`python run_pipeline.py` runs scrape → parse → models → warehouse → GA4 ingest.
All 9 modules then serve via the App 2 backend `/forecast/{module}`.
