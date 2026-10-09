import {
  ResponsiveContainer, LineChart, Line, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip,
} from "recharts";
import { HSBC_RED } from "../format";

// Renders query results as the most sensible visual, plus a data table.
export default function AutoChart({ rows, hint }) {
  if (!rows || rows.length === 0)
    return <p className="text-sm text-gray-400 py-6 text-center">No rows returned.</p>;

  const cols = Object.keys(rows[0]);

  // single value -> big number
  if (hint === "scorecard" || (rows.length === 1 && cols.length === 1)) {
    const v = rows[0][cols[cols.length - 1]];
    return (
      <div className="py-6 text-center">
        <div className="text-4xl font-extrabold text-gray-900">
          {typeof v === "number" ? v.toLocaleString() : String(v)}
        </div>
        <div className="text-sm text-gray-500 mt-1">{cols[cols.length - 1]}</div>
      </div>
    );
  }

  const x = cols[0];
  const yCols = cols.slice(1).filter((c) => typeof rows[0][c] === "number");
  const isLine = /date|period|month|day|quarter/i.test(x);

  return (
    <div className="space-y-4">
      {yCols.length > 0 && (
        <ResponsiveContainer width="100%" height={280}>
          {isLine ? (
            <LineChart data={rows} margin={{ left: -8, right: 8, top: 6 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef0f3" />
              <XAxis dataKey={x} tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              {yCols.map((c, i) => (
                <Line key={c} type="monotone" dataKey={c}
                  stroke={i === 0 ? HSBC_RED : "#2563eb"} strokeWidth={2.4} dot={{ r: 2 }} />
              ))}
            </LineChart>
          ) : (
            <BarChart data={rows} margin={{ left: -8, right: 8, top: 6 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef0f3" />
              <XAxis dataKey={x} tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              {yCols.map((c, i) => (
                <Bar key={c} dataKey={c} fill={i === 0 ? HSBC_RED : "#2563eb"} radius={[5, 5, 0, 0]} />
              ))}
            </BarChart>
          )}
        </ResponsiveContainer>
      )}
      <DataTable rows={rows} />
    </div>
  );
}

export function DataTable({ rows }) {
  if (!rows?.length) return null;
  const cols = Object.keys(rows[0]);
  return (
    <div className="overflow-x-auto rounded-xl border border-gray-100">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 text-gray-500">
          <tr>{cols.map((c) => <th key={c} className="text-left font-semibold px-3 py-2 whitespace-nowrap">{c}</th>)}</tr>
        </thead>
        <tbody>
          {rows.slice(0, 100).map((r, i) => (
            <tr key={i} className="border-t border-gray-100">
              {cols.map((c) => (
                <td key={c} className="px-3 py-2 whitespace-nowrap text-gray-700">
                  {typeof r[c] === "number" ? r[c].toLocaleString(undefined, { maximumFractionDigits: 2 }) : String(r[c])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
