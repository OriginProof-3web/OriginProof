/* A api-client의 세션·CSRF·errorInfo를 window.Hk로 이식. 비밀·본문 저장 없음. */
(function () {
  'use strict';
  const Hk = window.Hk = window.Hk || {};
  const requestId = () => 'req_' + crypto.randomUUID().replaceAll('-', '');
  function errorInfo(e) {
    const messages = {401:'다시 로그인해 주세요.',403:'권한 또는 CSRF를 확인해 주세요.',404:'기록을 찾지 못했습니다.',409:'현재 상태와 기존 작업을 조회해 주세요.',422:'입력 항목을 확인해 주세요.',429:'잠시 기다린 뒤 조회해 주세요.',503:'서버 또는 체인 연결 전 · 다시 조회해 주세요.'};
    return {status:e.status || 0, message:messages[e.status] || e.message || '연결 전', fieldErrors:e.fieldErrors || [], uncertain:!!e.uncertain};
  }
  function createSession(fetcher = window.fetch.bind(window)) {
    let stored = [];
    try { stored = JSON.parse(window.sessionStorage.getItem('hk.pending.v2') || '[]'); } catch (_) {}
    const pending = new Map(Array.isArray(stored)?stored:[]);
    function savePending() { try { window.sessionStorage.setItem('hk.pending.v2', JSON.stringify(Array.from(pending))); } catch (_) {} }
    async function api(path, body, id) {
      if (!/^\/v[123]\//.test(path)) throw Error('허용되지 않은 API 경로');
      const headers = {'Content-Type':'application/json'};
      if (body !== undefined) {
        headers['X-Request-ID'] = id || requestId();
        if (path !== '/v1/auth/login') {
          const me = await api('/v1/auth/me');
          if (!me.csrf_token) throw Error('CSRF 토큰 없음');
          headers['X-CSRF-Token'] = me.csrf_token;
        }
      }
      let res;
      try { res = await fetcher('/api' + path, {method:body === undefined?'GET':'POST', credentials:'same-origin', redirect:'error', headers, signal:AbortSignal.timeout(25000), ...(body === undefined?{}:{body:JSON.stringify(body)})}); }
      catch (_) { throw Object.assign(Error('연결 전 · 응답 유실 가능. 기존 요청을 조회해 주세요.'), {status:0, uncertain:body !== undefined}); }
      let data;
      try { data = await res.json(); } catch (_) { throw Object.assign(Error('응답 형식 미확인'),{status:res.status,uncertain:body !== undefined}); }
      if (!res.ok) throw Object.assign(Error(typeof data.detail === 'string'?data.detail:'요청 실패'), {status:res.status, fieldErrors:Array.isArray(data.detail)?data.detail:[], uncertain:body !== undefined && res.status >= 500});
      return data;
    }
    async function lookup(record) {
      if (record.readPath) return api(record.readPath);
      const rows = await api('/v1/operations?limit=200');
      const op = rows.find(x => x.request_id === record.id);
      if (!op) throw Error('기존 요청 미확인 · 첫 200건에서 찾지 못함. 재전송 금지, 작업 ID로 조회 필요');
      return api('/v1/operations/' + encodeURIComponent(op.operation_id));
    }
    async function write(path, body, options = {}) {
      const me = await api('/v1/auth/me');
      const fingerprint = new TextEncoder().encode(JSON.stringify([me.account_id,path,body]));
      const key = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',fingerprint)), b=>b.toString(16).padStart(2,'0')).join('');
      // 본문·비밀 대신 계정별 fingerprint와 요청 ID만 탭 저장소에 보존한다.
      let record = pending.get(key);
      if (record) return lookup(record);
      record = {id:requestId(), readPath:options.readPath}; pending.set(key, record); savePending();
      try { return await api(path, options.headerOnly?body:{...body,request_id:record.id}, record.id); }
      catch (e) {
        try { const state = await lookup(record); e.recovered = state; } catch (_) { /* 결과 불명: 재전송하지 않는다. */ }
        e.request_id = record.id; throw e;
      }
    }
    return {api,write,lookup,pending};
  }
  Hk.versionLabel = d => (d.version < d.latest_version ? '옛 버전 · ' : '새 버전 · ') + d.state + ' · v' + d.version;
  Hk.session = {createSession,requestId,errorInfo};
})();
