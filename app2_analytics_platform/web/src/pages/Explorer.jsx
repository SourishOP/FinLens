import { useEffect, useState } from "react";
import { Play } from "lucide-react";
import { api } from "../api";
import { PageTitle, Loading, ErrorNote } from "../components/ui";
import { DataTable } from "../components/AutoChart";

export default function Explorer() {
  const [catalog, setCatalog] = useState([]);
  const [sql, setSql] = useState("SELECT period_end, net_operating_income, profit_before_tax\nFROM hsbc_marts.financial_kpis\nORDER BY period_end");
  const [res, setRes] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { api.financials().then((f) => setCatalog(f.catalog || [])).catch(() => {}); }, []);

  const run = async () => {
    setLoading(true); setRes(null);
    try { setRes(await api.rawQuery(sql)); }
    catch (e) { setRes({ ok: false, reason: e.message }); }
    finally { setLoading(false); }
  };

  return (
    <>
      <PageTitle title="Data explorer"
        subtitle="Run read-only SQL directly. Every query is validated server-side (SELECT only)." />

      {catalog.length > 0 && (
        <div className="card mb-4">
          <h3 className="font-bold text-gray-900 mb-2">Available metrics (hsbc_marts.financial_kpis)</h3>
          <div className="flex flex-wrap gap-2">
            {catalog.map((c) => (
              <span key={c.key} className="pill bg-gray-100 text-gray-600" title={c.help}>
                {c.label}{c.unit ? ` (${c.unit})` : ""}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="card mb-4">
        <textarea value={sql} onChange={(e) => setSql(e.target.value)} rows={5}
          className="w-full font-mono text-sm rounded-xl border border-gray-200 p-3
                     focus:outline-none focus:ring-2 focus:ring-hsbc-red/30" />
        <div className="mt-3"><button className="btn-primary" onClick={run} disabled={loading}><Play size={16} /> Run</button></div>
      </div>

      {loading && <Loading />}
      {res && !loading && (
        res.ok
          ? <div className="card"><DataTable rows={res.rows} /></div>
          : <ErrorNote>{res.reason}</ErrorNote>
      )}
    </>
  );
}
