import { fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { afterEach, expect, test, vi } from "vitest";

import DemoPage from "./page";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("normal preset submits the generated API contract and displays the response", async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      session_id: "vsn_component_test",
      verification_status: "VERIFIED",
      lifecycle_status: "ACTIVE",
      reason_codes: [],
      checks: {
        proof_repository: "FOUND",
        payload_hash: "PASS",
        expiry: "PASS",
        candidate_match: "PASS",
        issuer: "ACTIVE",
        issuer_key: "ACTIVE",
        signature: "PASS",
      },
      verified_at: "2026-09-03T03:14:00Z",
      request_id: "req_demo_normal",
    }),
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<DemoPage />);
  fireEvent.click(screen.getByRole("button", { name: "정상 프리셋" }));
  fireEvent.click(screen.getByRole("button", { name: "실제 Verify API로 검증" }));

  expect(await screen.findByText("VERIFIED", { exact: true })).toBeVisible();
  expect(screen.getAllByText("ACTIVE", { exact: true }).length).toBeGreaterThan(0);
  expect(screen.getByRole("heading", { name: "정상 프리셋의 신뢰 기준" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "실제 검증 파이프라인" })).toBeVisible();
  expect(screen.getByText("Issuer ACTIVE · Key ACTIVE · Signature PASS")).toBeVisible();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/mvp/card-notices/verify",
    expect.objectContaining({
      method: "POST",
      body: expect.stringContaining('"amount_minor":154000'),
    }),
  );
});
