import { test, expect, type BrowserContext, type Page, type Response } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { randomUUID } from 'node:crypto';

// Synthetic accounts only. Passwords, session state, traces and source payloads are not saved.
const accountFile = process.env.ORIGINPROOF_TEST_ACCOUNTS;
test.skip(!accountFile, 'An explicit isolated synthetic account file is required.');
test.use({ trace: 'off', video: 'off', screenshot: 'off' });
type Role = 'bank' | 'office' | 'recipient' | 'recipient_other';
type Account = { username: string; password: string };
type Verdict = {
  verification_status: string;
  lifecycle_status: string | null;
  scope: string;
  reason_codes: string[];
  checks: Record<string, string>;
};
const proofFields = [
  'proof_id', 'issuer_id', 'key_id', 'proof_type', 'schema_version',
  'issued_at', 'expires_at', 'verification_path',
].sort();
function account(role: Role): Account {
  const rows = JSON.parse(readFileSync(accountFile!, 'utf8')) as Account[];
  const row = rows.find(item => item.username === role);
  if (!row?.password) throw new Error(`Missing isolated synthetic ${role} account.`);
  return row;
}
async function login(page: Page, role: Role) {
  const credentials = account(role);
  await page.goto(role.startsWith('recipient') ? '/user-login.html' : '/business-login.html');
  await page.getByLabel('계정 이름').fill(credentials.username);
  await page.getByLabel('비밀번호', { exact: true }).fill(credentials.password);
  await page.getByRole('button', { name: 'Sign In', exact: true }).click();
  await expect(page).toHaveURL(role.startsWith('recipient') ? /index.html#user/ : /business.html/);
}
function responseTo(page: Page, path: string) {
  return page.waitForResponse(response =>
    new URL(response.url()).pathname === path && response.request().method() === 'POST');
}
async function verifyByUI(page: Page, id: string, action: () => Promise<unknown>): Promise<Verdict> {
  const waiting = responseTo(page, `/api/v2/proofs/${id}/verify`);
  await action();
  const response: Response = await waiting;
  expect(response.status()).toBe(200);
  return await response.json() as Verdict;
}
function w3Verdict(result: Verdict, status: string, scope: string, reason?: string) {
  expect(result.verification_status).toBe(status);
  expect(result.scope).toBe(scope);
  expect(result.lifecycle_status).toBeNull();
  expect(result.checks.proof_status).toBe('NOT_RUN');
  if (reason) expect(result.reason_codes).toContain(reason);
}
async function denied(context: BrowserContext, id: string, candidate: Record<string, unknown>, status: number) {
  const content = await context.request.get(`/api/v2/proofs/${id}/content`);
  expect(content.status()).toBe(status);
  const comparison = await context.request.post(`/api/v2/proofs/${id}/verify`, {
    data: { request_id: `req_${randomUUID()}`, candidate },
  });
  expect(comparison.status()).toBe(status);
  expect(Object.keys(await comparison.json())).toEqual(['detail']);
}

for (const [issuer, type, changedLabel, missingLabel, reason] of [
  ['bank', 'PAYMENT_REQUEST', '금액 (최소 화폐 단위)', '통화', 'AMOUNT_MISMATCH'],
  ['office', 'OFFICIAL_DOCUMENT', '문서번호', '문서 개정 번호', 'FIELD_MISMATCH'],
] as const) {
  test(`D live ${type}: new issuance, fresh sessions, comparison boundaries and privacy`, async ({ browser }) => {
    const contexts: BrowserContext[] = [];
    async function fresh() {
      const context = await browser.newContext({
        baseURL: test.info().project.use.baseURL,
        reducedMotion: 'reduce',
        recordVideo: undefined,
      });
      contexts.push(context);
      return context;
    }
    try {
      const issuerContext = await fresh();
      const issuerPage = await issuerContext.newPage();
      let id = '';
      let link = '';
      let candidate: Record<string, unknown> = {};
      let changed = '';
      await test.step('Fresh issuer input is signed, saved and listed through actual UI/API', async () => {
        await login(issuerPage, issuer);
        await issuerPage.getByRole('button', { name: '새 Proof 발행', exact: true }).click();
        await issuerPage.getByRole('button', { name: '합성 예시 채우기' }).click();
        await issuerPage.getByLabel('지정 수신자', { exact: true }).selectOption({ label: account('recipient').username });
        const unique = `SYNTHETIC-W3-D-${randomUUID().slice(0, 8)}`;
        await issuerPage.getByLabel(type === 'PAYMENT_REQUEST' ? '합성 요청 대상 참조' : '문서번호', { exact: true }).fill(unique);
        const pending = responseTo(issuerPage, '/api/v2/issuer/proofs');
        await issuerPage.getByRole('button', { name: 'Proof 발행', exact: true }).click();
        const issued = await pending;
        expect(issued.status()).toBe(200);
        const view = await issued.json();
        id = view.proof_id;
        expect(id).toMatch(/^prf_[A-Za-z0-9_-]+$/);
        expect(view.proof_type).toBe(type);
        expect(Object.keys(view).sort()).toEqual(proofFields);
        await expect(issuerPage.getByRole('status')).toContainText(id);
        await issuerPage.getByRole('button', { name: '발행 목록', exact: true }).last().click();
        await expect(issuerPage.getByRole('heading', { name: 'Proof 상세' })).toBeVisible();
        link = (await issuerPage.getByRole('link', { name: '사용자 조회 화면' }).getAttribute('href'))!;
        const url = new URL(link, test.info().project.use.baseURL);
        expect([...url.searchParams.keys()]).toEqual(['proof_id']);
        expect(url.searchParams.get('proof_id')).toBe(id);
        const content = await issuerContext.request.get(`/api/v2/proofs/${id}/content`);
        expect(content.status()).toBe(200);
        const saved = await content.json();
        expect(saved.envelope.proof_id).toBe(id);
        expect(saved.envelope.proof_type).toBe(type);
        expect(saved.envelope.signature).toMatch(/^0x[0-9a-f]{130}$/i);
        const payload = saved.envelope.payload;
        candidate = type === 'PAYMENT_REQUEST'
          ? { amount_minor: payload.amount_minor, currency: payload.currency, target_ref: saved.target_ref }
          : { institution_code: payload.institution_code, document_type: payload.document_type, document_number: payload.document_number, version: payload.version };
        expect(type === 'PAYMENT_REQUEST' ? candidate.target_ref : candidate.document_number).toBe(unique);
        changed = type === 'PAYMENT_REQUEST' ? String(Number(candidate.amount_minor) + 1) : `${unique}-TAMPERED`;
      });

      const anonymous = await fresh();
      const publicPage = await anonymous.newPage();
      await test.step('Fresh anonymous link yields PROOF_ONLY and reveals no restricted values', async () => {
        w3Verdict(await verifyByUI(publicPage, id, () => publicPage.goto(link)), 'VERIFIED', 'PROOF_ONLY');
        await expect(publicPage.getByText('PROOF_ONLY', { exact: true })).toBeVisible();
        await expect(publicPage.getByText('미확인', { exact: true })).toBeVisible();
        const view = await anonymous.request.get(`/api/v2/proofs/${id}`);
        expect(view.status()).toBe(200);
        expect(Object.keys(await view.json()).sort()).toEqual(proofFields);
        await denied(anonymous, id, candidate, 401);
        await publicPage.getByRole('button', { name: '내용 비교', exact: true }).last().click();
        await publicPage.getByRole('button', { name: '발행 값 채우기' }).click();
        const labels = type === 'PAYMENT_REQUEST'
          ? ['금액 (최소 화폐 단위)', '통화', '요청 대상 코드']
          : ['기관 코드', '문서 유형', '문서번호', '문서 개정 번호'];
        for (const label of labels) await expect(publicPage.getByLabel(label, { exact: true })).toHaveValue('');
      });

      const recipient = await fresh();
      const recipientPage = await recipient.newPage();
      await test.step('Designated recipient completes normal, tampered, missing and mixed comparisons', async () => {
        await login(recipientPage, 'recipient');
        await recipientPage.getByLabel('Proof ID / 검증 링크').fill(id);
        w3Verdict(await verifyByUI(recipientPage, id, () => recipientPage.getByRole('button', { name: '조회', exact: true }).click()), 'VERIFIED', 'PROOF_ONLY');
        await recipientPage.getByRole('button', { name: '내용 비교', exact: true }).last().click();
        await recipientPage.getByRole('button', { name: '발행 값 채우기' }).click();
        const compare = () => recipientPage.getByRole('button', { name: '내용 비교', exact: true }).last().click();
        w3Verdict(await verifyByUI(recipientPage, id, compare), 'VERIFIED', 'FULL_COMPARISON');
        await expect(recipientPage.locator('.uw-comparison')).toContainText('VERIFIED · FULL_COMPARISON');
        await recipientPage.getByLabel(changedLabel, { exact: true }).fill(changed);
        w3Verdict(await verifyByUI(recipientPage, id, compare), 'TAMPERED', 'FULL_COMPARISON', reason);
        await expect(recipientPage.locator('.uw-comparison')).toContainText(reason);
        await recipientPage.getByRole('button', { name: '발행 값 채우기' }).click();
        await recipientPage.getByLabel(missingLabel, { exact: true }).fill('');
        w3Verdict(await verifyByUI(recipientPage, id, compare), 'INCONCLUSIVE', 'PARTIAL_COMPARISON', 'INPUT_INCOMPLETE');
        await expect(recipientPage.locator('.uw-comparison')).toContainText('INCONCLUSIVE · PARTIAL_COMPARISON');
        await recipientPage.getByLabel(changedLabel, { exact: true }).fill(changed);
        w3Verdict(await verifyByUI(recipientPage, id, compare), 'TAMPERED', 'PARTIAL_COMPARISON', reason);
        await expect(recipientPage.locator('.uw-comparison')).toContainText('TAMPERED · PARTIAL_COMPARISON');
      });

      await test.step('Refresh preserves authenticated access and logout restores public-only access', async () => {
        w3Verdict(await verifyByUI(recipientPage, id, () => recipientPage.goto(link)), 'VERIFIED', 'PROOF_ONLY');
        w3Verdict(await verifyByUI(recipientPage, id, () => recipientPage.reload()), 'VERIFIED', 'PROOF_ONLY');
        expect((await recipient.request.get(`/api/v2/proofs/${id}/content`)).status()).toBe(200);
        await recipientPage.locator('[data-workspace-trigger]').click();
        const logout = responseTo(recipientPage, '/api/v1/auth/logout');
        await recipientPage.getByRole('button', { name: '로그아웃', exact: true }).click();
        expect((await logout).status()).toBe(200);
        await expect(recipientPage).toHaveURL(/index.html$/);
        w3Verdict(await verifyByUI(recipientPage, id, () => recipientPage.goto(link)), 'VERIFIED', 'PROOF_ONLY');
        await denied(recipient, id, candidate, 401);
        const content = await issuerContext.request.get(`/api/v2/proofs/${id}/content`);
        const after = await content.json();
        expect(type === 'PAYMENT_REQUEST' ? after.target_ref : after.envelope.payload.document_number)
          .toBe(type === 'PAYMENT_REQUEST' ? candidate.target_ref : candidate.document_number);
        expect(after.envelope.payload.amount_minor ?? after.envelope.payload.version)
          .toBe(candidate.amount_minor ?? candidate.version);
      });

      await test.step('Other issuer and other recipient are denied before restricted comparison', async () => {
        for (const role of [issuer === 'bank' ? 'office' : 'bank', 'recipient_other'] as const) {
          const other = await fresh();
          await login(await other.newPage(), role);
          await denied(other, id, candidate, 404);
          if (!role.startsWith('recipient')) {
            const list = await other.request.get('/api/v2/issuer/proofs');
            expect(list.status()).toBe(200);
            expect((await list.json() as { proof_id: string }[]).some(row => row.proof_id === id)).toBe(false);
          }
        }
      });
    } finally {
      await Promise.all(contexts.map(context => context.close()));
    }
  });
}
