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
        checks: { payload: "MATCH", amount: "MISMATCH" },
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
  await expect(page.getByText("MISMATCH", { exact: true })).toBeVisible();
});
