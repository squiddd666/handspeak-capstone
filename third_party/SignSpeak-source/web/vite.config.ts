import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

export default defineConfig(({ mode }) => ({
  base: "/",
  server: {
    host: "::",
    port: 8080,
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
      "/ws/decoder": { target: "ws://localhost:8000", ws: true },
      "/ws/practice": { target: "ws://localhost:8000", ws: true },
      "/ws/hangman": { target: "ws://localhost:8000", ws: true },
    },
  },
  plugins: [react(), mode === "development" && componentTagger()].filter(Boolean),
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    outDir: path.resolve(__dirname, "../frontend"),
    emptyOutDir: true,
  },
}));
