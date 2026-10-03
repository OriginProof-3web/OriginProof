import {validationErrors} from './w3-input.js';
// Cookie session stays HttpOnly; no password, token or payload is stored in the browser.
export async function api(path, body, prefix = window.originproofTestApi ?? '/api') {
  if (location.protocol === 'file:') throw new Error('협업 테스트 시작.command로 서버를 실행해 주세요.');
  const headers = { 'Content-Type': 'application/json' };
  if (body !== undefined && !path.startsWith('/v1/auth/login') && !/^\/v2\/proofs\/[^/]+\/verify$/.test(path) && !(prefix === '/admin-analyzer' && path === '/v1/analyze/card-payment-notice')) {
    const me = await api('/v1/auth/me', undefined, prefix);
    headers['X-CSRF-Token'] = me.csrf_token;
  }
  const response = await fetch(prefix + path, {method: body === undefined ? 'GET' : 'POST', credentials:'same-origin', headers, ...(body === undefined ? {} : {body: JSON.stringify(body)})});
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail ?? data.error ?? '서버 연결 실패';
    const error = new Error(`${response.status} · ${Array.isArray(detail) ? '입력값을 확인해 주세요.' : detail}`);
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
