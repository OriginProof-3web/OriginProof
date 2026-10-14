import { defineConfig } from '@playwright/test';
import webConfig from '../../apps/web/playwright.config';

const baseURL = process.env.W3_WEB_URL ?? 'http://127.0.0.1:3000';
if (!['127.0.0.1', 'localhost', '[::1]'].includes(new URL(baseURL).hostname)) {
  throw new Error('D QA requires an isolated loopback web server.');
}
if (process.env.ORIGINPROOF_TEST_ACCOUNTS && process.env.W3_QA_DISPOSABLE !== '1') {
  throw new Error('W3_QA_DISPOSABLE=1 is required for live browser issuance.');
}
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
    baseURL,
    trace: 'off',
    video: 'off',
    screenshot: 'off',
  },
  webServer: undefined,
});
