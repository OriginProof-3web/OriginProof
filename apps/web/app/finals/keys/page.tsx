"use client";

import { FormEvent, useEffect, useState } from "react";

import type { AccountView, KeyView, OperationView } from "../../../../../packages/schemas/generated/types/api";
import { request } from "../api-client";

const operationLabels: Record<string, string> = {
  CONFIRMED: "체인 확인 완료", FAILED: "체인 작업 실패", UNKNOWN: "결과 확인 필요",
  SUBMITTED: "체인 확인 대기", PENDING_SUBMISSION: "제출 대기",
};

export default function KeyManagementPage() {
  const [account, setAccount] = useState<AccountView | null>(null);
  const [checked, setChecked] = useState(false);
  const [keys, setKeys] = useState<KeyView[] | null>(null);
  const [operation, setOperation] = useState<OperationView | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  function failure(reason: unknown) {
    const code = reason instanceof Error ? reason.message : "HTTP_ERROR";
    if (code === "AUTH_REQUIRED" || code === "HTTP_401") {
      setAccount(null); setKeys(null);
      setError("세션이 만료되었습니다. 다시 로그인해 주세요.");
    } else {
      setError(code === "HTTP_429" ? "요청이 많습니다. 잠시 후 상태를 조회해 주세요." : `작업을 처리하지 못했습니다 (${code}). 상태를 조회한 뒤 확인해 주세요.`);
    }
  }

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const current = await request<AccountView>("/v1/auth/me");
        if (!active) return;
        setAccount(current);
        if (current.role === "issuer") {
          const rows = await request<KeyView[]>("/v1/issuer/keys");
          if (active) setKeys(rows);
        }
      } catch (reason) { if (active) failure(reason); }
      finally { if (active) setChecked(true); }
    }
    void load();
    return () => { active = false; };
  }, []);

  async function refresh() {
    setBusy(true); setError("");
    try { setKeys(await request<KeyView[]>("/v1/issuer/keys")); }
    catch (reason) { failure(reason); }
    finally { setBusy(false); }
  }

  async function mutate(event: FormEvent<HTMLFormElement>, key?: KeyView) {
    event.preventDefault();
    if (!account || busy) return;
    const form = new FormData(event.currentTarget);
    const body: Record<string, string> = { request_id: `req_${crypto.randomUUID()}`, reason: String(form.get("reason") ?? "") };
    setError(""); setMessage("");
    if (!key) {
      const from = Date.parse(String(form.get("valid_from") ?? ""));
      const until = Date.parse(String(form.get("valid_until") ?? ""));
      if (!Number.isFinite(from) || !Number.isFinite(until) || until <= from) {
        setError("유효 종료 시각은 시작 시각보다 늦어야 합니다."); return;
      }
      body.valid_from = new Date(from).toISOString().replace(".000Z", "Z");
      body.valid_until = new Date(until).toISOString().replace(".000Z", "Z");
    }
    setBusy(true);
    try {
      const result = await request<OperationView>(key ? `/v1/issuer/keys/${encodeURIComponent(key.key_id)}/revoke` : "/v1/issuer/keys", {
        method: "POST", headers: { "X-CSRF-Token": account.csrf_token }, body: JSON.stringify(body),
      });
      setOperation(result);
      setMessage(operationLabels[result.status] ?? "상태 확인 필요");
      setKeys(await request<KeyView[]>("/v1/issuer/keys"));
    } catch (reason) { failure(reason); }
    finally { setBusy(false); }
  }

  async function inspectOperation(recover = false) {
    if (!operation || !account || busy) return;
    setBusy(true); setError("");
    try {
      const path = `/v1/operations/${encodeURIComponent(operation.operation_id)}`;
      setOperation(await request<OperationView>(recover ? `${path}/recover` : path, recover ? {
        method: "POST", headers: { "X-CSRF-Token": account.csrf_token }, body: "{}",
      } : undefined));
      setKeys(await request<KeyView[]>("/v1/issuer/keys"));
    } catch (reason) { failure(reason); }
    finally { setBusy(false); }
  }

  return <main className="finals-page">
    <header className="finals-header"><div><p className="eyebrow">ORIGINPROOF · FINALS W2</p><h1>발행 키 관리</h1><p>개인키는 서버에 보관하며 브라우저에는 공개 키와 실제 상태만 표시합니다.</p></div></header>
    {error && <p role="alert" className="finals-message finals-error">{error}</p>}
    {message && <p role="status">{message}</p>}
    {!checked ? <p role="status">로그인 상태를 확인하고 있습니다.</p> : !account ? <section className="finals-card"><h2>로그인이 필요합니다</h2><a href="/finals">로그인 화면으로 이동</a></section> : account.role !== "issuer" ? <section className="finals-card"><h2>발행기관 권한이 필요합니다</h2><p>발행기관 계정으로 로그인해 주세요.</p></section> : <>
      <section className="finals-card"><h2>내 기관의 공개 키</h2><button disabled={busy} onClick={() => void refresh()}>키 목록 새로고침</button>
        {keys === null ? <p>키 목록 조회 결과가 없습니다.</p> : keys.length === 0 ? <p role="status">등록된 키가 없습니다.</p> : keys.map(key => <article key={key.key_id}>
          <dl><div><dt>키 ID</dt><dd>{key.key_id}</dd></div><div><dt>공개 signer</dt><dd>{key.signer}</dd></div><div><dt>현재 상태</dt><dd>{key.status}</dd></div><div><dt>현재 발행 키</dt><dd>{key.selected ? "선택됨" : "선택 안 됨"}</dd></div></dl>
          {key.status !== "REVOKED" && <form onSubmit={event => void mutate(event, key)}><label>키 폐기 사유<input name="reason" required maxLength={500} /></label><label><input type="checkbox" required />유출 키 폐기는 해당 키의 기존 Proof도 현재 사용 불가로 만듭니다.</label><button disabled={busy}>키 폐기</button></form>}
        </article>)}
      </section>
      <section className="finals-card"><h2>키 생성·등록</h2><form className="finals-form" onSubmit={event => void mutate(event)}>
        <label>유효 시작 시각<input type="datetime-local" name="valid_from" required /></label><label>유효 종료 시각<input type="datetime-local" name="valid_until" required /></label><label>키 등록 사유<input name="reason" required maxLength={500} /></label>
        <button disabled={busy}>{busy ? "처리 중…" : "키 생성·등록"}</button>
      </form></section>
      {operation && <section className="finals-card"><h2>등록·폐기 작업 상태</h2><dl><div><dt>작업 ID</dt><dd>{operation.operation_id}</dd></div><div><dt>상태</dt><dd>{operationLabels[operation.status] ?? "상태 확인 필요"}</dd></div><div><dt>트랜잭션</dt><dd>{operation.tx_hash ?? "아직 없음"}</dd></div>{operation.error_code && <div><dt>오류</dt><dd>{operation.error_code}</dd></div>}</dl><button disabled={busy} onClick={() => void inspectOperation()}>작업 상태 조회</button>{["UNKNOWN", "SUBMITTED", "PENDING_SUBMISSION"].includes(operation.status) && <button disabled={busy} onClick={() => void inspectOperation(true)}>기존 거래 상태 복구</button>}</section>}
    </>}
  </main>;
}
