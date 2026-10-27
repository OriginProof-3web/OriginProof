import {api} from './api-client.js';
const note=document.querySelector('.status-demo-note');
try {
 const row=await api('/v1/issuer-applications/mine');
 if(!row) throw new Error('아직 제출된 기관 신청이 없습니다.');
 document.querySelector('.status-summary strong').textContent=row.issuer_name;
 document.querySelector('.status-summary small').textContent='신청 상태 · '+row.status;
 const index={PENDING_REVIEW:1,APPROVED_PENDING_CHAIN:3,ACTIVE:4,REJECTED:2}[row.status]??0;
 document.querySelectorAll('.application-step').forEach((step,i)=>{
  step.classList.toggle('current',i===index);
  const mark=step.querySelector('.step-mark');
  mark.className='step-mark '+(i<index?'complete':i===index?'active':'waiting');
  if(i===index && row.status!=='REJECTED')mark.innerHTML='<svg class="step-spinner" width="24" height="24" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="11" fill="none" stroke="#ffffff20" stroke-width="2"/><circle cx="12" cy="12" r="11" fill="none" stroke="#a8a3b0" stroke-width="2" stroke-dasharray="19.35 49.77"/></svg><span>'+String(i+1)+'</span>';
  else mark.textContent=i<index?'✓':String(i+1);
  step.querySelector('.step-detail,.step-pill').textContent=i<index?'완료':i===index?row.status:'대기';
 });
 note.textContent=row.decision_reason??'운영자 결정 사유가 아직 없습니다.';
} catch(error) {document.querySelector('.application-steps').hidden=true; document.querySelector('.status-summary').hidden=true;note.textContent=error.message+' · 기관 계정으로 로그인해 주세요.';}
