import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("amount-tampered preset calls the API and shows its deterministic result", async ({ page }) => {
  await page.route("**/api/v1/mvp/card-notices/verify", async (route) => {
    const request = route.request().postDataJSON();
    expect(request.candidate.amount_minor).toBe(1540000);
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        session_id: "vsn_demo_e2e",
        verification_status: "TAMPERED",
        lifecycle_status: "ACTIVE",
        reason_codes: ["AMOUNT_MISMATCH"],
        checks: {
          proof_repository: "FOUND",
          payload_hash: "PASS",
          expiry: "PASS",
          candidate_match: "FAIL",
        },
        verified_at: "2026-09-03T03:14:00Z",
        request_id: "req_demo_amount_tampered",
      }),
    });
  });

  await page.goto("/");
  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(accessibility.violations).toEqual([]);
  await page.getByRole("button", { name: "금액 변조 프리셋" }).click();
  await expect(page.getByLabel("금액 (원)")).toHaveValue("1540000");
  await page.getByRole("button", { name: "실제 Verify API로 검증" }).click();

  await expect(page.getByText("TAMPERED", { exact: true })).toBeVisible();
  await expect(page.getByText("AMOUNT_MISMATCH", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "실제 검증 파이프라인" })).toBeVisible();
  await expect(page.locator(".pipeline-panel").getByText("FAIL", { exact: true })).toBeVisible();
});

test("issuer can submit a synthetic application through the W1 browser flow", async ({ page }) => {
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({
    status: 401,
    contentType: "application/json",
    body: JSON.stringify({ detail: "AUTH_REQUIRED" }),
  }));
  await page.route("**/api/v1/auth/login", async (route) => {
    expect(route.request().postDataJSON()).toEqual({
      username: "demo-issuer-a",
      password: "synthetic-password",
    });
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        account_id: "acct_issuer_a",
        username: "demo-issuer-a",
        role: "issuer",
        issuer_id: "iss_demo_a",
        csrf_token: "csrf_test_token",
      }),
    });
  });
  await page.route("**/api/v1/issuer-applications/mine", (route) => route.fulfill({
    contentType: "application/json",
    body: "null",
  }));
  await page.route("**/api/v1/issuer-applications", async (route) => {
    expect(route.request().postDataJSON()).toEqual({ issuer_name: "Origin Mock Bank" });
    expect(route.request().headers()["x-csrf-token"]).toBe("csrf_test_token");
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        application_id: "app_demo_001",
        issuer_id: "iss_demo_a",
        issuer_name: "Origin Mock Bank",
        applicant_account_id: "acct_issuer_a",
        status: "PENDING_REVIEW",
        decision_reason: null,
        decided_by_account_id: null,
        created_at: "2026-09-30T00:00:00Z",
      }),
    });
  });

  await page.goto("/finals");
  await expect(page.getByRole("heading", { name: "테스트 계정 로그인" })).toBeVisible();
  const loginAccessibility = await new AxeBuilder({ page }).analyze();
  expect(loginAccessibility.violations).toEqual([]);

  await page.getByLabel("계정 이름").fill("demo-issuer-a");
  await page.getByLabel("비밀번호").fill("synthetic-password");
  await page.getByRole("button", { name: "로그인" }).click();
  await expect(page.getByRole("heading", { name: "발행기관 신청" })).toBeVisible();
  await page.getByLabel("합성 기관 이름").fill("Origin Mock Bank");
  await page.getByRole("button", { name: "신청 제출" }).click();
  await expect(page.getByText("검토 대기")).toBeVisible();
  const applicationAccessibility = await new AxeBuilder({ page }).analyze();
  expect(applicationAccessibility.violations).toEqual([]);
});

test("operator review remains pending on chain and issuer can re-query the decision", async ({ browser }) => {
  const application = {
    application_id: "app_demo_002",
    issuer_id: "iss_demo_b",
    issuer_name: "Origin Mock Office",
    applicant_account_id: "acct_issuer_b",
    status: "PENDING_REVIEW",
    decision_reason: null as string | null,
    decided_by_account_id: null as string | null,
    created_at: "2026-09-30T00:00:00Z",
  };
  const issuerContext = await browser.newContext();
  const issuerPage = await issuerContext.newPage();
  await issuerPage.route("**/api/v1/auth/me", (route) => route.fulfill({
    status: 401,
    contentType: "application/json",
    body: JSON.stringify({ detail: "AUTH_REQUIRED" }),
  }));
  await issuerPage.route("**/api/v1/auth/login", (route) => route.fulfill({
    contentType: "application/json",
    body: JSON.stringify({
      account_id: "acct_issuer_b",
      username: "demo-issuer-b",
      role: "issuer",
      issuer_id: "iss_demo_b",
      csrf_token: "issuer_csrf",
    }),
  }));
  await issuerPage.route("**/api/v1/issuer-applications/mine", (route) => route.fulfill({
    contentType: "application/json",
    body: JSON.stringify(application),
  }));

  await issuerPage.goto("/finals");
  await issuerPage.getByLabel("계정 이름").fill("demo-issuer-b");
  await issuerPage.getByLabel("비밀번호").fill("synthetic-password");
  await issuerPage.getByRole("button", { name: "로그인" }).click();
  await expect(issuerPage.getByText("검토 대기")).toBeVisible();

  const operatorContext = await browser.newContext();
  const operatorPage = await operatorContext.newPage();
  await operatorPage.route("**/api/v1/auth/me", (route) => route.fulfill({
    status: 401,
    contentType: "application/json",
    body: JSON.stringify({ detail: "AUTH_REQUIRED" }),
  }));
  await operatorPage.route("**/api/v1/auth/login", (route) => route.fulfill({
    contentType: "application/json",
    body: JSON.stringify({
      account_id: "acct_operator",
      username: "demo-operator",
      role: "operator",
      issuer_id: null,
      csrf_token: "operator_csrf",
    }),
  }));
  await operatorPage.route("**/api/v1/operator/issuer-applications", (route) => route.fulfill({
    contentType: "application/json",
    body: JSON.stringify([application]),
  }));
  await operatorPage.route("**/api/v1/operator/issuer-applications/app_demo_002/decision", async (route) => {
    expect(route.request().postDataJSON()).toEqual({ decision: "APPROVE", reason: "합성 기관 확인" });
    expect(route.request().headers()["x-csrf-token"]).toBe("operator_csrf");
    application.status = "APPROVED_PENDING_CHAIN";
    application.decision_reason = "합성 기관 확인";
    application.decided_by_account_id = "acct_operator";
    await route.fulfill({ contentType: "application/json", body: JSON.stringify(application) });
  });

  await operatorPage.goto("/finals");
  await operatorPage.getByLabel("계정 이름").fill("demo-operator");
  await operatorPage.getByLabel("비밀번호").fill("synthetic-password");
  await operatorPage.getByRole("button", { name: "로그인" }).click();
  await operatorPage.getByLabel("검토 사유").fill("합성 기관 확인");
  await operatorPage.getByRole("button", { name: "승인 검토" }).click();
  await expect(operatorPage.getByText("승인됨 · 체인 활성화 대기")).toBeVisible();

  await issuerPage.getByRole("button", { name: "신청 상태 새로고침" }).click();
  await expect(issuerPage.getByText("승인됨 · 체인 활성화 대기")).toBeVisible();
  await expect(issuerPage.getByText("운영자 검토는 승인됐지만 체인 활성화는 별도 확인이 필요합니다.")).toBeVisible();

  await issuerContext.close();
  await operatorContext.close();
});

test("operator sees uncertain chain work and audit history without a false success", async ({ page }) => {
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({
    status: 401,
    contentType: "application/json",
    body: JSON.stringify({ detail: "AUTH_REQUIRED" }),
  }));
  await page.route("**/api/v1/auth/login", (route) => route.fulfill({
    contentType: "application/json",
    body: JSON.stringify({
      account_id: "acct_operator",
      username: "demo-operator",
      role: "operator",
      issuer_id: null,
      csrf_token: "operator_csrf",
    }),
  }));
  await page.route("**/api/v1/operator/issuer-applications", (route) => route.fulfill({
    contentType: "application/json",
    body: "[]",
  }));
  await page.route("**/api/v1/operations/op_demo_unknown", (route) => route.fulfill({
    contentType: "application/json",
    body: JSON.stringify({
      operation_id: "op_demo_unknown",
      issuer_id: "iss_demo_a",
      action: "ACTIVATE_ISSUER",
      request_id: "req_demo_unknown",
      status: "UNKNOWN",
      tx_hash: null,
      error_code: "SUBMISSION_UNKNOWN",
      created_at: "2026-09-30T00:00:00Z",
    }),
  }));
  await page.route("**/api/v1/audit-events", (route) => route.fulfill({
    contentType: "application/json",
    body: JSON.stringify([{
      event_id: "evt_demo_unknown",
      actor_account_id: "acct_operator",
      issuer_id: "iss_demo_a",
      action: "ISSUER_APPLICATION_DECISION",
      target_id: "app_demo_001",
      before_status: "PENDING_REVIEW",
      after_status: "APPROVED_PENDING_CHAIN",
      created_at: "2026-09-30T00:00:00Z",
    }]),
  }));

  await page.goto("/finals");
  await page.getByLabel("계정 이름").fill("demo-operator");
  await page.getByLabel("비밀번호").fill("synthetic-password");
  await page.getByRole("button", { name: "로그인" }).click();
  await expect(page.getByRole("heading", { name: "기관 신청 검토" })).toBeVisible();
  await page.getByLabel("작업 ID").fill("op_demo_unknown");
  await page.getByRole("button", { name: "작업 상태 조회" }).click();
  await expect(page.getByText("결과 확인 필요")).toBeVisible();
  await expect(page.getByText("아직 없음")).toBeVisible();
  await page.getByRole("button", { name: "감사 이력 새로고침" }).click();
  await expect(page.getByText("PENDING_REVIEW → APPROVED_PENDING_CHAIN")).toBeVisible();
  await expect(page.getByText("체인 활성화 완료")).toHaveCount(0);
  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(accessibility.violations).toEqual([]);
});
