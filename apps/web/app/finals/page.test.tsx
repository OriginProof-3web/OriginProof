import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, expect, test, vi } from "vitest";

import FinalsPage from "./page";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function jsonResponse(payload: unknown, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: async () => payload };
}

function account(role: "issuer" | "operator" | "recipient") {
  return {
    account_id: `acct_${role}`,
    username: `demo-${role}`,
    role,
    issuer_id: role === "issuer" ? "iss_demo_a" : null,
    csrf_token: "csrf_test_token",
  };
}

test("issuer login loads the server role and submits only the institution name", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/api/v1/auth/me") return jsonResponse({ detail: "AUTH_REQUIRED" }, 401);
    if (url === "/api/v1/auth/login") return jsonResponse(account("issuer"));
    if (url === "/api/v1/issuer-applications/mine" && !init?.method) return jsonResponse(null);
    if (url === "/api/v1/issuer-applications" && init?.method === "POST") {
      return jsonResponse({
        application_id: "app_test_001",
        issuer_id: "iss_demo_a",
        issuer_name: "Origin Mock Bank",
        applicant_account_id: "acct_issuer",
        status: "PENDING_REVIEW",
        decision_reason: null,
        decided_by_account_id: null,
        created_at: "2026-09-30T00:00:00Z",
      }, 201);
    }
    throw new Error(`Unexpected request: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<FinalsPage />);
  await screen.findByRole("heading", { name: "테스트 계정 로그인" });
  fireEvent.change(screen.getByLabelText("계정 이름"), { target: { value: "demo-issuer-a" } });
  fireEvent.change(screen.getByLabelText("비밀번호"), { target: { value: "synthetic-password" } });
  fireEvent.click(screen.getByRole("button", { name: "로그인" }));

  expect(await screen.findByRole("heading", { name: "발행기관 신청" })).toBeVisible();
  fireEvent.change(screen.getByLabelText("합성 기관 이름"), { target: { value: "Origin Mock Bank" } });
  fireEvent.click(screen.getByRole("button", { name: "신청 제출" }));

  expect(await screen.findByText("검토 대기")).toBeVisible();
  const loginCall = fetchMock.mock.calls.find(([url]) => String(url) === "/api/v1/auth/login");
  expect(JSON.parse(String(loginCall?.[1]?.body))).toEqual({
    username: "demo-issuer-a",
    password: "synthetic-password",
  });
  const applicationCall = fetchMock.mock.calls.find(([url]) => String(url) === "/api/v1/issuer-applications");
  expect(JSON.parse(String(applicationCall?.[1]?.body))).toEqual({ issuer_name: "Origin Mock Bank" });
  expect(new Headers(applicationCall?.[1]?.headers).get("X-CSRF-Token")).toBe("csrf_test_token");
});

test("operator decision keeps chain activation separate from database approval", async () => {
  const row = {
    application_id: "app_test_002",
    issuer_id: "iss_demo_a",
    issuer_name: "Origin Mock Office",
    applicant_account_id: "acct_issuer",
    status: "PENDING_REVIEW",
    decision_reason: null,
    decided_by_account_id: null,
    created_at: "2026-09-30T00:00:00Z",
  };
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/api/v1/auth/me") return jsonResponse({ detail: "AUTH_REQUIRED" }, 401);
    if (url === "/api/v1/auth/login") return jsonResponse(account("operator"));
    if (url === "/api/v1/operator/issuer-applications" && !init?.method) return jsonResponse([row]);
    if (url.endsWith("/app_test_002/decision")) {
      return jsonResponse({ ...row, status: "APPROVED_PENDING_CHAIN", decision_reason: "합성 기관 확인" });
    }
    throw new Error(`Unexpected request: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<FinalsPage />);
  await screen.findByRole("heading", { name: "테스트 계정 로그인" });
  fireEvent.change(screen.getByLabelText("계정 이름"), { target: { value: "demo-operator" } });
  fireEvent.change(screen.getByLabelText("비밀번호"), { target: { value: "synthetic-password" } });
  fireEvent.click(screen.getByRole("button", { name: "로그인" }));
  await screen.findByRole("heading", { name: "기관 신청 검토" });
  fireEvent.change(screen.getByLabelText("검토 사유"), { target: { value: "합성 기관 확인" } });
  fireEvent.click(screen.getByRole("button", { name: "승인 검토" }));

  expect(await screen.findByText("승인됨 · 체인 활성화 대기")).toBeVisible();
  expect(screen.getByText("운영자 검토는 승인됐지만 체인 활성화는 별도 확인이 필요합니다.")).toBeVisible();
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/operator/issuer-applications/app_test_002/decision",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ decision: "APPROVE", reason: "합성 기관 확인" }),
    }),
  ));
});

test("an expired session returns to login instead of reporting an application result", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/api/v1/auth/me") return jsonResponse({ detail: "AUTH_REQUIRED" }, 401);
    if (url === "/api/v1/auth/login") return jsonResponse(account("issuer"));
    if (url === "/api/v1/issuer-applications/mine" && !init?.method) return jsonResponse(null);
    if (url === "/api/v1/issuer-applications") return jsonResponse({ detail: "AUTH_REQUIRED" }, 401);
    throw new Error(`Unexpected request: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<FinalsPage />);
  await screen.findByRole("heading", { name: "테스트 계정 로그인" });
  fireEvent.change(screen.getByLabelText("계정 이름"), { target: { value: "demo-issuer-a" } });
  fireEvent.change(screen.getByLabelText("비밀번호"), { target: { value: "synthetic-password" } });
  fireEvent.click(screen.getByRole("button", { name: "로그인" }));
  await screen.findByRole("heading", { name: "발행기관 신청" });
  fireEvent.change(screen.getByLabelText("합성 기관 이름"), { target: { value: "Origin Mock Bank" } });
  fireEvent.click(screen.getByRole("button", { name: "신청 제출" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("세션이 만료되었습니다");
  expect(await screen.findByRole("heading", { name: "테스트 계정 로그인" })).toBeVisible();
  await waitFor(() => expect(screen.queryByRole("heading", { name: "발행기관 신청" })).not.toBeInTheDocument());
});

test("logout sends the in-memory CSRF token and returns to login", async () => {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/api/v1/auth/me") return jsonResponse({ detail: "AUTH_REQUIRED" }, 401);
    if (url === "/api/v1/auth/login") return jsonResponse(account("recipient"));
    if (url === "/api/v1/auth/logout") return jsonResponse({ status: "logged_out" });
    throw new Error(`Unexpected request: ${url}`);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<FinalsPage />);
  await screen.findByRole("heading", { name: "테스트 계정 로그인" });
  fireEvent.change(screen.getByLabelText("계정 이름"), { target: { value: "demo-recipient" } });
  fireEvent.change(screen.getByLabelText("비밀번호"), { target: { value: "synthetic-password" } });
  fireEvent.click(screen.getByRole("button", { name: "로그인" }));
  await screen.findByRole("heading", { name: "수신자 계정" });
  fireEvent.click(screen.getByRole("button", { name: "로그아웃" }));

  expect(await screen.findByRole("heading", { name: "테스트 계정 로그인" })).toBeVisible();
  expect(await screen.findByRole("status")).toHaveTextContent("로그아웃했습니다.");
  const logoutCall = fetchMock.mock.calls.find(([url]) => String(url) === "/api/v1/auth/logout");
  expect(new Headers(logoutCall?.[1]?.headers).get("X-CSRF-Token")).toBe("csrf_test_token");
});
