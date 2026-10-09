"""HSBC FinOps Analytics & Prediction Platform — App 2 (Streamlit frontend).

The star product. Five feature areas in one concise, polished app:
  1. Dashboard      — GA4-style KPI scorecards + charts
  2. Ask the Data   — natural-language -> BigQuery (with generated SQL + auto-viz)
  3. Predictions    — all 7 model modules
  4. AI Reports     — AI-written analyst report + Excel/PDF export
  5. Data Explorer  — browse warehouse tables

Run (backend must be up on :8000):
    streamlit run app2_analytics_platform/frontend/app.py
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from app2_analytics_platform.frontend import api_client as api
from app2_analytics_platform.frontend.exporters import report_to_pdf, to_excel

# ---------------------------------------------------------------------------
# Page config + theme
# ---------------------------------------------------------------------------
HSBC_RED = "#DB0011"
st.set_page_config(page_title="HSBC FinOps Analytics", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown(f"""
<style>
  .stApp {{ background: #f7f7f8; }}
  [data-testid="stSidebar"] {{ background: #1c1c22; }}
  [data-testid="stSidebar"] * {{ color: #f0f0f0 !important; }}
  h1, h2, h3 {{ color: #11182c; }}
  .kpi-card {{ background:#fff; border-radius:14px; padding:18px 20px;
      box-shadow:0 1px 4px rgba(0,0,0,.08); border-left:5px solid {HSBC_RED}; }}
  .kpi-val {{ font-size:1.9rem; font-weight:700; color:#11182c; }}
  .kpi-lab {{ font-size:.8rem; color:#667; text-transform:uppercase;
      letter-spacing:.5px; }}
  .up {{ color:#0a7d33; font-weight:600; }} .down {{ color:{HSBC_RED}; font-weight:600; }}
  .pill {{ display:inline-block; background:{HSBC_RED}; color:#fff; padding:2px 10px;
      border-radius:12px; font-size:.72rem; margin-left:8px; }}
</style>
""", unsafe_allow_html=True)


def header():
    c1, c2 = st.columns([0.06, 0.94])
    c1.markdown(f"<div style='background:{HSBC_RED};width:46px;height:46px;"
                "border-radius:8px'></div>", unsafe_allow_html=True)
    c2.markdown("## HSBC FinOps Analytics & Prediction Platform")
    h = api.health()
    mode = h.get("warehouse_mode", "unknown") if "error" not in h else "backend down"
    tone = "#0a7d33" if mode == "bigquery" else "#b26a00" if mode == "local" else HSBC_RED
    st.markdown(f"<span style='color:{tone};font-size:.85rem'>warehouse: "
                f"<b>{mode}</b></span>", unsafe_allow_html=True)
    if "error" in h:
        st.error("Backend not reachable. Start it: "
                 "`uvicorn app2_analytics_platform.backend.main:app --port 8000`")
    st.divider()


# ---------------------------------------------------------------------------
# 1. Dashboard
# ---------------------------------------------------------------------------
def page_dashboard():
    st.subheader("Executive dashboard")
    cards = api.kpis()
    if "error" in cards or not cards:
        st.info("No KPI data yet. Run `python -m bigquery.load_to_bq` to populate.")
    else:
        cols = st.columns(len(cards))
        labels = {"net_operating_income": "Net operating income ($m)",
                  "profit_before_tax": "Profit before tax ($m)",
                  "cost_efficiency_ratio": "Cost efficiency (%)"}
        for col, (metric, c) in zip(cols, cards.items()):
            change = c.get("change_pct")
            arrow = ""
            if change is not None:
                cls = "up" if change >= 0 else "down"
                arrow = f"<span class='{cls}'>{'▲' if change>=0 else '▼'} {abs(change)}%</span>"
            col.markdown(
                f"<div class='kpi-card'><div class='kpi-lab'>"
                f"{labels.get(metric, metric)}</div>"
                f"<div class='kpi-val'>{c['value']:,.0f}</div>{arrow}"
                f"<div style='font-size:.72rem;color:#889'>{c['period']}</div></div>",
                unsafe_allow_html=True)

    fin = api.financials()
    series = fin.get("series", []) if "error" not in fin else []
    if series:
        df = pd.DataFrame(series)
        df["period_end"] = pd.to_datetime(df["period_end"])
        left, right = st.columns(2)
        with left:
            st.markdown("**Revenue & profit trend** (REAL, Data Packs)")
            fig = px.line(df, x="period_end",
                          y=[c for c in ["net_operating_income", "profit_before_tax"]
                             if c in df.columns],
                          markers=True)
            fig.update_layout(height=320, legend_title="", margin=dict(t=10))
            st.plotly_chart(fig, use_container_width=True)
        with right:
            if "cost_efficiency_ratio" in df.columns:
                st.markdown("**Cost efficiency ratio** (lower is better)")
                fig2 = px.bar(df, x="period_end", y="cost_efficiency_ratio",
                              color_discrete_sequence=[HSBC_RED])
                fig2.update_layout(height=320, margin=dict(t=10))
                st.plotly_chart(fig2, use_container_width=True)

    # Churn geography (GA4-style breakdown) via NL endpoint
    q = api.nl_query("show me churn by geography")
    if q.get("ok") and q.get("rows"):
        st.markdown("**Churn risk by geography** "
                    "<span class='pill'>SIMULATED</span>", unsafe_allow_html=True)
        cdf = pd.DataFrame(q["rows"])
        fig3 = px.bar(cdf, x="geography", y="customers", color="risk_band",
                      barmode="group",
                      color_discrete_map={"Low": "#9fb3c8", "Medium": "#f0a202",
                                          "High": HSBC_RED})
        fig3.update_layout(height=320, margin=dict(t=10))
        st.plotly_chart(fig3, use_container_width=True)


# ---------------------------------------------------------------------------
# 2. Ask the Data (NL -> SQL)
# ---------------------------------------------------------------------------
def _auto_chart(df: pd.DataFrame, hint: str):
    if df.empty:
        st.info("No rows returned."); return
    if hint == "scorecard":
        st.metric(df.columns[-1], df.iloc[0, -1]); return
    if hint == "line" and df.shape[1] >= 2:
        fig = px.line(df, x=df.columns[0], y=df.columns[1:].tolist(), markers=True)
        st.plotly_chart(fig, use_container_width=True)
    elif hint == "bar" and df.shape[1] >= 2:
        ycol = df.columns[-1]
        fig = px.bar(df, x=df.columns[0], y=ycol,
                     color_discrete_sequence=[HSBC_RED])
        st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df, use_container_width=True, hide_index=True)


def page_ask():
    st.subheader("Ask the data")
    st.caption("Type a question in plain English. It becomes a validated, "
               "read-only BigQuery query. The generated SQL is always shown.")
    examples = ["show me revenue by quarter", "churn by geography",
                "cost efficiency over time", "share price last 90 days",
                "top high risk churn customers"]
    picked = st.selectbox("Try an example (or type your own below)", [""] + examples)
    question = st.text_input("Your question", value=picked,
                             placeholder="e.g. show me profit before tax by quarter")
    if st.button("Run", type="primary") and question.strip():
        with st.spinner("Translating + querying..."):
            res = api.nl_query(question)
        if "error" in res:
            st.error(res["error"]); return
        eng = res.get("engine", "?")
        st.markdown(f"**Engine:** `{eng}`" +
                    (f"  ·  _{res['translation_note']}_" if res.get("translation_note") else ""))
        st.code(res.get("generated_sql") or res.get("sql"), language="sql")
        if not res.get("ok"):
            st.error(f"Rejected / failed: {res.get('reason')}"); return
        df = pd.DataFrame(res["rows"])
        _auto_chart(df, res.get("chart_hint", "table"))
        st.session_state["last_result"] = df


# ---------------------------------------------------------------------------
# 3. Predictions
# ---------------------------------------------------------------------------
def page_predictions():
    st.subheader("Predictions — 7 modules")
    tabs = st.tabs(["Stock price", "Market risk", "Credit risk (ECL)",
                    "Financials", "Capital optimization", "Churn"])

    with tabs[0]:
        st.caption("REAL data (yfinance HSBA.L). Model bake-off by RMSE.")
        if st.button("Run bake-off", key="sp"):
            r = api.forecast("stock_price")
            if r.get("leaderboard"):
                st.dataframe(pd.DataFrame(r["leaderboard"]), hide_index=True,
                             use_container_width=True)

    with tabs[1]:
        st.caption("REAL data. Value-at-Risk + GARCH volatility.")
        if st.button("Compute VaR", key="mr"):
            r = api.forecast("market_risk")
            if r.get("var"):
                st.metric("Annualised volatility", f"{r['annualised_vol']*100:.1f}%")
                vdf = pd.DataFrame(r["var"])
                vdf["var"] = (vdf["var"] * 100).round(2)
                vdf["cvar"] = (vdf["cvar"] * 100).round(2)
                st.dataframe(vdf, hide_index=True, use_container_width=True)

    with tabs[2]:
        st.caption("REAL data (Data Pack ECL series).")
        if st.button("Forecast ECL", key="cr"):
            r = api.forecast("credit_risk")
            if "history" in r:
                hist = pd.DataFrame({"period": list(r["history"]),
                                     "ecl_m": list(r["history"].values())})
                st.plotly_chart(px.bar(hist, x="period", y="ecl_m",
                                color_discrete_sequence=[HSBC_RED]),
                                use_container_width=True)
                st.write(f"Trend: **ECL {r['trend']}** · forecast:", r["forecast"])

    with tabs[3]:
        st.caption("REAL data. Quarterly forecast + backtest.")
        metric = st.selectbox("Metric", ["net_operating_income", "profit_before_tax"])
        if st.button("Forecast", key="fin"):
            r = api.forecast("financials", metric=metric)
            if r.get("forward"):
                st.dataframe(pd.DataFrame(r["forward"]), hide_index=True,
                             use_container_width=True)
                bt = r.get("backtest", {}).get("results", {})
                rows = [{"method": k, **v["metrics"]} for k, v in bt.items()
                        if "metrics" in v]
                if rows:
                    st.markdown("**Backtest (lower MAPE better):**")
                    st.dataframe(pd.DataFrame(rows), hide_index=True,
                                 use_container_width=True)

    with tabs[4]:
        st.caption("REAL-shaped segments. Max return on RWA under concentration limits.")
        if st.button("Optimize", key="opt"):
            r = api.forecast("optimization")
            if r.get("recommended_rwa_bn"):
                comp = pd.DataFrame([
                    {"segment": s, "current_rwa_bn": r["current"][s]["rwa_bn"],
                     "recommended_rwa_bn": r["recommended_rwa_bn"][s],
                     "rorwa_pct": r["current"][s]["rorwa_pct"]}
                    for s in r["recommended_rwa_bn"]])
                st.dataframe(comp, hide_index=True, use_container_width=True)
                st.success(f"Modelled PBT uplift: {r['uplift_m']:,} $m "
                           f"({r['uplift_pct']}%)")

    with tabs[5]:
        st.caption("SIMULATED customers. Churn risk by geography/band.")
        if st.button("Load churn summary", key="ch"):
            r = api.forecast("churn")
            if r.get("summary"):
                st.dataframe(pd.DataFrame(r["summary"]), hide_index=True,
                             use_container_width=True)


# ---------------------------------------------------------------------------
# 4. AI Reports + export
# ---------------------------------------------------------------------------
def page_reports():
    st.subheader("AI analyst report")
    topic = st.text_input("Report topic",
                          value="HSBC Q4 revenue seasonality and cost efficiency")
    if st.button("Generate report", type="primary"):
        fin = api.financials().get("series", [])
        data = {}
        if fin:
            last = fin[-1]
            data = {k: last[k] for k in ("period_end", "net_operating_income",
                    "profit_before_tax", "cost_efficiency_ratio") if k in last}
        res = api.report(topic, data)
        md = res.get("report", "")
        st.session_state["report_md"] = md
        st.session_state["report_topic"] = topic
        st.markdown(f"_engine: {res.get('engine')}_"
                    + (f" · {res.get('note')}" if res.get("note") else ""))
        st.markdown(md)

    if st.session_state.get("report_md"):
        st.divider()
        st.markdown("**Export**")
        c1, c2 = st.columns(2)
        pdf = report_to_pdf(st.session_state.get("report_topic", "Report"),
                            st.session_state["report_md"])
        c1.download_button("Download PDF", pdf, "hsbc_report.pdf", "application/pdf")
        fin = api.financials().get("series", [])
        if fin:
            xls = to_excel({"financials": pd.DataFrame(fin)})
            c2.download_button("Download Excel", xls, "hsbc_financials.xlsx",
                               "application/vnd.openxmlformats-officedocument."
                               "spreadsheetml.sheet")


# ---------------------------------------------------------------------------
# 5. Data explorer
# ---------------------------------------------------------------------------
def page_explorer():
    st.subheader("Data explorer")
    t = api.tables()
    if "error" in t:
        st.error(t["error"]); return
    st.write("Warehouse tables:")
    st.code("\n".join(t.get("tables", [])) or "(none)")
    sql = st.text_area("Run read-only SQL (validated server-side)",
                       value="SELECT * FROM hsbc_marts.financial_kpis "
                             "ORDER BY period_end")
    if st.button("Execute"):
        res = api.raw_query(sql)
        if res.get("ok"):
            df = pd.DataFrame(res["rows"])
            st.dataframe(df, use_container_width=True, hide_index=True)
            if not df.empty:
                st.download_button("Export Excel", to_excel({"result": df}),
                                   "query_result.xlsx")
        else:
            st.error(res.get("reason", "query failed"))


# ---------------------------------------------------------------------------
PAGES = {
    "📊 Dashboard": page_dashboard,
    "💬 Ask the data": page_ask,
    "🔮 Predictions": page_predictions,
    "📝 AI reports": page_reports,
    "🗃️ Data explorer": page_explorer,
}


def main():
    header()
    with st.sidebar:
        st.markdown("### Navigation")
        choice = st.radio("", list(PAGES.keys()), label_visibility="collapsed")
        st.divider()
        st.caption("REAL: financials, share price, risk.\n\n"
                   "SIMULATED (labelled): churn, acquisition.\n\n"
                   "Never predicts HSBC revenue from app traffic.")
    PAGES[choice]()


main()
