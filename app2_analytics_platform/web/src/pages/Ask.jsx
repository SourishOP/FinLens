import { useState } from "react";
import { Send, Sparkles, Code2 } from "lucide-react";
import { api } from "../api";
import { PageTitle, Loading, ErrorNote } from "../components/ui";
import AutoChart from "../components/AutoChart";

const EXAMPLES = [
  "show revenue by quarter",
  "which quarter had the worst cost efficiency ratio?",
  "average profit before tax across all quarters",
  "churn risk by geography",
  "share price over the last 90 days",
  "count high risk churn customers in the UK",
];

export default function Ask() {
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(false);
  const [res, setRes] = useState(null);

  const run = async (question) => {
    const text = question ?? q;
    if (!text.trim()) return;
    setQ(text);
    setLoading(true);
    setRes(null);
    try {
      setRes(await api.query(text));
    } catch (e) {
      setRes({ ok: false, reason: e.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <PageTitle title="Ask the data"
        subtitle="Type a question in plain English. It becomes a safe, read-only BigQuery query." />

      <div className="card mb-4">
        <div className="flex gap-2">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && run()}
            placeholder="e.g. show profit before tax by quarter"
            className="flex-1 rounded-xl border border-gray-200 px-4 py-2.5 text-sm
                       focus:outline-none focus:ring-2 focus:ring-hsbc-red/30" />
          <button className="btn-primary" onClick={() => run()} disabled={loading}>
            <Send size={16} /> Ask
          </button>
        </div>
        <div className="flex flex-wrap gap-2 mt-3">
          {EXAMPLES.map((ex) => (
            <button key={ex} onClick={() => run(ex)}
              className="pill bg-gray-100 text-gray-600 hover:bg-gray-200">
              {ex}
            </button>
          ))}
        </div>
      </div>

      {loading && <Loading label="Translating & querying…" />}

      {res && !loading && (
        <div className="space-y-4">
          {/* engine + SQL */}
          <div className="card">
            <div className="flex items-center gap-2 mb-2">
              <span className={`pill ${res.engine === "gemini"
                ? "bg-violet-100 text-violet-700" : "bg-gray-100 text-gray-600"}`}>
                <Sparkles size={12} className="mr-1" />
                {res.engine === "gemini" ? "AI (Gemini)" : "Keyword fallback"}
              </span>
              {res.translation_note && <span className="text-xs text-gray-400">{res.translation_note}</span>}
            </div>
            <div className="flex items-center gap-1.5 text-xs text-gray-400 mb-1">
              <Code2 size={13} /> Generated SQL
            </div>
            <pre className="bg-gray-900 text-gray-100 text-xs rounded-xl p-3 overflow-x-auto">
              {res.generated_sql || res.sql}
            </pre>
          </div>

          {/* result */}
          {res.ok
            ? <div className="card"><AutoChart rows={res.rows} hint={res.chart_hint} /></div>
            : <ErrorNote>Could not run: {res.reason}</ErrorNote>}
        </div>
      )}
    </>
  );
}
