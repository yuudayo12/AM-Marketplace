import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development the API runs on :8000; Vite proxies /api so cookies stay same-origin.
const API = process.env.SPEEDWAVE_API ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": { target: API, changeOrigin: false } },
  },
  build: { outDir: "dist", sourcemap: false },
});
