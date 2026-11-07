import {validationErrors} from './w3-input.js';
// Cookie session stays HttpOnly; no password, token or payload is stored in the browser.
export async function api(path, body, prefix = window.originproofTestApi ?? '/api', {timeoutMs=50000}={}) {
  if (location.protocol === 'file:') throw new Error('협업 테스트 시작.command로 서버를 실행해 주세요.');
  const mutation = body !== undefined && !path.startsWith('/v1/auth/login') && !/^\/v2\/proofs\/[^/]+\/verify$/.test(path) && !path.startsWith('/v1/analyze/');
  const headers = { 'Content-Type': 'application/json' };
  if (body !== undefined && !path.startsWith('/v1/auth/login') && !/^\/v2\/proofs\/[^/]+\/verify$/.test(path) && !(prefix === '/admin-analyzer' && path === '/v1/analyze/card-payment-notice')) {
    const me = await api('/v1/auth/me', undefined, prefix, {timeoutMs});
    headers['X-CSRF-Token'] = me.csrf_token;
  }
  let response;
  try { response = await fetch(prefix + path, {signal:AbortSignal.timeout(timeoutMs),method: body === undefined ? 'GET' : 'POST', credentials:'same-origin', headers, ...(body === undefined ? {} : {body: JSON.stringify(body)})}); }
  catch(cause) {const timeout=['TimeoutError','AbortError'].includes(cause?.name);throw Object.assign(new Error(timeout?'응답 확인 시간이 초과됐습니다.':'서버에 연결하지 못했습니다.'),{status:0,code:timeout?'TIMEOUT':'NETWORK',uncertain:mutation});}
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail ?? data.error ?? (response.status===429?'요청이 많습니다. 잠시 후 다시 시도해 주세요.':'서버 연결 실패');
    const error = new Error(`${response.status} · ${Array.isArray(detail) ? '입력값을 확인해 주세요.' : typeof detail==='string'?detail:'요청 처리 상태를 확인해 주세요.'}`);
    Object.assign(error, {status:response.status, fieldErrors:validationErrors(detail)});
    throw error;
  }
  return data;
}
// Only repeat read-only verification when the moving chain snapshot is inconclusive.
export async function verifyRead(path,body,prefix) {
  let result;
  for(let attempt=0;attempt<4;attempt++) {
    result=await api(path,body,prefix);
    if(result.verification_status!=='INCONCLUSIVE'||!result.reason_codes?.includes('DEPENDENCY_UNAVAILABLE'))return result;
    if(attempt<3)await new Promise(resolve=>setTimeout(resolve,150));
  }
  return result;
}
export function requestId() { return 'req_' + crypto.randomUUID().replaceAll('-', ''); }
export function seconds(value) { return new Date(value).toISOString().replace(/\.\d{3}Z$/, 'Z'); }
export async function logout() { try { await api('/v1/auth/logout', {}, '/api'); location.href='index.html'; } catch(error) { if(error.message.startsWith('401'))location.href='index.html'; else alert('로그아웃 실패: '+error.message); } }

if (typeof document !== 'undefined') document.querySelectorAll('[data-logout]').forEach(link=>link.addEventListener('click',event=>{event.preventDefault();void logout();}));

export function errorInfo(error) {
 const status=error?.status??Number(String(error?.message??error).match(/^(\d{3})/)?.[1]??0);
 const messages={401:'로그인이 만료됐습니다. 다시 로그인해 주세요.',403:'이 계정에는 요청한 작업 권한이 없습니다.',404:'등록된 기록을 찾지 못했습니다. ID와 조회 범위를 확인해 주세요.',409:'현재 상태에서는 실행할 수 없습니다. 기존 작업과 현재 상태를 먼저 조회해 주세요.',422:'표시된 입력값을 확인해 주세요.',429:'요청이 많습니다. 잠시 기다린 뒤 직접 다시 조회해 주세요.',503:'서버 또는 체인 연결을 확인하지 못했습니다. 현재 상태를 다시 조회해 주세요.'};
 const message=messages[status]??(error?.code==='TIMEOUT'?'응답을 확인하지 못했습니다.':error?.code==='NETWORK'?'서버에 연결하지 못했습니다.':String(error?.message??error));
 return {status,message:message+(error?.uncertain?' 변경 요청은 처리됐을 수 있습니다. 작업 이력에서 기존 요청을 먼저 확인해 주세요.':''),login:status===401,retryRead:['NETWORK','TIMEOUT'].includes(error?.code)||status===503,code:error?.code??String(status)};
}
