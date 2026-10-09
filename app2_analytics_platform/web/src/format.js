// Shared value formatting so the UI never shows raw/cryptic numbers.

export function fmt(value, unit) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const v = Number(value);
  if (unit === "$m") {
    if (Math.abs(v) >= 1000) return `$${(v / 1000).toFixed(2)}bn`;
    return `$${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}m`;
  }
  if (unit === "%") return `${v.toFixed(1)}%`;
  if (unit && unit.startsWith("score")) return v.toFixed(2);
  return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export function fmtQuarter(dateStr) {
  // "2024-12-31" -> "Q4 2024"
  if (!dateStr) return "";
  const d = new Date(dateStr);
  const q = Math.floor(d.getMonth() / 3) + 1;
  return `Q${q} ${d.getFullYear()}`;
}

export const HSBC_RED = "#DB0011";
export const CHART_COLORS = ["#DB0011", "#2563eb", "#0a7d33", "#f0a202", "#7c3aed", "#0891b2"];
