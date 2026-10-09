"""Build staging + marts tables from raw, portably across BigQuery and SQLite.

We keep the SQL to the common subset both engines accept (SELECT, JOIN, GROUP BY,
CASE, basic aggregates). Each transform reads from the warehouse via query() and
writes the result back via load_dataframe(), so the exact same code path works in
both modes.
"""
from __future__ import annotations

import pandas as pd


def _ds(wh, layer: str) -> str:
    return wh.cfg.dataset(layer)


def build_staging_financials(wh) -> None:
    """Pivot the long income-statement into a tidy wide staging table."""
    raw = wh.query(f"SELECT * FROM {_ds(wh, 'raw')}.group_income_statement")
    if raw.empty:
        print("[transform] staging_financials: no raw data, skip")
        return
    wide = (raw.pivot_table(index="period_end", columns="metric",
                            values="value_m", aggfunc="first")
            .reset_index())
    wide.columns.name = None
    # Derived, business-friendly fields
    if {"net_operating_income", "total_operating_expenses"}.issubset(wide.columns):
        wide["cost_efficiency_ratio"] = (
            wide["total_operating_expenses"].abs()
            / wide["net_operating_income"] * 100).round(1)
    wh.load_dataframe(wide, "staging", "financials_wide")
    print(f"[transform] staging.financials_wide: {len(wide)} rows")


def build_mart_financial_kpis(wh) -> None:
    """Marts: quarter-on-quarter growth + a clean KPI view for the dashboard."""
    try:
        df = wh.query(f"SELECT * FROM {_ds(wh, 'staging')}.financials_wide "
                      "ORDER BY period_end")
    except Exception:
        print("[transform] mart_financial_kpis: staging missing, skip")
        return
    if df.empty:
        return
    for col in ["net_operating_income", "profit_before_tax"]:
        if col in df.columns:
            df[f"{col}_qoq_pct"] = (df[col].pct_change() * 100).round(1)
    wh.load_dataframe(df, "marts", "financial_kpis")
    print(f"[transform] marts.financial_kpis: {len(df)} rows")


def build_mart_churn_summary(wh) -> None:
    """Marts: churn-risk banding + per-geography summary for the dashboard."""
    try:
        df = wh.query(f"SELECT * FROM {_ds(wh, 'raw')}.churn_scored")
    except Exception:
        print("[transform] mart_churn_summary: churn_scored missing, skip")
        return
    if df.empty:
        return
    df["risk_band"] = pd.cut(df["churn_risk"], [-0.01, 0.3, 0.6, 1.0],
                             labels=["Low", "Medium", "High"])
    summary = (df.groupby(["geography", "risk_band"], observed=True)
               .size().reset_index(name="customers"))
    wh.load_dataframe(summary, "marts", "churn_summary")
    # also a flat high-risk list for the "action" view
    high = (df[df["risk_band"] == "High"]
            .sort_values("churn_risk", ascending=False)
            .head(500))
    wh.load_dataframe(high, "marts", "churn_high_risk")
    print(f"[transform] marts.churn_summary ({len(summary)}) + "
          f"churn_high_risk ({len(high)})")


def run_all(wh) -> None:
    build_staging_financials(wh)
    build_mart_financial_kpis(wh)
    build_mart_churn_summary(wh)
