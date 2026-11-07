import {api as scopedApi,requestId} from './api-client.js';
const api=(path,body)=>scopedApi(path,body,'/test-api/operator');
const root=document.getElementById('operator-controls');
const alert=(value)=>{const node=text('p',value);node.setAttribute('role','alert');return node;};
const text=(tag,value)=>{const node=document.createElement(tag);node.textContent=value;return node;};
let busy=false;
const requests=new Map();
const stable=(key)=>{if(!requests.has(key))requests.set(key,requestId());return requests.get(key);};
async function refresh(){
 root.replaceChildren(text('h2','기관 신청·Registry 테스트'));
 try {
  const me=await api('/v1/auth/me');if(me.role!=='operator')throw new Error('실제 운영자 테스트 계정으로 로그인하면 승인·체인 작업을 실행할 수 있습니다.');
  const sync=await api('/v1/chain-sync');root.append(text('p',`체인 동기화: ${sync.status} · 조회의 최종 권위는 현재 체인입니다.`));
  const rows=await api('/v1/operator/issuer-applications');
  for(const row of rows){
   const card=document.createElement('section');card.className='test-card';card.append(text('h3',row.issuer_name),text('p',row.application_id+' · '+row.status),text('p',row.decision_reason??'검토 사유 없음'));
   const reason=document.createElement('input');reason.placeholder='검토·작업 사유';reason.setAttribute('aria-label','사유 '+row.issuer_name);card.append(reason);
   for(const [label,path,body] of row.status==='PENDING_REVIEW'?[['승인','decision',{decision:'APPROVE'}],['반려','decision',{decision:'REJECT'}]]:row.status==='APPROVED_PENDING_CHAIN'?[['체인 활성화','activate',{}]]:[]){
    const button=text('button',label);button.onclick=async()=>{
      if(busy)return;if(!reason.value.trim()){card.append(alert('사유를 입력해 주세요.'));return;}busy=true;button.disabled=true;
      try {const result=await api(`/v1/operator/issuer-applications/${row.application_id}/${path}`,{...body,...(path==='activate'?{request_id:stable(JSON.stringify([row.application_id,path,reason.value.trim()]))}:{}),reason:reason.value.trim()});await refresh();root.append(text('p',`${result.operation_id??result.application_id} · ${result.status}`));}catch(error){if(error.status===401)await refresh();else card.append(alert(error.message));}finally{busy=false;button.disabled=false;}
    };card.append(button);
   }
   if(['ACTIVE','SUSPENDED'].includes(row.status))for(const [label,action] of (row.status==='ACTIVE'?[['기관 중지','suspend'],['기관 영구 폐기','revoke']]:[['기관 재활성화','reactivate'],['기관 영구 폐기','revoke']])){
    const button=text('button',label);button.onclick=async()=>{if(busy)return;if(!reason.value.trim()){card.append(alert('작업 사유를 입력해 주세요.'));return;}if(!confirm(label+' 작업을 실행하시겠습니까?'))return;busy=true;button.disabled=true;try{const op=await api(`/v1/operator/issuers/${encodeURIComponent(row.issuer_id)}/${action}`,{request_id:stable(JSON.stringify([row.issuer_id,action,reason.value.trim()])),reason:reason.value.trim()});if(op.status==='CONFIRMED')requests.delete(JSON.stringify([row.issuer_id,action,reason.value.trim()]));await refresh();root.append(text('p',`${op.operation_id} · ${op.status}`));}catch(e){if(e.status===401)await refresh();else card.append(alert(e.message));}finally{busy=false;button.disabled=false;}};card.append(button);
   }
   root.append(card);
  }
  if(!rows.length)root.append(text('p','접수된 기관 신청이 없습니다.'));
  const ops=await api('/v1/operations');
  const tasks=document.createElement('section');tasks.className='test-card';tasks.append(text('h3','체인 작업 · 조회와 복구'));
  for(const op of ops){const item=document.createElement('div');item.append(text('p',`${op.action} · ${op.operation_id} · ${op.status} · ${op.next_action}`));if(['UNKNOWN','SUBMITTED','PENDING_SUBMISSION'].includes(op.status)){const recover=text('button','기존 거래 복구');recover.onclick=async()=>{if(busy)return;busy=true;recover.disabled=true;try{await api(`/v1/operations/${op.operation_id}/recover`,{});await refresh();}catch(e){if(e.status===401)await refresh();else item.append(alert(e.message));}finally{busy=false;recover.disabled=false;}};item.append(recover);}tasks.append(item);}root.append(tasks);

 }catch(error){root.append(alert(error.message));}
}
await refresh();

window.addEventListener('originproof-operator-refresh',()=>void refresh());

const ai=document.createElement('section');ai.className='uw-card';ai.append(text('h2','AI 후보 추출 · 카드 알림'));
ai.append(text('p','GitHub의 기존 Analyzer를 mock으로 실행합니다. 추출 결과는 진위 판정이 아니며 지급 요청·공식 문서 추출 API는 아직 제공되지 않습니다.'));
const input=document.createElement('textarea');input.maxLength=10000;input.rows=7;input.setAttribute('aria-label','합성 카드 알림 텍스트');ai.append(input);
const sample=text('button','합성 텍스트 채우기');sample.onclick=()=>{input.value='SYNTHETIC FIXTURE\nissuer: Origin Mock Bank\ncard: ****1234\namount: 85,000원\nmerchant: Synthetic Shop\napproved_at: 2026-10-03T09:00:00+09:00\ntransaction_id: SYNTHETIC-001';};ai.append(sample);
const extract=text('button','AI 후보 추출');const output=text('pre','');output.setAttribute('role','status');extract.onclick=async()=>{if(!input.value.trim())return;extract.disabled=true;try{const result=await scopedApi('/v1/analyze/card-payment-notice',{text:input.value},'/admin-analyzer');output.textContent=JSON.stringify(result,null,2);}catch(e){output.textContent=e.message;}finally{extract.disabled=false;}};ai.append(extract,output);document.getElementById('operator-panel').append(ai);
