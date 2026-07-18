import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  // @novnc/novnc uses top-level await internally, which the default esbuild
  // target (~ES2020, matched to older browsers) doesn't support.
  build: {
    target: "es2022",
  },
  server: {
    host: true,
    port: 5173,
  },
});
