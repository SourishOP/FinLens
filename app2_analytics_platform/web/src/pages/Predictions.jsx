import { useEffect, useState } from "react";
import {
  ResponsiveContainer, BarChart, Bar, LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend,
} from "recharts";
import { ChevronRight } from "lucide-react";
import { api } from "../api";
import { fmt, HSBC_RED, CHART_COLORS } from "../format";
import { PageTitle, ChartCard, Loading, ErrorNote, SourcePill } from "../components/ui";
import { DataTable } from "../components/AutoChart";

export default function Predictions() {
  const [modules, setModules] = useState(null);
  const [active, setActive] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { api.modules().then((m) => setModules(m.modules)).catch(() => setModules([])); }, []);

  const open = async (mod) => {
    setActive(mod); setData(null); setLoading(true);
    try { setData(await api.forecast(mod.key)); }
    catch (e) { setData({ error: e.message }); }
    finally { setLoading(false); }
  };

  if (!modules) return <><PageTitle title="Predictions" /><Loading /></>;

  return (
    <>
      <PageTitle title="Predictions"
        subtitle="Nine forecasting & risk models. Click any card to run it live." />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {modules.map((m) => (
          <button key={m.key} onClick={() => open(m)}
            className="card text-left hover:ring-2 hover:ring-hsbc-red/20">
            <div className="flex items-center justify-between mb-2">
              <SourcePill source={m.source} />
              <ChevronRight size={16} className="text-gray-300" />
            </div>
            <h3 className="font-bold text-gray-900">{m.title}</h3>
            <p className="text-sm text-gray-500 mt-1 leading-snug">{m.desc}</p>
          </button>
        ))}
      </div>

      {active && (
        <div className="mt-6">
          <div className="flex items-center gap-3 mb-3">
            <h2 className="text-lg font-extrabold text-gray-900">{active.title}</h2>
            <SourcePill source={active.source} />
          </div>
          {loading && <Loading label={`Running ${active.title}…`} />}
          {data?.error && <ErrorNote>{data.error}</ErrorNote>}
          {data && !data.error && !loading && <ModuleResult mod={active.key} data={data} />}
        </div>
      )}
    </>
  );
}

function Stat({ label, value, help }) {
  return (
    <div className="card">
      <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">{label}</div>
      <div className="text-2xl font-extrabold text-gray-900 mt-1">{value}</div>
      {help && <div className="text-xs text-gray-400 mt-1">{help}</div>}
    </div>
  );
}

function ModuleResult({ mod, data }) {
  if (mod === "financials") {
    const hist = (data.history || []).map((r) => ({ q: r.period_end?.slice(0, 7), actual: r.value_m }));
    const fwd = (data.forward || []).map((r) => ({ q: r.period_end?.slice(0, 7), forecast: r.forecast_m }));
    const series = [...hist, ...fwd];
    const last = fwd[fwd.length - 1];
    return (
      <>
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
          <Stat label="Next-quarter forecast" value={fwd[0] ? fmt(fwd[0].forecast, "$m") : "—"}
            help={fwd[0]?.q} />
          <Stat label="In 4 quarters" value={last ? fmt(last.forecast, "$m") : "—"} help={last?.q} />
          <Stat label="Model" value={data.best_method || "seasonal"}
            help={`${data.best_mape ?? ""}% avg error`} />
        </div>
        <ChartCard title="Revenue/profit — history & forecast"
          subtitle={`Actual then projected ($m) · model: ${data.best_method || "seasonal-naive"}`}>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={series} margin={{ left: -8, right: 8, top: 6 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef0f3" />
              <XAxis dataKey="q" tick={{ fontSize: 10 }} minTickGap={20} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}bn`} />
              <Tooltip formatter={(v) => fmt(v, "$m")} /><Legend />
              <Line type="monotone" dataKey="actual" name="Actual" stroke="#11182c" strokeWidth={2} dot={{ r: 2 }} connectNulls />
              <Line type="monotone" dataKey="forecast" name="Forecast" stroke={HSBC_RED} strokeWidth={2.5} strokeDasharray="6 4" dot={{ r: 2 }} connectNulls />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
      </>
    );
  }

  if (mod === "stock_price") {
    const hist = (data.history || []).map((r) => ({ date: r.date, actual: r.price }));
    const fc = (data.forecast || []).map((r) => ({ date: r.date, forecast: r.price }));
    // bridge: last actual point also carries the forecast start for a connected line
    const series = [...hist.map((h) => ({ ...h })), ...fc];
    const up = (data.change_pct ?? 0) >= 0;
    return (
      <>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          <Stat label="Current price" value={`${data.last_price} GBp`} help={`as of ${data.last_date}`} />
          <Stat label={`Forecast (+${data.horizon_days}d)`} value={`${data.target_price} GBp`}
            help={`best model: ${data.best_model}`} />
          <Stat label="Expected change" value={`${up ? "+" : ""}${data.change_pct}%`}
            help={up ? "projected rise" : "projected fall"} />
          <Stat label="Model accuracy" value={`${data.validation?.avg_pct_error}% err`}
            help={`direction ${data.validation?.direction_correct_pct}% correct`} />
        </div>
        <ChartCard title={`Share-price forecast (${data.ticker})`}
          subtitle={`History + next ${data.horizon_days} trading days · model: ${data.best_model}`}>
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={series} margin={{ left: -8, right: 8, top: 6 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef0f3" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} minTickGap={40} />
              <YAxis tick={{ fontSize: 11 }} domain={["auto", "auto"]} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="actual" name="Actual" stroke="#11182c"
                strokeWidth={2} dot={false} connectNulls />
              <Line type="monotone" dataKey="forecast" name="Forecast" stroke={HSBC_RED}
                strokeWidth={2.5} strokeDasharray="6 4" dot={false} connectNulls />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
      </>
    );
  }

  if (mod === "market_risk") {
    const v95 = (data.var || []).filter((r) => r.confidence === 0.95);
    return (
      <>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          <Stat label="Annualised volatility" value={fmt(data.annualised_vol * 100, "%")}
            help="How much the share price swings per year" />
          {v95.slice(0, 3).map((r) => (
            <Stat key={r.method} label={`VaR 95% · ${r.method}`} value={fmt(r.var * 100, "%")}
              help="Worst expected 1-day loss, 95% confidence" />
          ))}
        </div>
        <ChartCard title="Value-at-Risk by method" subtitle="One-day loss at 95% confidence (%)">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={v95.map((r) => ({ method: r.method, VaR: +(r.var * 100).toFixed(2) }))}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef0f3" />
              <XAxis dataKey="method" tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v) => `${v}%`} />
              <Bar dataKey="VaR" fill={HSBC_RED} radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </>
    );
  }

  if (mod === "credit_risk") {
    const hist = Object.entries(data.history || {}).map(([q, v]) => ({ q: q.slice(0, 7), v }));
    return (
      <>
        <div className="mb-3">
          <span className={`pill ${data.trend === "rising" ? "bg-red-100 text-red-700" : "bg-green-100 text-green-700"}`}>
            Credit losses {data.trend}
          </span>
        </div>
        <ChartCard title="Expected credit losses" subtitle="Quarterly loan-loss charge ($m) — rising = more risk">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={hist}><CartesianGrid strokeDasharray="3 3" stroke="#eef0f3" />
              <XAxis dataKey="q" tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v) => fmt(v, "$m")} />
              <Bar dataKey="v" name="ECL" fill={HSBC_RED} radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </>
    );
  }

  if (mod === "optimization") {
    const rows = Object.keys(data.recommended_rwa_bn || {}).map((s) => ({
      segment: s,
      "Current capital ($bn)": data.current[s].rwa_bn,
      "Recommended ($bn)": data.recommended_rwa_bn[s],
      "Return on capital %": data.current[s].rorwa_pct,
    }));
    return (
      <>
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
          <Stat label="Current total profit" value={fmt(data.current_total_pbt_m, "$m")} />
          <Stat label="Optimised profit" value={fmt(data.optimised_total_pbt_m, "$m")} />
          <Stat label="Modelled uplift" value={`+${data.uplift_pct}%`}
            help={`${fmt(data.uplift_m, "$m")} more profit`} />
        </div>
        <ChartCard title="Recommended capital allocation"
          subtitle="Shift capital toward higher-return segments (within risk limits)">
          <DataTable rows={rows} />
        </ChartCard>
      </>
    );
  }

  if (mod === "churn") {
    const byGeo = {};
    (data.summary || []).forEach((r) => {
      byGeo[r.geography] = byGeo[r.geography] || { geography: r.geography };
      byGeo[r.geography][r.risk_band] = r.customers;
    });
    const rows = Object.values(byGeo);
    return (
      <ChartCard title="Customer churn risk by region" subtitle="Number of customers in each risk band">
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={rows}><CartesianGrid strokeDasharray="3 3" stroke="#eef0f3" />
            <XAxis dataKey="geography" tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} />
            <Tooltip /><Legend />
            <Bar dataKey="Low" stackId="a" fill="#9fb3c8" />
            <Bar dataKey="Medium" stackId="a" fill="#f0a202" />
            <Bar dataKey="High" stackId="a" fill={HSBC_RED} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>
    );
  }

  if (mod === "traffic") {
    const fwd = (data.forward || []).map((r) => ({ d: r.date?.slice(5), sessions: r.sessions }));
    return (
      <ChartCard title="Daily sessions forecast (next 14 days)"
        subtitle="App + web traffic on our GA4 prototype">
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={fwd}><CartesianGrid strokeDasharray="3 3" stroke="#eef0f3" />
            <XAxis dataKey="d" tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} />
            <Tooltip />
            <Line type="monotone" dataKey="sessions" stroke={HSBC_RED} strokeWidth={2.5} dot={{ r: 2 }} />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>
    );
  }

  if (mod === "acquisition") {
    const rows = (data.by_geography || []).map((r) => ({
      geography: r.geography, "Customers": r.customers, "Avg propensity": r.avg_propensity,
    }));
    return (
      <div className="grid lg:grid-cols-2 gap-4">
        <ChartCard title="New-account propensity by region"
          subtitle="Average likelihood of opening a new product (higher = priority)">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={rows}><CartesianGrid strokeDasharray="3 3" stroke="#eef0f3" />
              <XAxis dataKey="geography" tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="Avg propensity" fill={HSBC_RED} radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Detail"><DataTable rows={rows} /></ChartCard>
      </div>
    );
  }

  if (mod === "transactions") {
    const rows = (data.by_channel || []).map((r) => ({
      channel: r.platform, "Sessions": r.sessions, "Transactions": r.transactions,
      "Conversion %": +(r.conversion_rate * 100).toFixed(1),
    }));
    return (
      <div className="grid lg:grid-cols-2 gap-4">
        <ChartCard title="Conversion by channel" subtitle="Mobile vs web — % of sessions that transact">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={rows}><CartesianGrid strokeDasharray="3 3" stroke="#eef0f3" />
              <XAxis dataKey="channel" tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v) => `${v}%`} />
              <Bar dataKey="Conversion %" fill={HSBC_RED} radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Channel detail"><DataTable rows={rows} /></ChartCard>
      </div>
    );
  }

  return <pre className="text-xs bg-gray-50 p-3 rounded-xl overflow-x-auto">{JSON.stringify(data, null, 2)}</pre>;
}

function BacktestTable({ results }) {
  if (!results) return <p className="text-sm text-gray-400">No backtest available.</p>;
  const rows = Object.entries(results).filter(([, v]) => v.metrics)
    .map(([name, v]) => ({ method: name.replace(/_/g, " "), "Avg % error": +v.metrics.MAPE.toFixed(1) }))
    .sort((a, b) => a["Avg % error"] - b["Avg % error"]);
  return <DataTable rows={rows} />;
}
