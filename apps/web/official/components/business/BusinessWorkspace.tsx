import { useEffect, useState, useRef, useCallback, type FormEvent } from "react";
import { ArrowRight, Copy, Building2, KeyRound, FilePlus2, FileText, History } from "lucide-react";

import ProofQr from "./ProofQr";
import { issueErrors, proofLink } from "../../w3-input.js";
import { api as scopedApi, verifyRead, requestId, seconds } from "../../api-client.js";
import type { AccountView, IssuerView, KeyView, ProofView, RecipientView, AuditView, OperationView, ApplicationView, PaymentIssue, DocumentIssue, ProofReconciliation } from "../api-types.generated";
type Action = "status" | "keys" | "issue" | "proofs" | "operations";
type Org = "bank" | "office";
type Key = { id: string; org: Org; signer: string; from: string; until: string; status: string; selected: boolean };
type RecordRow = { id: string; org: Org; type: string; recipient: string; expiry: string; fields: Record<string, string>; draft: boolean };
type Operation = { id: string; target: string; name: string; reason: string; time: string };
const orgs = { bank: { name: "Origin Mock Bank", id: "iss_origin_mock_bank", type: "PAYMENT_REQUEST", recipient: "recipient_bank_demo", key: "key_mock_bank_001" }, office: { name: "Origin Mock Office", id: "iss_origin_mock_office", type: "OFFICIAL_DOCUMENT", recipient: "recipient_office_demo", key: "key_mock_office_001" } };
const labels: Record<Action, string> = { status: "기관 상태", keys: "공개키 관리", issue: "Proof 발행", proofs: "발행 목록", operations: "작업 이력" };
const descriptions: Record<Action, string> = { status: "신청 검토 결정과 Registry 활성화 상태를 따로 확인합니다.", keys: "자기 기관의 공개 signer, 키 기간과 발행 키 선택을 관리합니다.", issue: "지급 요청 또는 공식 문서를 발행해 서버에 서명·저장합니다.", proofs: "자기 기관의 실제 발행 기록을 확인합니다.", operations: "서버에 저장된 감사 기록과 작업 결과를 확인합니다." };
const fieldNames: Record<string, string> = { amount_minor: "금액 (최소 화폐 단위)", currency: "통화", target_ref: "합성 요청 대상 참조", institution_code: "기관 코드", document_type: "문서 유형", document_number: "문서번호", version: "문서 개정 번호" };
const defaults = { payment: { amount_minor: "", currency: "KRW", target_ref: "" }, document: { institution_code: "ORIGIN_MOCK_OFFICE", document_type: "", document_number: "", version: "1" } };
const samples = { payment: { amount_minor: "85000", currency: "KRW", target_ref: "SYNTHETIC-PAYMENT-001" }, document: { institution_code: "ORIGIN_MOCK_OFFICE", document_type: "SYNTHETIC_CERTIFICATE", document_number: "MOCK-2026-001", version: "1" } };
const date = (value: string) => value ? new Date(value).toLocaleString("ko-KR") : "—";
const localTime=(offset:number)=>{const d=new Date(Date.now()+offset);return new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,16);};

export default function BusinessWorkspace({lifecycleEnabled=false,apiPrefix}: {lifecycleEnabled?:boolean;apiPrefix?:string}={}) {
  const api=useCallback((path:string,body?:object)=>lifecycleEnabled&&path.endsWith('/verify')?verifyRead(path,body,apiPrefix):apiPrefix===undefined?(body===undefined?scopedApi(path):scopedApi(path,body)):scopedApi(path,body,apiPrefix),[apiPrefix,lifecycleEnabled]);
  const [lifecycle,setLifecycle]=useState<ProofReconciliation["current_verification"]|null>(null);
  const [reconciliation,setReconciliation]=useState<ProofReconciliation|null>(null);
  const [loading,setLoading]=useState(true);
  const [action, setAction] = useState<Action>("status");
  const [org, setOrg] = useState<Org>("bank");
  const [scenario, setScenario] = useState("ACTIVE");
  const [keys,setKeys] = useState<Key[]>([]);
  const [records,setRecords] = useState<RecordRow[]>([]);
  const [recipients,setRecipients]=useState<RecipientView[]>([]);
  const [network,setNetwork]=useState<IssuerView | null>(null);
  const [application,setApplication]=useState<ApplicationView|null>(null);
  const [busy,setBusy]=useState(false);
  const submitting=useRef(false);
  const ids=useRef(new Map<string,string>());
  function stableId(body: object) {const fingerprint=JSON.stringify(body); if(!ids.current.has(fingerprint))ids.current.set(fingerprint,requestId());return ids.current.get(fingerprint)!;}
  const [qrVisible,setQrVisible]=useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [operations, setOperations] = useState<(Operation & { org: Org })[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [fieldErrors,setFieldErrors] = useState<Record<string,string>>({});
  const [reason, setReason] = useState("");
  const [keyFrom, setKeyFrom] = useState(()=>localTime(-60000));
  const [keyUntil, setKeyUntil] = useState(()=>localTime(30*86400000));
  const [keyAction, setKeyAction] = useState("register");
  const [keyTarget, setKeyTarget] = useState("");
  const [fields, setFields] = useState<Record<string, string>>(defaults.payment);
  const [recipient, setRecipient] = useState("");
  const [expiry, setExpiry] = useState("");
  const [chainOperations,setChainOperations]=useState<OperationView[]>([]);
  const [operationId,setOperationId]=useState("");
  const [operation,setOperation]=useState<OperationView | null>(null);
  const [query, setQuery] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const current = orgs[org];
  const active = network?.status === "ACTIVE";
  const key = keys.find((k) => k.org === org && k.selected) ?? {id:"선택된 발행 키 없음",signer:"—",from:"",until:"",status:"NOT_REGISTERED",selected:false};
  const own = records.filter((r) => r.org === org);
  const detail = own.find((r) => r.id === selected);
  const ownOperations = operations.filter((r) => r.org === org);
  const payment = org === "bank";
  const refresh=useCallback(async()=> {
    const me: AccountView=await api('/v1/auth/me');
    if(me.role!=="issuer")throw new Error("기관 계정으로 로그인해 주세요.");
    const next: Org=me.issuer_id===orgs.office.id?"office":"bank";
    if(![orgs.bank.id,orgs.office.id].includes(me.issuer_id??""))throw new Error("두 합성 기관 전용 테스트 환경입니다.");
    setOrg(next);setFields(next==="bank"?defaults.payment:defaults.document);
    const [state,keyRows,proofRows,recipientRows,audit,app] = await Promise.all([api('/v1/issuer/status').catch(()=>null),api('/v1/issuer/keys'),api('/v2/issuer/proofs'),api('/v2/issuer/recipients'),api('/v1/audit-events'),api('/v1/issuer-applications/mine')]);
    if(lifecycleEnabled)setChainOperations(await api("/v1/operations"));
    setNetwork(state);setScenario(state?.status??app?.status??"PENDING_REVIEW");setApplication(app);
    setKeys(keyRows.map((k:KeyView)=>({id:k.key_id,org:next,signer:k.signer,from:new Date(k.valid_from*1000).toISOString(),until:new Date(k.valid_until*1000).toISOString(),status:k.status,selected:k.selected})));
    setRecipients(recipientRows);
    setRecords(proofRows.map((p:ProofView)=>({id:p.proof_id,org:next,type:p.proof_type,recipient:"서버 binding",expiry:p.expires_at,fields:{},draft:false})));
    setOperations(audit.map((a:AuditView)=>({id:a.event_id,org:next,target:a.target_id,name:a.action,reason:a.reason??"",time:a.created_at,status:a.after_status})));
  },[api,lifecycleEnabled]);
  useEffect(()=>{refresh().catch(error=>setError(error.message)).finally(()=>setLoading(false));},[refresh]);
  async function run(body:object,path:string) {
    if(submitting.current)return;submitting.current=true;setBusy(true);setError("");setMessage("");
    try {const result=await api(path,path==="/v1/issuer-applications"?body:{...body,request_id:stableId({path,...body})});
      setMessage(`${result.operation_id??result.proof_id} · ${result.status??(lifecycleEnabled?`등록 ${result.registration_status??"미확인"}`:"발행 저장 완료")}${result.error_code?" · "+result.error_code:""}`);
      if(result.operation_id){setOperationId(result.operation_id);setOperation(result);}
      if(result.operation_id)setMessage(`${result.operation_id} · ${result.status} · ${result.tx_hash??"tx 미확인"}`);
      try {await refresh();} catch {setError("요청 결과는 수신했습니다. 목록을 다시 조회해 주세요.");}return result;
    }catch(error){setError((error as Error).message);setFieldErrors((error as Error & {fieldErrors?:Record<string,string>}).fieldErrors??{});}finally{submitting.current=false;setBusy(false);}
  }
  async function showProof(id:string) {setSelected(id);setLifecycle(null);setReconciliation(null);setError("");try {const content=await api(`/v2/proofs/${encodeURIComponent(id)}/content`);if(lifecycleEnabled){setLifecycle(await api(`/v2/proofs/${encodeURIComponent(id)}/verify`,{request_id:requestId()}));setReconciliation(await api(`/v2/issuer/proofs/${encodeURIComponent(id)}/reconciliation`));}const payload=content.envelope.payload;const fields=Object.fromEntries(Object.keys(content.envelope.proof_type==="PAYMENT_REQUEST"?defaults.payment:defaults.document).map(name=>[name,String(name==="target_ref"?content.target_ref??"":payload[name]??"")]));setRecords(rows=>rows.map(r=>r.id===id?{...r,fields}:r));}catch(error){setError((error as Error).message);}}
  useEffect(() => {
    const change = (event: Event) => {
      const next = (event as CustomEvent).detail?.key;
      if (Object.hasOwn(labels, next)) { setAction(next); setFieldErrors({}); setMessage(""); setError(""); setConfirmation(""); if ((event as CustomEvent).detail?.proofId) setSelected((event as CustomEvent).detail.proofId); }
    };
    window.addEventListener("originproof-action", change);
    return () => window.removeEventListener("originproof-action", change);
  }, []);
  const jump = (key: Action, proofId?: string) => (window as any).selectAction(key, proofId);
  function changeOrg(next: Org) {
    setOrg(next); setFields(next === "bank" ? defaults.payment : defaults.document); setRecipient(""); setExpiry(""); setSelected(null); setMessage(""); setError(""); setConfirmation(""); setKeyTarget(""); setReason("");
    window.dispatchEvent(new CustomEvent("originproof-business-org", { detail: next }));
  }
  async function prepareKey(event:FormEvent) {
    event.preventDefault();if(!active)return;
    if(!reason.trim()){setError("작업 사유를 입력해 주세요.");return;}
    if(keyAction==="revoke") {if(!keyTarget||confirmation!=="revoke"){setError("대상 키와 폐기 확인을 선택해 주세요.");return;}await run({reason},`/v1/issuer/keys/${encodeURIComponent(keyTarget)}/revoke`);}
    else {if(keyAction==="rotate"&&confirmation!=="rotate"){setError("키 교체 확인을 선택해 주세요.");return;}if(!keyFrom||!keyUntil||Date.parse(keyFrom)>=Date.parse(keyUntil)){setError("키 시작·종료 시각을 확인해 주세요.");return;}await run({reason,valid_from:seconds(keyFrom),valid_until:seconds(keyUntil)},keyAction==="rotate"?'/v1/issuer/keys/rotate':'/v1/issuer/keys');}
  }
  async function issue(event:FormEvent) {
    event.preventDefault();if(!active||submitting.current)return;
    const errors=issueErrors(fields,recipient,expiry);setFieldErrors(errors);
    if(Object.keys(errors).length){setError("표시된 입력 항목을 확인해 주세요.");return;}
    const content: PaymentIssue | DocumentIssue = payment
      ? {proof_type:"PAYMENT_REQUEST",amount_minor:Number(fields.amount_minor),currency:fields.currency.trim(),target_ref:fields.target_ref.trim()}
      : {proof_type:"OFFICIAL_DOCUMENT",institution_code:fields.institution_code.trim(),document_type:fields.document_type.trim(),document_number:fields.document_number.trim(),version:Number(fields.version)};
    const result=await run({recipient_id:recipient,expires_at:seconds(expiry),content},'/v2/issuer/proofs');
    if(result?.proof_id){setSelected(result.proof_id);await showProof(result.proof_id);}
  }
  async function prepareProof(kind=confirmation.startsWith("consume")?"consume":"revoke") {
    if(!lifecycleEnabled||!detail)return;
    if(kind!=="register"&&confirmation!==kind){setError("작업 확인을 선택해 주세요.");return;}
    if(kind==="revoke"&&!reason.trim()){setError("폐기 사유를 입력해 주세요.");return;}
    const path=kind==="consume"?`/v2/proofs/${detail.id}/consume`:`/v2/issuer/proofs/${detail.id}/${kind}`;
    const result=await run(kind==="revoke"?{reason:reason.trim()}:{},path);if(result){await showProof(detail.id);setConfirmation("");}
  }
  async function copy(text: string) {
    try { await navigator.clipboard.writeText(text); setMessage("복사했습니다."); } catch { setMessage("복사 기능을 사용할 수 없습니다. 표시된 ID나 링크를 선택해 복사해 주세요."); }
  }
  if(loading)return <div className="uw-shell"><p role="status">기관 정보 확인 중…</p></div>;
  return <div className="uw-shell">
    <header className="uw-header"><span className="uw-eyebrow">BUSINESS SPACE</span><span className="uw-preview">실제 API · 로컬 테스트</span><h1>{labels[action]}</h1><p>{descriptions[action]}</p></header>
    <div className="bw-context"><Building2 size={18} /><label>로그인 기관<select disabled value={org} onChange={(e) => changeOrg(e.target.value as Org)}><option value="bank">Origin Mock Bank</option><option value="office">Origin Mock Office</option></select></label><span>실제 기관 권한은 서버에서 확인합니다.</span></div>
    {action === "status" && <>
      <section className="uw-card"><div className="uw-result-heading"><h2>{current.name}</h2><span className="bw-badge">합성 기관</span></div><dl className="uw-summary"><div><dt>기관 ID</dt><dd>{current.id}</dd></div><div><dt>담당 범위</dt><dd>{payment ? "지급 요청" : "공식 문서"}</dd></div><div><dt>환경</dt><dd>{network ? `로컬 EVM · ${network.chain_id} · ${network.deployment_id}` : "체인 상태 미확인"}</dd></div><div><dt>검토 사유</dt><dd>{application?.decision_reason ?? "검토 사유 없음"}</dd></div></dl>
      <label className="bw-scenario">기관 상태<select disabled value={scenario} onChange={(e) => setScenario(e.target.value)}><option value="ACTIVE">체인 활성화</option><option value="PENDING_REVIEW">운영자 검토 대기 예시</option><option value="APPROVED_PENDING_CHAIN">승인·체인 활성화 대기 예시</option><option value="REJECTED">반려 예시</option><option value="SUSPENDED">기관 중지 예시</option></select></label>
      <ol className="bw-steps"><li><span>01</span><div><strong>기관 신청</strong><small>합성 신청 정보</small></div><b>{application ? "접수" : "미신청"}</b></li><li><span>02</span><div><strong>운영자 검토 결정</strong><small>기관이 자기 신청을 승인할 수 없습니다</small></div><b>{scenario === "PENDING_REVIEW" ? "검토 대기" : scenario === "REJECTED" ? "반려 예시" : application ? "승인" : "검토 기록 없음"}</b></li><li><span>03</span><div><strong>Registry 활성화</strong><small>DB 승인과 별도로 receipt·현재 상태를 확인합니다</small></div><b>{active ? "ACTIVE" : scenario === "SUSPENDED" ? "중지 예시" : "확인 대기"}</b></li></ol>
      <div className="uw-actions">{lifecycleEnabled&&!application&&<button className="uw-secondary" disabled={busy} onClick={()=>void run({issuer_name:current.name},"/v1/issuer-applications")}>기관 신청 접수</button>}<a className="uw-secondary" href="application-status.html">신청현황 페이지</a><button className="uw-primary" onClick={() => jump("keys")}>공개키 관리<ArrowRight size={16} /></button></div></section>
      <section className="bw-tiles">{([["keys", "공개키 관리", KeyRound], ["issue", "Proof 발행", FilePlus2], ["proofs", "발행 목록", FileText], ["operations", "작업 이력", History]] as const).map(([id, label, Icon]) => <button key={id} onClick={() => jump(id)}><Icon size={22} /><strong>{label}</strong><ArrowRight size={16} /></button>)}</section>
    </>}
    {action === "keys" && <>
      <section className="uw-card"><div className="uw-result-heading"><h2>발행 키</h2><span className="bw-badge">{key.status}</span></div><dl className="uw-summary"><div><dt>Key ID</dt><dd>{key.id}</dd></div><div><dt>공개 signer</dt><dd>{key.signer}</dd></div><div><dt>유효 기간</dt><dd>{date(key.from)} ~ {date(key.until)}</dd></div><div><dt>발행 키 선택</dt><dd>{key.selected ? "서버 선택 키" : "선택 안됨"}</dd></div></dl><p className="uw-note">개인키는 입력하거나 표시하지 않습니다. 서버에서 생성·보관합니다.</p></section>
      <section className="uw-card"><h2>키 작업 실행</h2><ul>{keys.map(k=><li key={k.id}>{k.id} · {k.status} · {k.selected?"선택됨":"이전 키"}</li>)}</ul><form onSubmit={prepareKey}><div className="uw-form-grid"><label>작업<select value={keyAction} onChange={(e) => { setKeyAction(e.target.value); setConfirmation(""); setMessage(""); }}><option value="register">신규 키 생성·등록</option><option value="rotate">정상 키 교체</option><option value="revoke">유출·폐기</option></select></label>{keyAction === "revoke" && <label>대상 키<select required value={keyTarget} onChange={(e) => setKeyTarget(e.target.value)}><option value="">키 선택</option>{keys.map(k=><option key={k.id} value={k.id}>{k.id} · {k.status}</option>)}</select></label>}{keyAction !== "revoke" && <><label>유효 시작 시각<input type="datetime-local" required value={keyFrom} onChange={(e) => setKeyFrom(e.target.value)} /></label><label>유효 종료 시각<input type="datetime-local" required value={keyUntil} onChange={(e) => setKeyUntil(e.target.value)} /></label></>}<label className="bw-wide">작업 사유<input required maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} /></label></div>
      {keyAction !== "register" && <label className="uw-confirm"><input type="checkbox" checked={confirmation === keyAction} onChange={(e) => setConfirmation(e.target.checked ? keyAction : "")} />{keyAction === "rotate" ? "새 키 등록 확정 후 전환하며 이전 키를 자동 폐기하지 않습니다." : "선택한 등록 키를 폐기합니다. 이 작업은 되돌릴 수 없습니다."}</label>}<div className="uw-actions"><button className="uw-primary" disabled={!active || busy} type="submit">키 작업 실행<ArrowRight size={16} /></button></div></form></section>
    </>}
    {action === "issue" && <section className="uw-card"><div className="uw-result-heading"><h2>{payment ? "지급 요청" : "공식 문서"}</h2><span className="bw-badge">schema 2.0.0</span></div><form onSubmit={issue} noValidate><div className="uw-form-grid"><label>발행 키<select disabled><option>{key.id}</option></select></label><label>지정 수신자<select aria-label="지정 수신자" aria-invalid={!!fieldErrors.recipient_id} aria-describedby="error-recipient" required value={recipient} onChange={(e) => setRecipient(e.target.value)}><option value="">합성 수신자 선택</option>{recipients.map(r=><option key={r.recipient_id} value={r.recipient_id}>{r.label}</option>)}</select>{fieldErrors.recipient_id && <small id="error-recipient" role="alert">{fieldErrors.recipient_id}</small>}</label>{Object.keys(payment ? defaults.payment : defaults.document).map((name) => <label key={name}>{fieldNames[name]}<input aria-label={fieldNames[name]} aria-invalid={!!fieldErrors[name]} aria-describedby={`error-${name}`} required maxLength={name==="target_ref"?500:120} readOnly={name === "institution_code"} inputMode={["amount_minor", "version"].includes(name) ? "numeric" : "text"} value={fields[name] ?? ""} onChange={(e) => setFields({ ...fields, [name]: e.target.value })} />{fieldErrors[name] && <small id={`error-${name}`} role="alert">{fieldErrors[name]}</small>}</label>)}<label>만료 시각<input aria-invalid={!!fieldErrors.expires_at} aria-describedby="error-expiry" type="datetime-local" required value={expiry} onChange={(e) => setExpiry(e.target.value)} />{fieldErrors.expires_at && <small id="error-expiry" role="alert">{fieldErrors.expires_at}</small>}</label></div><p className="uw-note">{payment ? "지급 요청은 1회 사용입니다." : "공식 문서는 반복 조회하며 consume 대상이 아닙니다."} ID·서명·수신자 binding·대상 hash·발행 시각은 서버가 생성합니다.</p><div className="uw-actions"><button type="submit" className="uw-primary" disabled={!active || busy || (key.status!=="ACTIVE" || !key.selected)}>Proof 발행<ArrowRight size={16} /></button><button className="uw-secondary" type="button" onClick={() => { setFields({ ...samples[payment ? "payment" : "document"] }); setRecipient(recipients[0]?.recipient_id ?? ""); const future = new Date(Date.now() + 86400000); const local = new Date(future.getTime() - future.getTimezoneOffset() * 60000); setExpiry(local.toISOString().slice(0, 16)); }}>합성 예시 채우기</button><button className="uw-secondary" type="button" onClick={() => jump("proofs")}>발행 목록</button></div></form></section>}
    {action === "proofs" && <>
      <section className="uw-card"><div className="uw-history-tools"><input aria-label="발행 목록 검색" placeholder="ID 또는 문서번호 검색" value={query} onChange={(e) => setQuery(e.target.value)} /><button className="uw-primary" onClick={() => jump("issue")}>새 발행</button></div><div className="uw-history">{own.filter((r) => `${r.id} ${r.fields.document_number ?? ""}`.toLowerCase().includes(query.trim().toLowerCase())).map((r) => <button key={r.id} onClick={() => { void showProof(r.id); setQrVisible(false); setConfirmation(""); setReason(""); setMessage(""); }}><span className="uw-history-icon"><FileText size={19} /></span><span><strong>{r.id}</strong><small>{r.type} · {r.draft ? "미발행 초안" : "발행 기록"}</small></span><ArrowRight size={16} /></button>)}</div>{!own.some((r) => `${r.id} ${r.fields.document_number ?? ""}`.toLowerCase().includes(query.trim().toLowerCase())) && <p className="uw-note">검색 결과가 없습니다.</p>}</section>
      {detail && <section className="uw-card"><div className="uw-result-heading"><h2>{detail.draft ? "발행 요청 초안" : "Proof 상세"}</h2><button className="uw-icon-button" aria-label="ID 복사" onClick={() => copy(detail.id)}><Copy size={18} /></button></div><dl className="uw-summary"><div><dt>{detail.draft ? "초안 ID" : "Proof ID"}</dt><dd>{detail.id}</dd></div><div><dt>현재 상태</dt><dd>{detail.draft ? "미발행 · 서버 서명/저장 대기" : lifecycleEnabled ? (lifecycle?.lifecycle_status??"미확인") : "실제 서명·DB 저장 · 현재 생명주기 미확인"}</dd></div><div><dt>수신자</dt><dd>{detail.recipient}</dd></div><div><dt>만료 시각</dt><dd>{date(detail.expiry)}</dd></div>{Object.entries(detail.fields).map(([name, value]) => <div key={name}><dt>{fieldNames[name]}</dt><dd>{value}</dd></div>)}</dl>
      {!detail.draft && <><div className="uw-actions"><button className="uw-secondary" onClick={() => copy((lifecycleEnabled?new URL(`admin.html?proof_id=${encodeURIComponent(detail.id)}`,location.href).href:proofLink(detail.id,location.href)))}>검증 링크 복사</button><a className="uw-secondary" href={(lifecycleEnabled?new URL(`admin.html?proof_id=${encodeURIComponent(detail.id)}`,location.href).href:proofLink(detail.id,location.href))} target="_blank" rel="noopener">{lifecycleEnabled?"관리자 조회 화면":"사용자 조회 화면"}</a></div><button className="uw-secondary" type="button" aria-expanded={qrVisible} onClick={()=>setQrVisible(!qrVisible)}>{qrVisible ? "QR 닫기" : "검증 QR 보기"}</button>{qrVisible && <ProofQr key={detail.id} proofId={detail.id} href={lifecycleEnabled?new URL(`admin.html?proof_id=${encodeURIComponent(detail.id)}`,location.href).href:undefined}/> }<div className="uw-form-grid"><label>관리 작업<select value={confirmation.startsWith("consume") ? "consume" : "revoke"} onChange={(e) => setConfirmation(e.target.value + "_selected")}><option value="revoke">Proof 폐기</option>{detail.type === "PAYMENT_REQUEST" && <option value="consume">허가된 요청 사용</option>}</select></label><label>작업 사유<input required maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} /></label></div><label className="uw-confirm"><input type="checkbox" checked={["revoke", "consume"].includes(confirmation)} onChange={(e) => { const kind = confirmation.startsWith("consume") ? "consume" : "revoke"; setConfirmation(e.target.checked ? kind : kind + "_selected"); }} />기관 권한·기간·현재 체인 상태 확인 후 실행하는 작업입니다.</label><button className="uw-primary" disabled={!lifecycleEnabled||busy||!active||!["revoke","consume"].includes(confirmation)} onClick={()=>void prepareProof()}>{lifecycleEnabled?"확인한 관리 작업 실행":"폐기·사용 API 제공 대기"}</button>{lifecycleEnabled&&<><div className="uw-status"><span>검증 <b>{lifecycle?.verification_status??"미확인"}</b></span><span>현재 체인 <b>{lifecycle?.lifecycle_status??"미확인"}</b></span><span>등록 일치 <b>{reconciliation?.registration_consistent===true?"일치":reconciliation?.registration_consistent===false?"불일치":"미확인"}</b></span></div><button className="uw-secondary" disabled={busy} onClick={()=>void showProof(detail.id)}>체인·DB 다시 조회</button><button className="uw-secondary" disabled={busy||!active} onClick={()=>void prepareProof("register")}>같은 Proof 등록 복구</button></>}</>}
      </section>}
    </>}
    {action === "operations" && <section className="uw-card"><form onSubmit={async e=>{e.preventDefault();setError("");try{setOperation(await api(`/v1/operations/${encodeURIComponent(operationId)}`));}catch(error){setError((error as Error).message);}}}><label>Operation ID<input required value={operationId} onChange={e=>setOperationId(e.target.value)} /></label><button className="uw-primary">작업 상태 조회</button></form>{lifecycleEnabled&&<div className="uw-history">{chainOperations.map(op=><button key={op.operation_id} onClick={()=>{setOperationId(op.operation_id);setOperation(op);}}><strong>{op.action}</strong><span>{op.operation_id} · {op.status} · {op.next_action}</span></button>)}</div>}{operation && <div className="uw-status"><span>{operation.operation_id} · <b>{operation.status}</b></span><span>{operation.tx_hash??"tx 미확인"}</span><span>{operation.error_code}</span>{["UNKNOWN","SUBMITTED","PENDING_SUBMISSION"].includes(operation.status)&&<button className="uw-secondary" disabled={busy} onClick={async()=>{setBusy(true);try{setOperation(await api(`/v1/operations/${operation.operation_id}/recover`,{}));await refresh();}catch(error){setError((error as Error).message);}finally{setBusy(false);}}}>기존 거래 상태 복구</button>}</div>}{ownOperations.length ? <div className="uw-history">{ownOperations.map((op) => <button key={op.id} onClick={() => setMessage(`${op.name}: ${op.reason} / ${op.target} · ${(op as any).status}`)}><span className="uw-history-icon"><History size={19} /></span><span><strong>{op.name}</strong><small>{op.target} · {(op as any).status}</small></span><time>{date(op.time)}</time></button>)}</div> : <div className="uw-empty"><History size={28} /><h2>아직 작업 이력이 없습니다</h2><p>기관·키·발행 작업의 서버 감사 기록이 표시됩니다.</p></div>}<p className="uw-note">실제 Operation의 제출·확정·실패·UNKNOWN은 서버 응답으로 표시합니다. 확인되지 않은 작업을 자동 재전송하지 않습니다.</p></section>}
    {!active && action !== "status" && <p className="uw-notice">현재 기관 상태에서는 변경 요청이 제한됩니다. 기관 상태 화면에서 이유를 확인해 주세요.</p>}
    {error && <p className="uw-error" role="alert">{error}{error.startsWith("401") && <a className="uw-secondary" href="business-login.html">기관 로그인</a>}</p>}{message && <p className="uw-notice" role="status">{message}</p>}
    <footer className="uw-footnote">서버 세션의 기관 권한으로 실행합니다. 체인 작업은 CONFIRMED 응답에서만 완료입니다.</footer>
  </div>;
}
