import { test, expect, type Browser, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { chmodSync, mkdirSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { randomUUID } from 'node:crypto';

// Connected-flow helpers reused from D PR #51 (17f78e3); A owns the acceptance fixes below.
const accountFile = process.env.W2_QA_ACCOUNTS;
const metadataFile = process.env.W2_QA_METADATA;
test.skip(!accountFile || !metadataFile, 'An explicitly prepared disposable W2 environment is required.');
test.use({ trace: 'off', video: 'off', screenshot: 'off' });
type Account = { username: string; account_id: string; password: string; role: string; issuer_id: string | null };
type Metadata = {
  approved_application_id: string;
  active_application_id: string;
  confirmed_operation_id: string;
  unknown_operation_id?: string;
  key_id: string;
  issuer_id: string;
  chain_id: number;
  source_commit_sha: string;
  web_url: string;
};
const screenshotDirectory = resolve(__dirname, '../../../build/w2-browser-qa/screenshots');
function metadata(): Metadata {
  return JSON.parse(readFileSync(metadataFile!, 'utf8')) as Metadata;
}
function account(username: string): Account {
  const rows = JSON.parse(readFileSync(accountFile!, 'utf8')) as Account[];
  const row = rows.find(item => item.username === username);
  if (!row?.password) throw new Error(`Missing prepared synthetic account ${username}.`);
  return row;
}
async function observed(page: Page, path: string, method: string, action: () => Promise<unknown>) {
  const pending = page.waitForResponse(response =>
    new URL(response.url()).pathname === `/api${path}` && response.request().method() === method);
  await action();
  return await pending;
}
async function login(page: Page, username: string) {
  const row = account(username);
  await page.goto('/finals');
  await expect(page.getByRole('heading', { name: '테스트 계정 로그인' })).toBeVisible();
  await page.getByLabel('계정 이름').fill(row.username);
  // The password argument does not appear in a locator.fill call log.
  await page.getByLabel('비밀번호').evaluate((input, password) => {
    (input as HTMLInputElement).value = password;
  }, row.password);
  const response = await observed(page, '/v1/auth/login', 'POST', () =>
    page.getByRole('button', { name: '로그인', exact: true }).click());
  expect(response.status()).toBe(200);
  expect((await response.json()).role).toBe(row.role);
  await expect(page.locator('.account-strip')).toContainText(row.username);
}
async function session(browser: Browser, username: string | null, run: (page: Page) => Promise<void>) {
  const baseURL = test.info().project.use.baseURL;
  const url = new URL(baseURL!);
  if (process.env.W2_QA_DISPOSABLE !== '1' || !process.env.W2_WEB_URL ||
      url.protocol !== 'http:' || !['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname) ||
      url.username || url.password || url.pathname !== '/' || url.search || url.hash ||
      url.href !== new URL(metadata().web_url).href) {
    throw new Error('W2 browser QA requires an explicit local HTTP origin.');
  }
  const context = await browser.newContext({ baseURL, reducedMotion: 'reduce' });
  try {
    const page = await context.newPage();
    if (username) await login(page, username);
    await run(page);
  } finally {
    await context.close();
  }
}
async function screenshot(page: Page, name: string) {
  // Only synthetic post-login screens are captured; password fields are always masked.
  mkdirSync(screenshotDirectory, { recursive: true, mode: 0o700 });
  const path = resolve(screenshotDirectory, `${name}.png`);
  await page.screenshot({ path, fullPage: true, mask: [page.locator('input[type="password"]')] });
  chmodSync(path, 0o600);
}

for (const [username, decision, label] of [
  ['w2_approve', 'APPROVE', '승인됨 · 체인 활성화 대기'],
  ['w2_reject', 'REJECT', '반려됨'],
] as const) {
  test(`[connected] actual application ${decision}, issuer refresh, fresh login and logout`, async ({ browser }) => {
    await session(browser, username, async issuer => {
      const name = `Origin Mock W2 D ${decision} ${randomUUID().slice(0, 8)}`;
      await issuer.getByLabel('합성 기관 이름').fill(name);
      const created = await observed(issuer, '/v1/issuer-applications', 'POST', () =>
        issuer.getByRole('button', { name: '신청 제출', exact: true }).click());
      expect(created.status()).toBe(201);
      const application = await created.json();
      expect(application.status).toBe('PENDING_REVIEW');
      expect(application.issuer_id).toBe(account(username).issuer_id);
      await expect(issuer.getByText('검토 대기', { exact: true })).toBeVisible();

      await session(browser, 'w2_operator', async operator => {
        const item = operator.locator('.application-item').filter({ hasText: name });
        await expect(item).toHaveCount(1);
        await item.getByLabel('검토 사유').fill('D synthetic browser QA');
        const response = await observed(operator,
          `/v1/operator/issuer-applications/${application.application_id}/decision`, 'POST', () =>
            item.getByRole('button', { name: decision === 'APPROVE' ? '승인 검토' : '반려', exact: true }).click());
        expect(response.status()).toBe(200);
        expect((await response.json()).status).toBe(decision === 'APPROVE' ? 'APPROVED_PENDING_CHAIN' : 'REJECTED');
        await expect(item.getByText(label, { exact: true })).toBeVisible();
      });

      const refreshed = await observed(issuer, '/v1/issuer-applications/mine', 'GET', () =>
        issuer.getByRole('button', { name: '신청 상태 새로고침', exact: true }).click());
      expect(refreshed.status()).toBe(200);
      expect((await refreshed.json()).application_id).toBe(application.application_id);
      await expect(issuer.getByText(label, { exact: true })).toBeVisible();
      await screenshot(issuer, `connected-${decision.toLowerCase()}`);
      await session(browser, username, async freshIssuer => {
        await expect(freshIssuer.getByText(label, { exact: true })).toBeVisible();
        const reread = await observed(freshIssuer, '/v1/issuer-applications/mine', 'GET', () => freshIssuer.reload());
        expect(reread.status()).toBe(200);
        expect((await reread.json()).application_id).toBe(application.application_id);
        await expect(freshIssuer.getByText(label, { exact: true })).toBeVisible();
      });
      const logout = await observed(issuer, '/v1/auth/logout', 'POST', () =>
        issuer.getByRole('button', { name: '로그아웃', exact: true }).click());
      expect(logout.status()).toBe(200);
      await expect(issuer.getByRole('heading', { name: '테스트 계정 로그인' })).toBeVisible();
      await issuer.reload();
      await expect(issuer.getByRole('heading', { name: '테스트 계정 로그인' })).toBeVisible();
      await expect(issuer.locator('.application-summary')).toHaveCount(0);
    });
  });
}

test('[connected] real confirmed Operation and own audit events are read through the UI', async ({ browser }) => {
  const data = metadata();
  await session(browser, 'w2_active', async page => {
    await page.getByLabel('작업 ID').fill(data.confirmed_operation_id);
    const response = await observed(page, `/v1/operations/${data.confirmed_operation_id}`, 'GET', () =>
      page.getByRole('button', { name: '작업 상태 조회', exact: true }).click());
    expect(response.status()).toBe(200);
    const operation = await response.json();
    expect(operation.operation_id).toBe(data.confirmed_operation_id);
    expect(operation.status).toBe('CONFIRMED');
    expect(operation.issuer_id).toBe(data.issuer_id);
    expect(operation.tx_hash).toMatch(/^0x[0-9a-f]{64}$/i);
    await expect(page.locator('.operation-summary')).toContainText('체인 확인 완료');
    await expect(page.locator('.operation-summary')).toContainText(operation.tx_hash);
    const responseEvents = await observed(page, '/v1/audit-events', 'GET', () =>
      page.getByRole('button', { name: '감사 이력 새로고침', exact: true }).click());
    expect(responseEvents.status()).toBe(200);
    const events = await responseEvents.json() as { issuer_id: string; action: string; target_id: string }[];
    expect(events.length).toBeGreaterThan(0);
    expect(events.every(event => event.issuer_id === data.issuer_id)).toBe(true);
    await expect(page.locator('.audit-list')).toContainText(data.key_id);
    await screenshot(page, 'connected-operation-audit');
  });
});

test('[connected] real UNKNOWN Operation is shown without a confirmed success', async ({ browser }) => {
  const id = metadata().unknown_operation_id;
  test.skip(!id, 'The disposable helper has not provided an actual UNKNOWN operation.');
  await session(browser, 'w2_active', async page => {
    await page.getByLabel('작업 ID').fill(id!);
    const response = await observed(page, `/v1/operations/${id}`, 'GET', () =>
      page.getByRole('button', { name: '작업 상태 조회', exact: true }).click());
    expect(response.status()).toBe(200);
    expect((await response.json()).status).toBe('UNKNOWN');
    await expect(page.locator('.operation-summary')).toContainText('결과 확인 필요');
    await expect(page.locator('.operation-summary')).not.toContainText('체인 확인 완료');
    await screenshot(page, 'connected-unknown');
  });
});

test('[connected] another issuer is denied another institution Operation through the actual UI', async ({ browser }) => {
  const id = metadata().confirmed_operation_id;
  await session(browser, 'w2_approved', async page => {
    await page.getByLabel('작업 ID').fill(id);
    const response = await observed(page, `/v1/operations/${id}`, 'GET', () =>
      page.getByRole('button', { name: '작업 상태 조회', exact: true }).click());
    expect(response.status()).toBe(404);
    await expect(page.locator('.finals-inline-error')).toContainText('작업을 찾을 수 없거나 조회 권한이 없습니다.');
    await expect(page.locator('.operation-summary')).toHaveCount(0);
    await screenshot(page, 'connected-other-issuer-denied');
  });
});

test('[connected] anonymous, operator and recipient see the actual issuer-only key access gate', async ({ browser }) => {
  await session(browser, null, async page => {
    const response = await observed(page, '/v1/auth/me', 'GET', () => page.goto('/finals/keys'));
    expect(response.status()).toBe(401);
    await expect(page.getByRole('heading', { name: '로그인이 필요합니다' })).toBeVisible();
  });
  for (const username of ['w2_operator', 'w2_recipient']) {
    await session(browser, username, async page => {
      const response = await observed(page, '/v1/auth/me', 'GET', () => page.goto('/finals/keys'));
      expect(response.status()).toBe(200);
      expect((await response.json()).role).not.toBe('issuer');
      await expect(page.getByRole('heading', { name: '발행기관 권한이 필요합니다' })).toBeVisible();
      await expect(page.getByRole('button', { name: '입력 조건 확인', exact: true })).toHaveCount(0);
    });
  }
});

// These are ordinary, intentionally unmet acceptance assertions. Never mark them xfail/pass.

test('[acceptance] ACTIVE is explained after actual refresh', async ({ browser }) => {
  await session(browser, 'w2_active', async page => {
    const response = await observed(page, '/v1/issuer-applications/mine', 'GET', () => page.getByRole('button', { name: '신청 상태 새로고침', exact: true }).click());
    expect((await response.json()).status).toBe('ACTIVE');
    await expect(page.locator('.application-summary')).toContainText('활성화 완료');
  });
});
test('[acceptance] approved summary has valid definition-list structure', async ({ browser }) => {
  await session(browser, 'w2_approved', async page => {
    const result = await new AxeBuilder({ page }).include('.application-summary').withRules(['definition-list']).analyze();
    expect(result.violations.map(item => item.id)).not.toContain('definition-list');
  });
});
test('[acceptance] current institution keys use actual GET', async ({ browser }) => {
  await session(browser, 'w2_active', async page => {
    const response = await observed(page, '/v1/issuer/keys', 'GET', () => page.goto('/finals/keys'));
    expect(response.status()).toBe(200);
    await expect(page.getByText(metadata().key_id, { exact: true })).toBeVisible();
  });
});
test('[acceptance] registration sends actual POST and preserves key after fresh login', async ({ browser }) => {
  let id = '';
  await session(browser, 'w2_active', async page => {
    await page.goto('/finals/keys');
    await page.getByLabel('유효 시작 시각').fill('2026-10-01T10:00');
    await page.getByLabel('유효 종료 시각').fill('2026-11-03T10:00');
    await page.getByLabel('키 등록 사유').fill('A synthetic registration acceptance');
    const response = await observed(page, '/v1/issuer/keys', 'POST', () => page.getByRole('button', { name: '키 생성·등록', exact: true }).click());
    expect(response.status()).toBe(200);
    const op = await response.json(); expect(op.status).toBe('CONFIRMED'); id = op.target_id;
    await expect(page.getByText(id, { exact: true })).toBeVisible();
  });
  await session(browser, 'w2_active', async page => {
    await page.goto('/finals/keys'); await expect(page.getByText(id, { exact: true })).toBeVisible();
  });
});
test('[acceptance] revocation uses displayed key with explicit confirmation and reload', async ({ browser }) => {
  await session(browser, 'w2_active', async page => {
    await page.goto('/finals/keys');
    const item = page.locator('article').filter({ has: page.getByText(metadata().key_id, { exact: true }) });
    await item.getByLabel('키 폐기 사유').fill('A synthetic compromise acceptance');
    await item.getByRole('checkbox').check();
    const response = await observed(page, `/v1/issuer/keys/${metadata().key_id}/revoke`, 'POST', () => item.getByRole('button', { name: '키 폐기', exact: true }).click());
    expect(response.status()).toBe(200); expect((await response.json()).status).toBe('CONFIRMED');
    await expect(item).toContainText('REVOKED');
    await page.reload(); await expect(page.locator('article').filter({ has: page.getByText(metadata().key_id, { exact: true }) })).toContainText('REVOKED');
  });
});
test('[acceptance] approval activates chain through actual UI and fresh issuer sees ACTIVE', async ({ browser }) => {
  await session(browser, 'w2_operator', async page => {
    const target = page.locator('.application-item').filter({ hasText: 'W2 Synthetic approved' });
    await target.getByLabel('활성화 사유').fill('A synthetic activation acceptance');
    const response = await observed(page, `/v1/operator/issuer-applications/${metadata().approved_application_id}/activate`, 'POST', () => target.getByRole('button', { name: '체인 활성화', exact: true }).click());
    expect(response.status()).toBe(200); expect((await response.json()).status).toBe('CONFIRMED');
    await expect(target).toContainText('활성화 완료');
  });
  await session(browser, 'w2_approved', async page => { await expect(page.locator('.application-summary')).toContainText('활성화 완료'); });
});
