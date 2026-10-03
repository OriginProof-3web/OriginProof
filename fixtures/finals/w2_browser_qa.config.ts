import { defineConfig } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import webConfig from '../../apps/web/playwright.config';

if (process.env.W2_QA_DISPOSABLE !== '1' || !process.env.W2_WEB_URL ||
    !process.env.W2_QA_ACCOUNTS || !process.env.W2_QA_METADATA) {
  throw new Error('Explicit disposable W2 acknowledgement, web origin, accounts and metadata are required.');
}
const webURL = new URL(process.env.W2_WEB_URL);
const metadata = JSON.parse(readFileSync(process.env.W2_QA_METADATA, 'utf8')) as { web_url: string };
if (webURL.protocol !== 'http:' || !['127.0.0.1', 'localhost', '[::1]'].includes(webURL.hostname) ||
    webURL.username || webURL.password || webURL.pathname !== '/' || webURL.search || webURL.hash ||
    webURL.href !== new URL(metadata.web_url).href) {
  throw new Error('W2 web origin must be local and match the prepared disposable metadata.');
}

// Keep product acceptance failures separate from connected-flow QA results.
export default defineConfig({
  ...webConfig,
  testDir: '.',
  testMatch: 'w2_browser_qa.spec.ts',
  forbidOnly: true,
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 90_000,
  expect: { timeout: 5_000 },
  outputDir: '../../build/w2-browser-qa/playwright-results',
  reporter: [
    ['list'],
    ['json', { outputFile: process.env.PLAYWRIGHT_JSON_OUTPUT_NAME ?? resolve(__dirname, '../../build/w2-browser-qa/browser-results.json') }],
  ],
  use: {
    ...webConfig.use,
    baseURL: webURL.href,
    contextOptions: { reducedMotion: 'reduce' },
    trace: 'off',
    video: 'off',
    screenshot: 'off',
  },
  projects: [
    { name: 'connected', grep: /^\[connected\]/, use: webConfig.projects?.[0].use },
    { name: 'acceptance-gaps', grep: /^\[acceptance\]/, use: webConfig.projects?.[0].use },
  ],
  webServer: undefined,
});
