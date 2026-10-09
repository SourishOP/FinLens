import { useEffect, useState } from "react";
import {
  ResponsiveContainer, LineChart, Line, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend,
} from "recharts";
import { api } from "../api";
import { fmt, fmtQuarter, HSBC_RED, CHART_COLORS } from "../format";
import { PageTitle, KpiCard, ChartCard, Loading, ErrorNote } from "../components/ui";

export default function Overview() {
  const [kpis, setKpis] = useState(null);
  const [series, setSeries] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    Promise.all([api.kpis(), api.financials()])
      .then(([k, f]) => {
        setKpis(k.cards || []);
        setSeries((f.series || []).map((r) => ({ ...r, q: fmtQuarter(r.period_end) })));
      })
      .catch((e) => setErr(e.message));
  }, []);

  if (err) return <><PageTitle title="Overview" /><ErrorNote>Backend not reachable: {err}. Start it with uvicorn on :8000.</ErrorNote></>;
  if (!kpis || !series) return <><PageTitle title="Overview" /><Loading /></>;

  return (
    <>
      <PageTitle title="Executive overview"
        subtitle="Group performance — real published financials" />

      {/* KPI row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-5">
        {kpis.map((c) => (
          <KpiCard key={c.key} label={c.label} display={c.display} help={c.help}
            changePct={c.change_pct} trendGood={c.trend_good} period={fmtQuarter(c.period)} />
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ChartCard title="Revenue & profit by quarter" subtitle="Net operating income vs profit before tax ($m)">
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={series} margin={{ left: -10, right: 8, top: 6 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef0f3" />
              <XAxis dataKey="q" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}bn`} />
              <Tooltip formatter={(v) => fmt(v, "$m")} />
              <Legend />
              <Line type="monotone" dataKey="net_operating_income" name="Revenue"
                stroke={HSBC_RED} strokeWidth={2.5} dot={{ r: 3 }} />
              <Line type="monotone" dataKey="profit_before_tax" name="Profit before tax"
                stroke={CHART_COLORS[1]} strokeWidth={2.5} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Cost efficiency ratio" subtitle="Costs as % of income — lower is better">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={series} margin={{ left: -10, right: 8, top: 6 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef0f3" />
              <XAxis dataKey="q" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${v}%`} />
              <Tooltip formatter={(v) => fmt(v, "%")} />
              <Bar dataKey="cost_efficiency_ratio" name="Cost efficiency" fill={HSBC_RED} radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </>
  );
}
