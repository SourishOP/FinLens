"""Human-readable labels, units, descriptions, and value formatting.

The raw warehouse/model fields use short machine names (net_operating_income,
rorwa_pct, MAPE...). This module maps them to clear display names, units, and
formatted strings so the UI is self-explanatory to a non-technical reader.
"""
from __future__ import annotations

from typing import Any

# metric key -> (display name, unit, help text)
METRIC_META: dict[str, dict[str, str]] = {
    "net_operating_income": {
        "label": "Revenue (net operating income)", "unit": "$m",
        "help": "Total income from operations before costs, in millions of US dollars."},
    "net_interest_income": {
        "label": "Net interest income", "unit": "$m",
        "help": "Income from lending minus interest paid, in $m."},
    "net_fee_income": {
        "label": "Net fee income", "unit": "$m",
        "help": "Income from fees and commissions, in $m."},
    "profit_before_tax": {
        "label": "Profit before tax", "unit": "$m",
        "help": "Group profit before tax is deducted, in $m."},
    "profit_after_tax": {
        "label": "Profit after tax", "unit": "$m",
        "help": "Group profit after tax, in $m."},
    "expected_credit_losses": {
        "label": "Expected credit losses", "unit": "$m",
        "help": "Money set aside for loans expected to default. Higher = more credit risk."},
    "total_operating_expenses": {
        "label": "Operating expenses", "unit": "$m",
        "help": "Total running costs of the bank, in $m."},
    "cost_efficiency_ratio": {
        "label": "Cost efficiency ratio", "unit": "%",
        "help": "Costs as a % of income. Lower is better (more efficient)."},
    "net_operating_income_qoq_pct": {
        "label": "Revenue change vs last quarter", "unit": "%",
        "help": "Quarter-on-quarter growth in revenue."},
    "profit_before_tax_qoq_pct": {
        "label": "Profit change vs last quarter", "unit": "%",
        "help": "Quarter-on-quarter growth in profit before tax."},
    "churn_risk": {
        "label": "Churn risk", "unit": "score 0-1",
        "help": "Probability a customer leaves. 1 = certain to leave."},
    "acquisition_propensity": {
        "label": "Acquisition propensity", "unit": "score 0-1",
        "help": "Likelihood a customer opens a new product. Higher = better lead."},
    "annualised_vol": {
        "label": "Annualised volatility", "unit": "%",
        "help": "How much the share price swings over a year. Higher = riskier."},
}

# module key -> (title, one-line description, data-source tag)
MODULE_META: dict[str, dict[str, str]] = {
    "financials": {
        "title": "Financial forecast",
        "desc": "Predicts next-quarter revenue and profit from HSBC's real published results.",
        "source": "REAL — HSBC Data Packs"},
    "stock_price": {
        "title": "Share-price forecast",
        "desc": "Forecasts HSBC's share price for the next 30 trading days using the most accurate model (auto-selected).",
        "source": "REAL — market data"},
    "market_risk": {
        "title": "Market risk (Value-at-Risk)",
        "desc": "Estimates the worst expected one-day loss on HSBC stock at 95% and 99% confidence.",
        "source": "REAL — market data"},
    "credit_risk": {
        "title": "Credit risk (expected losses)",
        "desc": "Forecasts expected credit losses and whether credit quality is improving or worsening.",
        "source": "REAL — HSBC Data Packs"},
    "optimization": {
        "title": "Capital allocation optimiser",
        "desc": "Recommends how to spread capital across business segments to maximise return within risk limits.",
        "source": "REAL inputs — decision-support model"},
    "churn": {
        "title": "Customer churn risk",
        "desc": "Identifies customers most likely to leave, so the bank can act early.",
        "source": "SIMULATED customers (methodology demo)"},
    "acquisition": {
        "title": "New-account propensity",
        "desc": "Ranks customers by how likely they are to open a new product — a priority list for campaigns.",
        "source": "SIMULATED customers (methodology demo)"},
    "traffic": {
        "title": "Digital traffic forecast",
        "desc": "Forecasts daily app/web sessions, capturing weekday vs weekend patterns.",
        "source": "REAL — our GA4 prototype"},
    "transactions": {
        "title": "Transaction analytics",
        "desc": "Transaction volumes and which channel (mobile vs web) converts best.",
        "source": "REAL — our GA4 prototype"},
}

# model-metric short forms -> friendly names
METRIC_GLOSSARY = {
    "MAPE": "Avg % error",
    "RMSE": "Typical error size",
    "MAE": "Avg error",
    "DirectionalAccuracy": "Direction correct %",
    "ROC_AUC": "Ranking accuracy (0.5-1)",
    "PR_AUC": "Precision quality (0-1)",
    "Brier": "Probability accuracy (lower better)",
    "rorwa_pct": "Return on capital %",
    "var": "Value-at-Risk",
    "cvar": "Expected shortfall",
}


def meta_for(metric: str) -> dict[str, str]:
    return METRIC_META.get(metric, {"label": metric.replace("_", " ").title(),
                                    "unit": "", "help": ""})


def module_meta(module: str) -> dict[str, str]:
    return MODULE_META.get(module, {"title": module.replace("_", " ").title(),
                                    "desc": "", "source": ""})


def format_value(metric: str, value: Any) -> str:
    """Return a nicely formatted string for a metric value."""
    if value is None:
        return "—"
    unit = meta_for(metric).get("unit", "")
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    if unit == "$m":
        return f"${v:,.0f}m"
    if unit == "%":
        return f"{v:.1f}%"
    if unit.startswith("score"):
        return f"{v:.2f}"
    return f"{v:,.2f}"


def glossary() -> dict[str, str]:
    """Full glossary for a UI tooltip/legend so no term is unexplained."""
    g = {k: v["help"] for k, v in METRIC_META.items() if v.get("help")}
    g.update(METRIC_GLOSSARY)
    return g
