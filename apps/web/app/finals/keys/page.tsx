"use client";

import { FormEvent, useEffect, useState } from "react";

type Account = { role: string; username: string };

export default function KeyManagementPage() {
  const [account, setAccount] = useState<Account | null>(null);
  const [sessionChecked, setSessionChecked] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetch("/api/v1/auth/me")
      .then(async (response) => {
        if (!response.ok) return null;
        return (await response.json()) as Account;
      })
      .then((current) => {
        if (active && current) setAccount(current);
      })
      .catch(() => undefined)
      .finally(() => {
        if (active) setSessionChecked(true);
      });
    return () => { active = false; };
  }, []);

  function inspectRequest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    setError(null);
    const form = new FormData(event.currentTarget);
    const validFrom = Date.parse(String(form.get("valid_from") ?? ""));
    const validUntil = Date.parse(String(form.get("valid_until") ?? ""));
    if (!Number.isFinite(validFrom) || !Number.isFinite(validUntil) || validUntil <= validFrom) {
      setError("유효 종료 시각은 시작 시각보다 늦어야 합니다.");
      return;
    }
    setMessage("유효 기간 입력은 확인했습니다. 키 생성·등록 API 계약이 없어 요청은 전송하지 않았습니다.");
  }

  return (
    <main className="finals-page">
      <header className="finals-header">
        <div>
          <p className="eyebrow">ORIGINPROOF · FINALS W2</p>
          <h1>발행 키 관리</h1>
          <p className="subtitle">브라우저에는 공개 signer와 키 상태만 표시하며 개인키를 입력하거나 보관하지 않습니다.</p>
        </div>
        {account && <span className="account-strip">{account.username} · 발행기관 담당자</span>}
      </header>
      {!sessionChecked ? <p role="status">로그인 상태를 확인하고 있습니다.</p> : !account ? (
        <section className="finals-card">
          <h2>로그인이 필요합니다</h2>
          <p>준비된 발행기관 계정으로 로그인한 뒤 키 관리 화면을 이용해 주세요.</p>
          <a href="/finals">로그인 화면으로 이동</a>
        </section>
      ) : account.role !== "issuer" ? (
        <section className="finals-card">
          <h2>발행기관 권한이 필요합니다</h2>
          <p>계정 role은 서버 응답으로 확인합니다. 운영자 계정으로 발행 키를 변경할 수 없습니다.</p>
        </section>
      ) : (
        <>
          <section className="finals-card" aria-labelledby="keys-heading">
            <h2 id="keys-heading">내 기관의 공개 키</h2>
            <p>키 목록·상세 API 계약이 아직 연결되지 않았습니다. 현재 등록 상태를 조회하지 못했으므로 빈 목록이나 등록 완료로 단정하지 않습니다.</p>
            <p className="chain-pending" role="status">키 목록: 조회 미실행 · 체인 상태: 확인 대기</p>
          </section>
          <section className="finals-card key-create-card" aria-labelledby="create-key-heading">
            <h2 id="create-key-heading">키 유효 기간 입력</h2>
            <p>서버 측 합성 서명기와 challenge 검증이 준비되어야 등록할 수 있습니다. 개인키 생성은 브라우저에서 수행하지 않습니다.</p>
            <form className="finals-form" onSubmit={inspectRequest}>
              <label>유효 시작 시각<input type="datetime-local" name="valid_from" required /></label>
              <label>유효 종료 시각<input type="datetime-local" name="valid_until" required /></label>
              <button type="submit">입력 조건 확인</button>
            </form>
            {error && <p className="finals-message finals-error" role="alert">{error}</p>}
            {message && <p className="finals-message finals-info" role="status">{message}</p>}
          </section>
          <section className="finals-card" aria-labelledby="key-contract-heading">
            <h2 id="key-contract-heading">등록·폐기 API 연결 대기</h2>
            <p>W2-C3가 공개할 key ID, signer, 기간, 상태와 operation 응답 모델을 받은 뒤 생성·등록·목록·폐기와 실패/재조회 상태를 연결합니다. 정상 교체는 신규 키 확정 후 발행 키를 전환하며, 폐기한 키는 다시 활성화하지 않습니다.</p>
          </section>
        </>
      )}
    </main>
  );
}
