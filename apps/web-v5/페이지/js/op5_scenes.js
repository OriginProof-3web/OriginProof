/* 캡처용 장면 재현 (business.html?demo=장면 일 때만 씀. 기본 첫 화면에는 아무 일도 안 함).
   - 모두 가짜 응답(서버·지갑을 부르지 않음). 말풍선 칩에 '장면 재현 · 가짜 응답'이 붙음. 저장소에 남기지 않음.
   - 응답 모양·오류 코드는 계약(d0111d8)과 시험 자료(시험/fixtures/originproof, 코드로 재구성) 그대로.
   장면: example(예시 모드 결과) · api(실서버 모드 연결 전 응답) · wallet(지갑 단계) · retention(보관/삭제) */
(function () {
  'use strict';
  var Hk = (window.Hk = window.Hk || {});
  var NAMES = ['example', 'api', 'wallet', 'retention'];
  var NOW = 1792000000;
  var ME = { account_id: 'acc_scene', username: 'scene_issuer', role: 'issuer', issuer_id: 'iss_origin_mock_bank', csrf_token: 'fixture' };
  var ACCOUNT = '0x1111111111111111111111111111111111111111';
  var DOC = '0x' + 'ab'.repeat(32);
  var V3_UNAVAILABLE = {
    session_id: 'vsn_0000000000000000000000000000000a', verification_status: 'INCONCLUSIVE', comparison_scope: 'ID_ONLY', document: null,
    checks: [
      { name: 'signature', status: 'NOT_RUN', field_path: null, reason_code: null },
      { name: 'original_hash', status: 'NOT_RUN', field_path: null, reason_code: null },
      { name: 'protected_fields', status: 'NOT_RUN', field_path: null, reason_code: null },
      { name: 'current_state', status: 'UNAVAILABLE', field_path: null, reason_code: 'CHAIN_UNAVAILABLE' },
      { name: 'content', status: 'NOT_RUN', field_path: null, reason_code: null }
    ],
    reason_codes: ['CHAIN_UNAVAILABLE'], checked_at: NOW, chain_id: '31337', verifying_contract: '0x0000000000000000000000000000000000000001', block_number: null, block_hash: null
  };
  function job(id, status, extra) {
    var j = { analysis_id: id, status: status, retain_report: false, retain_original: false, result_expires_at: null, original_expires_at: null, report: null, error_code: null };
    for (var k in extra || {}) j[k] = extra[k];
    return j;
  }

  function reply(r) {
    var headers = r.headers || {};
    var body = r.status === 204 ? '' : JSON.stringify(r.body == null ? null : r.body);
    return Promise.resolve({
      status: r.status,
      headers: { get: function (h) { for (var k in headers) if (k.toLowerCase() === String(h).toLowerCase()) return headers[k]; return h.toLowerCase() === 'content-type' ? 'application/json' : null; } },
      text: function () { return Promise.resolve(body); }
    });
  }

  function routes(name) {
    var n = { analyses: 0, list: 0 };
    var removed = {};
    return function (url, init) {
      var m = (init && init.method) || 'GET';
      var p = String(url).replace(/^\/api/, '');
      if (p === '/v1/auth/me') return { status: 200, body: ME };
      if (p === '/health/live') return { status: 200, body: { status: 'live' } };
      if (p === '/health/ready') return { status: 503, body: { detail: 'RUNTIME_NOT_READY' } };
      if (p === '/v1/issuer/status') return { status: 200, body: { chain_id: 31337, deployment_id: 'dep_scene', issuer_id: 'iss_origin_mock_bank', status: 'ACTIVE' } };
      if (p === '/v1/issuer-applications/mine') return { status: 200, body: { application_id: 'app_scene', applicant_account_id: 'acc_scene', issuer_id: 'iss_origin_mock_bank', issuer_name: '합성 기관', status: 'APPROVED', created_at: '2026-10-25T00:00:00Z', decided_by_account_id: null, decision_reason: null } };
      if (p === '/v1/issuer/keys') return { status: 200, body: [] };
      if (p.indexOf('/v1/operations') === 0) return { status: 200, body: [] };
      if (name === 'api') {
        if (p === '/v3/inputs' && m === 'POST') return { status: 201, body: { input_ref: 'inp_scene_' + (n.analyses + 1), expires_at: NOW + 3600 } };
        if (p === '/v3/analyses' && m === 'POST') {
          n.analyses++;
          if (n.analyses === 1) return { status: 202, body: job('ana_scene_1', 'QUEUED') };
          return { status: 429, body: { detail: 'ANALYSIS_LIMIT' }, headers: { 'Retry-After': '600' } };
        }
        if (p === '/v3/analyses/ana_scene_1') return { status: 200, body: job('ana_scene_1', 'FAILED', { error_code: 'ANALYZER_UNAVAILABLE', result_expires_at: NOW + 600 }) };
        if (p === '/v3/verifications') return { status: 200, body: V3_UNAVAILABLE };
      }
      if (name === 'wallet') {
        if (p === '/v3/key-challenges' || p === '/v3/document-drafts' || p === '/v3/revoke-drafts') return { status: 503, body: { detail: 'WALLET_REGISTRY_UNAVAILABLE' } };
      }
      if (name === 'retention') {
        var items = [
          job('ana_scene_keep1', 'COMPLETED', { retain_report: true, retain_original: true, result_expires_at: NOW + 7 * 86400, original_expires_at: NOW + 7 * 86400 }),
          job('ana_scene_keep2', 'COMPLETED', { retain_report: true, retain_original: false, result_expires_at: NOW + 7 * 86400 })
        ].filter(function (x) { return !removed[x.analysis_id]; });
        if (p.indexOf('/v3/analyses?') === 0) return { status: 200, body: { items: items, next_cursor: null } };
        var d = /^\/v3\/analyses\/(ana_[A-Za-z0-9_]+)$/.exec(p);
        if (d && m === 'DELETE') { removed[d[1]] = true; return { status: 204 }; }
      }
      return { status: 404, body: { detail: 'NOT_FOUND' } };
    };
  }

  function fetchFor(name) {
    var r = routes(name);
    return function (url, init) { return reply(r(url, init || {})); };
  }
  // 지갑 장면: 가짜 지갑(계정 연결만, 서명까지 가지 않음 — 서버가 503 을 주는 단계에서 멈춤)
  function ethereum(name) {
    if (name !== 'wallet') return undefined;
    return { request: function (q) { return q && q.method === 'eth_requestAccounts' ? Promise.resolve([ACCOUNT]) : Promise.reject({ code: 4001 }); } };
  }
  function mode(name) { return name === 'example' ? 'sample' : 'api'; }

  function run(name, ui) {
    var chain = Promise.resolve();
    var step = function (f) { chain = chain.then(f).then(function () { return null; }, function () { return null; }); };
    if (name === 'example') {
      var s = Hk.sampleAdapter.get('tamper');
      step(function () { return ui.submitText(s.input.text); });
    }
    if (name === 'api') {
      step(function () { return ui.menu('status'); });
      step(function () { return ui.submitText('[OO카드] 이번 달 결제 안내입니다. 자세한 내용은 고객센터로 문의해 주세요.'); });
      step(function () { return ui.submitText(JSON.stringify({ document_id: DOC, version: 1 })); });
      step(function () { return ui.submitText('[OO공단] 보험료 납부 안내입니다. 기한 안에 납부해 주세요.'); });
    }
    if (name === 'wallet') {
      step(function () { return ui.menu('issue'); });
      step(function () { return ui.menu('keys'); });
      step(function () {
        var btns = document.querySelectorAll('#chatThread .add-btn');
        var b = Array.prototype.filter.call(btns, function (x) { return /^지갑 키 증명 시작/.test(x.textContent); })[0];
        if (b) b.click();
        return new Promise(function (r) { setTimeout(r, 50); });
      });
    }
    if (name === 'retention') {
      step(function () { return ui.menu('operations'); });
      step(function () { return ui.showAnalyses(); });
      step(function () { return ui.removeAnalysis('ana_scene_keep2', null); });
      step(function () { return ui.showAnalyses(); });
    }
    return chain;
  }

  Hk.op5scenes = { valid: function (n) { return NAMES.indexOf(n) >= 0; }, fetchFor: fetchFor, ethereum: ethereum, mode: mode, run: run, NAMES: NAMES };
})();
