# FinLens — Finance Analytics & Prediction Platform

> An interview case study for the **HSBC Analyst Intern — Global Finance Operations & Finance
> Change Delivery** role. FinLens demonstrates GA4, BigQuery/GCP, Python, forecasting, risk,
> optimization, and business reporting through two apps and a 7-module modelling layer.
>
> **Not affiliated with or endorsed by HSBC.** All HSBC data used here is public (quarterly
> Data Packs and market prices); no confidential customer or operational data is ever accessed.

---

## Table of contents

1. [What this is](#what-this-is)
2. [Data honesty](#data-honesty)
3. [JD skills demonstrated](#jd-skills-demonstrated)
4. [The 7 prediction modules](#the-7-prediction-modules)
5. [Two-app architecture](#two-app-architecture)
6. [End-to-end data flow](#end-to-end-data-flow)
7. [GA4 feature parity](#ga4-feature-parity)
8. [Inside the HSBC Data Packs](#inside-the-hsbc-data-packs)
9. [Project structure](#project-structure)
10. [Quick start](#quick-start)
11. [Build order](#build-order)
12. [Going live — real BigQuery + GA4 + App 1](#going-live--real-bigquery--ga4--app-1)
13. [Open the apps on your phone](#open-the-apps-on-your-phone)
14. [Looker Studio dashboard](#looker-studio-dashboard)
15. [Assumptions, limitations & provenance](#assumptions-limitations--provenance)
16. [Research references](#research-references)
17. [Environment](#environment)

---

## What this is

- **App 1 — banking clone (data source only).** A Flutter "HSBC-style" prototype whose only
  job is to generate **real GA4 events we legitimately own**. One codebase runs on Web +
  Android + iOS. It simulates login, accounts, transactions, and bill pay, and is instrumented
  with GA4 (via Firebase Analytics): `page_view`, `report_download`, `filter_applied`,
  transaction events, device/channel, and session data. It never touches HSBC's real app or site.
- **App 2 — analytics & prediction platform (the star).** A React + Vite frontend + FastAPI
  backend product with GA4-style visualizations, natural-language → BigQuery querying,
  AI-generated reports, Excel/PDF export, and all 7 prediction modules.

---

## Data honesty

This project never claims access to confidential HSBC data. Every layer is labelled:

| Layer | Source | Real / Simulated |
|---|---|---|
| Financials (revenue, PBT, RoTE, ECL, CET1, RWA, segments) | HSBC public quarterly Data Packs (scraped) | **REAL** |
| Share price / market | yfinance `HSBA.L` (30-min refresh) | **REAL** |
| Analyst consensus | HSBC published consensus estimates | **REAL** |
| Digital adoption (app vs web) | App 1 + GA4 (our own app) | **REAL GA4, our own app** |
| Churn / acquisition | public benchmark (`ChurnModelling.csv`) / simulated | **SIMULATED (labelled)** |

**What is impossible (and why) — never claimed:**

- GA4 on HSBC's real website/app — we don't own them; the data is confidential/legally protected.
- Predicting HSBC revenue from app traffic — no such correlation exists; the two layers are kept
  strictly separate.
- A full native banking app clone — out of scope, and the wrong skill for an analyst role.

**Refresh velocity (matched to each source):**

- Quarterly financials → checked **daily**, re-parsed only when a new document appears.
- Share price → **every 30 minutes** via the scheduler (the legitimate fast-moving source).
- GA4 events → near real-time via the native GA4 → BigQuery export.

---

## JD skills demonstrated

| JD / slide requirement | Where demonstrated |
|---|---|
| Google Analytics (GA4) | App 1 instrumentation + GA4→BigQuery export + GA4-style views in App 2 |
| BigQuery / SQL | Warehouse + NL→SQL feature |
| GCP | BigQuery, Gemini (NL→SQL), Looker Studio |
| Python | Models, scrapers, backend |
| R (optional bonus) | Can re-implement one forecast in R |
| Excel | Data Pack parsing + Excel export of reports |
| Modelling / forecasting | 7 prediction modules |
| Optimization | Capital allocation + cost optimizer |
| Risk management | ECL/CET1 forecasting, VaR/volatility |
| Insights for decision-making | App 2 dashboards + AI reports |
| Summarize approach / assumptions / limitations | Validation reports + assumptions section below |
| Data preparation & management | Scraper, parser, layered BigQuery |

---

## The 7 prediction modules

All methods are grounded in research (see [references](#research-references)).

| # | Module | Method | Data | Real/Sim |
|---|---|---|---|---|
| 1 | Stock price | ARIMA vs Prophet vs LSTM/GRU **bake-off** + MAPE/RMSE | yfinance HSBA.L | REAL |
| 2 | Financials (revenue/PBT/RoTE) | SARIMA/Prophet, benchmarked vs analyst consensus | Data Packs | REAL |
| 3 | User traffic | Prophet session forecasting (weekly seasonality) | GA4 (our app) | REAL |
| 4 | Transactions | Prophet volume forecast + conversion by channel/geo | GA4 (our app) | REAL |
| 5 | Churn ("potential to leave") | LightGBM/XGBoost + SHAP + calibration + gains/lift | benchmark/sim | SIMULATED |
| 6 | Acquisition propensity | lead-scoring (LogReg baseline + ensemble) + uplift | benchmark/sim | SIMULATED |
| 7a | Risk | ECL forecast, ECL/loans ratio, CET1-vs-minimum buffer, VaR + volatility (GARCH/rolling) | Data Packs + yfinance | REAL |
| 7b | Optimization | Capital allocation (max RoRWA under CET1 constraint) + cost LP (scipy/PuLP) | Data Pack segment data (+ stated assumptions) | REAL inputs |

**Modelling principles (interview-defensible):**

- Match model complexity to data size: ~20–40 quarterly points → classical models
  (SARIMA/Prophet), **not** deep learning (would overfit — interviewers notice).
- Every module ships a **validation report**: train/test split, metrics
  (MAPE/RMSE for forecasts; ROC-AUC/PR-AUC/Brier for classifiers), plots.
- Churn insight framing: targeting the top 40% predicted churners captures ~80% of churn
  (cumulative gains / lift chart).
- Explainability via **SHAP** (regulatory relevance for a bank).
- Churn/acquisition validated on the public **ChurnModelling.csv** benchmark, clearly labelled.

---

## Two-app architecture

### App 1 — banking clone (data source only)

- **Stack:** Flutter → one codebase runs on Web + Android + iOS.
- **Purpose:** exists only to generate **real GA4 events** we legitimately own.
- Fed by a **traffic simulator** (see [GA4 feature parity](#ga4-feature-parity)) since there
  are no real users. iOS *builds* require macOS; Web + Android run on Windows.

### App 2 — analytics & prediction platform (the star)

- **Frontend:** React + Vite (SPA dashboards, charts, NL query box).
- **Backend:** FastAPI (Python) — holds GCP credentials, validates all SQL.
- Pulls together everything: GA4-style visualizations, NL→SQL, AI reports, Excel/PDF export,
  and all 7 prediction modules.

```
App 2 FRONTEND (React + Vite)
  • GA4-style dashboard (cards, line/bar/pie, geo, funnel, cohort, realtime)
  • NL query box: question -> see SQL -> see chart
  • Prediction views (all 7 modules)
  • AI report builder + Excel/PDF export
        │ REST/HTTPS
        ▼
App 2 BACKEND (FastAPI)
  • /query    -> NL→SQL (Gemini) -> validate (SELECT-only) -> BigQuery
  • /metrics  -> pre-built GA4-style aggregations
  • /forecast -> serve 7 prediction modules
  • /report   -> AI-generated report (text + charts)
  • /realtime -> recent GA4 events
        │                         │
        ▼                         ▼
  BigQuery (GCP)            Model layer (7 modules -> write predictions back to BQ)
```

**Security boundary:** the frontend NEVER talks to BigQuery directly. Every query (NL-generated
or raw) passes `SqlGuard` in the backend — SELECT-only, blocks DROP/DELETE/UPDATE/INSERT,
restricts datasets via an allow-list, injects LIMIT, enforces byte/row limits + timeout. The
service-account key lives only server-side. Generated SQL is always shown to the user (trust +
the honest "NL→SQL isn't perfect" story).

---

## End-to-end data flow

```
DATA SOURCES
  HSBC Data Packs (public PDF/Excel) ─scraper→ parser → data/financials/*.csv   [REAL]
  Yahoo Finance (HSBA.L)             ─yfinance──────────→ share price (30 min)   [REAL]
  App 1 (Flutter) + traffic sim      ─GA4 events────────→ GA4 property           [REAL, our app]
  Synthetic customers                ─generator─────────→ churn / acquisition    [SIMULATED]
                     │                                   │ GA4→BigQuery export
                     ▼                                   ▼
            WAREHOUSE  (BigQuery OR local SQLite)  —  raw → staging → marts
            financials, share_price, ga4_sessions, churn/acquisition scored, financial_kpis…
                     │                     │
         modelling layer (7 modules)       │ SQL
         writes predictions back           ▼
                     │              Looker Studio (BigQuery direct)
                     ▼
         App 2 BACKEND (FastAPI)  —  NL→SQL + SqlGuard, /query /forecast /report
                     ▼
         App 2 FRONTEND (React + Vite) — dashboard · ask · predictions · reports
```

**Component map:**

| Layer | Tech | Dir |
|---|---|---|
| Financial ingest | requests + pdfplumber | `scrapers/`, `parsers/` |
| Market data | yfinance (+ cache) | `modelling/common/market_data.py` |
| GA4 generation | Measurement Protocol | `traffic_simulator/`, `app1_banking_clone/` |
| GA4 ingest | BigQuery export / sim | `bigquery/ga4_ingest.py` |
| Warehouse | BigQuery / SQLite | `bigquery/` |
| Models (9) | statsmodels, Prophet, LightGBM, scipy/PuLP, arch | `modelling/` |
| Backend | FastAPI + Gemini | `app2_analytics_platform/backend/` |
| Frontend | React + Vite + Plotly | `app2_analytics_platform/web/` |

**Dual-mode warehouse:** `bigquery/config.py` detects credentials. No creds → a local SQLite
mirror with the same `dataset.table` names; with `.env` creds → real BigQuery. No code changes
to switch, so the platform stays demoable offline while being production-ready.

---

## GA4 feature parity

App 2 rebuilds these GA4 report types over our BigQuery data (cleaner, and with our forecasts):

- **Realtime** — active users now, events in the last 30 min.
- **Time-series line charts** — active users, sessions, events over time.
- **Scorecards / KPI cards** — big-number metrics + % change vs prior period.
- **Bar charts** — top pages, top events, traffic by channel/source.
- **Pie / donut** — device category (mobile vs web vs tablet), new vs returning.
- **Geo map** — users by country/region.
- **Funnel exploration** — login → view account → start txn → complete (drop-off).
- **Path exploration** — flow between screens.
- **Retention / cohort** — repeat usage over days/weeks.
- **Free-form tables** — pivot any dimension × metric with filters.

**Traffic simulator (fills the "no users" gap, honestly):**

- Layer 1: real seed sessions (you click through on web/Android/iOS).
- Layer 2: Playwright headless browsers driving randomized journeys (~60% mobile / 40% web,
  ~70% complete a transaction, evening peaks, some abandon).
- Layer 3: GA4 Measurement Protocol — send events directly via HTTP to backfill volume/history.

---

## Inside the HSBC Data Packs

Standardised quarterly tables (same structure each quarter → loadable). Recent quarters have
**Excel** versions (`pandas.read_excel`); older ones are **PDF** (camelot/pdfplumber).

- **Group income statement:** revenue / net operating income, net interest income (NII),
  net interest margin (NIM), operating expenses, expected credit losses (ECL),
  profit before tax (reported + excl. notable items), profit after tax.
- **Key ratios:** RoTE, cost efficiency ratio, EPS, dividend per share.
- **Segment breakdown:** Hong Kong, UK, CIB, IWPB, + Corporate Centre.
- **Balance sheet:** total assets, customer loans, customer deposits, RWA.
- **Capital & liquidity:** CET1 ratio, LCR, leverage ratio.

**Caveats stated openly:**

- Quarterly (~20–24 points over 5–6 years); reader-formatted (merged cells, multi-row headers).
- The Jan-2025 segment reorganisation breaks continuity → we lead with the continuous
  **group-level** revenue/PBT/RoTE as primary forecast targets, mapping old→new segments only
  with a documented assumption.

---

## Project structure

```
FinLens/
├── app1_banking_clone/     # Flutter: web+Android+iOS, GA4-instrumented  [data source]
├── app2_analytics_platform/
│   ├── web/                # React + Vite SPA: dashboard + NL query + reports + export
│   ├── frontend/           # legacy Streamlit prototype (superseded by web/)
│   └── backend/            # FastAPI: NL→SQL, validation, BigQuery, forecasts, reports
├── scrapers/               # Playwright+BS4 Data Pack finder; yfinance market data
├── parsers/                # pandas / camelot / pdfplumber → tidy tables
├── scheduler/              # APScheduler: 30-min + daily jobs
├── modelling/              # 7 prediction modules + common (backtesting, metrics, registry)
├── bigquery/               # schema, load jobs, SQL transforms (raw → staging → marts)
├── traffic_simulator/      # Playwright + GA4 Measurement Protocol event generators
├── data/                   # financial CSVs, cache, predictions (downloads git-ignored)
├── requirements.txt
└── README.md
```

---

## Quick start

```powershell
# 1. Create & activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. (first run only) install Playwright browsers
python -m playwright install chromium

# Models that need NO cloud accounts run immediately, e.g. the stock bake-off:
python -m modelling.stock_price.run
```

The platform runs fully offline against the local SQLite warehouse. To go live on real
BigQuery + real GA4 + App 1, follow [Going live](#going-live--real-bigquery--ga4--app-1).

---

## Build order

So there is always something demoable, we build in this order:

1. **Scaffold** project + requirements.txt + README.
2. **Instant real-data models** — stock bake-off + risk/VaR via yfinance.
3. **Data Pack scraper + parser** → tidy financial CSVs.
4. **Remaining models** — financials vs consensus, churn+SHAP, acquisition, risk, optimization.
5. **BigQuery** datasets, load jobs, SQL transforms, write predictions back.
6. **App 2 backend** — NL→SQL + validation + forecast serving + AI reports.
7. **App 2 frontend** — GA4-style dashboard + NL query + reports + Excel/PDF export.
8. **App 1 (Flutter) + GA4 + traffic simulator** — generate real GA4 data.
9. **Wire GA4→BigQuery into App 2**, Looker Studio board, assumptions memo.

---

## Going live — real BigQuery + GA4 + App 1

Three phases. All free-tier.

> **Security:** never paste the service-account JSON or the API secret anywhere public.
> Keep them in local files / `.env` (both are git-ignored).

### Phase A — real BigQuery on GCP

1. Create a GCP project at <https://console.cloud.google.com> → note the **Project ID**
   (e.g. `finlens-472310`, not the display name).
2. Enable **billing** (free tier is enough — BigQuery free tier covers 1 TB queries + 10 GB
   storage/month; our data is MBs, so expect ~$0).
3. Enable the **BigQuery API**.
4. Create a **service account** (`finlens-sa`) with roles **BigQuery Data Editor** + **BigQuery
   Job User**; add a **JSON key** and save it as `service-account.json` in the project root
   (already git-ignored).
5. Fill in `.env`:
   ```
   GCP_PROJECT_ID=your-project-id-here
   GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
   BQ_DATASET_RAW=hsbc_raw
   BQ_DATASET_STAGING=hsbc_staging
   BQ_DATASET_MARTS=hsbc_marts
   ```
6. Verify: `python -m bigquery.config` (expect `mode=BIGQUERY`) then
   `python -m bigquery.load_to_bq`. The warehouse auto-switches — no code changes.

### Phase B — real GA4 + GA4→BigQuery export

1. Create a GA4 property (<https://analytics.google.com>) with a **Web** data stream (and an
   **App**/Firebase stream for the Flutter app). Note the **Measurement ID** (`G-XXXXXXXXXX`).
2. On that stream, create a **Measurement Protocol API secret**. Add both to `.env`:
   ```
   GA4_MEASUREMENT_ID=G-XXXXXXXXXX
   GA4_API_SECRET=paste-secret-here
   ```
3. Generate real events: `python -m traffic_simulator.ga4_measurement_protocol --sessions 500`
   (or run App 1 and click through it). Confirm they arrive in GA4 Realtime.
4. Link **GA4 → BigQuery** (GA4 Admin → BigQuery Links → choose your project → Daily, and
   Streaming for near-real-time). GA4 creates dataset `analytics_<propertyId>` with daily
   `events_*` tables. Add to `.env`:
   ```
   GA4_EXPORT_DATASET=analytics_XXXXXXXXX
   ```
   Then `python -m bigquery.ga4_ingest` reads the real export instead of simulating.

### Phase C — App 1 (Flutter) emitting real GA4 events

1. Install the **Flutter SDK** (Windows): download from
   <https://docs.flutter.dev/get-started/install/windows>, unzip to e.g. `C:\src\flutter`, add
   `C:\src\flutter\bin` to PATH, then `flutter --version` and `flutter doctor` (install Chrome
   for web; Android Studio only for Android builds; iOS builds need a Mac).
2. Create a **Firebase** project linked to the **same** GCP project (so Firebase, GA4, and
   BigQuery share one project) and enable Google Analytics (link to the GA4 property from B1).
3. Wire Firebase into the Flutter app:
   ```powershell
   dart pub global activate flutterfire_cli
   cd app1_banking_clone
   flutterfire configure        # generates lib/firebase_options.dart
   flutter pub get
   flutter run -d chrome        # web; emits real GA4 events as you click
   ```

### Gemini via Vertex AI (NL→SQL + AI reports)

Gemini runs through Vertex AI using the project's service account (no API key). Requirements:
Vertex AI API enabled, the service account granted `roles/aiplatform.user`, and billing on the
project. Set `GCP_PROJECT_ID`, `GEMINI_LOCATION`, and `GEMINI_MODEL` in `.env`. Without Vertex
access, keyword/template fallbacks run.

### After all three phases

- `python run_pipeline.py` populates **real BigQuery**.
- App 2 (backend `uvicorn …` + frontend) now reads real BigQuery, with real financials, real
  share price, real GA4 adoption data, and (if Vertex AI is configured) real Gemini NL→SQL +
  AI reports.
- Honest reminder: GA4 shows **your prototype's** traffic, not HSBC's real customers.

---

## Open the apps on your phone

Both apps run on this PC and are reachable from a phone on the **same Wi-Fi network**.
Find this PC's Wi-Fi IPv4 with `ipconfig` (look under "Wireless LAN adapter Wi-Fi").

| App | URL on phone (replace with your PC IP) |
|-----|----------------------------------------|
| **App 2 — Analytics dashboard** | `http://<PC-IP>:5173` |
| **App 1 — Banking app** | `http://<PC-IP>:5000` |

App 2's dashboard calls the backend through its own Vite proxy, so only port 5173 needs to be
open — the phone never contacts :8000 directly.

**Start all services (3 terminals, from project root):**

```powershell
# 1. Backend (BigQuery + Gemini) — bound to all interfaces
.\.venv\Scripts\python.exe -m uvicorn app2_analytics_platform.backend.main:app --host 0.0.0.0 --port 8000

# 2. App 2 web dashboard (React/Vite) — LAN exposed
cd app2_analytics_platform\web ; npm run dev

# 3. App 1 banking app (Flutter web)
cd app1_banking_clone ; flutter run -d chrome --web-port 5000 --web-hostname 0.0.0.0
```

**If the phone can't connect:** confirm the same Wi-Fi (not a guest network with AP isolation);
allow Node and Python through Windows Firewall on **Private** networks; some corporate/VPN
networks block device-to-device traffic (try a home or hotspot network). Clicking through App 1
on a phone fires the same real GA4 events (login, screen_view, transactions) as on desktop.

---

## Looker Studio dashboard

Looker Studio connects directly to BigQuery, so once the warehouse is in BigQuery mode you can
build an executive board in minutes — complementing App 2 (which adds NL→SQL, forecasts, and AI
reports Looker Studio can't do).

1. <https://lookerstudio.google.com> → Create → **Data source** → **BigQuery**.
2. Pick your project → dataset `hsbc_marts` → table `financial_kpis`. Add more sources for
   `churn_summary`, `ga4_sessions`, and the GA4 export.

**Suggested pages:**

- **Financial performance** — scorecards (net operating income, PBT, cost efficiency ratio);
  time series of `net_operating_income` / `profit_before_tax`; bar of `cost_efficiency_ratio` by quarter.
- **Digital adoption (GA4)** — scorecards (sessions, transactions, conversion rate); pie by
  `platform` (mobile vs web); geo map by `geo`; daily sessions with the Prophet forecast overlaid.
- **Risk & customers** — `churn_summary` stacked bar by geography / risk band; table of
  `churn_high_risk` top customers.

Label GA4 and churn tiles as **prototype / simulated** data on the board. Financials and share
price are real public data.

---

## Assumptions, limitations & provenance

The kind of disclosure a bank's risk and finance functions expect (and what the JD asks for:
"summarize approach, assumptions and limitations").

### Data provenance

| Data | Source | Status |
|---|---|---|
| Group income statement (NII, revenue, ECL, opex, PBT, PAT) | HSBC public quarterly Data Packs (scraped PDFs) | **REAL** |
| Share price / returns | Yahoo Finance, ticker HSBA.L | **REAL** |
| Segment figures used in capital optimizer | shaped like HSBC's segments; illustrative values | **ILLUSTRATIVE** (swap in parsed segment-page data for fully real) |
| App vs web digital adoption | our own prototype (App 1) + traffic simulator | **REAL events, SIMULATED volume** |
| Customer churn / acquisition | synthetic customers (mirrors public ChurnModelling benchmark) | **SIMULATED** |

### What we deliberately never do

- Never attach GA4 to HSBC's real website/app (impossible and confidential).
- Never predict HSBC's real revenue from app traffic — the two layers are kept strictly separate.
- Never claim access to HSBC internal operational data.

### Model-by-model limitations

1. **Stock price (REAL):** daily prices are near-random-walk; ARIMA ≈ naive and both beat
   Prophet. We report directional accuracy, not just RMSE. Not investment advice.
2. **Financials (REAL):** only ~8 usable quarterly points → classical methods only
   (seasonal-naive wins). A trend/LSTM would overfit. Forecasts are indicative.
3. **Traffic (REAL/our app):** Prophet wins here (strong weekly seasonality) — the opposite of
   the stock case, which validates matching models to data.
4. **Transactions (REAL/our app):** conversion rates reflect simulator design (~60%); on real
   GA4 they'd reflect genuine funnel behaviour.
5. **Churn (SIMULATED):** ROC-AUC ~0.71 on synthetic data with transparent signal; SHAP recovers
   the planted drivers. The methodology is the deliverable, ready to point at real data.
6. **Acquisition (SIMULATED):** lead-scoring deciles; top decile ~1.8x base rate.
7. **Risk — market (REAL):** VaR/CVaR three ways + GARCH; historical 99% VaR shows fatter tails
   than Gaussian — a reason not to trust parametric VaR alone.
8. **Risk — credit (REAL):** ECL forecast from the Data Pack series; small sample, so trend
   direction matters more than the point value.
9. **Capital optimization (REAL inputs):** decision-support maximising return on RWA under
   concentration limits — a recommendation, not HSBC's internal policy.

### Known constraints

- Quarterly financial history is short; add more Data Pack URLs to extend it.
- The Jan-2025 segment reorganisation breaks segment-level continuity → we lead with continuous
  group-level series.
- NL→SQL is not infallible; the generated SQL is always shown and validated (SELECT-only,
  dataset allow-list) before running.
- The Flutter app is a complete scaffold; the Python traffic simulator produces equivalent GA4
  events when no Flutter SDK is present on the build machine.

---

## Research references

- **Bank churn** → XGBoost/LightGBM + SHAP; leakage-safe calibrated pipeline (~0.87 ROC-AUC on
  the public benchmark; top 40% captures ~80% churn). Beyond-churn "financial fragmentation"
  XGBoost cascade.
- **Stock price** → ARIMA (stable) vs Prophet (seasonal) vs LSTM/GRU (complex); HSBC-specific
  case study found LSTM lowest error, GRU competitive with faster training.
- **Web traffic** → Prophet handles seasonality/holidays; LSTM for page-view series; Prophet+LSTM hybrid.
- **Acquisition** → propensity / lead-scoring (LogReg interpretable baseline + ensembles);
  Next-Best-Action = propensity + uplift.

Full source URLs were captured during design; content was rephrased for licensing compliance.

---

## Environment

Verified on Windows: Python 3.13.1, pip 24.3.1, git 2.49.0, Node 24.13.1. Needed later: GCP
account (BigQuery, Gemini), GA4 property, Firebase (App 1), Flutter SDK (App 1), Android Studio
(Android builds), macOS (iOS builds only). Secrets (`.env`, `service-account.json`) are
git-ignored and never committed.
