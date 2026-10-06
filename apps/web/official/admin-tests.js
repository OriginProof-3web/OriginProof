const results=document.querySelector('#test-results');
let pollTimer;
const labels={passed:'통과',failed:'실패',failure:'실패',error:'실행 오류',skipped:'미실행',running:'실행 중',not_run:'미실행'};
async function showGitUpdate(){
  if(location.protocol==='file:')return;
  try{
    const response=await fetch('github-update.json',{cache:'no-store'});
    if(!response.ok)return;
    const update=await response.json();
    const card=document.createElement('section');card.className='test-card';
    const heading=document.createElement('h2');heading.textContent='최신 GitHub · 김형준님 진행 상태';card.append(heading);
    const checked=document.createElement('p');checked.textContent='확인: '+new Date(update.checked_at).toLocaleString('ko-KR')+' · 팀원 보고와 이 관리자 직접 검사 결과는 별도입니다.';card.append(checked);
    for(const line of update.progress){const p=document.createElement('p');p.textContent=line;card.append(p);}
    const list=document.createElement('ul');
    for(const pr of update.pull_requests){
      const item=document.createElement('li');const link=document.createElement('a');
      link.href=pr.url;link.textContent=`PR #${pr.number} · ${pr.title}`;item.append(link);
      item.append(document.createTextNode(` — ${pr.state}${pr.draft?' / Draft':''} · ${pr.sha.slice(0,7)} · ${pr.note}`));list.append(item);
    }
    card.append(list);results.append(card);
  }catch{const p=document.createElement('p');p.textContent='최신 GitHub 기록을 불러오지 못했습니다. 아래 검사 기록은 기존 결과입니다.';results.append(p);}
}
async function refresh(){
  try{
    let data=window.collaborationSavedResults;
    if(location.protocol!=='file:'){
      const response=await fetch('collaboration-results.json',{cache:'no-store'});
      if(!response.ok)throw new Error('아직 검사 기록이 없습니다.');
      data=await response.json();
    }
    data??={};
    data.admin??={title:'최신 관리자 기능 · 실제 API/체인 · mock AI',status:'not_run',sha:'3ef1fd40943914c1450e8bc05047119ab7eabbc0',cases:[]};
    data.w3??={title:'현재 웹 · 기업/개인/관리자 · QR · 실제 연결',status:'not_run',sha:'현재 작업 소스',cases:[]};
    document.querySelector('#test-message').textContent=location.protocol==='file:'?'마지막으로 저장된 실제 검사 결과입니다.':'';
    results.replaceChildren();
    await showGitUpdate();
    for(const [id,report] of Object.entries(data)){
      const card=document.createElement('section');card.className='test-card';
      const heading=document.createElement('h2');heading.textContent=`${id==='w5-a'?'W5 A 화면 검사':id==='admin'?'관리자 기능 검사':id==='web'?'웹 연결 검사':id==='w3'?'기업·개인·관리자 웹 검사':'PR #'+id} · ${report.title}`;card.append(heading);
      const summary=document.createElement('p');
      const commands=report.cases.filter(c=>c.group==='현재 GitHub 웹 소스');
      const cases=report.cases.filter(c=>c.group!=='현재 GitHub 웹 소스');
      const passed=cases.filter(c=>c.status==='passed').length;
      const skipped=cases.filter(c=>c.status==='skipped').length;
      const failed=cases.filter(c=>c.status==='failure'||c.status==='error').length;
      summary.textContent=`${labels[report.status]} · ${passed}개 통과 / ${failed}개 실패 / ${skipped}개 미실행${commands.length?' · 명령 '+commands.filter(c=>c.status==='passed').length+'/'+commands.length+' 통과':''}`;card.append(summary);
      const sha=document.createElement('p');sha.className='test-meta';sha.textContent=`검사 SHA: ${report.sha}${report.worktree_modified?' + 로컬 변경':''} · ${report.finished_at?new Date(report.finished_at).toLocaleString('ko-KR'):'진행 중'}`;card.append(sha);
      if(report.web_fingerprint){const fingerprint=document.createElement('p');fingerprint.className='test-meta';fingerprint.textContent='실행 화면 식별값: '+report.web_fingerprint;card.append(fingerprint);}
      const button=document.createElement('button');button.textContent=id==='w3'?'웹 검사 다시 실행':id==='web'?'웹 연결 검사 다시 실행':id==='admin'?'관리자 기능 검사 다시 실행':'이 PR 검사 다시 실행';button.disabled=report.replayable===false||(location.protocol!=='file:'&&report.status==='running');if(report.replayable===false)button.textContent='검사 기록 · 실행 명령으로 재현';
      button.addEventListener('click',async()=>{if(location.protocol==='file:'){location.href='http://127.0.0.1:8768/admin.html';return}button.disabled=true;try{const r=await fetch(`/run-pr/${id}`,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});if(!r.ok)throw new Error(`실행 요청 실패: ${r.status}`);setTimeout(refresh,500)}catch(e){document.querySelector('#test-message').textContent=e.message;button.disabled=false}});card.append(button);
      const details=document.createElement('details');const title=document.createElement('summary');title.textContent='개별 검사 결과 보기';details.append(title);
      const list=document.createElement('ul');
      for(const c of report.cases){const item=document.createElement('li');item.textContent=`${labels[c.status]} · ${c.group} / ${c.name}${c.detail?' — '+c.detail:''}`;list.append(item)}
      details.append(list);card.append(details);
      const logs=document.createElement('details');const logTitle=document.createElement('summary');logTitle.textContent='실행 명령·로그';logs.append(logTitle);const pre=document.createElement('pre');pre.textContent=`${report.command||''}\n${report.output||''}`;logs.append(pre);card.append(logs);results.append(card);
    }
    if(location.protocol!=='file:'&&Object.values(data).some(r=>r.status==='running'))pollTimer=setTimeout(refresh,10000);
  }catch(e){document.querySelector('#test-message').textContent=location.protocol==='file:'?'검사 실행은 로컬 서버에서 가능합니다. http://127.0.0.1:8768/user-login.html로 접속해 주세요.':e.message}
}
refresh();
