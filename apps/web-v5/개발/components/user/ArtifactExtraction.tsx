import {useRef, useState} from 'react';
import type {ComparisonInput} from '../api-types.generated';

type Props = {
  proofType: string;
  fields: Record<string,string>;
  extract?: (text:string)=>Promise<ComparisonInput>;
  onApply: (values:Record<string,string>)=>void;
};
export default function ArtifactExtraction({proofType,fields,extract,onApply}:Props){
  const [text,setText]=useState('');
  const [candidate,setCandidate]=useState<ComparisonInput|null>(null);
  const [error,setError]=useState('');
  const [busy,setBusy]=useState(false);
  const version=useRef(0);
  async function run(){
    if(!extract||busy||!text.trim())return;
    const token=++version.current;setBusy(true);setCandidate(null);setError('');
    try{const result=await extract(text);if(token===version.current)setCandidate(result);}
    catch(error){if(token===version.current)setError((error as Error).message);}
    finally{if(token===version.current)setBusy(false);}
  }
  const values=Object.fromEntries(Object.keys(fields).map(key=>[key,String(candidate?.[key as keyof ComparisonInput]??'')]));
  return <section className="uw-card" aria-label="AI 비교 항목 추출">
    <h2>자료에서 비교 항목 추출</h2>
    <p className="uw-note">{proofType==='PAYMENT_REQUEST'?'지급 요청':'공식 문서'}의 텍스트를 붙여 넣으세요. 추출값을 확인한 뒤 내용 비교에 적용합니다.</p>
    <label>자료 텍스트<textarea className="uw-artifact-text" maxLength={10000} rows={6} value={text} onChange={event=>{version.current++;setText(event.target.value);setCandidate(null);setError('');setBusy(false);}} /></label>
    <div className="uw-actions"><button type="button" className="uw-secondary" disabled={!extract||busy||!text.trim()} onClick={()=>void run()}>{busy?'추출 중…':'비교 항목 추출'}</button></div>
    {!extract&&<p className="uw-note">이 유형의 추출 API는 연결 준비 중입니다. 아래 항목은 직접 입력할 수 있습니다.</p>}
    {error&&<p role="alert" className="uw-error">{error}</p>}
    {candidate&&<><dl className="uw-summary">{Object.entries(values).map(([key,value])=><div key={key}><dt>{key}</dt><dd>{value||'추출하지 못함 · 직접 입력 필요'}</dd></div>)}</dl><button type="button" className="uw-secondary" onClick={()=>onApply(values)}>확인한 추출값을 비교 항목에 적용</button><p className="uw-note">추출 결과는 진위 판정이 아닙니다. 원문과 비교해 수정한 뒤 내용 비교를 실행해 주세요.</p></>}
  </section>;
}
