import { TrendingUp, TrendingDown, Info, Loader2 } from "lucide-react";

export function PageTitle({ title, subtitle }) {
  return (
    <div className="mb-5">
      <h1 className="text-xl md:text-2xl font-extrabold text-gray-900">{title}</h1>
      {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
    </div>
  );
}

export function KpiCard({ label, display, help, changePct, trendGood, period }) {
  const hasChange = changePct !== null && changePct !== undefined;
  const up = hasChange && changePct >= 0;
  const color = !hasChange ? "text-gray-400"
    : trendGood ? "text-green-600" : "text-hsbc-red";
  return (
    <div className="card group">
      <div className="flex items-start justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">
          {label}
        </span>
        {help && (
          <span className="relative group/tt">
            <Info size={14} className="text-gray-300 hover:text-gray-500" />
            <span className="hidden group-hover/tt:block absolute right-0 top-5 z-10 w-52
                             bg-gray-900 text-white text-[11px] rounded-lg p-2 shadow-lg">
              {help}
            </span>
          </span>
        )}
      </div>
      <div className="mt-2 text-2xl md:text-3xl font-extrabold text-gray-900">{display}</div>
      <div className="mt-1 flex items-center gap-2 text-xs">
        {hasChange && (
          <span className={`inline-flex items-center gap-1 font-semibold ${color}`}>
            {up ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
            {Math.abs(changePct)}%
          </span>
        )}
        {period && <span className="text-gray-400">{period}</span>}
      </div>
    </div>
  );
}

export function ChartCard({ title, subtitle, right, children, className = "" }) {
  return (
    <div className={`card ${className}`}>
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-bold text-gray-900">{title}</h3>
          {subtitle && <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>}
        </div>
        {right}
      </div>
      {children}
    </div>
  );
}

export function Loading({ label = "Loading…" }) {
  return (
    <div className="flex items-center justify-center gap-2 text-gray-400 py-10">
      <Loader2 className="animate-spin" size={18} /> {label}
    </div>
  );
}

export function ErrorNote({ children }) {
  return (
    <div className="rounded-xl bg-red-50 border border-red-100 text-red-700 text-sm p-3">
      {children}
    </div>
  );
}

export function SourcePill({ source }) {
  const real = source?.toUpperCase().startsWith("REAL");
  return (
    <span className={`pill ${real ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"}`}>
      {source}
    </span>
  );
}
