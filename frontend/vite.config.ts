import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// In Docker Compose the API runs at http://api:8000; locally at http://localhost:8000.
const apiTarget = process.env.API_PROXY_TARGET ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { "/api": apiTarget },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test-setup.ts"],
  },
});
