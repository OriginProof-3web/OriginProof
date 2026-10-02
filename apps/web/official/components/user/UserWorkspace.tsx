import { useEffect, useState, useRef, useCallback, type FormEvent } from "react";
import { Search, ArrowRight, Copy, Check, FileText, History, RefreshCw } from "lucide-react";

import ArtifactExtraction from "./ArtifactExtraction";
import { api, requestId } from "../../api-client.js";
import type { ProofView, ProofContent } from "../api-types.generated";

import type { FinalsVerificationResult } from "../core-types.generated";
type Action = "verify" | "compare" | "consume" | "history";
type Proof = { id: string; issuer: string; type: "PAYMENT_REQUEST" | "OFFICIAL_DOCUMENT"; issued: string; expires: string; fields: Record<string, string> };
type Entry = { id: string; proof: string; action: string; summary: string; time: string };
const fieldNames: Record<string, string> = { amount_minor: "금액 (최소 화폐 단위)", currency: "통화", target_ref: "요청 대상 코드", institution_code: "기관 코드", document_type: "문서 유형", document_number: "문서번호", version: "문서 개정 번호" };
const labels: Record<Action, string> = { verify: "Proof 조회", compare: "내용 비교", consume: "요청 사용", history: "검증 내역" };
const descriptions: Record<Action, string> = { verify: "받은 Proof ID 또는 검증 링크를 입력해 발행 기록을 확인하세요.", compare: "받은 자료의 핵심 내용을 입력해 서버에서 발행 내용과 비교하세요.", consume: "지정 수신자가 받은 1회성 요청의 사용 조건을 확인합니다.", history: "현재 화면에서 수행한 조회·비교 기록입니다. 새로고침하면 초기화됩니다." };
function parseProof(value: string): string {
  const input = value.trim();
  if (/^prf_[A-Za-z0-9_-]+$/.test(input)) return input;
  try { const url = new URL(input); if (!["https:", "http:"].includes(url.protocol)) return ""; const id = url.searchParams.get("proof_id") ?? url.pathname.split("/").filter(Boolean).at(-1) ?? ""; return /^prf_[A-Za-z0-9_-]+$/.test(id) ? id : ""; } catch { return ""; }
}
function time(value: string) { return new Date(value).toLocaleString("ko-KR"); }
function Summary({ proof }: { proof: Proof }) {
  return <dl className="uw-summary">
    <div><dt>Proof ID</dt><dd>{proof.id}</dd></div><div><dt>발행기관</dt><dd>{proof.issuer}</dd></div>
    <div><dt>자료 유형</dt><dd>{proof.type === "PAYMENT_REQUEST" ? "지급 요청" : "공식 문서"}</dd></div>
    <div><dt>발행 시각</dt><dd>{time(proof.issued)}</dd></div><div><dt>만료 시각</dt><dd>{time(proof.expires)}</dd></div>
  </dl>;
}
function Checks({ result }: { result: FinalsVerificationResult | null }) {
 return <details className="uw-checks"><summary>검사 근거</summary><ul>{Object.entries(result?.checks ?? {}).map(([label,state])=><li key={label}><span>{label}</span><span>{state}</span></li>)}</ul><p>{result?.reason_codes?.join(" · ")}</p></details>;
}

export default function UserWorkspace() {
  const [result,setResult] = useState<FinalsVerificationResult | null>(null);
  const [busy,setBusy] = useState(false);
  const generation=useRef(0);
  const pending=useRef(false);
  const [action, setAction] = useState<Action>("verify");
  const [input, setInput] = useState("");
  const [proof, setProof] = useState<Proof | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [values, setValues] = useState<Record<string, string>>({});
  const [rows, setRows] = useState<{ key: string; state: string }[] | null>(null);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [filter, setFilter] = useState("");
  const [historyAction, setHistoryAction] = useState("all");
  const [copied, setCopied] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const record = useCallback((id: string, kind: string, summary: string) => {
    const entry = { id: crypto.randomUUID(), proof: id, action: kind, summary, time: new Date().toISOString() };
    setEntries(previous=>[entry,...previous].slice(0,50));
  }, []);
  const load = useCallback(async (id: string) => {
    const token=++generation.current; setBusy(true);setError("");setResult(null);setProof(null);
    try {
      const view: ProofView = await api(`/v2/proofs/${encodeURIComponent(id)}`);
      const verification: FinalsVerificationResult = await api(`/v2/proofs/${encodeURIComponent(id)}/verify`,{request_id:requestId()});
      let fields=Object.fromEntries((view.proof_type==="PAYMENT_REQUEST"?["amount_minor","currency","target_ref"]:["institution_code","document_type","document_number","version"]).map(name=>[name,""]));
      // Restricted content is never inferred from a public Proof ID.
      try { const content: ProofContent=await api(`/v2/proofs/${encodeURIComponent(id)}/content`); const payload=content.envelope.payload; fields=Object.fromEntries(Object.keys(fields).map(name=>[name,String(name==="target_ref"?content.target_ref??"":(payload as any)[name]??"")])); } catch {}
      if(token!==generation.current)return;
      setProof({id:view.proof_id,issuer:view.issuer_id,type:view.proof_type,issued:view.issued_at,expires:view.expires_at,fields});setResult(verification);
      record(id,"verify",`${verification.verification_status} · ${verification.scope}`);
    } catch(error) {if(token===generation.current)setError((error as Error).message);} finally{if(token===generation.current)setBusy(false);}
  }, [record]);
  useEffect(() => {
    const linkedId = new URLSearchParams(location.search).get("proof_id");
    if (linkedId) {
      const id = parseProof(linkedId);
      setInput(linkedId);
      if(id) void load(id);
    }
    const change = (event: Event) => {
      const detail = (event as CustomEvent).detail;
      const next = detail?.key === "home" ? "verify" : detail?.key;
      if (Object.hasOwn(labels, next)) { setAction(next); setError(""); setMessage(""); setRows(null); setConfirmed(false); setCopied(false); if (detail.proofId) { setInput(detail.proofId); void load(detail.proofId); setValues({}); } }
    };
    window.addEventListener("originproof-action", change);
    return () => window.removeEventListener("originproof-action", change);
  }, [load]);
  function lookup(event: FormEvent) {
    event.preventDefault();setMessage("");setRows(null);setConfirmed(false);setValues({});setCopied(false);
    const id=parseProof(input);if(!id){setProof(null);setError("Proof ID 또는 검증 링크를 입력해 주세요.");return;}void load(id);
  }
  async function compare(event: FormEvent) {
    event.preventDefault();if(!proof||pending.current)return;pending.current=true;const token=++generation.current;setBusy(true);setError("");
    try {
      const candidate=Object.fromEntries(Object.entries(values).filter(([,value])=>value.trim()).map(([key,value])=>[key,["amount_minor","version"].includes(key)?Number(value):value.trim()]));
      const verdict: FinalsVerificationResult=await api(`/v2/proofs/${encodeURIComponent(proof.id)}/verify`,{request_id:requestId(),candidate});
      if(token!==generation.current)return;
      setResult(verdict);setMessage(`${verdict.verification_status} · ${verdict.scope} · ${verdict.reason_codes?.join(" · ")}`);
      setRows([]);record(proof.id,"compare",`${verdict.verification_status} · ${verdict.scope}`);
    }catch(error){if(token===generation.current)setError((error as Error).message);}finally{pending.current=false;if(token===generation.current)setBusy(false);}
  }
  function useRequest() {
    if (!proof || !confirmed) return;
    setMessage(proof.type === "OFFICIAL_DOCUMENT" ? "문서형은 1회 사용 대상이 아닙니다." : "사용 요청을 제출하지 않았습니다. 서버의 수신자 권한 확인과 체인 상태 연결이 필요합니다.");
    record(proof.id, "consume", "사용 조건 확인 · API 연결 대기 · 미제출");
  }
  function jump(next: Action, id?: string) { (window as any).selectAction(next, id); }
  async function copy() {
    if (!proof) return;
    try { await navigator.clipboard.writeText(proof.id); setCopied(true); } catch { setMessage("복사를 사용할 수 없습니다. 표시된 Proof ID를 선택해 복사해 주세요."); }
  }
  const visible = entries.filter((entry) => (historyAction === "all" || entry.action === historyAction) && `${entry.proof} ${entry.summary}`.toLowerCase().includes(filter.trim().toLowerCase()));
  return <div className="uw-shell">
    <header className="uw-header"><span className="uw-eyebrow">PERSONAL SPACE</span><span className="uw-preview">실제 API · 로컬 테스트</span><h1>{labels[action]}</h1><p>{descriptions[action]}</p></header>
    {action === "history" ? <section className="uw-card">
      <div className="uw-history-tools"><label className="uw-search"><Search size={17} /><input aria-label="검증 내역 검색" placeholder="Proof ID 또는 결과 검색" value={filter} onChange={(e) => setFilter(e.target.value)} /></label>
      <select aria-label="작업 유형 필터" value={historyAction} onChange={(e) => setHistoryAction(e.target.value)}><option value="all">전체 내역</option><option value="verify">조회</option><option value="compare">내용 비교</option><option value="consume">사용 조건 확인</option></select></div>
      {visible.length ? <div className="uw-history">{visible.map((entry) => <button key={entry.id} onClick={() => jump("verify", entry.proof)}><span className="uw-history-icon"><History size={19} /></span><span><strong>{entry.proof}</strong><small>{entry.summary}</small></span><time>{time(entry.time)}</time><ArrowRight size={16} /></button>)}</div> : <div className="uw-empty"><History size={28} /><h2>{entries.length ? "검색 결과가 없습니다" : "아직 확인한 내역이 없습니다"}</h2><p>Proof를 조회하면 이 화면에 검사 기록이 남습니다.</p><button className="uw-primary" onClick={() => jump("verify")}>Proof 조회하기</button></div>}
    </section> : <>
      <section className="uw-card"><form onSubmit={lookup} className="uw-lookup"><label htmlFor="uw-proof">Proof ID / 검증 링크</label><div><input id="uw-proof" placeholder="prf_… 또는 검증 링크" maxLength={2048} value={input} onChange={(e) => { generation.current++; setBusy(false); setResult(null); setInput(e.target.value); setProof(null); setRows(null); setMessage(""); setError(""); setConfirmed(false); }} required /><button className="uw-primary" disabled={busy} type="submit"><Search size={17} />조회</button></div></form>

      <p className="uw-note">QR에서 읽은 검증 링크도 입력할 수 있습니다.</p></section>
      {error && <p role="alert" className="uw-error">{error}{/^(401|403|404)/.test(error) && <a className="uw-secondary" href={`user-login.html?next=${encodeURIComponent(`index.html?proof_id=${proof?.id??parseProof(input)}#user`)}`}>비교 계정 로그인</a>}</p>}
      {proof && <section className="uw-card uw-result"><div className="uw-result-heading"><div><span className="uw-eyebrow">{proof.type}</span><h2>{action === "compare" ? "받은 자료의 내용" : action === "consume" ? "요청 사용 조건" : "발행 기록"}</h2></div><button className="uw-icon-button" title="Proof ID 복사" aria-label="Proof ID 복사" onClick={copy}>{copied ? <Check size={18} /> : <Copy size={18} />}</button></div><Summary proof={proof} />
      {action === "verify" && <><div className="uw-status"><span>검증 판정 <b>{result?.verification_status ?? "미실행"}</b></span><span>현재 상태 <b>{result?.lifecycle_status ?? "미확인"}</b></span><span>조회 범위 <b>{result?.scope ?? "발행 기록"}</b></span></div><p className="uw-note">ID 조회로 받은 자료의 내용 일치를 확인할 수는 없습니다.</p><Checks result={result} /><div className="uw-actions"><button className="uw-primary" onClick={() => jump("compare", proof.id)}>내용 비교<ArrowRight size={16} /></button>{proof.type === "PAYMENT_REQUEST" && <button className="uw-secondary" onClick={() => jump("consume", proof.id)}>요청 사용</button>}</div></>}
      {action === "compare" && <ArtifactExtraction key={proof.id} proofType={proof.type} fields={proof.fields} onApply={values=>{generation.current++;setBusy(false);setValues(values);setRows(null);setMessage("");setError("");}} />}
      {action === "compare" && <form onSubmit={compare} className="uw-compare"><div className="uw-form-grid">{Object.keys(proof.fields).map((key) => <label key={key}>{fieldNames[key]}<input value={values[key] ?? ""} inputMode={["amount_minor", "version"].includes(key) ? "numeric" : "text"} maxLength={key === "target_ref" ? 500 : 120} onChange={(e) => { generation.current++; setBusy(false); setValues({ ...values, [key]: e.target.value }); setRows(null); setMessage(""); setError(""); }} /></label>)}</div><div className="uw-actions"><button type="button" className="uw-secondary" onClick={() => { setValues({ ...proof.fields }); setRows(null); setMessage(""); setError(""); }}>발행 값 채우기</button><button className="uw-primary" disabled={busy} type="submit">내용 비교<ArrowRight size={16} /></button></div><p className="uw-note">지정 수신자 또는 발행기관 계정으로 로그인해야 내용을 비교할 수 있습니다.</p>{rows && <div className="uw-comparison" aria-live="polite"><h3>{message}</h3>{rows.map((row) => <div key={row.key}><span>{fieldNames[row.key]}</span><b className={row.state === "불일치" ? "uw-mismatch" : ""}>{row.state}</b></div>)}<p className="uw-note">{result?.reason_codes?.join(" · ")}</p></div>}{result && <Checks result={result} />}</form>}
      {action === "consume" && <>{proof.type === "OFFICIAL_DOCUMENT" ? <p className="uw-error">공식 문서는 사용 처리 대상이 아닙니다. 조회와 내용 비교를 이용해 주세요.</p> : <><ul className="uw-conditions"><li><span>1회성 요청 유형</span><b>지급 요청</b></li><li><span>지정 수신자 인증</span><b>서버 확인 대기</b></li><li><span>기간·폐기·사용 여부</span><b>체인 확인 대기</b></li></ul><label className="uw-confirm"><input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} />조회와 별개인 1회성 사용 요청임을 확인했습니다.</label><button className="uw-primary" disabled={true} onClick={useRequest}>요청 사용 · API 제공 대기<ArrowRight size={16} /></button><p className="uw-note">실제 요청은 전송되지 않으며 사용 완료로 처리하지 않습니다.</p></>}{message && <p className="uw-notice" role="status">{message}</p>}</>}
      {action !== "compare" && message && action !== "consume" && <p className="uw-notice" role="status">{message}</p>}
      </section>}
      {!proof && !error && <div className="uw-empty"><FileText size={29} /><h2>확인할 자료를 선택하세요</h2><p>발행기관에서 받은 ID를 입력하고 조회해 주세요.</p></div>}
    </>}
    <footer className="uw-footnote"><RefreshCw size={13} />API의 검사 결과를 표시합니다. 현재 Proof 생명주기 검사는 NOT_RUN입니다.</footer>
  </div>;
}
