# App 2 backend (FastAPI)

The secure middle tier. The frontend never touches the warehouse directly —
credentials live here and every query is validated before execution.

## Run

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app2_analytics_platform.backend.main:app --reload --port 8000
# docs at http://127.0.0.1:8000/docs
```

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | liveness + warehouse mode (local/bigquery) |
| GET | `/tables` | list warehouse tables |
| POST | `/query` `{question}` | NL->SQL -> validate -> run; returns rows + chart hint + generated SQL |
| POST | `/query/raw` `{sql}` | validate -> run (for the "edit the SQL" UX) |
| GET | `/metrics/kpis` | KPI scorecards (value + % change) |
| GET | `/metrics/financials` | full financial KPI series |
| GET | `/forecast/{module}` | serve a prediction module (stock_price, market_risk, credit_risk, financials, optimization, churn) |
| POST | `/report` `{topic,data}` | AI analyst report (Gemini, or template fallback) |

## Security — `sql_guard.py`

Every query (LLM-generated or raw) passes `SqlGuard.validate()` which enforces:
single statement, SELECT/WITH only, hard block on DROP/DELETE/UPDATE/INSERT/DDL,
table references restricted to `hsbc_raw`/`hsbc_staging`/`hsbc_marts`, and a LIMIT
is injected if missing. 11/11 adversarial tests pass (injection, cross-dataset,
stacked statements, `created_at` false-positive).

## Offline fallback operation

Gemini runs through **Vertex AI** (service-account auth, no API key).

- **NL->SQL** (`nl_to_sql.py`): uses Gemini when Vertex is configured (`GCP_PROJECT_ID`
  set + reachable); otherwise a keyword fallback returns safe canned SELECTs so the
  feature demos offline.
- **AI reports**: Gemini when Vertex is available; otherwise a structured template
  with the honest real-vs-simulated data caveats.

Set `GCP_PROJECT_ID`, `GEMINI_LOCATION`, and `GEMINI_MODEL` in `.env` (Vertex AI API
enabled + service account `roles/aiplatform.user`) for full AI behaviour.
