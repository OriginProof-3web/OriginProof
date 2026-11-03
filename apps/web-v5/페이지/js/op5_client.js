/* 5안 서버 연결 도우미 (화면을 만지지 않음 → node 에서 가짜 fetch·가짜 지갑으로 시험: 시험/op5_client.test.js).
   가져온 것 위에 얹음(새로 짜지 않음):
   - 요청 보내기: api_adapter.js(5안 확장) Hk.api.makeCaller({ base }) — 같은 출처 /api, 로그인 쿠키, 쓰기의 X-CSRF-Token
   - request_id: session.js Hk.session.requestId (req_ + 32자리)
   - 개인정보 가림: text_tools.js
   계약 기준: OriginProof phase/W6 d0111d8 — docs/api/v5_c_runtime.md "A: 화면에서 사용할 순서",
   docs/runbooks/v5_wallet_local.md, packages/schemas/generated/openapi.json. 경로·필드·오류 코드는 모두 거기서 옮김.
   비밀값(비밀번호·CSRF 토큰·서명)은 저장소에 남기지 않음. 작업 이력에는 operation_id·request_id·종류·상태만 둠. */
(function () {
  'use strict';
  var Hk = (window.Hk = window.Hk || {});

  /* ---------------- 오류 코드 → 쉬운 말 (코드 문자열은 계약 그대로) ---------------- */
  var CODE_TEXT = {
    WALLET_REGISTRY_UNAVAILABLE: '서버에 블록체인 장부(Registry) 연결부가 아직 붙지 않았어요. 체인을 조회하는 지갑 기능은 연결된 뒤에 쓸 수 있어요.',
    WALLET_REGISTRY_NOT_CONFIGURED: '서버에 장부(Registry) 주소가 설정되지 않았어요.',
    ANALYZER_UNAVAILABLE: '서버에 AI 분석기가 아직 연결되지 않았어요.',
    RUNTIME_NOT_READY: '서버는 켜져 있지만 아직 준비가 안 됐어요(계정·장부 연결 등 준비 항목이 남음). 꺼진 것과는 달라요.',
    RATE_LIMITED: '요청이 많아 서버가 잠시 막았어요.',
    ANALYSIS_LIMIT: '분석은 계정당 동시에 1건, 10분에 5건까지만 받아요.',
    EMAIL_ISSUE_LIMIT: '메일 코드를 너무 자주 요청했어요.', EMAIL_REISSUE_LIMIT: '메일 코드를 너무 자주 다시 요청했어요.', EMAIL_ATTEMPT_LIMIT: '메일 코드를 너무 많이 틀렸어요.',
    RESULT_EXPIRED: '결과 보관 시간이 지나 더는 볼 수 없어요.',
    INPUT_EXPIRED: '입력 보관 시간(1시간)이 지나 분석할 수 없어요.',
    ORIGINAL_UNAVAILABLE: '원본을 보관하지 않았거나 보관 시간이 지났어요.',
    SIGNATURE_EXPIRED: '서명 기한이 지났어요. 서명 요청을 새로 만들어야 해요.',
    PROPOSAL_EXPIRED: '제안 기한이 지났어요.', EMAIL_CODE_EXPIRED: '메일 코드 기한이 지났어요.',
    VERIFICATION_SESSION_EXPIRED: '검증 세션(24시간)이 지났어요.',
    AUTH_REQUIRED: '로그인이 필요해요.', INVALID_CREDENTIALS: '계정 이름이나 비밀번호가 맞지 않아요.',
    CSRF_REQUIRED: '로그인 확인값(CSRF)이 맞지 않아 서버가 막았어요. 다시 로그인해 주세요.',
    ORIGIN_FORBIDDEN: '허용되지 않은 화면 주소에서 보낸 요청이라 서버가 막았어요.',
    FORBIDDEN: '이 계정으로는 할 수 없는 작업이에요.', APPLICANT_REQUIRED: '기관 신청자 계정만 할 수 있어요.', APPROVER_REQUIRED: '승인 지갑이 등록된 운영 계정만 할 수 있어요.',
    DOCUMENT_OWNER_MISMATCH: '다른 기관의 문서예요.',
    REQUEST_ID_CONFLICT: '같은 요청 번호로 다른 내용을 보냈어요. 처음부터 다시 시작해 주세요.',
    INPUT_SUPPORT_UNDECIDED: '서버가 글 입력 받기를 아직 켜지 않았어요.',
    INPUT_ALREADY_ANALYZED: '이미 분석을 맡긴 입력이에요.',
    EMPTY_INPUT: '빈 글은 받을 수 없어요.',
    INPUT_NOT_FOUND: '입력을 찾지 못했어요.', ANALYSIS_NOT_FOUND: '분석 기록을 찾지 못했어요.', OPERATION_NOT_FOUND: '작업을 찾지 못했어요.',
    DOCUMENT_NOT_FOUND: '문서를 찾지 못했어요.', SIGNING_REQUEST_NOT_FOUND: '서명 요청을 찾지 못했어요.', APPLICATION_NOT_FOUND: '기관 신청을 찾지 못했어요.',
    PROOF_NOT_FOUND: 'Proof 를 찾지 못했어요.', NOT_FOUND: '찾지 못했어요.', VERIFICATION_SESSION_NOT_FOUND: '검증 세션을 찾지 못했어요.',
    INSTITUTION_CHECKS_REQUIRED: '기관 확인(명부·메일·내부 승인)이 먼저 끝나야 해요.',
    APPLICATION_NOT_APPROVED: '기관 신청이 아직 승인되지 않았어요.',
    ISSUER_NOT_REGISTERED: '체인에 아직 활성 기관으로 등록되지 않았어요.', ISSUER_SUSPENDED: '기관이 정지된 상태예요.', ISSUER_NOT_ACTIVE: '기관이 활성 상태가 아니에요.',
    KEY_NOT_ACTIVE: '기관 서명 키가 활성 상태가 아니에요.', KEY_PROOF_REQUIRED: '지갑 키 증명(key-proofs)을 먼저 해야 해요.', KEY_COMPROMISED: '사고 처리된 키예요.',
    VERSION_CONFLICT: '문서 버전이 맞지 않아요. 다음 버전 번호를 확인해 주세요.',
    NONCE_ALREADY_RESERVED: '같은 기관에 아직 확정되지 않은 작업이 있어요. 작업 이력에서 먼저 확인해 주세요.',
    NONCE_ALREADY_USED: '이미 쓴 업무 번호(nonce)예요.',
    INVALID_SIGNATURE: '서명이 서명 요청과 맞지 않아요.', KEY_PROOF_MISMATCH: '키 증명 서명이 맞지 않아요.',
    SIGNATURE_ALREADY_SUBMITTED: '이 서명 요청에는 이미 서명을 냈어요.', SIGNED_SUBMISSION_REQUIRED: '서명을 먼저 제출해야 해요.',
    DIRECT_TX_MISMATCH: '거래 해시가 이 서명 요청의 거래와 맞지 않아요.', DIRECT_TX_ALREADY_BOUND: '이미 다른 거래가 연결된 서명 요청이에요.',
    SIGNING_REQUEST_MISMATCH: '주소의 서명 요청 번호와 본문의 번호가 달라요.',
    DOCUMENT_ALREADY_REVOKED: '이미 철회된 문서예요.', EXPIRY_IN_PAST: '만료 시각이 이미 지났어요.', CONTENT_OR_PERIOD_INVALID: '내용이나 기간이 규칙에 맞지 않아요.',
    INSTITUTION_CODE_MISMATCH: '기관 코드가 이 기관과 맞지 않아요.',
    DEPLOYMENT_CHANGED: '장부 배포가 바뀌었어요. 이전 배포의 작업은 보존만 해요.',
    CHAIN_UNAVAILABLE: '블록체인에 연결하지 못했어요.', CHAIN_RECORD_MISMATCH: '체인 기록과 서버 기록이 맞지 않아요.', CHAIN_OR_SIGNER_UNAVAILABLE: '체인이나 서명 장치에 연결하지 못했어요.',
    STORED_SIGNING_REQUEST_INVALID: '저장된 서명 요청이 올바르지 않아요.', STORED_CONTENT_MISMATCH: '저장된 원본이 서명 내용과 맞지 않아요.',
    CHALLENGE_ALREADY_USED: '이미 쓴 키 증명 요청이에요.', SIGNER_ALREADY_USED: '이미 쓰인 지갑 주소예요.', NOT_SUBMITTED: '아직 제출되지 않은 작업이에요.',
    ANALYSIS_TIMEOUT: '분석 시간(180초)이 지나 멈췄어요.', WORKER_STOPPED: '분석 작업자가 멈췄어요.', PROCESS_RESTARTED: '서버가 다시 시작돼 분석이 실패 처리됐어요.',
    REQUEST_TOO_LARGE: '보낸 내용이 너무 커요.',
    DEMO_EMAIL_NOT_ENABLED: '데모 메일이 켜져 있지 않아요.', DEMO_EMAIL_SECRET_NOT_CONFIGURED: '데모 메일 설정이 없어요.',
    SELF_APPROVAL_FORBIDDEN: '신청자 본인은 내부 승인을 할 수 없어요.', INTERNAL_APPROVER_REQUIRED: '이 계정은 이 기관의 지정된 승인자가 아니에요.',
    EMAIL_CODE_INVALID: '확인 코드가 맞지 않아요.', DEMO_EMAIL_DOMAIN_MISMATCH: '이 기관의 합성 도메인 메일 주소가 아니에요.',
    EMAIL_VERIFICATION_REQUIRED: '신청자의 메일 확인이 먼저 끝나야 해요.', ALREADY_DECIDED: '이미 내부 승인 결정이 끝났어요.',
    PROPOSAL_NOT_FOUND: '제안을 찾지 못했어요.', ISSUER_NOT_FOUND: '기관을 찾지 못했어요.'
  };
  var STATUS_TEXT = {
    400: '요청 형식이 맞지 않아요.', 401: '로그인이 필요해요.', 403: '권한이 없거나 로그인 확인값이 맞지 않아요.', 404: '찾지 못했어요.',
    405: '이 서버에는 이 경로가 없어요.', 409: '지금 상태에서는 할 수 없어요. 기존 작업과 현재 상태를 먼저 확인해 주세요.', 410: '보관 기한이 지났어요.',
    413: '보낸 내용이 너무 커요.', 422: '보낸 항목 형식을 서버가 받지 않았어요.', 429: '요청이 많아 잠시 막혔어요.'
  };

  function str(v) { return v == null ? '' : String(v); }
  function detailOf(res) {
    var d = res && res.data;
    if (!d || typeof d !== 'object') return '';
    var v = d.detail != null ? d.detail : d.error;
    return typeof v === 'string' ? v : '';
  }
  function fieldsOf(res) {
    var d = res && res.data;
    if (d && Array.isArray(d.detail)) return d.detail.map(function (x) { return Array.isArray(x && x.loc) ? x.loc.slice(1).join('.') : ''; }).filter(Boolean);
    if (d && Array.isArray(d.field_paths)) return d.field_paths.map(str);
    return [];
  }

  /* 응답 → { ok, status, code, text, retryAfter, uncertain }. 코드는 응답 그대로, 글은 위 표 그대로(지어내지 않음) */
  function explain(res, opt) {
    opt = opt || {};
    if (!res) return { ok: false, status: 0, code: 'NO_RESPONSE', text: '응답이 없어요.' };
    if (res.error === 'network' && res.detail === 'SampleMode') return { ok: false, status: 0, code: 'SAMPLE_MODE', text: '예시 모드로 바뀌어 서버에 보내지 않았어요.' };
    if (res.error === 'bad_shape') return { ok: false, status: res.status, code: 'UPSTREAM_SCHEMA_MISMATCH', text: '서버 응답이 작업 형식과 맞지 않아요. 기존 작업부터 다시 조회해 주세요.', uncertain: true };
    if (res.error === 'timeout') return { ok: false, status: 0, code: 'TIMEOUT', text: '서버가 제한 시간 안에 답하지 않았어요. 처리됐을 수도 있으니 다시 보내기 전에 상태를 먼저 확인해 주세요.', uncertain: true };
    if (res.error === 'network') {
      var fileMode = opt.fileMode === true;
      return { ok: false, status: 0, code: 'NETWORK', uncertain: true, text: fileMode
        ? '이 화면이 파일로 열려 있어 같은 출처 /api 연결을 쓸 수 없어요. 개발/협업 테스트 시작.command 로 연 화면에서 해 주세요.'
        : '서버에 닿지 못했어요. 서버가 꺼져 있거나 연결 주소가 틀렸어요.' };
    }
    var s = res.status;
    if (s >= 200 && s < 300) return { ok: true, status: s, code: '', text: '' };
    var code = detailOf(res);
    var ra = res.retryAfter && /^\d{1,6}$/.test(String(res.retryAfter)) ? +res.retryAfter : null;
    var text = CODE_TEXT[code] || STATUS_TEXT[s] || (s >= 500 ? '서버가 지금 처리하지 못했어요.' : '요청이 처리되지 않았어요.');
    if (s === 422 && fieldsOf(res).length) text += ' (확인할 항목: ' + fieldsOf(res).slice(0, 5).join(', ') + ')';
    if (s === 429) text += ra != null ? ' ' + ra + '초 뒤에 다시 해 주세요.' : ' 잠시 뒤 다시 해 주세요.';
    return { ok: false, status: s, code: code || ('HTTP_' + s), text: text, retryAfter: ra, uncertain: s >= 500 && s !== 503 };
  }

  /* ---------------- 입력 검증 ---------------- */
  var RE = {
    hex32: /^0x[0-9a-f]{64}$/, address: /^0x[0-9a-fA-F]{40}$/, sig: /^0x[0-9a-fA-F]{130}$/,
    wsr: /^wsr_[A-Za-z0-9_-]+$/, op: /^op_[A-Za-z0-9_-]+$/, ana: /^ana_[A-Za-z0-9_-]{1,128}$/, app: /^app_[A-Za-z0-9_-]+$/, prf: /^prf_[A-Za-z0-9_-]{1,124}$/
  };
  var SAFE = 9007199254740991;
  function isInt(v, lo, hi) { return typeof v === 'number' && Number.isInteger(v) && v >= lo && v <= hi; }
  function txt(v, lo, hi) { return typeof v === 'string' && v.trim().length >= lo && v.trim().length <= hi; }
  function httpsUrl(v) { return v == null || (typeof v === 'string' && v.length <= 2048 && /^https:\/\/[^\s/?#@]+[^\s@]*$/.test(v)); }
  function fail(m) { return { ok: false, message: m }; }

  /* 발행 초안(document-drafts) 입력: 계약 DocumentDraftRequest·PaymentContent·OfficialContent 그대로(모르는 칸은 거부) */
  function parseDraft(text, nowSec) {
    var d;
    try { d = JSON.parse(text); } catch (e) { return fail('JSON 형식이 맞지 않아요. { 로 시작하는 묶음 하나를 붙여 넣어 주세요.'); }
    if (!d || typeof d !== 'object' || Array.isArray(d)) return fail('{ } 묶음 하나여야 해요.');
    var keys = ['doc_key', 'expected_version', 'expires_at', 'content'];
    var extra = Object.keys(d).filter(function (k) { return keys.indexOf(k) < 0; });
    if (extra.length) return fail('모르는 항목이 있어요: ' + extra.slice(0, 5).join(', ') + ' (request_id 는 화면이 붙여요)');
    if (typeof d.doc_key !== 'string' || !RE.hex32.test(d.doc_key)) return fail('doc_key 는 0x + 소문자 16진수 64자리여야 해요.');
    if (!isInt(d.expected_version, 1, SAFE)) return fail('expected_version 은 1 이상의 정수(다음 버전 번호)여야 해요.');
    if (!isInt(d.expires_at, 0, SAFE)) return fail('expires_at 은 초 단위 정수(유닉스 시각)여야 해요.');
    if (nowSec && d.expires_at <= nowSec) return fail('expires_at 이 이미 지난 시각이에요.');
    var c = d.content;
    if (!c || typeof c !== 'object' || Array.isArray(c)) return fail('content 는 { } 묶음이어야 해요.');
    var allow, check;
    if (c.notice_type === 'PAYMENT_REQUEST') {
      allow = ['notice_type', 'amount_minor', 'currency', 'payee_bank_name', 'payee_account_number', 'payee_account_holder', 'payment_purpose', 'due_at', 'official_url'];
      check = [
        [isInt(c.amount_minor, 1, SAFE), 'amount_minor 는 0보다 큰 정수예요.'],
        [typeof c.currency === 'string' && /^[A-Z]{3}$/.test(c.currency), 'currency 는 영문 대문자 3자(KRW 등)예요.'],
        [txt(c.payee_bank_name, 1, 120), 'payee_bank_name 은 1~120자예요.'],
        [typeof c.payee_account_number === 'string' && /^[0-9]{6,32}$/.test(c.payee_account_number.replace(/[ -]/g, '')), 'payee_account_number 는 숫자 6~32자리예요.'],
        [txt(c.payee_account_holder, 1, 120), 'payee_account_holder 는 1~120자예요.'],
        [txt(c.payment_purpose, 1, 500), 'payment_purpose 는 1~500자예요.'],
        [isInt(c.due_at, 0, SAFE), 'due_at 은 초 단위 정수예요.'],
        [httpsUrl(c.official_url), 'official_url 은 https 주소여야 해요.']
      ];
    } else if (c.notice_type === 'OFFICIAL_DOCUMENT') {
      allow = ['notice_type', 'institution_code', 'document_type', 'document_number', 'title', 'summary', 'official_url'];
      check = [
        [txt(c.institution_code, 1, 120), 'institution_code 는 1~120자예요.'],
        [txt(c.document_type, 1, 120), 'document_type 은 1~120자예요.'],
        [txt(c.document_number, 1, 120), 'document_number 는 1~120자예요.'],
        [txt(c.title, 1, 200), 'title 은 1~200자예요.'],
        [txt(c.summary, 1, 2000), 'summary 는 1~2000자예요.'],
        [httpsUrl(c.official_url), 'official_url 은 https 주소여야 해요.']
      ];
    } else return fail('content.notice_type 은 PAYMENT_REQUEST 또는 OFFICIAL_DOCUMENT 예요.');
    var bad = Object.keys(c).filter(function (k) { return allow.indexOf(k) < 0; });
    if (bad.length) return fail('content 에 모르는 항목이 있어요: ' + bad.slice(0, 5).join(', '));
    for (var i = 0; i < check.length; i++) if (!check[i][0]) return fail(check[i][1]);
    return { ok: true, body: { doc_key: d.doc_key, expected_version: d.expected_version, expires_at: d.expires_at, content: c } };
  }
  /* 철회 입력: "0x…(64) 버전" 또는 {"document_id","version"} */
  function parseRevoke(text) {
    var s = String(text || '').trim();
    var m = /^(0x[0-9a-fA-F]{64})\s+v?(\d{1,15})$/.exec(s);
    var d = null;
    if (m) d = { document_id: m[1].toLowerCase(), version: +m[2] };
    else { try { d = JSON.parse(s); } catch (e) { d = null; } }
    if (!d || typeof d !== 'object' || typeof d.document_id !== 'string' || !RE.hex32.test(d.document_id.toLowerCase())) return fail('문서 ID(0x + 16진수 64자리)와 버전을 "0x… 2" 처럼 넣어 주세요.');
    if (!isInt(d.version, 1, SAFE)) return fail('버전은 1 이상의 정수예요.');
    return { ok: true, body: { document_id: d.document_id.toLowerCase(), version: d.version } };
  }
  function parseTxHash(text) {
    var s = String(text || '').trim();
    if (!/^0x[0-9a-fA-F]{64}$/.test(s)) return fail('거래 해시는 0x + 16진수 64자리예요.');
    return { ok: true, value: s.toLowerCase() };
  }
  /* 연결 주소: 같은 출처 경로(/api 등) 또는 이 컴퓨터 주소만 */
  function parseBase(text) {
    var s = String(text || '').trim();
    if (/^\/(?!\/)[A-Za-z0-9._~-]{1,40}(\/[A-Za-z0-9._~-]{1,40}){0,3}$/.test(s)) return { ok: true, value: s.replace(/\/+$/, '') };
    var n = Hk.text ? Hk.text.normalizeServerUrl(s) : '';
    if (n && Hk.api && Hk.api.isLoopback(n)) return { ok: true, value: n };
    return fail('주소는 같은 출처 경로(예: /api) 또는 이 컴퓨터 주소(예: http://127.0.0.1:8000)만 받아요.');
  }

  var OP_STATUS = ['PENDING_SUBMISSION', 'SUBMITTED', 'CONFIRMED', 'FAILED', 'UNKNOWN'];
  function isOperation(x, id) { return !!x && typeof x === 'object' && RE.op.test(str(x.operation_id)) && OP_STATUS.indexOf(x.status) >= 0 && (id == null || x.operation_id === id); }

  /* ---------------- 서버 도우미 ---------------- */
  /* opts: { fetch, base('/api'), timeoutMs, opStore(sessionStorage 꼴), fileMode } */
  function createClient(opts) {
    var base = typeof opts.base === 'string' && opts.base ? opts.base : '/api';
    var timeout = opts.timeoutMs || 25000;
    var caller = Hk.api.makeCaller({ fetch: opts.fetch, base: base, csrf: csrf, serverUrl: '' });
    var inflight = {};     // 같은 요청이 진행 중이면 같은 약속을 돌려줌(두 번 보내지 않음)
    var keepId = {};       // 결과가 불확실했던 요청은 같은 request_id 를 다시 씀(서버가 기존 결과를 돌려줌)
    var deleted = {};      // 사용자가 지운 분석 번호
    // request_id: session.js(req_ + UUID 32자리), 그게 안 되는 환경이면 api_adapter.js rid(req_jjin_ + 16자리)
    function newId() { try { return Hk.session.requestId(); } catch (e) { return Hk.api.rid(); } }

    function call(method, path, body) { return caller.call(method, path, body, timeout); }
    function get(path) { return call('GET', path, null); }
    function csrf() {
      return get('/v1/auth/me').then(function (r) { return r.status === 200 && r.data && typeof r.data.csrf_token === 'string' ? r.data.csrf_token : null; });
    }
    function say(res) { return explain(res, { fileMode: opts.fileMode }); }

    /* 쓰기: request_id 를 붙임. key 가 같으면(같은 경로·같은 본문) 진행 중 요청을 다시 보내지 않음 */
    function write(method, path, body, o) {
      o = o || {};
      var key = o.key || method + ' ' + path + ' ' + JSON.stringify(body == null ? null : body);
      if (inflight[key]) return inflight[key];
      var rid = null;
      var payload = body;
      if (o.requestId !== false && body != null) {
        rid = keepId[key] || newId();
        payload = {};
        Object.keys(body).forEach(function (k) { payload[k] = body[k]; });
        payload.request_id = rid;
      }
      var p = call(method, path, payload).then(function (res) {
        var e = say(res);
        res.request_id = rid;
        res.uncertain = !!e.uncertain;
        // 503 도 서버가 작업을 먼저 저장한 뒤 체인 조회에서 낼 수 있어 같은 번호로 재시도함(wallet_governance.py:273-274)
        if ((res.uncertain || res.status === 503) && rid) keepId[key] = rid; else delete keepId[key];
        delete inflight[key];
        return res;
      }, function (err) { delete inflight[key]; throw err; });
      inflight[key] = p;
      return p;
    }

    /* health: live·ready 를 함께 묻고 사람 말로 */
    function health() {
      return Promise.all([get('/health/live'), get('/health/ready')]).then(function (r) {
        var live = r[0], ready = r[1];
        var L = live.status === 200 && live.data && live.data.status === 'live'
          ? { ok: true, text: '서버 프로그램이 켜져 있어요.', code: 'HTTP 200' }
          : { ok: false, text: say(live).text || '서버 프로그램 상태를 확인하지 못했어요.', code: live.error ? live.error : 'HTTP ' + live.status };
        var R;
        if (ready.status === 200 && ready.data && ready.data.status === 'ready') R = { ok: true, text: '검증 서버가 준비돼 있어요.', code: 'HTTP 200' };
        else if (ready.status === 503 && detailOf(ready) === 'RUNTIME_NOT_READY') R = { ok: false, text: CODE_TEXT.RUNTIME_NOT_READY, code: 'HTTP 503 RUNTIME_NOT_READY' };
        else R = { ok: false, text: say(ready).text || '준비 상태를 확인하지 못했어요.', code: ready.error ? ready.error : 'HTTP ' + ready.status + (detailOf(ready) ? ' ' + detailOf(ready) : '') };
        return { live: L, ready: R, ok: L.ok && R.ok };
      });
    }

    /* ---- 보관/삭제 (D 계약) ---- */
    function isDeleted(id) { return deleted[id] === true; }
    function listAnalyses() { return get('/v3/analyses?limit=20'); }
    function guardRead(id, path) {
      if (!RE.ana.test(String(id))) return Promise.resolve({ status: 0, error: 'bad_id' });
      if (isDeleted(id)) return Promise.resolve({ status: 0, ignored: true });
      return get(path).then(function (res) { if (isDeleted(id)) return { status: 0, ignored: true }; return res; });
    }
    function report(id) { return guardRead(id, '/v3/analyses/' + id + '/report'); }
    function original(id) { return guardRead(id, '/v3/analyses/' + id + '/original'); }
    function analysis(id) { return guardRead(id, '/v3/analyses/' + id); }
    function removeAnalysis(id) {
      if (!RE.ana.test(String(id))) return Promise.resolve({ status: 0, error: 'bad_id' });
      deleted[id] = true;                       // 먼저 표시: 이 뒤에 오는 응답은 모두 버림
      return write('DELETE', '/v3/analyses/' + id, null, { requestId: false });
    }

    /* ---- 작업 이력(이 탭에서 만든 v3 작업 번호만, 비밀·본문 없음) ---- */
    var OPS_KEY = 'op5.ops.v1';
    function readOps() {
      var s = opts.opStore;
      try { var v = JSON.parse((s && s.getItem(OPS_KEY)) || '[]'); return Array.isArray(v) ? v.filter(function (x) { return x && RE.op.test(String(x.operation_id)); }).slice(0, 30) : []; } catch (e) { return []; }
    }
    function track(op, kind) {
      if (!op || !RE.op.test(String(op.operation_id))) return;
      var list = readOps().filter(function (x) { return x.operation_id !== op.operation_id; });
      list.unshift({ operation_id: op.operation_id, request_id: str(op.request_id).slice(0, 130), kind: str(kind).slice(0, 20), status: str(op.status).slice(0, 30), next_action: str(op.next_action).slice(0, 20), at: Date.now() });
      try { if (opts.opStore) opts.opStore.setItem(OPS_KEY, JSON.stringify(list.slice(0, 30))); } catch (e) { /* 저장 실패해도 화면은 계속 */ }
    }
    /* 성공 응답도 계약 OperationView 모양(같은 작업 번호·상태 값)일 때만 믿음. 아니면 error='bad_shape' */
    function checkOp(res, id) {
      if (res && !res.error && res.status >= 200 && res.status < 300 && !isOperation(res.data, id)) res.error = 'bad_shape';
      return res;
    }
    function operation(id) { return RE.op.test(String(id)) ? get('/v3/operations/' + id).then(function (r) { return checkOp(r, id); }) : Promise.resolve({ status: 0, error: 'bad_id' }); }
    function reconcile(id) { return RE.op.test(String(id)) ? write('POST', '/v3/operations/' + id + '/reconcile', null, { requestId: false }).then(function (r) { return checkOp(r, id); }) : Promise.resolve({ status: 0, error: 'bad_id' }); }
    /* 작업 결과 다루기: UNKNOWN 이면 다시 보내지 않고 reconcile 로 기존 거래부터 조회(계약 4번).
       복구 조회가 실패하면 reconcileFailed=true, before 에 기존 작업(저장된 UNKNOWN 은 그대로) */
    function follow(res, kind) {
      if (!res || res.status < 200 || res.status >= 300) return Promise.resolve(res);
      if (checkOp(res).error) return Promise.resolve(res);
      track(res.data, kind);
      if (res.data.status !== 'UNKNOWN') return Promise.resolve(res);
      return reconcile(res.data.operation_id).then(function (r2) {
        r2.reconciled = true;
        r2.before = res.data;
        if (!r2.error && r2.status >= 200 && r2.status < 300) track(r2.data, kind);
        else r2.reconcileFailed = true;
        return r2;
      });
    }

    return {
      base: base, call: call, get: get, write: write, csrf: csrf, say: say, health: health,
      me: function () { return get('/v1/auth/me'); },
      login: function (username, password) {
        if (!txt(username, 1, 120) || typeof password !== 'string' || password.length < 1 || password.length > 256) return Promise.resolve({ status: 0, error: 'bad_input' });
        return call('POST', '/v1/auth/login', { username: username, password: password });
      },
      logout: function () { return write('POST', '/v1/auth/logout', {}, { requestId: false }); },
      listAnalyses: listAnalyses, analysis: analysis, report: report, original: original, removeAnalysis: removeAnalysis, isDeleted: isDeleted,
      readOps: readOps, track: track, operation: operation, reconcile: reconcile, follow: follow,
      pending: function () { return Object.keys(inflight).length; }
    };
  }

  /* ---------------- 기관 지갑 (window.ethereum) ----------------
     서버에는 서명(0x…)만 보내고 개인키·비밀 문구는 다루지 않음. EIP-712 형식은 계약 wallet_signatures.py EIP712_TYPES 그대로. */
  var EIP712_TYPES = {
    EIP712Domain: [{ name: 'name', type: 'string' }, { name: 'version', type: 'string' }, { name: 'chainId', type: 'uint256' }, { name: 'verifyingContract', type: 'address' }],
    Publish: [['action', 'uint8'], ['issuerId', 'bytes32'], ['docKey', 'bytes32'], ['documentId', 'bytes32'], ['version', 'uint64'], ['keyId', 'bytes32'], ['originalHash', 'bytes32'], ['protectedHash', 'bytes32'], ['contentSchema', 'bytes32'], ['signatureSchema', 'bytes32'], ['originalHashAlgorithm', 'uint8'], ['protectedHashAlgorithm', 'uint8'], ['issuedAt', 'uint64'], ['expiresAt', 'uint64'], ['nonce', 'uint256'], ['deadline', 'uint64']],
    Revoke: [['action', 'uint8'], ['issuerId', 'bytes32'], ['docKey', 'bytes32'], ['documentId', 'bytes32'], ['version', 'uint64'], ['keyId', 'bytes32'], ['nonce', 'uint256'], ['deadline', 'uint64']],
    KeyProof: [['action', 'uint8'], ['applicationId', 'bytes32'], ['issuerId', 'bytes32'], ['signer', 'address'], ['challengeNonce', 'bytes32'], ['deadline', 'uint64']]
  };
  function pairs(list) { return list.map(function (p) { return Array.isArray(p) ? { name: p[0], type: p[1] } : p; }); }
  function checkSigningRequest(sr, primary) {
    if (!sr || typeof sr !== 'object') return '서명 요청 응답이 비어 있어요.';
    if (!RE.wsr.test(str(sr.signing_request_id))) return '서명 요청 번호(signing_request_id) 형식이 맞지 않아요.';
    if (sr.primary_type !== primary) return '서명 종류가 ' + primary + ' 가 아니에요.';
    if (!sr.domain || sr.domain.name !== 'OriginProof' || sr.domain.version !== '1' || !RE.address.test(str(sr.domain.verifyingContract))) return '서명 domain 이 계약과 달라요.';
    if (!RE.address.test(str(sr.expected_signer))) return '서명할 지갑 주소(expected_signer)가 없어요.';
    if (!sr.message || typeof sr.message !== 'object') return '서명할 내용(message)이 없어요.';
    return '';
  }
  function typedData(sr) {
    var types = { EIP712Domain: pairs(EIP712_TYPES.EIP712Domain) };
    types[sr.primary_type] = pairs(EIP712_TYPES[sr.primary_type]);
    return { types: types, primaryType: sr.primary_type, domain: sr.domain, message: sr.message };
  }

  /* opts: { client, ethereum: () => window.ethereum } — 각 단계는 { ok, step, text, code, data } 를 돌려줌 */
  function createWallet(opts) {
    var client = opts.client;
    function eth() { try { return typeof opts.ethereum === 'function' ? opts.ethereum() : null; } catch (e) { return null; } }
    function no(step, code, text, data) { return { ok: false, step: step, code: code, text: text, data: data || null }; }
    function yes(step, text, data) { return { ok: true, step: step, text: text, data: data || null }; }
    function fromRes(step, res) { var e = client.say(res); return no(step, e.code, e.text, { status: res.status, retryAfter: e.retryAfter, request_id: res.request_id, uncertain: res.uncertain }); }

    function connect() {
      var w = eth();
      if (!w || typeof w.request !== 'function') return Promise.resolve(no('wallet', 'WALLET_REQUIRED', '브라우저 지갑이 필요해요. 이 브라우저에는 지갑(window.ethereum)이 없어요. 지갑 확장 프로그램을 켠 브라우저에서 다시 해 주세요.'));
      return Promise.resolve().then(function () { return w.request({ method: 'eth_requestAccounts' }); }).then(function (acc) {
        var a = Array.isArray(acc) ? str(acc[0]) : '';
        if (!RE.address.test(a)) return no('wallet', 'WALLET_NO_ACCOUNT', '지갑에서 계정을 받지 못했어요.');
        return yes('wallet', '지갑 연결: ' + a.slice(0, 6) + '…' + a.slice(-4), { account: a });
      }, function (e) {
        return no('wallet', e && e.code === 4001 ? 'WALLET_REJECTED' : 'WALLET_ERROR', e && e.code === 4001 ? '지갑에서 연결을 거절했어요.' : '지갑 연결 중 오류가 났어요.');
      });
    }
    function sign(sr, account) {
      var w = eth();
      if (!w || typeof w.request !== 'function') return Promise.resolve(no('sign', 'WALLET_REQUIRED', '브라우저 지갑이 필요해요.'));
      if (str(account).toLowerCase() !== str(sr.expected_signer).toLowerCase()) {
        return Promise.resolve(no('sign', 'SIGNER_MISMATCH', '연결한 지갑 주소가 서명 요청의 기관 지갑 주소와 달라요. 등록한 기관 지갑으로 바꿔 주세요.'));
      }
      return Promise.resolve().then(function () {
        return w.request({ method: 'eth_signTypedData_v4', params: [account, JSON.stringify(typedData(sr))] });
      }).then(function (sig) {
        if (!RE.sig.test(str(sig))) return no('sign', 'BAD_SIGNATURE_SHAPE', '지갑이 돌려준 서명 형식이 맞지 않아요.');
        return yes('sign', '지갑 서명 받음(서명 값만 서버로 보내요)', { signature: str(sig).toLowerCase() });
      }, function (e) {
        return no('sign', e && e.code === 4001 ? 'WALLET_REJECTED' : 'WALLET_ERROR', e && e.code === 4001 ? '지갑에서 서명을 거절했어요.' : '지갑 서명 중 오류가 났어요.');
      });
    }
    function draft(step, path, body, primary) {
      return client.write('POST', path, body).then(function (res) {
        if (res.status !== 201) return fromRes(step, res);
        var bad = checkSigningRequest(res.data, primary);
        if (bad) return no(step, 'UPSTREAM_SCHEMA_MISMATCH', bad);
        return yes(step, '서명 요청을 받았어요(' + res.data.signing_request_id + ')', { sr: res.data, request_id: res.request_id });
      });
    }
    function submitSigned(step, path, sr, signature, kind) {
      return client.write('POST', path, { signing_request_id: sr.signing_request_id, signature: signature }).then(function (res) {
        if (res.status !== 202 && res.status !== 200) return fromRes(step, res);
        return client.follow(res, kind).then(function (r2) { return opResult(step, r2, res); });
      });
    }
    function opResult(step, r2, first) {
      if (r2 && r2.reconcileFailed) {
        var failed = fromRes(step, r2);
        failed.text = '작업 ' + str(r2.before.operation_id) + ' · 상태 ' + str(r2.before.status) + ' · 복구 조회를 하지 못했어요. 거래를 다시 보내지 말고 같은 작업을 다시 조회해 주세요. ' + failed.text;
        failed.data.op = r2.before;
        return failed;
      }
      if (!r2 || r2.error || r2.status < 200 || r2.status >= 300) return fromRes(step, r2 || first);
      var op = r2.data || {};
      var t = '작업 ' + str(op.operation_id) + ' · 상태 ' + str(op.status) + ' · 다음 ' + str(op.next_action);
      if (r2.reconciled) t = '응답이 UNKNOWN 이라 다시 보내지 않고 복구 조회(reconcile)했어요. ' + t;
      if (op.status === 'PENDING_SUBMISSION') t += ' · 아직 확정이 아니에요(지갑 거래 제출 필요).';
      return yes(step, t, { op: op, reconciled: !!r2.reconciled });
    }

    /* 키 증명: 기관 신청 번호 → 지갑 연결 → key-challenges → 서명 → key-proofs */
    function keyProof(onStep) {
      var say = typeof onStep === 'function' ? onStep : function () {};
      var account;
      return client.get('/v1/issuer-applications/mine').then(function (res) {
        if (res.status !== 200) { var x = fromRes('application', res); say(x); return x; }
        var appId = res.data && res.data.application_id;
        if (!RE.app.test(str(appId))) { var y = no('application', 'APPLICATION_NOT_FOUND', '이 계정의 기관 신청 번호(app_…)를 찾지 못했어요.'); say(y); return y; }
        say(yes('application', '기관 신청 번호 확인: ' + appId));
        return connect().then(function (c) {
          say(c);
          if (!c.ok) return c;
          account = c.data.account;
          return draft('challenge', '/v3/key-challenges', { application_id: appId, signer: account }, 'KeyProof').then(function (d) {
            say(d);
            if (!d.ok) return d;
            return sign(d.data.sr, account).then(function (s) {
              say(s);
              if (!s.ok) return s;
              return client.write('POST', '/v3/key-proofs', { signing_request_id: d.data.sr.signing_request_id, signature: s.data.signature }).then(function (res2) {
                var r = res2.status === 200 ? yes('proof', '키 증명을 서버가 받았어요. 이제 운영자가 등록 제안을 준비해요.', res2.data) : fromRes('proof', res2);
                say(r);
                return r;
              });
            });
          });
        });
      });
    }
    /* 발행: document-drafts → 서명 → publications (거래 해시는 따로 submitTx) */
    function publish(draftBody, onStep) {
      var say = typeof onStep === 'function' ? onStep : function () {};
      return connect().then(function (c) {
        say(c);
        if (!c.ok) return c;
        return draft('draft', '/v3/document-drafts', draftBody, 'Publish').then(function (d) {
          say(d);
          if (!d.ok) return d;
          return sign(d.data.sr, c.data.account).then(function (s) {
            say(s);
            if (!s.ok) return s;
            return submitSigned('publication', '/v3/publications', d.data.sr, s.data.signature, 'publish').then(function (r) { r.sr = d.data.sr; say(r); return r; });
          });
        });
      });
    }
    function revoke(body, onStep) {
      var say = typeof onStep === 'function' ? onStep : function () {};
      return connect().then(function (c) {
        say(c);
        if (!c.ok) return c;
        return draft('revoke-draft', '/v3/revoke-drafts', body, 'Revoke').then(function (d) {
          say(d);
          if (!d.ok) return d;
          return sign(d.data.sr, c.data.account).then(function (s) {
            say(s);
            if (!s.ok) return s;
            return submitSigned('revocation', '/v3/revocations', d.data.sr, s.data.signature, 'revoke').then(function (r) { r.sr = d.data.sr; say(r); return r; });
          });
        });
      });
    }
    /* 지갑에서 보낸 거래 해시 알리기: signing-requests/{id}/transactions (같은 signing_request_id, 새 request_id) */
    function submitTx(signingRequestId, txHash, kind) {
      if (!RE.wsr.test(str(signingRequestId))) return Promise.resolve(no('tx', 'BAD_ID', '서명 요청 번호 형식이 맞지 않아요.'));
      var t = parseTxHash(txHash);
      if (!t.ok) return Promise.resolve(no('tx', 'BAD_TX_HASH', t.message));
      return client.write('POST', '/v3/signing-requests/' + signingRequestId + '/transactions', { signing_request_id: signingRequestId, tx_hash: t.value }).then(function (res) {
        if (res.status !== 202 && res.status !== 200) return fromRes('tx', res);
        return client.follow(res, kind || 'tx').then(function (r2) { return opResult('tx', r2, res); });
      });
    }
    return { connect: connect, sign: sign, keyProof: keyProof, publish: publish, revoke: revoke, submitTx: submitTx, typedData: typedData };
  }

  /* ---------------- 첨부: 문서 사진 → DOCUMENT_IMAGE 입력(#92) ----------------
     POST /v3/inputs 가 kind DOCUMENT_IMAGE(PNG·JPEG·WebP, 5MB 이하, image_base64)를 받는다(서버 기본 꺼짐 → 409 INPUT_SUPPORT_UNDECIDED).
     여기서는 파일을 base64 로 바꿔 돌려주기만 하고, 보내기는 api_adapter.check(…, { image }) 가 한다. PDF·음성은 받지 않는다. */
  var IMAGE_TYPES = ['image/png', 'image/jpeg', 'image/webp'];
  function uploadAttachment(file) {
    var name = file && typeof file.name === 'string' ? file.name : '';
    if (!file || IMAGE_TYPES.indexOf(file.type) < 0) return Promise.resolve({ ok: false, code: 'UNSUPPORTED_INPUT', name: name, text: '문서 사진(PNG·JPG·WebP)만 보낼 수 있어요.' });
    if (file.size > 5 * 1024 * 1024) return Promise.resolve({ ok: false, code: 'MALFORMED_INPUT', name: name, text: '사진이 5MB보다 커요.' });
    return new Promise(function (resolve) {
      var fr = new FileReader();
      fr.onload = function () { var u = String(fr.result || ''); resolve({ ok: true, name: name, image: { media_type: file.type, base64: u.slice(u.indexOf(',') + 1) } }); };
      fr.onerror = function () { resolve({ ok: false, code: 'MALFORMED_INPUT', name: name, text: '사진 파일을 읽지 못했어요.' }); };
      fr.readAsDataURL(file);
    });
  }

  // Connection captions follow received reports; prepared RAG is not a connection signal.
  function analysisCaption(answer) {
    if (answer && answer.sample) return '규칙·AI 위험 분석 · 예시 응답';
    if (!answer || answer.analysis_status !== 'COMPLETED' || !answer.ai_report) return '규칙·AI 위험 분석 · 서버 분석기 연결 전';
    var limits = Array.isArray(answer.ai_report.limitations) ? answer.ai_report.limitations : [];
    if (limits.some(function (x) { return typeof x === 'string' && x.indexOf('LLM_ANALYSIS_UNAVAILABLE:') === 0; })) return '규칙 검사 · AI 분석 사용 불가';
    if (limits.indexOf('MOCK_REPLAY_NOT_MODEL_PERFORMANCE') >= 0) return '규칙·AI 위험 분석 · 기록 응답';
    return '규칙·AI 위험 분석 · 서버 보고서';
  }
  Hk.op5 = {
    uploadAttachment: uploadAttachment,
    analysisCaption: analysisCaption,
    CODE_TEXT: CODE_TEXT, explain: explain, createClient: createClient, createWallet: createWallet,
    parseDraft: parseDraft, parseRevoke: parseRevoke, parseTxHash: parseTxHash, parseBase: parseBase,
    EIP712_TYPES: EIP712_TYPES, typedData: typedData, RE: RE
  };
})();
