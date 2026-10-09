"""Natural-language -> SQL translation (Gemini via Vertex AI), with a fallback.

Two paths:
  * Gemini path  : when GCP_PROJECT_ID is set, we call Gemini on Vertex AI with
                   the question + a compact schema description and ask for a
                   single BigQuery SELECT.
  * Fallback path: when Vertex is unavailable (or a call errors), a small
                   rule/keyword matcher maps common questions to canned safe
                   SELECTs so the feature stays demoable offline. It always
                   returns valid SQL or a clear "couldn't translate" message.

Either way the output is passed through SqlGuard before execution — the LLM is
never trusted directly.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()  # load Vertex config (GCP_PROJECT_ID, GEMINI_LOCATION, ...) from .env

# Compact schema description shown to the LLM and used by the fallback.
SCHEMA_DOC = """
Tables (BigQuery standard SQL). Money values are in $m unless noted.

hsbc_marts.financial_kpis(period_end DATE, net_interest_income, net_fee_income,
    net_operating_income, expected_credit_losses, total_operating_expenses,
    profit_before_tax, profit_after_tax, cost_efficiency_ratio,
    net_operating_income_qoq_pct, profit_before_tax_qoq_pct)
hsbc_marts.churn_summary(geography STRING, risk_band STRING, customers INT)
hsbc_marts.churn_high_risk(... per-customer columns ..., churn_risk FLOAT)
hsbc_raw.share_price(Date STRING, Open, High, Low, Close, Volume)
hsbc_raw.acquisition_scored(... customer columns ..., acquisition_propensity FLOAT)
hsbc_raw.churn_scored(... customer columns ..., churn_risk FLOAT)
""".strip()

_PROMPT = """You are a BigQuery SQL expert for an HSBC finance analytics warehouse.
Translate the user's question into ONE BigQuery standard-SQL SELECT statement.

Rules:
- Output ONLY the SQL, no prose, no markdown fences.
- SELECT only. Never modify data.
- Use only the tables/columns in the schema below.
- Always include a LIMIT (<= 1000).

Schema:
{schema}

Question: {question}
SQL:"""


@dataclass
class Translation:
    sql: str
    engine: str          # 'gemini' or 'fallback'
    note: str = ""


def _gemini_available() -> bool:
    # Vertex AI auths via service account / ADC + project, not an API key.
    return bool(os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT"))


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


def translate(question: str) -> Translation:
    if _gemini_available():
        try:
            return _gemini_translate(question)
        except Exception as exc:  # fall back rather than fail the request
            fb = _fallback_translate(question)
            fb.note = f"Gemini error, used fallback: {exc}"
            return fb
    return _fallback_translate(question)


def _gemini_translate(question: str) -> Translation:
    # Current SDK (google-genai), via Vertex AI.
    client = _make_client()
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    resp = client.models.generate_content(
        model=model,
        contents=_PROMPT.format(schema=SCHEMA_DOC, question=question),
    )
    sql = _strip_fences(resp.text)
    return Translation(sql=sql, engine="gemini")


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:sql)?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text).strip()
    return text


# ---------------------------------------------------------------------------
# Keyword fallback — demoable without an API key
# ---------------------------------------------------------------------------
_RULES: list[tuple[list[str], str]] = [
    (["churn", "geography"],
     "SELECT geography, risk_band, customers FROM hsbc_marts.churn_summary "
     "ORDER BY geography, risk_band LIMIT 100"),
    (["high", "risk", "churn"],
     "SELECT geography, churn_risk FROM hsbc_marts.churn_high_risk "
     "ORDER BY churn_risk DESC LIMIT 20"),
    (["profit", "quarter"],
     "SELECT period_end, profit_before_tax FROM hsbc_marts.financial_kpis "
     "ORDER BY period_end LIMIT 100"),
    (["revenue"],
     "SELECT period_end, net_operating_income FROM hsbc_marts.financial_kpis "
     "ORDER BY period_end LIMIT 100"),
    (["cost", "efficiency"],
     "SELECT period_end, cost_efficiency_ratio FROM hsbc_marts.financial_kpis "
     "ORDER BY period_end LIMIT 100"),
    (["share", "price"],
     "SELECT Date, Close FROM hsbc_raw.share_price ORDER BY Date DESC LIMIT 90"),
    (["acquisition", "propensity"],
     "SELECT geography, acquisition_propensity FROM hsbc_raw.acquisition_scored "
     "ORDER BY acquisition_propensity DESC LIMIT 20"),
]


def _fallback_translate(question: str) -> Translation:
    q = question.lower()
    for keywords, sql in _RULES:
        if all(k in q for k in keywords):
            return Translation(sql=sql, engine="fallback")
    # default: most useful general view
    return Translation(
        sql="SELECT period_end, net_operating_income, profit_before_tax "
            "FROM hsbc_marts.financial_kpis ORDER BY period_end LIMIT 100",
        engine="fallback",
        note="Vertex AI unavailable and no keyword match; returned a default "
             "financial-KPI query. Set GCP_PROJECT_ID + Vertex config in .env "
             "for full NL->SQL.")
