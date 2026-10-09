import { useState } from "react";
import { FileText, Sparkles } from "lucide-react";
import { api } from "../api";
import { PageTitle, Loading, ErrorNote } from "../components/ui";

const TOPICS = [
  "HSBC Q4 revenue seasonality and cost efficiency",
  "Credit risk outlook from expected credit losses",
  "Capital allocation opportunities across segments",
];

function renderMarkdown(md) {
  // tiny markdown: #/##/- and paragraphs
  return md.split("\n").map((line, i) => {
    if (line.startsWith("## ")) return <h3 key={i} className="font-bold text-gray-900 mt-4 mb-1">{line.slice(3)}</h3>;
    if (line.startsWith("# ")) return <h2 key={i} className="text-lg font-extrabold text-hsbc-red mt-2 mb-2">{line.slice(2)}</h2>;
    if (line.startsWith("- ")) return <li key={i} className="ml-5 list-disc text-sm text-gray-700">{line.slice(2)}</li>;
    if (!line.trim()) return <div key={i} className="h-2" />;
    return <p key={i} className="text-sm text-gray-700 leading-relaxed">{line}</p>;
  });
}

export default function Reports() {
  const [topic, setTopic] = useState(TOPICS[0]);
  const [loading, setLoading] = useState(false);
  const [res, setRes] = useState(null);

  const gen = async () => {
    if (!topic.trim()) return;
    setLoading(true); setRes(null);
    try { setRes(await api.report(topic)); }
    catch (e) { setRes({ error: e.message }); }
    finally { setLoading(false); }
  };

  return (
    <>
      <PageTitle title="AI analyst reports"
        subtitle="Generate a concise management report with findings, assumptions and limitations." />

      <div className="card mb-4">
        <div className="flex gap-2">
          <input value={topic} onChange={(e) => setTopic(e.target.value)}
            className="flex-1 rounded-xl border border-gray-200 px-4 py-2.5 text-sm
                       focus:outline-none focus:ring-2 focus:ring-hsbc-red/30" />
          <button className="btn-primary" onClick={gen} disabled={loading}>
            <Sparkles size={16} /> Generate
          </button>
        </div>
        <div className="flex flex-wrap gap-2 mt-3">
          {TOPICS.map((t) => (
            <button key={t} onClick={() => setTopic(t)}
              className="pill bg-gray-100 text-gray-600 hover:bg-gray-200">{t}</button>
          ))}
        </div>
      </div>

      {loading && <Loading label="Writing report…" />}
      {res?.error && <ErrorNote>{res.error}</ErrorNote>}
      {res && !res.error && !loading && (
        <div className="card">
          <div className="flex items-center gap-2 mb-3">
            <FileText size={16} className="text-hsbc-red" />
            <span className={`pill ${res.engine === "gemini"
              ? "bg-violet-100 text-violet-700" : "bg-gray-100 text-gray-600"}`}>
              {res.engine === "gemini" ? "AI (Gemini)" : "Template"}
            </span>
            {res.note && <span className="text-xs text-gray-400">{res.note}</span>}
          </div>
          <div className="prose-sm">{renderMarkdown(res.report || "")}</div>
        </div>
      )}
    </>
  );
}
