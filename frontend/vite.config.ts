import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  base: "/app/",
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["icon.svg"],
      manifest: {
        name: "domAIn",
        short_name: "domAIn",
        description: "Multi-agent decision council chat",
        theme_color: "#c17f0a",
        background_color: "#f7f5f2",
        display: "standalone",
        start_url: "/app/",
        scope: "/app/",
        icons: [
          {
            src: "icon.svg",
            sizes: "any",
            type: "image/svg+xml",
            purpose: "any maskable",
          },
        ],
      },
      workbox: {
        navigateFallback: "/app/index.html",
        globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2}"],
      },
    }),
  ],
  server: {
    proxy: {
      "/chat": "http://localhost:8000",
      "/sources": "http://localhost:8000",
      "/connections": "http://localhost:8000",
      "/oauth": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
