import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

type Account = { username: string; password: string; account_id: string; issuer_id: string | null };
const accounts = JSON.parse(process.env.W1_QA_ACCOUNTS ?? "{}") as Record<string, Account>;
test.skip(!process.env.W1_QA_ACCOUNTS, "Opt-in: run scripts/ci/w1_live_qa.py with a disposable DB");

async function login(page: Page, account: Account) {
  await page.goto("/finals");
  await page.getByLabel("계정 이름").fill(account.username);
  await page.getByLabel("비밀번호").fill(account.password);
  await page.getByRole("button", { name: "로그인", exact: true }).click();
  await expect(page.getByRole("button", { name: "로그아웃" })).toBeVisible();
}

test("real W1 roles, CSRF, application decisions, session persistence and isolation", async ({ browser }) => {
  const contexts = await Promise.all(Array.from({ length: 4 }, () => browser.newContext()));
  const [issuer, other, admin, recipient] = await Promise.all(contexts.map(c => c.newPage()));
  try {
    await issuer.goto("/finals");
    await expect(issuer.getByRole("heading", { name: "테스트 계정 로그인" })).toBeVisible();
    expect((await issuer.request.get("/api/v1/operator/issuer-applications")).status()).toBe(401);
    expect((await issuer.request.post("/api/v1/auth/login", { data: {
      username: accounts.issuer_a.username, password: accounts.issuer_a.password, role: "operator",
    } })).status()).toBe(422);
    expect((await new AxeBuilder({ page: issuer }).analyze()).violations).toEqual([]);

    await login(issuer, accounts.issuer_a);
    await expect(issuer.getByRole("heading", { name: "발행기관 신청" })).toBeVisible();
    const identity = await (await issuer.request.get("/api/v1/auth/me")).json();
    expect((await issuer.request.post("/api/v1/issuer-applications", {
      data: { issuer_name: "Synthetic bank" },
    })).status()).toBe(403);
    expect((await issuer.request.post("/api/v1/issuer-applications", {
      headers: { "X-CSRF-Token": identity.csrf_token },
      data: { issuer_name: "Synthetic bank", issuer_id: accounts.issuer_b.issuer_id },
    })).status()).toBe(422);
    await issuer.getByLabel("합성 기관 이름").fill("W1 Synthetic Bank");
    await issuer.getByRole("button", { name: "신청 제출" }).click();
    await expect(issuer.getByText("검토 대기", { exact: true })).toBeVisible();
    const application = await (await issuer.request.get("/api/v1/issuer-applications/mine")).json();
    expect(application.issuer_id).toBe(accounts.issuer_a.issuer_id);
    const decisionPath = `/api/v1/operator/issuer-applications/${application.application_id}/decision`;
    expect((await issuer.request.post(decisionPath, {
      headers: { "X-CSRF-Token": identity.csrf_token }, data: { decision: "APPROVE", reason: "denied" },
    })).status()).toBe(403);
    await issuer.reload();
    await expect(issuer.getByText("검토 대기", { exact: true })).toBeVisible();

    await login(other, accounts.issuer_b);
    expect(await (await other.request.get("/api/v1/issuer-applications/mine")).json()).toBeNull();
    expect((await other.request.get("/api/v1/operator/issuer-applications")).status()).toBe(403);
    await other.getByLabel("합성 기관 이름").fill("W1 Synthetic Office");
    await other.getByRole("button", { name: "신청 제출" }).click();
    await expect(other.getByText("검토 대기", { exact: true })).toBeVisible();

    await login(admin, accounts.operator);
    const bank = admin.locator(".application-item").filter({ hasText: "W1 Synthetic Bank" });
    await bank.getByLabel("검토 사유").fill("synthetic approval");
    await bank.getByRole("button", { name: "승인 검토" }).click();
    await expect(bank.getByText("승인됨 · 체인 활성화 대기", { exact: true })).toBeVisible();
    const adminIdentity = await (await admin.request.get("/api/v1/auth/me")).json();
    expect((await admin.request.post(decisionPath, {
      headers: { "X-CSRF-Token": adminIdentity.csrf_token },
      data: { decision: "APPROVE", reason: "duplicate" },
    })).status()).toBe(409);
    const office = admin.locator(".application-item").filter({ hasText: "W1 Synthetic Office" });
    await office.getByLabel("검토 사유").fill("synthetic rejection");
    await office.getByRole("button", { name: "반려", exact: true }).click();
    await expect(office.getByText("반려됨", { exact: true })).toBeVisible();
    await admin.reload();
    await expect(bank.getByText("승인됨 · 체인 활성화 대기", { exact: true })).toBeVisible();
    expect((await new AxeBuilder({ page: admin }).analyze()).violations).toEqual([]);

    await issuer.getByRole("button", { name: "신청 상태 새로고침" }).click();
    await expect(issuer.getByText("승인됨 · 체인 활성화 대기", { exact: true })).toBeVisible();
    await expect(issuer.getByText("운영자 검토는 승인됐지만 체인 활성화는 별도 확인이 필요합니다.")).toBeVisible();
    await issuer.screenshot({ path: process.env.W1_QA_SCREENSHOT ?? "test-results/w1-approved.png" });
    await issuer.getByRole("button", { name: "로그아웃" }).click();
    await expect(issuer.getByRole("heading", { name: "테스트 계정 로그인" })).toBeVisible();
    expect((await issuer.request.get("/api/v1/auth/me")).status()).toBe(401);
    await login(issuer, accounts.issuer_a);
    await expect(issuer.getByText("승인됨 · 체인 활성화 대기", { exact: true })).toBeVisible();
    expect((await new AxeBuilder({ page: issuer }).analyze()).violations).toEqual([]);
    await other.reload();
    await expect(other.getByText("반려됨", { exact: true })).toBeVisible();
    await expect(other.getByText("W1 Synthetic Bank", { exact: true })).toHaveCount(0);

    await login(recipient, accounts.recipient);
    await expect(recipient.getByRole("heading", { name: "수신자 계정" })).toBeVisible();
    await expect(recipient.getByRole("button", { name: "신청 제출" })).toHaveCount(0);
    expect((await recipient.request.get("/api/v1/operator/issuer-applications")).status()).toBe(403);
    const recipientIdentity = await (await recipient.request.get("/api/v1/auth/me")).json();
    expect((await recipient.request.post("/api/v1/issuer-applications", {
      headers: { "X-CSRF-Token": recipientIdentity.csrf_token }, data: { issuer_name: "denied" },
    })).status()).toBe(403);
    await recipient.getByRole("button", { name: "로그아웃" }).click();
    await expect(recipient.getByRole("heading", { name: "테스트 계정 로그인" })).toBeVisible();
    await login(recipient, accounts.self_operator);
    const selfApplication = recipient.locator(".application-item").filter({ hasText: "Self approval adversarial" });
    await selfApplication.getByLabel("검토 사유").fill("must be denied");
    await selfApplication.getByRole("button", { name: "승인 검토" }).click();
    await expect(recipient.getByRole("alert").filter({ hasText: "본인 기관의 신청은 승인할 수 없습니다." })).toBeVisible();
    await expect(selfApplication.getByText("검토 대기", { exact: true })).toBeVisible();
  } finally {
    await Promise.all(contexts.map(c => c.close()));
  }
});
