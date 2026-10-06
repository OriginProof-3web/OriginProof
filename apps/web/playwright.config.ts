import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  use: {
    baseURL: process.env.ORIGINPROOF_WEB_BASE_URL ?? "http://127.0.0.1:3000",
    trace: "on-first-retry",
    contextOptions: { reducedMotion: "reduce" },
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: process.env.ORIGINPROOF_WEB_BASE_URL ? undefined : {
    // CI builds first; exercise that build with the same server used for live QA.
    command: process.env.CI ? "pnpm start --hostname 127.0.0.1" : "pnpm dev --hostname 127.0.0.1",
    url: "http://127.0.0.1:3000",
    reuseExistingServer: !process.env.CI,
  },
});
