import {api} from './api-client.js';
function notice(form, text) {
  let error = form.querySelector('[role="alert"]');
  if (!error) { error=document.createElement('p'); error.setAttribute('role','alert'); error.className='status-demo-note'; form.append(error); }
  error.hidden=false; error.textContent=text;
}
document.querySelectorAll('[data-auth-form]').forEach(form => form.addEventListener('submit',async event=>{
 event.preventDefault(); const values=new FormData(form); const username=String(values.get('username')??''); const password=String(values.get('password')??'');
 // Empty input keeps the explicitly requested design-preview navigation, without a session.
 if(!username && !password) { location.href=form.dataset.previewNext; return; }
 const button=form.querySelector('button[type="submit"]');button.disabled=true;
 try { const me=await api('/v1/auth/login',{username,password}); let next='index.html#user';
 const requested=new URLSearchParams(location.search).get('next');
 if(requested){const target=new URL(requested,location.href);if(target.origin===location.origin && target.pathname==='/index.html' && /^prf_[A-Za-z0-9_-]+$/.test(target.searchParams.get('proof_id')??''))next=target.pathname+target.search+ '#user';}
 location.href=me.role==='operator'?'admin.html':me.role==='issuer'?'business.html':next; }
 catch(error){notice(form,error.message);} finally{button.disabled=false;}
}));
document.querySelector('[data-status-lookup]')?.addEventListener('submit', event=>{event.preventDefault();location.href='application-status.html';});
document.querySelector('[data-issuer-application]')?.addEventListener('submit',async event=>{
 event.preventDefault();const form=event.currentTarget;const fields=new FormData(form);
 try { await api('/v1/issuer-applications',{issuer_name:String(fields.get('issuer_name')??'')});location.href='application-status.html'; }
 catch(error){notice(form,error.message+' · 기관 테스트 계정으로 먼저 로그인해 주세요. 현재 API는 기관명만 저장합니다.');}
});
document.querySelector('[data-individual-application]')?.addEventListener('submit',event=>{event.preventDefault();notice(event.currentTarget,'공개 회원가입 API는 아직 제공되지 않습니다. 준비된 개인 테스트 계정으로 로그인해 주세요.');});

document.querySelectorAll("[data-signup-choice]").forEach(button=>button.addEventListener("click",()=>{const target=button.dataset.signupChoice;document.querySelectorAll(".signup-panel").forEach(panel=>{panel.hidden=panel.id!==`${target}-application-panel`});document.querySelectorAll("[data-signup-choice]").forEach(choice=>choice.setAttribute("aria-pressed",String(choice===button)));}));

function showSignupFromHash(){
  const target=location.hash.slice(1);
  if(target!=="business"&&target!=="individual")return;
  document.querySelectorAll(".signup-panel").forEach(panel=>{panel.hidden=panel.id!==`${target}-application-panel`});
}
showSignupFromHash();
window.addEventListener("hashchange",showSignupFromHash);

const applicationForm=document.querySelector('[data-issuer-application]');
if(applicationForm){
 applicationForm.querySelectorAll('input,select,textarea').forEach(field=>{if(field.name!=='issuer_name'){field.disabled=true;field.required=false;}});
 const hint=document.createElement('p');hint.className='status-demo-note';hint.textContent='현재 저장소 API는 기관명만 저장합니다. 나머지 기관 정보 항목은 서버 지원 대기 중입니다.';applicationForm.append(hint);
}
