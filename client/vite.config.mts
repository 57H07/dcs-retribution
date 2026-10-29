/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// QLiberationMap loads build/index.html through file://, so every asset path
// must be relative (base "./"). `npm start` serves on localhost:3000, the URL
// the Qt UI opens with --dev and the Electron shell waits for.
export default defineConfig({
  base: "./",
  plugins: [react()],
  server: {
    port: 3000,
    strictPort: true,
  },
  preview: {
    port: 3000,
    strictPort: true,
  },
  build: {
    outDir: "build",
    sourcemap: true,
    // One bundle read from disk by the Qt web view: chunk size is not a
    // download concern here (~395 kB gzipped, as with react-scripts).
    chunkSizeWarningLimit: 2000,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/setupTests.ts",
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
