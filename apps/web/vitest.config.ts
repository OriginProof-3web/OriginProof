import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: { dedupe: ["react", "react-dom"] },
  test: {
    environment: "jsdom",
    setupFiles: "./test/setup.ts",
    include: ["app/**/*.test.tsx"],
  },
  esbuild: {
    jsx: "automatic",
  },
});
