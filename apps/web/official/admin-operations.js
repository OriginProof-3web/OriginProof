import {api,requestId} from './api-client.js';
const root=document.getElementById('operator-controls');
const text=(tag,value)=>{const node=document.createElement(tag);node.textContent=value;return node;};
let busy=false;
async function refresh(){
 root.replaceChildren(text('h2','기관 신청·Registry 테스트'));
 try {
  const me=await api('/v1/auth/me');if(me.role!=='operator')throw new Error('실제 운영자 테스트 계정으로 로그인하면 승인·체인 작업을 실행할 수 있습니다.');
  const rows=await api('/v1/operator/issuer-applications');
  for(const row of rows){
   const card=document.createElement('section');card.className='test-card';card.append(text('h3',row.issuer_name),text('p',row.application_id+' · '+row.status),text('p',row.decision_reason??'검토 사유 없음'));
   const reason=document.createElement('input');reason.placeholder='검토·작업 사유';reason.setAttribute('aria-label','사유 '+row.issuer_name);card.append(reason);
   for(const [label,path,body] of row.status==='PENDING_REVIEW'?[['승인','decision',{decision:'APPROVE'}],['반려','decision',{decision:'REJECT'}]]:row.status==='APPROVED_PENDING_CHAIN'?[['체인 활성화','activate',{request_id:requestId()}]]:[]){
    const button=text('button',label);button.onclick=async()=>{
      if(busy)return;if(!reason.value.trim()){card.append(text('p','사유를 입력해 주세요.'));return;}busy=true;button.disabled=true;
      try {const result=await api(`/v1/operator/issuer-applications/${row.application_id}/${path}`,{...body,reason:reason.value.trim()});await refresh();root.append(text('p',`${result.operation_id??result.application_id} · ${result.status}`));}catch(error){card.append(text('p',error.message));}finally{busy=false;button.disabled=false;}
    };card.append(button);
   }
   root.append(card);
  }
  if(!rows.length)root.append(text('p','접수된 기관 신청이 없습니다.'));
 }catch(error){root.append(text('p',error.message));}
}
await refresh();
