import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import React from "react";
import { afterEach, expect, test, vi } from "vitest";

import ProofWorkbenchPage from "./page";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

test("issuer gets a policy-based payment form without a fake issue result", async () => {
  const fetchMock = vi.fn(async () => ({ ok: true, json: async () => ({ role: "issuer", username: "demo-issuer-a" }) }));
  vi.stubGlobal("fetch", fetchMock);
  render(<ProofWorkbenchPage />);

  expect(await screen.findByRole("heading", { name: "새 Proof 입력" })).toBeVisible();
  const issueForm = screen.getByRole("button", { name: "입력 조건 확인" }).closest("form");
  expect(issueForm).not.toBeNull();
  fireEvent.change(screen.getAllByLabelText("Proof 유형")[0], { target: { value: "PAYMENT_REQUEST" } });
  fireEvent.change(within(issueForm!).getByLabelText("금액 (최소 화폐 단위)"), { target: { value: "12000" } });
  fireEvent.change(within(issueForm!).getByLabelText("통화 코드"), { target: { value: "KRW" } });
  fireEvent.change(within(issueForm!).getByLabelText("합성 요청 참조"), { target: { value: "synthetic-invoice-01" } });
  fireEvent.change(within(issueForm!).getByLabelText("만료 시각"), { target: { value: "2030-10-01T12:00" } });
  fireEvent.click(within(issueForm!).getByRole("button", { name: "입력 조건 확인" }));

  expect(await screen.findByText(/요청은 전송하지 않았습니다/)).toBeVisible();
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

test("public lookup remains separate from comparison and explicitly stays unexecuted", async () => {
  const fetchMock = vi.fn(async () => ({ ok: false, json: async () => ({ detail: "AUTH_REQUIRED" }) }));
  vi.stubGlobal("fetch", fetchMock);
  render(<ProofWorkbenchPage />);

  await screen.findByRole("heading", { name: "공개 Proof ID 조회" });
  fireEvent.change(screen.getByLabelText("Proof ID"), { target: { value: "proof_synthetic_001" } });
  fireEvent.click(screen.getByRole("button", { name: "Proof 조회" }));
  expect(await screen.findByText(/조회 요청을 전송하지 않았습니다/)).toBeVisible();
  expect(screen.getByText("조회 미실행 · 현재 상태 미확인")).toBeVisible();
  expect(screen.getByRole("heading", { name: "받은 자료 필드 비교" })).toBeVisible();
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

test("comparison requires a permitted server role", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: false, json: async () => ({ detail: "AUTH_REQUIRED" }) })));
  render(<ProofWorkbenchPage />);
  await screen.findByRole("heading", { name: "받은 자료 필드 비교" });

  const form = screen.getByRole("button", { name: "비교 요청 준비" }).closest("form");
  expect(form).not.toBeNull();
  fireEvent.submit(form!);
  expect(await screen.findByRole("alert")).toHaveTextContent("발행기관 담당자 또는 지정 수신자 로그인");
});

test("issue and comparison forms can select proof types independently", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, json: async () => ({ role: "issuer", username: "demo-issuer-a" }) })));
  render(<ProofWorkbenchPage />);
  await screen.findByRole("heading", { name: "새 Proof 입력" });

  fireEvent.change(screen.getAllByLabelText("Proof 유형")[1], { target: { value: "OFFICIAL_DOCUMENT" } });
  const issueForm = screen.getByRole("button", { name: "입력 조건 확인" }).closest("form");
  const comparisonForm = screen.getByRole("button", { name: "비교 요청 준비" }).closest("form");
  expect(within(issueForm!).getByLabelText("금액 (최소 화폐 단위)")).toBeVisible();
  expect(within(comparisonForm!).getByLabelText("문서 번호")).toBeVisible();
});
