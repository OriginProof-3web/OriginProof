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
      checks: { signature: "PASS", candidate_match: "PASS" },
      verified_at: "2026-09-03T03:14:00Z",
      request_id: "req_demo_normal",
    }),
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<DemoPage />);
  fireEvent.click(screen.getByRole("button", { name: "정상 프리셋" }));
  fireEvent.click(screen.getByRole("button", { name: "실제 Verify API로 검증" }));

  expect(await screen.findByText("VERIFIED", { exact: true })).toBeVisible();
  expect(screen.getByText("ACTIVE", { exact: true })).toBeVisible();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/mvp/card-notices/verify",
    expect.objectContaining({
      method: "POST",
      body: expect.stringContaining('"amount_minor":154000'),
    }),
  );
});
