import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/spot": "http://localhost:8001",
      "/health": "http://localhost:8001",
      "/intel": "http://localhost:8001",
      "/forecast": "http://localhost:8001",
    },
  },
});
