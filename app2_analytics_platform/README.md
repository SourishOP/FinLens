# App 2 — Analytics & Prediction Platform (the star product)

A single, polished Streamlit app pulling everything together: GA4-style
visualizations, natural-language -> BigQuery querying, all 7 prediction modules,
AI-written reports, and Excel/PDF export. It talks only to the FastAPI backend
(never the warehouse directly).

## Run (two processes)

```powershell
.\.venv\Scripts\Activate.ps1

# 1) backend (holds credentials, validates all SQL)
uvicorn app2_analytics_platform.backend.main:app --port 8000

# 2) frontend (new terminal)
streamlit run app2_analytics_platform/frontend/app.py --server.port 8501
```

Open http://localhost:8501 . Make sure the warehouse is populated first:
`python -m bigquery.load_to_bq`.

## Feature areas

1. **Dashboard** — KPI scorecards (value + % change), revenue/profit trend,
   cost-efficiency bars, churn-by-geography (GA4-style breakdowns via Plotly).
2. **Ask the data** — type plain English -> validated read-only BigQuery query.
   Always shows the generated SQL and auto-selects the chart type.
3. **Predictions** — tabs for all 7 modules (stock price, market risk, credit
   risk/ECL, financials, capital optimization, churn).
4. **AI reports** — AI-written analyst report (Gemini or template fallback) with
   PDF + Excel download.
5. **Data explorer** — browse tables, run validated SQL, export results.

## Config

- `BACKEND_URL` (default `http://127.0.0.1:8000`) — point the frontend at the backend.
- Theme: HSBC red `#DB0011`. Honest REAL vs SIMULATED labelling throughout.
- Degrades gracefully: if the backend is down, the app shows a clear banner
  instead of crashing.
