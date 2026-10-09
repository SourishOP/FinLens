import { useEffect, useState } from "react";
import {
  ResponsiveContainer, AreaChart, Area, BarChart, Bar, LineChart, Line,
  PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from "recharts";
import { api } from "../api";
import { HSBC_RED, CHART_COLORS } from "../format";
import { PageTitle, ChartCard, Loading, ErrorNote, SourcePill } from "../components/ui";
import { DataTable } from "../components/AutoChart";
import ErrorBoundary from "../components/ErrorBoundary";

const TABS = [
  ["overview", "Overview"], ["realtime", "Realtime"], ["acquisition", "Acquisition"],
  ["engagement", "Engagement"], ["retention", "Retention"],
  ["demographics", "Demographics"], ["tech", "Tech"],
];

export default function GA4() {
  const [tab, setTab] = useState("overview");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);

  useEffect(() => {
    setLoading(true); setData(null); setErr(null);
    api.ga4Report(tab)
      .then((d) => { if (d.error) setErr(d.error); else setData(d); })
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false));
  }, [tab]);

  return (
    <>
      <PageTitle title="Digital analytics (GA4)"
        subtitle="GA4-style reports on app & web usage, from our GA4-instrumented prototype." />

      <div className="flex gap-2 overflow-x-auto pb-2 mb-4">
        {TABS.map(([k, label]) => (
          <button key={k} onClick={() => setTab(k)}
            className={`px-3.5 py-2 rounded-xl text-sm font-medium whitespace-nowrap transition-colors ${
              tab === k ? "bg-hsbc-red text-white" : "bg-white text-gray-600 hover:bg-gray-100"}`}>
            {label}
          </button>
        ))}
      </div>

      {data?.source && <div className="mb-4"><SourcePill source={"REAL — " + data.source} /></div>}
      {loading && <Loading label="Loading report…" />}
      {err && <ErrorNote>{err}</ErrorNote>}
      {data && !loading && (
        <ErrorBoundary resetKey={tab}>
          <Report tab={tab} d={data} />
        </ErrorBoundary>
      )}
    </>
  );
}

function Scorecards({ items }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
      {items.map((it) => (
        <div key={it.label} className="card">
          <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">{it.label}</div>
          <div className="text-2xl font-extrabold text-gray-900 mt-1">{it.value}</div>
        </div>
      ))}
    </div>
  );
}

function NoData() {
  return <p className="text-sm text-gray-400 py-6 text-center">No data for this view yet.</p>;
}

function Donut({ data, nameKey, valueKey }) {
  if (!data?.length) return <NoData />;
  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie data={data} dataKey={valueKey} nameKey={nameKey} innerRadius={55}
          outerRadius={90} paddingAngle={2}>
          {data.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
        </Pie>
        <Tooltip /><Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}

function HBar({ data, cat, val, color = HSBC_RED }) {
  if (!data?.length) return <NoData />;
  return (
    <ResponsiveContainer width="100%" height={Math.max(200, data.length * 38)}>
      <BarChart data={data} layout="vertical" margin={{ left: 20, right: 16 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#eef0f3" horizontal={false} />
        <XAxis type="number" tick={{ fontSize: 11 }} />
        <YAxis type="category" dataKey={cat} tick={{ fontSize: 11 }} width={110} />
        <Tooltip />
        <Bar dataKey={val} fill={color} radius={[0, 5, 5, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function num(n) { return n === null || n === undefined ? "—" : Number(n).toLocaleString(); }

function Report({ tab, d }) {
  if (tab === "overview") {
    const k = d.kpis || {};
    return (
      <>
        <Scorecards items={[
          { label: "Sessions", value: num(k.sessions) },
          { label: "New users", value: num(k.new_users) },
          { label: "Returning users", value: num(k.returning_users) },
          { label: "Conversions", value: num(k.conversions) },
          { label: "Engagement rate", value: `${k.engagement_rate ?? "—"}%` },
          { label: "Avg engagement", value: `${k.avg_engagement_sec ?? "—"}s` },
          { label: "Engaged sessions", value: num(k.engaged_sessions) },
          { label: "Total sessions", value: num(k.total_sessions) },
        ]} />
        <ChartCard title="Sessions & conversions over time" subtitle="Daily, last 120 days">
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={d.trend} margin={{ left: -8, right: 8, top: 6 }}>
              <defs>
                <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={HSBC_RED} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={HSBC_RED} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef0f3" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} minTickGap={40} />
              <YAxis tick={{ fontSize: 11 }} /><Tooltip /><Legend />
              <Area type="monotone" dataKey="sessions" stroke={HSBC_RED} fill="url(#g1)" strokeWidth={2} />
              <Line type="monotone" dataKey="conversions" stroke={CHART_COLORS[1]} strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
      </>
    );
  }

  if (tab === "realtime") {
    const k = d.kpis || {};
    return (
      <>
        <Scorecards items={[
          { label: "Active users (latest)", value: num(k.active_users) },
          { label: "Conversions (latest)", value: num(k.conversions) },
        ]} />
        <div className="grid lg:grid-cols-2 gap-4">
          <ChartCard title="Active users by country"><HBar data={d.by_country} cat="country" val="active_users" /></ChartCard>
          <ChartCard title="Active users by device"><Donut data={d.by_device} nameKey="device_category" valueKey="active_users" /></ChartCard>
        </div>
        <div className="mt-4"><ChartCard title="Top events (latest window)"><DataTable rows={d.top_events} /></ChartCard></div>
      </>
    );
  }

  if (tab === "acquisition") {
    return (
      <>
        <ChartCard title="Sessions by channel" subtitle="How users arrive">
          <HBar data={d.by_channel} cat="channel" val="sessions" />
        </ChartCard>
        <div className="grid lg:grid-cols-2 gap-4 mt-4">
          <ChartCard title="Channel detail"><DataTable rows={d.by_channel} /></ChartCard>
          <ChartCard title="By source"><DataTable rows={d.by_source} /></ChartCard>
        </div>
      </>
    );
  }

  if (tab === "engagement") {
    const k = d.kpis || {};
    return (
      <>
        <Scorecards items={[
          { label: "Avg engagement time", value: `${k.avg_engagement_sec ?? "—"}s` },
          { label: "Engaged sessions", value: num(k.engaged_sessions) },
          { label: "Sessions", value: num(k.sessions) },
          { label: "Engaged / day", value: num(k.engaged_per_day) },
        ]} />
        <div className="grid lg:grid-cols-2 gap-4">
          <ChartCard title="Events by name"><HBar data={d.events} cat="event_name" val="event_count" /></ChartCard>
          <ChartCard title="Events over time">
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={d.trend} margin={{ left: -8, right: 8, top: 6 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eef0f3" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} minTickGap={40} />
                <YAxis tick={{ fontSize: 11 }} /><Tooltip />
                <Line type="monotone" dataKey="events" stroke={HSBC_RED} strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>
        </div>
      </>
    );
  }

  if (tab === "retention") {
    return (
      <>
        <ChartCard title="New vs returning users" subtitle="Daily">
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={d.new_vs_returning} margin={{ left: -8, right: 8, top: 6 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef0f3" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} minTickGap={40} />
              <YAxis tick={{ fontSize: 11 }} /><Tooltip /><Legend />
              <Area type="monotone" dataKey="new_users" stackId="1" stroke={HSBC_RED} fill={HSBC_RED} fillOpacity={0.5} />
              <Area type="monotone" dataKey="returning_users" stackId="1" stroke={CHART_COLORS[1]} fill={CHART_COLORS[1]} fillOpacity={0.5} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
        <div className="mt-4"><ChartCard title="Weekly cohort retention" subtitle="Users active N weeks after first visit">
          <CohortHeatmap cells={d.cohort} />
        </ChartCard></div>
      </>
    );
  }

  if (tab === "demographics") {
    return (
      <>
        <ChartCard title="Users by country"><HBar data={d.country} cat="country" val="users" /></ChartCard>
        <div className="grid lg:grid-cols-2 gap-4 mt-4">
          <ChartCard title="Users by age"><HBar data={d.age} cat="age_band" val="users" color={CHART_COLORS[1]} /></ChartCard>
          <ChartCard title="Users by gender"><Donut data={d.gender} nameKey="gender" valueKey="users" /></ChartCard>
        </div>
      </>
    );
  }

  if (tab === "tech") {
    return (
      <div className="grid lg:grid-cols-3 gap-4">
        <ChartCard title="By device"><Donut data={d.device} nameKey="device_category" valueKey="users" /></ChartCard>
        <ChartCard title="By browser"><Donut data={d.browser} nameKey="browser" valueKey="users" /></ChartCard>
        <ChartCard title="By operating system"><Donut data={d.operating_system} nameKey="operating_system" valueKey="users" /></ChartCard>
      </div>
    );
  }
  return <pre className="text-xs bg-gray-50 p-3 rounded-xl overflow-x-auto">{JSON.stringify(d, null, 2)}</pre>;
}

// Retention cohort heatmap: cohort rows x weeks-since columns, colour = % of wk0.
function CohortHeatmap({ cells }) {
  if (!cells?.length) return <p className="text-sm text-gray-400">No cohort data.</p>;
  const cohorts = [...new Set(cells.map((c) => c.cohort))].sort();
  const maxWeek = Math.max(...cells.map((c) => c.weeks_since));
  const lookup = {};
  cells.forEach((c) => { lookup[`${c.cohort}|${c.weeks_since}`] = c.active; });
  const base = {};
  cohorts.forEach((co) => { base[co] = lookup[`${co}|0`] || 1; });

  const shade = (pct) => {
    // red intensity by retention %
    const a = Math.min(1, Math.max(0.05, pct));
    return `rgba(219,0,17,${a})`;
  };

  return (
    <div className="overflow-x-auto">
      <table className="text-xs border-separate" style={{ borderSpacing: 3 }}>
        <thead>
          <tr>
            <th className="text-left px-2 py-1 text-gray-500">Cohort (week of)</th>
            {Array.from({ length: maxWeek + 1 }, (_, w) => (
              <th key={w} className="px-2 py-1 text-gray-500">W{w}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {cohorts.map((co) => (
            <tr key={co}>
              <td className="px-2 py-1 whitespace-nowrap text-gray-600">{co}</td>
              {Array.from({ length: maxWeek + 1 }, (_, w) => {
                const v = lookup[`${co}|${w}`];
                if (v === undefined) return <td key={w} />;
                const pct = v / base[co];
                return (
                  <td key={w} className="px-2 py-1 text-center rounded font-medium"
                    style={{ background: shade(pct), color: pct > 0.5 ? "#fff" : "#111" }}
                    title={`${v} users (${Math.round(pct * 100)}%)`}>
                    {Math.round(pct * 100)}%
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
