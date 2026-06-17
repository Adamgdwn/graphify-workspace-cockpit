import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) return undefined;
          if (id.includes("/react") || id.includes("/react-dom")) return "react";
          if (id.includes("/cytoscape-fcose")) return "cytoscape-fcose";
          if (id.includes("/cytoscape-layout-utilities")) return "cytoscape-layout";
          if (id.includes("/cytoscape/")) return "cytoscape";
          return "vendor";
        },
      },
    },
  },
  server: {
    proxy: { "/api": "http://localhost:8000" },
  },
});
