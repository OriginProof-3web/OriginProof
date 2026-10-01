"use client";

import { FormEvent, useEffect, useState } from "react";

type ProofType = "PAYMENT_REQUEST" | "OFFICIAL_DOCUMENT";
type Role = "operator" | "issuer" | "recipient";
type Account = { role: Role; username: string };

const proofTypeLabels: Record<ProofType, string> = {
  PAYMENT_REQUEST: "지급 요청",
  OFFICIAL_DOCUMENT: "공식 문서",
};

export default function ProofWorkbenchPage() {
  const [account, setAccount] = useState<Account | null>(null);
  const [sessionChecked, setSessionChecked] = useState(false);
  const [issueProofType, setIssueProofType] = useState<ProofType>("PAYMENT_REQUEST");
  const [compareProofType, setCompareProofType] = useState<ProofType>("PAYMENT_REQUEST");
  const [issueNotice, setIssueNotice] = useState<string | null>(null);
  const [lookupNotice, setLookupNotice] = useState<string | null>(null);
  const [compareNotice, setCompareNotice] = useState<string | null>(null);
  const [issueError, setIssueError] = useState<string | null>(null);
  const [compareError, setCompareError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetch("/api/v1/auth/me")
      .then(async (response) => response.ok ? (await response.json()) as Account : null)
      .then((current) => { if (active && current) setAccount(current); })
      .catch(() => undefined)
      .finally(() => { if (active) setSessionChecked(true); });
    return () => { active = false; };
  }, []);

  function prepareIssue(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIssueError(null);
    setIssueNotice(null);
    const values = new FormData(event.currentTarget);
    const expiresAt = Date.parse(String(values.get("expires_at") ?? ""));
    if (!Number.isFinite(expiresAt) || expiresAt <= Date.now()) {
        setIssueError("만료 시각은 현재보다 뒤여야 합니다.");
      return;
    }
    if (issueProofType === "PAYMENT_REQUEST") {
      const amount = Number(values.get("amount_minor"));
      const currency = String(values.get("currency") ?? "").trim();
      const targetRef = String(values.get("target_ref") ?? "").trim();
      if (!Number.isSafeInteger(amount) || amount <= 0) {
        setIssueError("금액은 양의 정수 최소 화폐 단위로 입력해 주세요.");
        return;
      }
      if (!/^[A-Z]{3}$/.test(currency)) {
        setIssueError("통화는 대문자 3자리 코드로 입력해 주세요.");
        return;
      }
      if (!targetRef) {
        setIssueError("합성 요청 참조를 입력해 주세요.");
        return;
      }
    } else {
      const version = Number(values.get("version"));
      if (!Number.isSafeInteger(version) || version <= 0) {
        setIssueError("문서 개정 번호는 양의 정수여야 합니다.");
        return;
      }
      const requiredText = ["institution_code", "document_type", "document_number"];
      if (requiredText.some((field) => !String(values.get(field) ?? "").trim())) {
        setIssueError("기관 코드, 문서 유형과 문서 번호를 입력해 주세요.");
        return;
      }
    }
    setIssueNotice("화면 입력을 확인했습니다. 발행 API/생성 모델이 없어 요청은 전송하지 않았습니다.");
  }

  function prepareLookup(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLookupNotice("공개 Proof 조회 API가 아직 연결되지 않아 조회 요청을 전송하지 않았습니다.");
  }

  function prepareComparison(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCompareError(null);
    setCompareNotice(null);
    if (!account || (account.role !== "issuer" && account.role !== "recipient")) {
      setCompareError("제한 필드 비교는 발행기관 담당자 또는 지정 수신자 로그인 후 이용할 수 있습니다.");
      return;
    }
    setCompareNotice("비교 API/응답 모델이 아직 연결되지 않아 비교 요청을 전송하지 않았습니다.");
  }

  return (
    <main className="finals-page proof-workbench">
      <header className="finals-header">
        <div>
          <p className="eyebrow">ORIGINPROOF · FINALS W3</p>
          <h1>Proof 발행과 검증 준비</h1>
          <p className="subtitle">아래는 ADR 0001 기준의 화면 입력 초안입니다. 저장·서명·검증은 연결되지 않았으며 성공 결과를 만들지 않습니다.</p>
        </div>
        {account && <span className="account-strip">{account.username} · {account.role}</span>}
      </header>

      <section className="finals-card" aria-labelledby="issue-proof-heading">
        <h2 id="issue-proof-heading">새 Proof 입력</h2>
        {!sessionChecked ? <p role="status">로그인 상태를 확인하고 있습니다.</p> : account?.role !== "issuer" ? (
          <p>발행 입력은 발행기관 담당자 화면입니다. {account ? "현재 계정은 발행기관 담당자가 아닙니다." : <a href="/finals">테스트 계정으로 로그인해 주세요.</a>}</p>
        ) : (
          <>
            <label>Proof 유형
                <select value={issueProofType} onChange={(event) => { setIssueProofType(event.target.value as ProofType); setIssueNotice(null); setIssueError(null); }}>
                <option value="PAYMENT_REQUEST">{proofTypeLabels.PAYMENT_REQUEST}</option>
                <option value="OFFICIAL_DOCUMENT">{proofTypeLabels.OFFICIAL_DOCUMENT}</option>
              </select>
            </label>
            <form className="finals-form proof-form" onSubmit={prepareIssue}>
              {issueProofType === "PAYMENT_REQUEST" ? (
                <>
                  <label>금액 (최소 화폐 단위)<input name="amount_minor" type="number" min="1" step="1" required /></label>
                  <label>통화 코드<input name="currency" maxLength={3} pattern="[A-Z]{3}" placeholder="KRW" required /></label>
                  <label>합성 요청 참조<input name="target_ref" autoComplete="off" required /></label>
                </>
              ) : (
                <>
                  <label>합성 기관 코드<input name="institution_code" autoComplete="off" required /></label>
                  <label>문서 유형<input name="document_type" required /></label>
                  <label>문서 번호<input name="document_number" autoComplete="off" required /></label>
                  <label>문서 개정 번호<input name="version" type="number" min="1" step="1" required /></label>
                </>
              )}
              <label>수신자<select name="recipient_id" disabled required defaultValue="">
                <option value="">수신자 목록 API 대기</option>
              </select></label>
              <label>만료 시각<input name="expires_at" type="datetime-local" required /></label>
              <p className="contract-pending" role="status">합성 테스트 값만 입력해 주세요. 서버가 Proof ID, nonce, binding과 issued_at을 생성합니다. 수신자 목록과 발행 API 계약을 기다리고 있습니다.</p>
              <button type="submit">입력 조건 확인</button>
            </form>
            {issueError && <p className="finals-message finals-error" role="alert">{issueError}</p>}
            {issueNotice && <p className="finals-message finals-info" role="status">{issueNotice}</p>}
          </>
        )}
      </section>

      <section className="finals-card" aria-labelledby="lookup-heading">
        <h2 id="lookup-heading">공개 Proof ID 조회</h2>
        <p>ID-only 조회는 발행 근거 범위만 확인합니다. 자료 내용 일치나 전체 현재 사용 가능 여부를 주장하지 않습니다.</p>
        <form className="proof-inline-form" onSubmit={prepareLookup}>
          <label>Proof ID<input name="proof_id" autoComplete="off" required /></label>
          <button type="submit">Proof 조회</button>
        </form>
        {lookupNotice && <p className="finals-message finals-info" role="status">{lookupNotice}</p>}
        <p className="chain-pending" role="status">조회 미실행 · 현재 상태 미확인</p>
      </section>

      <section className="finals-card" aria-labelledby="compare-heading">
        <h2 id="compare-heading">받은 자료 필드 비교</h2>
        <p>비교는 공개 ID 조회와 분리하며, 발행기관 담당자 또는 지정 수신자 인증 뒤 허용된 필드만 확인합니다. 조회는 consume을 실행하지 않습니다.</p>
        <form className="finals-form proof-form" onSubmit={prepareComparison}>
          <label>Proof 유형
            <select value={compareProofType} onChange={(event) => { setCompareProofType(event.target.value as ProofType); setCompareNotice(null); setCompareError(null); }}>
              <option value="PAYMENT_REQUEST">{proofTypeLabels.PAYMENT_REQUEST}</option>
              <option value="OFFICIAL_DOCUMENT">{proofTypeLabels.OFFICIAL_DOCUMENT}</option>
            </select>
          </label>
          {compareProofType === "PAYMENT_REQUEST" ? (
            <>
              <label>금액 (최소 화폐 단위)<input name="compare_amount_minor" type="number" min="1" step="1" required /></label>
              <label>통화 코드<input name="compare_currency" maxLength={3} pattern="[A-Z]{3}" required /></label>
              <label>합성 요청 참조<input name="compare_target_ref" autoComplete="off" required /></label>
            </>
          ) : (
            <>
              <label>합성 기관 코드<input name="compare_institution_code" required /></label>
              <label>문서 유형<input name="compare_document_type" required /></label>
              <label>문서 번호<input name="compare_document_number" autoComplete="off" required /></label>
              <label>문서 개정 번호<input name="compare_version" type="number" min="1" step="1" required /></label>
            </>
          )}
          <button type="submit">비교 요청 준비</button>
        </form>
        {compareError && <p className="finals-message finals-error" role="alert">{compareError}</p>}
        {compareNotice && <p className="finals-message finals-info" role="status">{compareNotice}</p>}
        <p className="contract-pending">검증 API 미연결 · lifecycle은 null/미확인 · 성공 판정 미실행</p>
      </section>

      <section className="finals-card" aria-labelledby="history-heading">
        <h2 id="history-heading">발행 기록</h2>
        <p>자기 기관 목록·상세 API가 없어 Proof 목록은 표시하지 않습니다. 발행 API 연결 후 서버가 반환한 저장 ID를 표시합니다.</p>
      </section>
    </main>
  );
}
