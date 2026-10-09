import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server proxies /api -> FastAPI backend so the frontend and backend share
// an origin (no CORS headaches). --host exposes it on the LAN for phone access.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // listen on 0.0.0.0 so the phone can reach it
    port: 5173,
    // allow any host header (so http://<LAN-IP>:5173 from a phone works)
    allowedHosts: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
});
