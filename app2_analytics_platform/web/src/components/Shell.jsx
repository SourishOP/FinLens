import { useState, useEffect } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard, MessageSquareText, TrendingUp, FileText, Database, Menu, X,
  BarChart3,
} from "lucide-react";
import { api } from "../api";

const NAV = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/ga4", label: "Digital (GA4)", icon: BarChart3 },
  { to: "/ask", label: "Ask the data", icon: MessageSquareText },
  { to: "/predictions", label: "Predictions", icon: TrendingUp },
  { to: "/reports", label: "Reports", icon: FileText },
  { to: "/explorer", label: "Data explorer", icon: Database },
];

function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <div className="w-8 h-8 rounded-md bg-hsbc-red grid place-items-center shrink-0">
        <div className="w-4 h-4 bg-white"
             style={{ clipPath: "polygon(50% 0,100% 50%,50% 100%,0 50%)" }} />
      </div>
      <div className="leading-tight">
        <div className="font-extrabold text-[15px] text-gray-900">Lumen</div>
        <div className="text-[10px] uppercase tracking-wider text-gray-400">Analytics</div>
      </div>
    </div>
  );
}

export default function Shell({ children }) {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState(null);
  const loc = useLocation();

  useEffect(() => { api.health().then((h) => setMode(h.warehouse_mode)).catch(() => setMode("offline")); }, []);
  useEffect(() => { setOpen(false); }, [loc.pathname]);

  const sidebar = (
    <nav className="flex flex-col gap-1 p-3">
      {NAV.map(({ to, label, icon: Icon, end }) => (
        <NavLink key={to} to={to} end={end}
          className={({ isActive }) =>
            `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-colors ${
              isActive ? "bg-hsbc-red text-white shadow-sm"
                       : "text-gray-600 hover:bg-gray-100"}`}>
          <Icon size={18} /> {label}
        </NavLink>
      ))}
    </nav>
  );

  return (
    <div className="min-h-screen flex bg-gray-100">
      {/* Desktop sidebar */}
      <aside className="hidden md:flex md:flex-col w-60 bg-white border-r border-gray-200 shrink-0">
        <div className="p-4 border-b border-gray-100"><Logo /></div>
        {sidebar}
        <div className="mt-auto p-4 text-[11px] text-gray-400 leading-relaxed">
          Real: financials, share price, risk.<br />
          Simulated (labelled): churn, acquisition.
        </div>
      </aside>

      {/* Mobile drawer */}
      {open && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={() => setOpen(false)} />
          <aside className="absolute left-0 top-0 bottom-0 w-64 bg-white shadow-xl">
            <div className="p-4 border-b border-gray-100 flex items-center justify-between">
              <Logo />
              <button onClick={() => setOpen(false)}><X size={20} /></button>
            </div>
            {sidebar}
          </aside>
        </div>
      )}

      <div className="flex-1 flex flex-col min-w-0">
        {/* Topbar */}
        <header className="sticky top-0 z-30 bg-white/90 backdrop-blur border-b border-gray-200">
          <div className="h-14 px-4 flex items-center gap-3">
            <button className="md:hidden" onClick={() => setOpen(true)}><Menu size={22} /></button>
            <div className="md:hidden"><Logo /></div>
            <div className="ml-auto flex items-center gap-3">
              <ModeBadge mode={mode} />
            </div>
          </div>
        </header>

        <main className="flex-1 p-4 md:p-6 max-w-[1400px] w-full mx-auto">{children}</main>
      </div>
    </div>
  );
}

function ModeBadge({ mode }) {
  const map = {
    bigquery: ["bg-green-100 text-green-700", "Live · BigQuery"],
    local: ["bg-amber-100 text-amber-700", "Local mode"],
    offline: ["bg-red-100 text-red-700", "Backend offline"],
  };
  const [cls, text] = map[mode] || ["bg-gray-100 text-gray-500", "connecting…"];
  return <span className={`pill ${cls}`}>{text}</span>;
}
