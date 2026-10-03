import { defineConfig } from '@playwright/test';
import webConfig from '../../apps/web/playwright.config';

// D-owned live QA: run only against the explicitly prepared local production server.
export default defineConfig({
  ...webConfig,
  testDir: '.',
  testMatch: 'w3_browser_qa.spec.ts',
  timeout: 120_000,
  workers: 1,
  retries: 0,
  reporter: 'list',
  outputDir: process.env.W3_BROWSER_OUTPUT ?? '/private/tmp/originproof-w3-browser-results',
  use: {
    ...webConfig.use,
    baseURL: process.env.W3_WEB_URL ?? 'http://127.0.0.1:3000',
    trace: 'off',
    video: 'off',
    screenshot: 'off',
  },
  webServer: undefined,
});
