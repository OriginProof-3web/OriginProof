import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    setupFiles: "./test/setup.ts",
    include: ["app/**/*.test.tsx"],
  },
  esbuild: {
    jsx: "automatic",
  },
});
