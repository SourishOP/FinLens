# Warehouse layer (BigQuery + local mirror)

Runs in two modes, auto-detected (see `bigquery/config.py`):

- **LOCAL** (default, no setup): a SQLite mirror at `data/warehouse.db` with the
  same `dataset.table` structure as BigQuery. Fully demoable offline.
- **BIGQUERY** (when `.env` has `GCP_PROJECT_ID` + `GOOGLE_APPLICATION_CREDENTIALS`):
  real datasets, load jobs, and queries on Google BigQuery (EU location).

## Layers

```
raw      group_income_statement | churn_scored | acquisition_scored | share_price
staging  financials_wide        (pivoted + cost efficiency ratio)
marts    financial_kpis         (QoQ growth) | churn_summary | churn_high_risk
```

## Run

```powershell
python -m bigquery.config        # show detected mode
python -m bigquery.load_to_bq    # load raw + build staging/marts
```

## Switch to real BigQuery

1. Create a GCP project and a BigQuery-enabled service account; download its JSON key.
2. In `.env`: set `GCP_PROJECT_ID` and `GOOGLE_APPLICATION_CREDENTIALS=./service-account.json`.
3. Re-run `python -m bigquery.load_to_bq` — datasets are created automatically, no code change.

The App 2 backend's NL->SQL feature writes BigQuery-style SQL; in local mode the
warehouse transparently translates `dataset.table` to the SQLite equivalent.
