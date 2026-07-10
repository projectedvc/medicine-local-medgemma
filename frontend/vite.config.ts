import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  if (mode === "production" && !env.VITE_API_URL?.trim()) {
    throw new Error("VITE_API_URL is required for a production build.");
  }

  return {
    plugins: [react()],
    server: {
      host: "0.0.0.0",
      port: 5173,
      strictPort: true,
      allowedHosts: true,
      proxy: {
        "/api": {
          target: "http://127.0.0.1:8000",
          changeOrigin: true
        }
      }
    }
  };
});
