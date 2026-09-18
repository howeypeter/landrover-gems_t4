import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Build output lands INSIDE the Python package so `gems_t4 api` serves it as
// static files. In dev, `npm run dev` runs Vite and proxies /api (incl. the
// WebSocket) to the running `gems_t4 api` on :8080.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    outDir: "../gems_t4/app/web/static",
    emptyOutDir: true,
  },
  server: {
    proxy: {
      "/api": { target: "http://127.0.0.1:8080", ws: true, changeOrigin: true },
    },
  },
});
