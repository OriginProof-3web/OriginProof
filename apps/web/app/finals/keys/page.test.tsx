import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, expect, test, vi } from "vitest";

import KeyManagementPage from "./page";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
const account = { role: "issuer", username: "demo-issuer-a", csrf_token: "csrf_test" };
const key = { key_id: "key_test", signer: "0xsynthetic", status: "ACTIVE", selected: true };
function response(payload: unknown, status = 200) { return { ok: status < 300, status, json: async () => payload }; }
function setup(status = "CONFIRMED", failingStatus = 0) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path.endsWith("/auth/me")) return response(account);
    if (init?.method === "POST") return failingStatus ? response({}, failingStatus) : response({ operation_id: "op_test", status, tx_hash: status === "CONFIRMED" ? "0xsynthetic" : null });
    if (path.endsWith("/keys")) return response([key]);
    if (path.endsWith("/op_test")) return response({ operation_id: "op_test", status, tx_hash: null });
    throw new Error(`Unexpected ${path}`);
  });
  vi.stubGlobal("fetch", fetchMock); render(<KeyManagementPage />); return fetchMock;
}
async function fillRegistration() {
  await screen.findByText("key_test");
  fireEvent.change(screen.getByLabelText("유효 시작 시각"), { target: { value: "2026-10-01T10:00" } });
  fireEvent.change(screen.getByLabelText("유효 종료 시각"), { target: { value: "2026-11-01T10:00" } });
  fireEvent.change(screen.getByLabelText("키 등록 사유"), { target: { value: "합성 키 등록" } });
}

test("issuer queries actual key list, never renders private-key input", async () => {
  const mock = setup(); await screen.findByText("key_test");
  expect(mock).toHaveBeenCalledWith("/api/v1/issuer/keys", expect.anything());
  expect(screen.queryByLabelText(/개인키|서명키/)).not.toBeInTheDocument();
});
test("invalid dates never submit registration", async () => {
  const mock = setup(); await fillRegistration();
  fireEvent.change(screen.getByLabelText("유효 종료 시각"), { target: { value: "2026-10-01T09:00" } });
  fireEvent.click(screen.getByRole("button", { name: "키 생성·등록" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("시작 시각보다 늦어야");
  expect(mock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(0);
});
test("valid registration sends CSRF, whole-second UTC and distinct request ID", async () => {
  const mock = setup(); await fillRegistration();
  fireEvent.click(screen.getByRole("button", { name: "키 생성·등록" }));
  await screen.findByText("op_test");
  const call = mock.mock.calls.find(([, init]) => init?.method === "POST")!;
  const body = JSON.parse(String(call[1]?.body));
  expect(call[0]).toBe("/api/v1/issuer/keys");
  expect(new Headers(call[1]?.headers).get("X-CSRF-Token")).toBe("csrf_test");
  expect(body.request_id).toMatch(/^req_/); expect(body.reason).toBe("합성 키 등록");
  expect(body.valid_from).toMatch(/00Z$/); expect(body.valid_until).toMatch(/00Z$/);
});
test("revocation submits the displayed key ID with its reason", async () => {
  const mock = setup(); await screen.findByText("key_test");
  fireEvent.change(screen.getByLabelText("키 폐기 사유"), { target: { value: "합성 유출 폐기" } });
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(screen.getByRole("button", { name: "키 폐기" }));
  await screen.findByText("op_test");
  expect(mock.mock.calls.find(([, init]) => init?.method === "POST")?.[0]).toBe("/api/v1/issuer/keys/key_test/revoke");
});
test("unknown mutation offers same Operation recovery and no confirmed message", async () => {
  const mock = setup("UNKNOWN"); await fillRegistration();
  fireEvent.click(screen.getByRole("button", { name: "키 생성·등록" })); await screen.findByText("op_test");
  expect(screen.queryByText("체인 확인 완료")).not.toBeInTheDocument();
  await waitFor(() => expect(screen.getByRole("button", { name: "기존 거래 상태 복구" })).toBeEnabled());
  fireEvent.click(screen.getByRole("button", { name: "기존 거래 상태 복구" }));
  await waitFor(() => expect(mock.mock.calls.some(([path]) => String(path).endsWith("/op_test/recover"))).toBe(true));
});
test("rate limit does not resend mutation", async () => {
  const mock = setup("CONFIRMED", 429); await fillRegistration();
  fireEvent.click(screen.getByRole("button", { name: "키 생성·등록" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("요청이 많습니다");
  expect(mock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1);
});
test("operator cannot see issuer key mutation controls", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => response({ role: "operator", username: "demo-operator" })));
  render(<KeyManagementPage />);
  expect(await screen.findByRole("heading", { name: "발행기관 권한이 필요합니다" })).toBeVisible();
  expect(screen.queryByRole("button", { name: "키 생성·등록" })).not.toBeInTheDocument();
});
test("session expiry clears key controls", async () => {
  const mock = setup("CONFIRMED", 401); await fillRegistration();
  fireEvent.click(screen.getByRole("button", { name: "키 생성·등록" }));
  expect(await screen.findByRole("heading", { name: "로그인이 필요합니다" })).toBeVisible();
  expect(screen.getByRole("alert")).toHaveTextContent("세션이 만료");
  expect(mock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1);
});
