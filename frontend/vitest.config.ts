import { defineConfig } from "vitest/config";

export default defineConfig({
  base: "/app/",
  test: {
    environment: "node",
  },
});
