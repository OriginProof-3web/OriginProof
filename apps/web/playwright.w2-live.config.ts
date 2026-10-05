import { defineConfig, devices } from "@playwright/test";

if (process.env.W2_QA_DISPOSABLE !== "1" || !process.env.W2_WEB_URL) {
  throw new Error("A prepared disposable W2 environment is required.");
}
const origin = new URL(process.env.W2_WEB_URL);
if (origin.protocol !== "http:" || !["127.0.0.1", "localhost"].includes(origin.hostname)) {
  throw new Error("The W2 live origin must be local HTTP.");
}
export default defineConfig({
  testDir: "./e2e", testMatch: "w2-live.spec.ts", workers: 1, retries: 0, timeout: 90_000,
  expect: { timeout: 8_000 },
  reporter: [["list"], ["json", { outputFile: process.env.PLAYWRIGHT_JSON_OUTPUT_NAME }]],
  use: { ...devices["Desktop Chrome"], baseURL: origin.href, trace: "off", video: "off", screenshot: "off" },
});
