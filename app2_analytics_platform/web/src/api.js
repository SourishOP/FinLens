import axios from "axios";

// In dev, Vite proxies /api -> backend. In prod you can set VITE_API_URL.
const BASE = import.meta.env.VITE_API_URL || "/api";

const http = axios.create({ baseURL: BASE, timeout: 180000 });

export const api = {
  health: () => http.get("/health").then((r) => r.data),
  kpis: () => http.get("/metrics/kpis").then((r) => r.data),
  financials: () => http.get("/metrics/financials").then((r) => r.data),
  modules: () => http.get("/modules").then((r) => r.data),
  glossary: () => http.get("/glossary").then((r) => r.data),
  forecast: (module, metric) =>
    http
      .get(`/forecast/${module}`, { params: metric ? { metric } : {} })
      .then((r) => r.data),
  query: (question) =>
    http.post("/query", { question }).then((r) => r.data),
  rawQuery: (sql) => http.post("/query/raw", { sql }).then((r) => r.data),
  report: (topic, data) =>
    http.post("/report", { topic, data }).then((r) => r.data),
  ga4Catalog: () => http.get("/ga4").then((r) => r.data),
  ga4Report: (key) => http.get(`/ga4/${key}`).then((r) => r.data),
};
