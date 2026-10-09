"""App 2 backend — FastAPI.

Security model: the frontend never touches the warehouse directly. Every
NL->SQL query passes through SqlGuard (SELECT-only, dataset allow-list, LIMIT
injection) before execution. Credentials live only here, server-side.

Endpoints:
  GET  /health                 -> liveness + warehouse mode
  GET  /tables                 -> list warehouse tables
  POST /query     {question}   -> NL->SQL -> validate -> run -> rows + chart hint
  POST /query/raw {sql}        -> validate -> run (for the "edit the SQL" UX)
  GET  /metrics/kpis           -> financial KPI scorecards
  GET  /metrics/financials     -> full financial KPI series
  GET  /forecast/{module}      -> serve a prediction module
  POST /report    {topic,data} -> AI-generated analyst report

Run:
    uvicorn app2_analytics_platform.backend.main:app --reload --port 8000
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app2_analytics_platform.backend import services
from app2_analytics_platform.backend.nl_to_sql import translate
from app2_analytics_platform.backend.sql_guard import SqlGuard

app = FastAPI(title="HSBC FinOps Analytics API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

guard = SqlGuard()


class QuestionReq(BaseModel):
    question: str


class RawSqlReq(BaseModel):
    sql: str


class ReportReq(BaseModel):
    topic: str
    data: dict | None = None


def _chart_hint(rows: list[dict]) -> str:
    """Suggest a chart type from the result shape (GA4-style auto-viz)."""
    if not rows:
        return "none"
    cols = list(rows[0].keys())
    if len(cols) == 1:
        return "table"
    first = cols[0].lower()
    if len(rows) == 1 and len(cols) <= 3:
        return "scorecard"
    if any(k in first for k in ["date", "period", "month", "day"]):
        return "line"
    return "bar"


def _run_validated(sql: str) -> dict[str, Any]:
    res = guard.validate(sql)
    if not res.ok:
        return {"ok": False, "reason": res.reason, "sql": sql}
    try:
        df = services.warehouse().query(res.sql)
        rows = df.to_dict(orient="records")
        return {"ok": True, "sql": res.sql, "rows": rows,
                "row_count": len(rows), "chart_hint": _chart_hint(rows)}
    except Exception as exc:
        return {"ok": False, "reason": f"execution error: {exc}", "sql": res.sql}


@app.get("/health")
def health():
    return {"status": "ok", "warehouse_mode": services.warehouse().cfg.mode}


@app.get("/tables")
def tables():
    return {"tables": services.warehouse().list_tables()}


@app.post("/query")
def query(req: QuestionReq):
    t = translate(req.question)
    out = _run_validated(t.sql)
    out.update({"engine": t.engine, "translation_note": t.note,
                "generated_sql": t.sql})
    return out


@app.post("/query/raw")
def query_raw(req: RawSqlReq):
    return _run_validated(req.sql)


@app.get("/metrics/kpis")
def metrics_kpis():
    return services.kpi_scorecards()


@app.get("/metrics/financials")
def metrics_financials():
    return {"series": services.financial_kpis(),
            "catalog": services.metric_catalog()}


@app.get("/metrics/catalog")
def metrics_catalog():
    return {"catalog": services.metric_catalog()}


@app.get("/glossary")
def glossary():
    from app2_analytics_platform.backend.labels import glossary as g
    return g()


@app.get("/modules")
def modules():
    """List all prediction modules with friendly title/description/source."""
    from app2_analytics_platform.backend.labels import MODULE_META
    return {"modules": [{"key": k, **v} for k, v in MODULE_META.items()]}


@app.get("/forecast/{module}")
def forecast(module: str, metric: str | None = None):
    kwargs = {"metric": metric} if metric else {}
    return services.forecast(module, **kwargs)


# ─── GA4-style digital-analytics reports ───
GA4_REPORTS = [
    {"key": "overview", "title": "Overview", "desc": "Headline users, sessions, engagement and conversions."},
    {"key": "realtime", "title": "Realtime", "desc": "Activity in the latest window — users now, by country/device, top events."},
    {"key": "acquisition", "title": "Acquisition", "desc": "How users arrive — by channel and source."},
    {"key": "engagement", "title": "Engagement", "desc": "Events, engaged sessions and average engagement time."},
    {"key": "retention", "title": "Retention", "desc": "New vs returning users and weekly cohort retention."},
    {"key": "demographics", "title": "Demographics", "desc": "Users by country, age and gender."},
    {"key": "tech", "title": "Tech", "desc": "Users by device, browser and operating system."},
]


@app.get("/ga4")
def ga4_catalog():
    return {"reports": GA4_REPORTS}


@app.get("/ga4/{report}")
def ga4_report(report: str):
    from app2_analytics_platform.backend import ga4_reports
    return ga4_reports.run(report)


@app.post("/report")
def report(req: ReportReq):
    return services.generate_report(req.topic, req.data)
