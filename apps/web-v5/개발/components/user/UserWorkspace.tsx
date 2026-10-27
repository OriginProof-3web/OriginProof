import { useEffect, useState, useRef, useCallback, type FormEvent } from "react";
import { Search, ArrowRight, Copy, Check, FileText, History, RefreshCw } from "lucide-react";

import ErrorNotice from "../ErrorNotice";
import ArtifactExtraction from "./ArtifactExtraction";
import { api as scopedApi, verifyRead, requestId } from "../../api-client.js";
import type { ProofView, ProofContent, OperationView } from "../api-types.generated";

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

export default function UserWorkspace({lifecycleEnabled=false,apiPrefix}: {lifecycleEnabled?:boolean;apiPrefix?:string}={}) {
  const api=useCallback((path:string,body?:object)=>lifecycleEnabled&&path.endsWith('/verify')?verifyRead(path,body,apiPrefix):apiPrefix===undefined?(body===undefined?scopedApi(path):scopedApi(path,body)):scopedApi(path,body,apiPrefix),[apiPrefix,lifecycleEnabled]);
  const consumeIds=useRef(new Map<string,string>());
  const [operation,setOperation]=useState<OperationView|null>(null);
  const [result,setResult] = useState<FinalsVerificationResult | null>(null);
  const [busy,setBusy] = useState(false);
  const generation=useRef(0);
  const pending=useRef(false);
  const [action, setAction] = useState<Action>("verify");
  const [input, setInput] = useState("");
  const [proof, setProof] = useState<Proof | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState("");
  const [values, setValues] = useState<Record<string, string>>({});
  const [rows, setRows] = useState<{ key: string; state: string }[] | null>(null);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [filter, setFilter] = useState("");
  const [historyAction, setHistoryAction] = useState("all");
  const [copied, setCopied] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const reportError=useCallback((error:unknown)=>{
    if((error as {status?:number})?.status===401){setProof(null);setResult(null);setValues({});setRows(null);setOperation(null);setEntries([]);setConfirmed(false);consumeIds.current.clear();}
    setError(error);
  },[]);
  const record = useCallback((id: string, kind: string, summary: string) => {
    const entry = { id: crypto.randomUUID(), proof: id, action: kind, summary, time: new Date().toISOString() };
    setEntries(previous=>[entry,...previous].slice(0,50));
  }, []);
  const load = useCallback(async (id: string) => {
    const token=++generation.current; setBusy(true);setError("");setResult(null);setProof(null);setMessage("");
    try {
      const view: ProofView = await api(`/v2/proofs/${encodeURIComponent(id)}`);
      const verification: FinalsVerificationResult = await api(`/v2/proofs/${encodeURIComponent(id)}/verify`,{request_id:requestId()});
      let fields=Object.fromEntries((view.proof_type==="PAYMENT_REQUEST"?["amount_minor","currency","target_ref"]:["institution_code","document_type","document_number","version"]).map(name=>[name,""]));
      // Restricted content is never inferred from a public Proof ID.
      try { const content: ProofContent=await api(`/v2/proofs/${encodeURIComponent(id)}/content`); const payload=content.envelope.payload; fields=Object.fromEntries(Object.keys(fields).map(name=>[name,String(name==="target_ref"?content.target_ref??"":(payload as any)[name]??"")])); } catch(error) {if((error as {status?:number})?.status===401)throw error;}
      if(token!==generation.current)return;
      setProof({id:view.proof_id,issuer:view.issuer_id,type:view.proof_type,issued:view.issued_at,expires:view.expires_at,fields});setResult(verification);
      record(id,"verify",`${verification.verification_status} · ${verification.scope}`);
    } catch(error) {if(token===generation.current)reportError(error);} finally{if(token===generation.current)setBusy(false);}
  }, [record,api,reportError]);
  useEffect(() => {
    const requestGeneration=generation;
    const linkedId = new URLSearchParams(location.search).get("proof_id");
    if (linkedId) {
      const id = parseProof(linkedId);
      setInput(linkedId);
      if(id) void load(id);
    }
    const change = (event: Event) => {
      const detail = (event as CustomEvent).detail;
      const next = detail?.key === "home" ? "verify" : detail?.key;
      if (Object.hasOwn(labels, next)) { generation.current++;setBusy(false);setOperation(null);setAction(next); setError(""); setMessage(""); setRows(null); setConfirmed(false); setCopied(false); if (detail.proofId) { setInput(detail.proofId); void load(detail.proofId); setValues({}); } }
    };
    window.addEventListener("originproof-action", change);
    return () => {requestGeneration.current++;window.removeEventListener("originproof-action", change);};
  }, [load]);
  function lookup(event: FormEvent) {
    event.preventDefault();setOperation(null);setMessage("");setRows(null);setConfirmed(false);setValues({});setCopied(false);
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
    }catch(error){if(token===generation.current)reportError(error);}finally{pending.current=false;if(token===generation.current)setBusy(false);}
  }
  async function submitConsume() {
    if(!lifecycleEnabled||!proof||!confirmed||pending.current)return;
    pending.current=true;setBusy(true);setError("");
    const id=proof.id;const token=++generation.current;
    if(!consumeIds.current.has(id))consumeIds.current.set(id,requestId());
    try{const op=await api(`/v2/proofs/${id}/consume`,{request_id:consumeIds.current.get(id)});if(token!==generation.current)return;setOperation(op);setMessage(`${op.operation_id} · ${op.status} · ${op.error_code??""}`);record(id,"consume",op.status);await load(id);setConfirmed(false);}
    catch(error){if(token===generation.current)reportError(error);}finally{pending.current=false;if(token===generation.current)setBusy(false);}
  }
  function jump(next: Action, id?: string) { (window as any).selectAction(next, id); }
  async function copy() {
    if (!proof) return;
    try { await navigator.clipboard.writeText(proof.id); setCopied(true); } catch { setMessage("복사를 사용할 수 없습니다. 표시된 Proof ID를 선택해 복사해 주세요."); }
  }
  const visible = entries.filter((entry) => (historyAction === "all" || entry.action === historyAction) && `${entry.proof} ${entry.summary}`.toLowerCase().includes(filter.trim().toLowerCase()));
  return <div className="uw-shell" aria-busy={busy}>
    <header className="uw-header"><span className="uw-eyebrow">PERSONAL SPACE</span><span className="uw-preview">실제 API · 로컬 테스트</span><h1>{labels[action]}</h1><p>{descriptions[action]}</p></header>
    {action === "history" ? <section className="uw-card">
      <div className="uw-history-tools"><label className="uw-search"><Search size={17} /><input aria-label="검증 내역 검색" placeholder="Proof ID 또는 결과 검색" value={filter} onChange={(e) => setFilter(e.target.value)} /></label>
      <select aria-label="작업 유형 필터" value={historyAction} onChange={(e) => setHistoryAction(e.target.value)}><option value="all">전체 내역</option><option value="verify">조회</option><option value="compare">내용 비교</option><option value="consume">사용 조건 확인</option></select></div>
      {visible.length ? <div className="uw-history">{visible.map((entry) => <button key={entry.id} onClick={() => jump("verify", entry.proof)}><span className="uw-history-icon"><History size={19} /></span><span><strong>{entry.proof}</strong><small>{entry.summary}</small></span><time>{time(entry.time)}</time><ArrowRight size={16} /></button>)}</div> : <div className="uw-empty"><History size={28} /><h2>{entries.length ? "검색 결과가 없습니다" : "아직 확인한 내역이 없습니다"}</h2><p>Proof를 조회하면 이 화면에 검사 기록이 남습니다.</p><button className="uw-primary" onClick={() => jump("verify")}>Proof 조회하기</button></div>}
    </section> : <>
      <section className="uw-card"><form onSubmit={lookup} className="uw-lookup"><label htmlFor="uw-proof">Proof ID / 검증 링크</label><div><input id="uw-proof" placeholder="prf_… 또는 검증 링크" maxLength={2048} value={input} onChange={(e) => { generation.current++; setBusy(false); setResult(null); setInput(e.target.value); setProof(null); setRows(null); setMessage(""); setError(""); setConfirmed(false); }} required /><button className="uw-primary" disabled={busy} type="submit"><Search size={17} />조회</button></div></form>

      <p className="uw-note">QR에서 읽은 검증 링크도 입력할 수 있습니다.</p></section>
      <ErrorNotice error={error} loginHref={`user-login.html?next=${encodeURIComponent(`index.html?proof_id=${proof?.id??parseProof(input)}#user`)}`} retry={()=>{const id=parseProof(input);if(id)void load(id);}}/>
      {busy&&<p role="status">요청을 확인하고 있습니다. 변경 결과를 확인하기 전에 다시 전송하지 마세요.</p>}
      {proof && <section className="uw-card uw-result"><div className="uw-result-heading"><div><span className="uw-eyebrow">{proof.type}</span><h2>{action === "compare" ? "받은 자료의 내용" : action === "consume" ? "요청 사용 조건" : "발행 기록"}</h2></div><button className="uw-icon-button" title="Proof ID 복사" aria-label="Proof ID 복사" onClick={copy}>{copied ? <Check size={18} /> : <Copy size={18} />}</button></div><Summary proof={proof} />
      {action === "verify" && <><div className="uw-status"><span>검증 판정 <b>{result?.verification_status ?? "미실행"}</b></span><span>현재 상태 <b>{result?.lifecycle_status ?? "미확인"}</b></span><span>조회 범위 <b>{result?.scope ?? "발행 기록"}</b></span></div><p className="uw-note">확인 시각: {result?.verified_at?time(result.verified_at):"미확인"}</p><p className="uw-note">미등록은 위조 판정이 아닙니다. VERIFIED도 기간·폐기·사용 여부에 따라 현재 사용이 제한될 수 있습니다.</p><p className="uw-note">ID 조회로 받은 자료의 내용 일치를 확인할 수는 없습니다.</p><Checks result={result} /><div className="uw-actions"><button className="uw-primary" onClick={() => jump("compare", proof.id)}>내용 비교<ArrowRight size={16} /></button>{proof.type === "PAYMENT_REQUEST" && <button className="uw-secondary" onClick={() => jump("consume", proof.id)}>요청 사용</button>}</div></>}
      {action === "compare" && <ArtifactExtraction key={proof.id} proofType={proof.type} fields={proof.fields} onApply={values=>{generation.current++;setBusy(false);setValues(values);setResult(null);setRows(null);setMessage("");setError("");}} />}
      {action === "compare" && <form onSubmit={compare} className="uw-compare"><div className="uw-form-grid">{Object.keys(proof.fields).map((key) => <label key={key}>{fieldNames[key]}<input value={values[key] ?? ""} inputMode={["amount_minor", "version"].includes(key) ? "numeric" : "text"} maxLength={key === "target_ref" ? 500 : 120} onChange={(e) => { generation.current++; setBusy(false); setValues({ ...values, [key]: e.target.value }); setResult(null); setRows(null); setMessage(""); setError(""); }} /></label>)}</div><div className="uw-actions"><button type="button" className="uw-secondary" onClick={() => { generation.current++;setBusy(false);setValues({ ...proof.fields }); setResult(null);setRows(null); setMessage(""); setError(""); }}>발행 값 채우기</button><button className="uw-primary" disabled={busy} type="submit">내용 비교<ArrowRight size={16} /></button></div><p className="uw-note">지정 수신자 또는 발행기관 계정으로 로그인해야 내용을 비교할 수 있습니다.</p>{rows && <div className="uw-comparison" aria-live="polite"><h3>{message}</h3>{rows.map((row) => <div key={row.key}><span>{fieldNames[row.key]}</span><b className={row.state === "불일치" ? "uw-mismatch" : ""}>{row.state}</b></div>)}<p className="uw-note">{result?.reason_codes?.join(" · ")}</p></div>}{result && <Checks result={result} />}</form>}
      {action === "consume" && <>{proof.type === "OFFICIAL_DOCUMENT" ? <p className="uw-error">공식 문서는 사용 처리 대상이 아닙니다. 조회와 내용 비교를 이용해 주세요.</p> : <><ul className="uw-conditions"><li><span>1회성 요청 유형</span><b>지급 요청</b></li><li><span>지정 수신자 인증</span><b>서버에서 권한 확인</b></li><li><span>기간·폐기·사용 여부</span><b>{result?.lifecycle_status??"미확인"}</b></li></ul><label className="uw-confirm"><input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} />조회와 별개인 1회성 사용 요청임을 확인했습니다.</label><button className="uw-primary" disabled={!lifecycleEnabled||!confirmed||busy||result?.lifecycle_status!=="ACTIVE"} onClick={()=>void submitConsume()}>{lifecycleEnabled?"1회 사용 요청 실행":"요청 사용 · API 제공 대기"}<ArrowRight size={16} /></button><p className="uw-note">{lifecycleEnabled?"CONFIRMED와 현재 체인 상태를 확인해야 사용 완료입니다.":"실제 요청은 전송되지 않으며 사용 완료로 처리하지 않습니다."}</p></>}{operation&&<div className="uw-status"><span>{operation.operation_id} · {operation.status}</span>{["UNKNOWN","SUBMITTED","PENDING_SUBMISSION"].includes(operation.status)&&<button className="uw-secondary" disabled={busy} onClick={async()=>{setBusy(true);try{setOperation(await api(`/v1/operations/${operation.operation_id}/recover`,{}));if(proof)await load(proof.id);}catch(e){reportError(e);}finally{setBusy(false);}}}>기존 사용 거래 복구</button>}</div>}{message && <p className="uw-notice" role="status">{message}</p>}</>}
      {action !== "compare" && message && action !== "consume" && <p className="uw-notice" role="status">{message}</p>}
      </section>}
      {!proof && !error && <div className="uw-empty"><FileText size={29} /><h2>확인할 자료를 선택하세요</h2><p>발행기관에서 받은 ID를 입력하고 조회해 주세요.</p></div>}
    </>}
    <footer className="uw-footnote"><RefreshCw size={13} />{lifecycleEnabled?"현재 체인 상태와 API의 검사 결과를 표시합니다. ID 조회와 내용 비교는 별도입니다.":"API의 검사 결과를 표시합니다. 현재 Proof 생명주기 검사는 NOT_RUN입니다."}</footer>
  </div>;
}
