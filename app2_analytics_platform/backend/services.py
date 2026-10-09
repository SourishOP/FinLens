"""Service layer: metrics, prediction serving, and AI report generation.

These wrap the warehouse and the modelling layer so the FastAPI routes stay thin.
Everything degrades gracefully: if a model's data isn't present, the endpoint
returns a clear message rather than crashing.
"""
from __future__ import annotations

import os
from typing import Any

import pandas as pd
from dotenv import load_dotenv

from bigquery.warehouse import get_warehouse

load_dotenv()  # load Vertex config (GCP_PROJECT_ID, GEMINI_LOCATION, ...) from .env

_wh = None


def warehouse():
    global _wh
    if _wh is None:
        _wh = get_warehouse()
    return _wh


# ---------------------------------------------------------------------------
# GA4-style metrics / KPIs from the warehouse
# ---------------------------------------------------------------------------
def financial_kpis() -> list[dict[str, Any]]:
    try:
        import math
        df = warehouse().query(
            "SELECT * FROM hsbc_marts.financial_kpis ORDER BY period_end")
        # NaN/inf (e.g. first quarter's QoQ change) aren't valid JSON -> None.
        records = df.to_dict(orient="records")
        for row in records:
            for k, v in row.items():
                if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                    row[k] = None
        return records
    except Exception as exc:
        return [{"error": str(exc)}]


def kpi_scorecards() -> dict[str, Any]:
    """Big-number cards with % change vs prior quarter, fully labelled."""
    from app2_analytics_platform.backend.labels import format_value, meta_for
    df = warehouse().query(
        "SELECT * FROM hsbc_marts.financial_kpis ORDER BY period_end")
    if df.empty or len(df) < 2:
        return {"cards": []}
    latest, prev = df.iloc[-1], df.iloc[-2]
    cards = []
    for metric in ["net_operating_income", "profit_before_tax",
                   "cost_efficiency_ratio"]:
        if metric in df.columns:
            cur, old = latest[metric], prev[metric]
            change = ((cur - old) / old * 100) if old else None
            m = meta_for(metric)
            # For cost efficiency, lower is better -> invert the "good" direction.
            good_up = metric != "cost_efficiency_ratio"
            cards.append({
                "key": metric,
                "label": m["label"], "unit": m["unit"], "help": m["help"],
                "value": float(cur),
                "display": format_value(metric, cur),
                "change_pct": round(float(change), 1) if change is not None else None,
                "trend_good": bool(change is not None and
                                   ((change >= 0) == good_up)),
                "period": str(latest["period_end"])})
    return {"cards": cards}


# ---------------------------------------------------------------------------
# Prediction serving (the 7 modules)
# ---------------------------------------------------------------------------
def metric_catalog() -> list[dict[str, Any]]:
    """List the financial-KPI columns with their labels/units for the UI."""
    from app2_analytics_platform.backend.labels import meta_for
    try:
        df = warehouse().query(
            "SELECT * FROM hsbc_marts.financial_kpis LIMIT 1")
    except Exception:
        return []
    out = []
    for col in df.columns:
        if col == "period_end":
            continue
        m = meta_for(col)
        out.append({"key": col, "label": m["label"], "unit": m["unit"],
                    "help": m["help"]})
    return out


def forecast(module: str, **kwargs) -> dict[str, Any]:
    from app2_analytics_platform.backend.labels import module_meta
    meta = module_meta(module)
    try:
        result = _forecast_impl(module, **kwargs)
        if isinstance(result, dict):
            result.setdefault("title", meta["title"])
            result.setdefault("description", meta["desc"])
            result.setdefault("source", meta["source"])
        return result
    except Exception as exc:
        return {"module": module, "title": meta["title"],
                "description": meta["desc"], "source": meta["source"],
                "error": str(exc)}


def _forecast_impl(module: str, **kwargs) -> dict[str, Any]:
    if module == "stock_price":
        from modelling.stock_price.bakeoff import predict
        return {"module": module, **predict(period=kwargs.get("period", "2y"),
                                             horizon=kwargs.get("horizon", 30))}
    if module == "market_risk":
        from modelling.risk.market_risk import full_report
        rep = full_report()
        return {"module": module, "annualised_vol": rep["ann_volatility"],
                "var": [{"method": r.method, "confidence": r.confidence,
                         "var": r.var, "cvar": r.cvar} for r in rep["var_results"]],
                "garch": rep["garch"]}
    if module == "credit_risk":
        from modelling.risk.credit_risk import forecast_ecl
        return {"module": module, **forecast_ecl()}
    if module == "financials":
        import math as _math
        from modelling.financials.forecast import (backtest, forecast_forward,
                                                    load_series)
        metric = kwargs.get("metric", "net_operating_income")
        bt = backtest(metric)
        # auto-select the best method by lowest MAPE
        scored = [(name, r["metrics"]["MAPE"]) for name, r in bt["results"].items()
                  if "metrics" in r and not _math.isnan(r["metrics"]["MAPE"])]
        best_method, best_mape = (min(scored, key=lambda x: x[1])
                                  if scored else ("seasonal_naive", None))
        fwd = forecast_forward(metric, horizon=4, method=best_method)
        s = load_series(metric)
        history = [{"period_end": d.strftime("%Y-%m-%d"), "value_m": float(v)}
                   for d, v in s.items()]
        # bridge: repeat last actual as the first forecast anchor for a joined line
        fwd_records = fwd.assign(
            period_end=fwd["period_end"].astype(str)).to_dict(orient="records")
        return {"module": module, "metric": metric,
                "best_method": best_method.replace("_", "-"),
                "best_mape": round(best_mape, 1) if best_mape is not None else None,
                "history": history, "forward": fwd_records}
    if module == "optimization":
        from modelling.optimization.capital_allocation import capital_allocation
        return {"module": module, **capital_allocation()}
    if module == "churn":
        df = warehouse().query(
            "SELECT geography, risk_band, customers FROM hsbc_marts.churn_summary")
        return {"module": module, "summary": df.to_dict(orient="records")}
    if module == "acquisition":
        # Average acquisition propensity by geography (priority campaign regions).
        df = warehouse().query(
            "SELECT geography, AVG(acquisition_propensity) AS avg_propensity, "
            "COUNT(*) AS customers FROM hsbc_raw.acquisition_scored "
            "GROUP BY geography ORDER BY avg_propensity DESC")
        df["avg_propensity"] = df["avg_propensity"].round(3)
        return {"module": module, "by_geography": df.to_dict(orient="records")}
    if module == "traffic":
        from modelling.traffic.forecast import forecast as traffic_fc
        return traffic_fc()
    if module == "transactions":
        from modelling.transactions.model import (conversion_by_channel,
                                                  conversion_by_geo,
                                                  volume_forecast)
        return {"module": module,
                "by_channel": conversion_by_channel().to_dict(orient="records"),
                "by_geo": conversion_by_geo().to_dict(orient="records"),
                "volume_backtest": volume_forecast()}
    return {"error": f"unknown module '{module}'"}


# ---------------------------------------------------------------------------
# AI report generation (Gemini, with offline fallback)
# ---------------------------------------------------------------------------
def _ai_available() -> bool:
    # Vertex AI auths via service account / ADC + project, not an API key.
    return bool(os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT"))


def generate_report(topic: str, data: dict | None = None) -> dict[str, Any]:
    data = data or {}
    if _ai_available():
        try:
            return {"topic": topic, "engine": "gemini",
                    "report": _gemini_report(topic, data)}
        except Exception as exc:
            return {"topic": topic, "engine": "fallback",
                    "report": _template_report(topic, data),
                    "note": f"Gemini error: {exc}"}
    return {"topic": topic, "engine": "fallback",
            "report": _template_report(topic, data)}


def _make_client():
    """Build a google-genai client backed by Vertex AI.

    Auth uses the service account in GOOGLE_APPLICATION_CREDENTIALS (ADC),
    with the project from GCP_PROJECT_ID and region from GEMINI_LOCATION.
    """
    from google import genai
    return genai.Client(
        vertexai=True,
        project=os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT"),
        location=os.getenv("GEMINI_LOCATION", "us-central1"),
    )


def _gemini_report(topic: str, data: dict) -> str:
    # Current SDK (google-genai), via Vertex AI.
    client = _make_client()
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    prompt = (
        "Write a concise finance analyst report (<= 250 words) for HSBC senior "
        "management on the topic below. Structure: Summary, Key findings, "
        "Assumptions & limitations. Be factual; use the data provided.\n\n"
        f"Topic: {topic}\nData: {data}")
    return client.models.generate_content(model=model, contents=prompt).text


def _template_report(topic: str, data: dict) -> str:
    lines = [f"# Analyst report: {topic}", "",
             "## Summary",
             "Automated draft (configure Vertex AI for AI-written narrative).", ""]
    if data:
        lines.append("## Key figures")
        for k, v in list(data.items())[:12]:
            lines.append(f"- {k}: {v}")
        lines.append("")
    lines += ["## Assumptions & limitations",
              "- Financials from HSBC public Data Packs; share price from market data.",
              "- Churn/acquisition use SIMULATED customer data (clearly labelled).",
              "- Small quarterly sample => classical forecasting; see validation metrics."]
    return "\n".join(lines)
