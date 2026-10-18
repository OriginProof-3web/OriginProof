import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { afterEach, expect, test, vi } from "vitest";

import KeyManagementPage from "./page";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

test("issuer sees contract-pending key state and no private-key input", async () => {
  const fetchMock = vi.fn(async () => ({ ok: true, json: async () => ({ role: "issuer", username: "demo-issuer-a" }) }));
  vi.stubGlobal("fetch", fetchMock);
  render(<KeyManagementPage />);

  expect(await screen.findByRole("heading", { name: "내 기관의 공개 키" })).toBeVisible();
  expect(screen.getByText(/키 목록: 조회 미실행/)).toBeVisible();
  expect(screen.queryByLabelText(/개인키|서명키/)).not.toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("유효 시작 시각"), { target: { value: "2026-10-01T10:00" } });
  fireEvent.change(screen.getByLabelText("유효 종료 시각"), { target: { value: "2026-10-01T09:00" } });
  fireEvent.click(screen.getByRole("button", { name: "입력 조건 확인" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("시작 시각보다 늦어야 합니다");

  fireEvent.change(screen.getByLabelText("유효 종료 시각"), { target: { value: "2026-10-02T09:00" } });
  fireEvent.click(screen.getByRole("button", { name: "입력 조건 확인" }));
  expect(await screen.findByText(/요청은 전송하지 않았습니다/)).toBeVisible();
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

test("operator cannot use issuer key management controls", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, json: async () => ({ role: "operator", username: "demo-operator" }) })));
  render(<KeyManagementPage />);

  expect(await screen.findByRole("heading", { name: "발행기관 권한이 필요합니다" })).toBeVisible();
  expect(screen.queryByRole("button", { name: "입력 조건 확인" })).not.toBeInTheDocument();
});
