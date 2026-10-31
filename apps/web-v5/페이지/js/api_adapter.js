/* 실제 서버 연결 어댑터 (A3).
   [5안 확장 2026-10-26 피터] web-2안 원본을 복사해 아래만 더함(원본은 그대로):
   - opts.base: 같은 출처 프록시 경로(기본 '/api') 또는 이 컴퓨터 주소. 이때는 web-2안 중계(X-Jjin-*) 대신
     로그인 쿠키(credentials)와 쓰기 요청의 X-CSRF-Token(opts.csrf 가 줌)을 씀.
   - opts.retain(): 분석 요청의 retain_report / retain_original 선택값.
   - opts.isDeleted(analysis_id): 사용자가 지운 분석이면 늦게 온 응답을 버림.
   - opts.onAnalysis(analysis_id): 분석 번호가 정해지는 순간 알림(삭제 단추용).
   - 401 로그인 필요 문구를 5안(로그인 화면 있음)에 맞게 opts.loginWhy 로 바꿀 수 있음.
   - SampleAdapter 와 같은 모양: check(text) -> Promise<Answer>. 입력 형식이 틀리면 Promise.reject({ userMessage }).
   - 응답 -> 화면은 웹_설계.md 4.1 직원별 대응표·1.8 칸별 상태대로만 옮김. 판정(verification_status 등)은 다시 계산하지 않음.
   - 근거: docs/_A1_엔드포인트_조사.md (v1 card-notices/verify 만 지금 쓸 수 있음, v3 는 기본 구성에서 연결 전).
   - fetch·시간·주소는 밖에서 받음(시험: tools/api_adapter.test.js 가 가짜 fetch 를 넣음).
   - 화면에 바로 보이는 글에는 영문 코드를 넣지 않고, 코드는 직원 말풍선 2줄(line2)과 '자세히'(details)에만 넣음. */
(function () {
  'use strict';
  var Hk = (window.Hk = window.Hk || {});

  var VERIFY_TIMEOUT_MS = 25000;     // 4.1 common.held_timeout "응답 없음(25초)"
  var HEALTH_TIMEOUT_MS = 8000;
  var POLL_MS = 2000;
  var POLL_LIMIT_MS = 200000;        // 2.4 P9 ANALYSIS_POLL_TIMEOUT
  var LOOPBACK = ['127.0.0.1', 'localhost', '[::1]'];

  /* ---------------- 4.1 말풍선 문구 (bubble_key -> [1줄, 모양]) ---------------- */
  var B = {
    'intake.fixture': ['시연 자료 받음', '확인됨'],
    'intake.received': ['접수했어요(1시간 보관)', '확인됨'],
    'common.not_connected': ['연결 전', '연결 전'],
    'common.held_timeout': ['응답 없음(25초), 판단 보류', '보류'],
    'common.held_error': ['응답 오류, 판단 보류', '보류'],
    'common.held_dependency': ['장애로 확인 못 함, 판단 보류', '보류'],
    'common.held_expired': ['입력 보관 시간이 지나 보류', '보류'],
    'ledger.recorded': ['발행 기록 있음', '확인됨'],
    'ledger.recorded_noblock': ['발행 기록 있음', '확인됨'],
    'ledger.not_found': ['장부에 이 기관/문서 기록이 없어요', '경고'],
    'ledger.unreachable': ['장부에 연결 못 함, 판단 보류', '보류'],
    'ledger.not_run': ['앞 단계에서 멈춰 확인 안 함', '해당 없음'],
    'signature.match': ['기관 서명과 일치', '확인됨'],
    'signature.mismatch': ['기관 서명과 달라요', '경고'],
    'signature.not_run': ['앞 단계에서 멈춰 확인 안 함', '해당 없음'],
    'signature.held': ['서명을 확인할 자료가 없어 보류', '보류'],
    'signature.no_source': ['확인할 원본 없음', '해당 없음'],
    'original.same': ['원본 그대로', '확인됨'],
    'original.changed': ['바뀐 곳: {필드}', '경고'],
    'original.changed_unknown': ['보호 항목 중 바뀐 곳이 있어요', '경고'],
    'original.no_source': ['확인할 원본 없음', '해당 없음'],
    'original.not_run': ['앞 단계에서 멈춰 확인 안 함', '해당 없음'],
    'original.held': ['원본 자료가 없어 비교 보류', '보류'],
    'status.active': ['현재 유효', '확인됨'],
    'status.key_compromised': ['서명 키가 유출 처리된 기관이에요', '경고'],
    'status.revoked': ['철회된 안내예요', '경고'],
    'status.issuer_suspended': ['이 기관은 정지된 상태예요', '경고'],
    'status.key_invalid': ['기관 서명 키가 유효하지 않아요', '경고'],
    'status.expired': ['기한이 지난 안내예요', '주의'],
    'status.superseded': ['새 버전 v{latest_version}이 있어요', '주의'],
    'status.held': ['현재 상태 판단 보류', '보류'],
    'status.no_source': ['확인할 원본 없음', '해당 없음'],
    'status.not_run': ['앞 단계에서 멈춰 확인 안 함', '해당 없음'],
    'ai.no_clear': ['뚜렷한 위험 신호는 못 찾았어요', '정보'],
    'ai.caution': ['주의: {quote}', '주의'],
    'ai.high': ['위험 신호: {quote}', '경고'],
    'ai.undetermined': ['판단하기 어려워요', '보류'],
    'ai.timeout': ['분석 시간이 초과돼 보류', '보류'],
    'ai.result_expired': ['결과 보관 시간이 지났어요', '보류'],
    'ai.cancelled': ['분석이 취소됐어요, 판단 보류', '보류'],
    'ai.failed': ['AI 분석 실패, 판단 보류', '보류'],     // 새 키(T2): 계약 실패 코드 중 제공처·형식 문제(아래 AI_FAIL)
    'report.ready': ['네 축 보고서를 정리했어요', '확인됨'],
    'ai.none': ['분석하지 않음', '해당 없음']      // 4.1 표에 없는 새 키(항목 입력은 문자 원문이 없음, 피터 A3)
  };
  var SHAPE_TONE = { '확인됨': 'ok', '경고': 'fail', '주의': 'caution', '정보': 'info', '해당 없음': 'none', '보류': 'pending', '연결 전': 'offline' };

  // 보류 사유 순위(4.1 "판단 보류 사유 우선순위", 작을수록 앞)
  var HOLD_RANK = {
    'common.held_timeout': 2, 'common.held_error': 2,
    'ledger.unreachable': 3, 'common.held_dependency': 3,
    'ai.timeout': 4, 'ai.failed': 4, 'common.held_expired': 5, 'ai.result_expired': 5, 'ai.cancelled': 6,
    'signature.held': 7, 'original.held': 7, 'status.held': 7
  };
  var HOLD_BODY = {
    'common.held_timeout': '서버가 25초 안에 답하지 않아 판단을 보류했어요.',
    'common.held_error': '서버 응답에 문제가 있어 판단을 보류했어요.',
    'ledger.unreachable': '장부에 연결하지 못해 판단을 보류했어요.',
    'common.held_dependency': '서버 쪽 장애로 확인하지 못해 판단을 보류했어요.',
    'ai.timeout': '분석 시간이 초과돼 판단을 보류했어요.',
    'ai.failed': 'AI 분석이 결과를 내지 못해 판단을 보류했어요.',
    'common.held_expired': '입력 보관 시간이 지나 판단을 보류했어요.',
    'ai.result_expired': '분석 결과 보관 시간이 지나 판단을 보류했어요.',
    'ai.cancelled': '분석이 취소돼 판단을 보류했어요.',
    'signature.held': '서명을 확인할 자료가 없어 판단을 보류했어요.',
    'original.held': '원본 자료가 없거나 일부만 비교해서 판단을 보류했어요.',
    'status.held': '현재 상태를 확인하지 못해 판단을 보류했어요.'
  };

  function T() { return Hk.text; }
  function has(list, v) { return Array.isArray(list) && list.indexOf(v) >= 0; }
  function str(v) { return v == null ? '' : String(v); }

  /* 직원 한 명의 말풍선. params 는 {필드}·{quote}·{latest_version} 자리에 넣을 값 */
  function obs(staff, key, line2, params, line3) {
    var row = B[key] || ['응답 오류, 판단 보류', '보류'];
    var line1 = row[0].replace(/\{([^}]+)\}/g, function (m, k) { return params && params[k] != null ? String(params[k]) : m; });
    var o = { staff: staff, bubble_key: key, line1: line1, line2: str(line2), shape: row[1], tone: SHAPE_TONE[row[1]] };
    if (staff === 'ai' && o.tone === 'ok') o.tone = 'info';
    if (line3) o.line3 = line3;
    return o;
  }
  function nameOf(o) {
    if (o && !o.name) (Hk.STAFF || []).forEach(function (s) { if (s.id === o.staff) o.name = s.name; });
    if (o && !o.name) o.name = o.staff;
    return o;
  }
  function kind(key) {
    if (key === 'common.not_connected') return 'offline';
    if (HOLD_RANK[key]) return 'held';
    if (/\.not_run$/.test(key)) return 'not_run';
    if (/\.no_source$/.test(key)) return 'no_source';
    return 'result';
  }
  function bestHold(keys) {
    return keys.filter(function (k) { return HOLD_RANK[k]; }).sort(function (a, b) { return HOLD_RANK[a] - HOLD_RANK[b]; })[0];
  }

  /* ---------------- 1.8 칸별 상태 ---------------- */
  var AX_OFFLINE = { status: '연결 전', tone: 'offline', icon: 'plug', body: '이 확인 기능은 아직 연결 전이에요.' };
  var AX_NOT_RUN = { status: '확인 안 함', tone: 'none', icon: 'dash', body: '앞 단계에서 멈춰 이 항목은 확인하지 않았어요.' };
  var AX_NO_SOURCE = { status: '확인할 원본 없음', tone: 'none', icon: 'dash', body: '비교할 원본이 없어서 확인하지 않았어요.' };
  function axHeld(key, extra) { return { status: '보류', tone: 'pending', icon: 'question', body: HOLD_BODY[key] + (extra ? ' ' + extra : '') }; }
  function axis(id, name, staff, s, more) {
    var a = { axis: id, name: name, status: s.status, tone: s.tone, icon: s.icon, body: s.body, staff: staff };
    for (var k in more || {}) a[k] = more[k];
    return a;
  }

  function officialAxis(L, S, holdExtra) {
    var keys = [L.bubble_key, S.bubble_key];
    var s;
    if (keys.indexOf('common.not_connected') >= 0) s = AX_OFFLINE;
    else if (L.bubble_key === 'ledger.not_found') s = { status: '기록 없음', tone: 'fail', icon: 'warn', body: '장부에서 이 기관 또는 이 문서의 발행 기록을 찾지 못했어요.' };
    else if (S.bubble_key === 'signature.mismatch') s = { status: '서명 불일치', tone: 'fail', icon: 'warn', body: '서명이 등록된 기관의 서명과 달라요.' };
    else if (bestHold(keys)) s = axHeld(bestHold(keys), holdExtra);
    else if (kind(L.bubble_key) === 'not_run' || kind(S.bubble_key) === 'not_run') s = AX_NOT_RUN;
    else if (kind(L.bubble_key) === 'no_source' || kind(S.bubble_key) === 'no_source') s = { status: '해당 없음', tone: 'none', icon: 'dash', body: '확인할 원본이 없어요.' };
    else s = { status: '확인됨', tone: 'ok', icon: 'check', body: '등록된 기관이 이 안내문을 발행한 기록이 있고, 서명도 그 기관 것이에요.' };
    return axis('official', '공식 발행', ['ledger', 'signature'], s);
  }

  function originalAxis(O, compare, sentCount, holdExtra) {
    var k = O.bubble_key;
    var s;
    var more = {};
    if (k === 'common.not_connected') s = AX_OFFLINE;
    else if (HOLD_RANK[k]) s = axHeld(k, holdExtra);
    else if (k === 'original.same') s = { status: '일치', tone: 'ok', icon: 'check', body: '받은 내용이 원본과 한 글자도 다르지 않아요.' + (sentCount ? ' (보낸 항목 ' + sentCount + '개 기준)' : '') };
    else if (k === 'original.changed') {
      s = { status: '불일치', tone: 'fail', icon: 'warn', body: O.line1 + '.' };
      if (compare) more.compare = compare;
    } else if (k === 'original.changed_unknown') s = { status: '불일치', tone: 'fail', icon: 'warn', body: '보호 항목 중 바뀐 곳이 있어요.' };
    else if (k === 'original.no_source') s = AX_NO_SOURCE;
    else s = AX_NOT_RUN;
    return axis('original', '원본 일치', ['original'], s, more);
  }

  function statusAxis(St, holdExtra) {
    var k = St.bubble_key;
    var map = {
      'status.active': { status: '유효', tone: 'ok', icon: 'check', body: '지금도 유효한 안내예요.' },
      'status.revoked': { status: '철회됨', tone: 'fail', icon: 'warn', body: '기관이 이 안내를 철회했어요.' },
      'status.superseded': { status: '새 버전 있음', tone: 'caution', icon: 'caution', body: St.line1.replace(/있어요$/, '있어요.') + ' 새 버전을 확인하세요.' },
      'status.issuer_suspended': { status: '기관 정지', tone: 'fail', icon: 'warn', body: '이 기관은 지금 정지 상태예요.' },
      'status.key_compromised': { status: '서명 키 유출', tone: 'fail', icon: 'warn', body: '이 기관의 서명 키가 유출 처리됐어요. 서명을 믿을 수 없어요.' },
      'status.key_invalid': { status: '서명 키 무효', tone: 'fail', icon: 'warn', body: '이 기관의 서명 키가 지금 유효하지 않아요.' },
      'status.expired': { status: '만료', tone: 'caution', icon: 'caution', body: '유효기간이 지났어요.' },
      'status.no_source': AX_NO_SOURCE,
      'common.not_connected': AX_OFFLINE
    };
    var s = map[k] || (HOLD_RANK[k] ? axHeld(k, holdExtra) : AX_NOT_RUN);
    return axis('status', '현재 상태', ['status'], s);
  }

  function aiAxis(A, quote, llmUnran, why) {
    var k = A.bubble_key;
    var unran = llmUnran ? ' AI 상세 분석 미실행(규칙 검사 결과만)' : '';
    var map = {
      'ai.no_clear': { status: '뚜렷한 신호 없음', tone: 'info', icon: 'info', body: '뚜렷한 위험 신호는 못 찾았어요. 문제가 없다는 뜻은 아니에요.' + unran },
      'ai.caution': { status: '주의', tone: 'caution', icon: 'caution', body: '주의: ' + quote + unran },
      'ai.high': { status: '위험 신호', tone: 'fail', icon: 'warn', body: '위험 신호: ' + quote + unran },
      'ai.undetermined': { status: '판단하기 어려움', tone: 'pending', icon: 'question', body: 'AI가 판단하기 어려운 내용이에요.' + unran },
      'common.not_connected': { status: 'AI 분석 연결 전', tone: 'offline', icon: 'plug', body: 'AI 분석은 아직 연결 전이에요.' + (why ? ' ' + why : '') }
    };
    var s = map[k] || (HOLD_RANK[k] ? axHeld(k, why) : { status: '확인 안 함', tone: 'none', icon: 'dash', body: why || '이 입력은 AI 분석을 하지 않았어요.' });
    return axis('ai', 'AI 위험', ['ai'], s, { note: 'AI는 설명만 하고 발행 여부를 판정하지 않아요.' });
  }

  /* ---------------- 1.8 검증 엔진 결과 문장 ---------------- */
  var VS = {
    VERIFIED: { text: "검증 엔진 기준으로 발행 기록·서명·원본이 맞아요. 지금도 유효한지는 '현재 상태' 칸을 보세요.", badge: { tone: 'info', icon: 'info', text: '발행 기록 확인' } },
    NOT_REGISTERED: { text: '장부에서 등록된 발행 기록을 찾지 못했어요.', badge: { tone: 'fail', icon: 'warn', text: '기록 없음' } },
    TAMPERED: { text: '원본과 다른 곳이 있어요.', badge: { tone: 'fail', icon: 'warn', text: '원본과 다름' } },
    INCONCLUSIVE: { text: '일부를 확인하지 못해 판단을 보류했어요.', badge: { tone: 'pending', icon: 'question', text: '판단 보류' } },
    ERROR: { text: '검증 중 오류가 나서 결과를 만들지 못했어요.', badge: { tone: 'pending', icon: 'question', text: '결과 없음' } }
  };
  /* 시연 표기 대응표(감사 T1 재작업, 3회차 멘토 명령 1 프리셋 ③). 이 상수가 대응의 유일한 출처.
     - 검증 엔진 값(verification_status)은 바꾸지 않음. 엔진에 UNVERIFIED 값은 없음(웹_설계.md 1.8: 5개만 정의).
     - 멘토 시연 대본의 'UNVERIFIED' = 엔진 NOT_REGISTERED(예: reason_codes ISSUER_NOT_FOUND).
     - 영문 코드라 화면에 바로 보이는 글에는 넣지 않고 '자세히'(details)에만 넣음(sample_tool.py (f), 재디자인_설계.md '자세히(영문 코드·내부값)').
       바로 보이는 표기는 위 VS 의 한국어('기록 없음')를 그대로 씀. */
  var DEMO_TERM = { NOT_REGISTERED: 'UNVERIFIED' };
  function demoTermRows(vs) {
    if (typeof vs !== 'string' || !Object.prototype.hasOwnProperty.call(DEMO_TERM, vs)) return [];
    return [{ label: '시연 표기', value: DEMO_TERM[vs] + ' (검증 엔진 값 ' + vs + '와 같은 뜻)' }];
  }
  var NEXT_DEFAULT = '링크를 누르거나 돈을 보내기 전에, 기관의 공식 전화번호로 직접 확인하세요.';
  var NEXT_BAD = '이 안내의 내용으로 돈을 보내지 마세요. 기관의 공식 전화번호로 직접 확인하세요.';

  /* ---------------- 입력 해석 ---------------- */
  var V1_FIELDS = ['issuer_name', 'masked_card', 'amount_minor', 'currency', 'merchant', 'approved_at', 'transaction_id'];
  var IGNORED_KEYS = /^(_source|source|expected_[a-z_]+)$/;     // 시험 자료의 설명·기대값: 서버에 보내지도, 판정에 쓰지도 않음
  var PROOF_ID_RE = /^prf_[A-Za-z0-9_-]{1,124}$/;
  var DOC_ID_RE = /^0x[0-9a-f]{64}$/;

  function fail(msg) { var e = new Error(msg); e.userMessage = msg; return e; }

  // 구조 입력(JSON): { proof_id, 후보 항목들 | candidate:{…}, document_id, version, protected_fields }
  function parseStructured(text) {
    var data;
    try { data = JSON.parse(text); } catch (e) { throw fail('JSON 형식이 맞지 않아요. 중괄호로 시작하는 입력은 항목 입력(JSON)으로 읽어요.'); }
    if (!data || typeof data !== 'object' || Array.isArray(data)) throw fail('항목 입력(JSON)은 { } 묶음 하나여야 해요.');
    var src = {};
    var ignored = [];
    Object.keys(data).forEach(function (k) {
      if (IGNORED_KEYS.test(k)) { ignored.push(k); return; }
      if (k === 'candidate' && data[k] && typeof data[k] === 'object' && !Array.isArray(data[k])) {
        Object.keys(data[k]).forEach(function (c) { src[c] = data[k][c]; });
        return;
      }
      src[k] = data[k];
    });
    var allowed = V1_FIELDS.concat(['proof_id', 'document_id', 'version', 'protected_fields']);
    var unknown = Object.keys(src).filter(function (k) { return allowed.indexOf(k) < 0; });
    if (unknown.length) throw fail('모르는 항목이 있어요: ' + unknown.slice(0, 5).join(', '));

    var out = { structured: true, ignored: ignored, candidate: {}, proofId: '', documentId: '', version: null, protectedFields: null };
    if (src.proof_id != null) {
      if (typeof src.proof_id !== 'string' || !PROOF_ID_RE.test(src.proof_id)) throw fail('proof_id 형식이 맞지 않아요. (prf_ 로 시작, 영문·숫자·_·- 만)');
      out.proofId = src.proof_id;
    }
    if (src.document_id != null) {
      if (typeof src.document_id !== 'string' || !DOC_ID_RE.test(src.document_id)) throw fail('document_id 형식이 맞지 않아요. (0x + 소문자 16진수 64자리)');
      out.documentId = src.document_id;
    }
    if (src.version != null) {
      if (typeof src.version !== 'number' || !Number.isInteger(src.version) || src.version < 1) throw fail('version 은 1 이상의 정수여야 해요.');
      out.version = src.version;
    }
    if (src.protected_fields != null) {
      var pf = src.protected_fields;
      if (typeof pf !== 'object' || Array.isArray(pf) || !Object.keys(pf).length) throw fail('protected_fields 는 비어 있지 않은 { } 묶음이어야 해요.');
      Object.keys(pf).forEach(function (k) {
        var v = pf[k];
        if (!/^[a-z_]{1,64}$/.test(k) || !(v === null || typeof v === 'string' || Number.isInteger(v))) throw fail('protected_fields 값은 글자·정수·null 만 쓸 수 있어요.');
      });
      out.protectedFields = pf;
    }
    V1_FIELDS.forEach(function (k) {
      var v = src[k];
      if (v == null) return;
      var ok = k === 'amount_minor' ? (Number.isInteger(v) && v > 0)
        : k === 'masked_card' ? (typeof v === 'string' && /^\d{4}$/.test(v))
        : k === 'currency' ? (typeof v === 'string' && /^[A-Z]{3}$/.test(v))
        : (typeof v === 'string' && v.trim().length > 0 && v.length <= 200);
      if (!ok) throw fail(k + ' 값의 형식이 맞지 않아요.');
      out.candidate[k] = v;
    });
    if (!out.proofId && !out.documentId) throw fail('항목 입력에는 proof_id 나 document_id 가 있어야 해요.');
    if (out.proofId && !out.documentId && !Object.keys(out.candidate).length) {
      // 빈 후보를 보내면 엔진은 비교할 항목이 없어 늘 통과시킴(verification.py _candidate_mismatch) → 보내지 않음
      throw fail('비교할 항목(금액·가맹점 등)을 하나 이상 넣어 주세요.');
    }
    return out;
  }

  function parse(text) {
    if (/^\s*\{/.test(text)) return parseStructured(text);
    var refs = T().findRefs(text);
    return { structured: false, refs: refs, first: refs[0] || null, text: text };
  }

  /* ---------------- 응답 -> 직원 말풍선 (v1) ---------------- */
  function mapV1(r) {
    var c = r.checks && typeof r.checks === 'object' ? r.checks : {};
    var rc = Array.isArray(r.reason_codes) ? r.reason_codes : [];
    var life = r.lifecycle_status || null;
    var repoDown = c.proof_repository === 'UNAVAILABLE';
    var notFound = has(rc, 'PROOF_NOT_FOUND');
    var chainDown = c.blockchain_reader === 'UNAVAILABLE' && has(rc, 'DEPENDENCY_UNAVAILABLE') && !life;
    var codes = rc.join(' · ');
    var dep = function (s) { return obs(s, 'common.held_dependency', repoDown ? 'proof_repository' : 'blockchain_reader'); };

    var L, S, O, St;
    if (repoDown) L = dep('ledger');
    else if (notFound || has(rc, 'ISSUER_NOT_FOUND') || c.issuer === 'NOT_FOUND') L = obs('ledger', 'ledger.not_found', codes);
    else if (chainDown) L = obs('ledger', 'ledger.unreachable', 'DEPENDENCY_UNAVAILABLE');
    else if (c.issuer === 'ACTIVE' || life === 'ISSUER_SUSPENDED') L = obs('ledger', 'ledger.recorded_noblock', '');
    else L = obs('ledger', 'ledger.not_run', '');

    if (repoDown) S = dep('signature');
    else if (notFound) S = obs('signature', 'signature.no_source', 'PROOF_NOT_FOUND');
    else if (c.signature === 'PASS') S = obs('signature', 'signature.match', 'key_id 응답에 없음 · 서명자 주소 연결 전');
    else if (c.signature === 'FAIL') S = obs('signature', 'signature.mismatch', codes);
    else if (chainDown) S = dep('signature');
    else S = obs('signature', 'signature.not_run', '');

    if (repoDown) O = dep('original');
    else if (notFound) O = obs('original', 'original.no_source', 'PROOF_NOT_FOUND');
    else if (c.payload_hash === 'FAIL') O = obs('original', 'original.changed_unknown', codes);
    else if (c.candidate_match === 'FAIL') {
      O = has(rc, 'AMOUNT_MISMATCH') ? obs('original', 'original.changed', 'AMOUNT_MISMATCH', { '필드': '금액' }) : obs('original', 'original.changed_unknown', codes);
    } else if (c.candidate_match === 'PASS') O = obs('original', 'original.same', '');
    else O = obs('original', 'original.not_run', '');

    // 4.4-1: checks.issuer 가 없으면 lifecycle_status 를 쓰지 않음(만료만 예외)
    if (repoDown) St = dep('status');
    else if (notFound) St = obs('status', 'status.no_source', 'PROOF_NOT_FOUND');
    else if (c.expiry === 'EXPIRED') St = obs('status', 'status.expired', 'PROOF_EXPIRED');
    else if (life === 'ISSUER_SUSPENDED') St = obs('status', 'status.issuer_suspended', 'ISSUER_SUSPENDED');
    else if (life === 'ISSUER_KEY_REVOKED') St = obs('status', 'status.key_invalid', 'ISSUER_KEY_REVOKED');
    else if (chainDown) St = dep('status');
    else if (!('issuer' in c)) St = obs('status', 'status.not_run', '');
    else if (life === 'ACTIVE' && c.issuer === 'ACTIVE') St = obs('status', 'status.active', 'ACTIVE');
    else if (life) St = obs('status', 'status.held', str(life));
    else St = obs('status', 'status.not_run', '');
    return { ledger: L, signature: S, original: O, status: St };
  }

  /* ---------------- 응답 -> 직원 말풍선 (v3) ---------------- */
  function mapV3(r) {
    var rc = Array.isArray(r.reason_codes) ? r.reason_codes : [];
    var vs = r.verification_status;
    var doc = r.document && typeof r.document === 'object' ? r.document : null;
    var chk = {};
    (Array.isArray(r.checks) ? r.checks : []).forEach(function (x) { if (x && x.name) chk[x.name] = x; });
    var st = function (n) { return chk[n] ? chk[n].status : 'NOT_RUN'; };
    var reasonOf = function (n) { return chk[n] && chk[n].reason_code ? chk[n].reason_code : ''; };
    var dep = has(rc, 'CHAIN_SNAPSHOT_UNAVAILABLE') || has(rc, 'CHAIN_UNAVAILABLE');
    var noDoc = vs === 'NOT_REGISTERED' || has(rc, 'DOCUMENT_NOT_REGISTERED');
    var depCode = has(rc, 'CHAIN_SNAPSHOT_UNAVAILABLE') ? 'CHAIN_SNAPSHOT_UNAVAILABLE' : 'CHAIN_UNAVAILABLE';
    // NOT_RUN 인 직원: 장애 > 엔진 보류(INCONCLUSIVE) > 앞 단계 중단 (4.1 우선순위)
    var notRun = function (s, heldKey) {
      if (dep) return obs(s, 'common.held_dependency', depCode);
      if (noDoc) return obs(s, s + '.no_source', 'DOCUMENT_NOT_REGISTERED');
      if (vs === 'INCONCLUSIVE' && heldKey) return obs(s, heldKey, rc.join(' · '));
      return obs(s, s + '.not_run', '');
    };
    var extra = rc.filter(function (x) { return /^(METADATA_|CHAIN_RECORD_MISMATCH)/.test(x); });

    var L;
    if (noDoc) L = obs('ledger', 'ledger.not_found', 'DOCUMENT_NOT_REGISTERED');
    else if (dep) L = obs('ledger', 'ledger.unreachable', depCode);
    else if (doc) L = obs('ledger', r.block_number ? 'ledger.recorded' : 'ledger.recorded_noblock', [r.block_number ? '블록 #' + r.block_number : ''].concat(extra).filter(Boolean).join(' · '));
    else L = obs('ledger', 'ledger.not_run', '');

    var S;
    var sig = st('signature');
    // G1: 서명자 주소는 응답에 없음 → key_id 만 보여 주고 주소는 연결 전(추가 호출 안 함)
    if (sig === 'PASSED') S = obs('signature', 'signature.match', 'key_id ' + (doc && doc.key_id ? doc.key_id : '없음') + ' · 서명자 주소 연결 전');
    else if (sig === 'FAILED') S = obs('signature', 'signature.mismatch', reasonOf('signature'));
    else if (sig === 'UNAVAILABLE') S = obs('signature', 'signature.held', reasonOf('signature'));
    else S = notRun('signature', 'signature.held');

    var O;
    var parts = ['protected_fields', 'content', 'original_hash'];
    var failed = parts.filter(function (n) { return st(n) === 'FAILED'; });
    if (failed.length) {
      var pf = chk.protected_fields;
      var codes = failed.map(reasonOf).filter(Boolean).join(' · ');
      O = pf && pf.status === 'FAILED' && pf.reason_code === 'PROTECTED_FIELDS_MISMATCH' && pf.field_path
        ? obs('original', 'original.changed', codes, { '필드': pf.field_path })
        : obs('original', 'original.changed_unknown', codes);
    } else if (st('protected_fields') === 'PASSED' || st('content') === 'PASSED') {
      O = obs('original', 'original.same', has(rc, 'CONTENT_PARTIALLY_COMPARED') ? 'CONTENT_PARTIALLY_COMPARED' : '');
    } else if (parts.some(function (n) { return st(n) === 'UNAVAILABLE'; })) {
      O = obs('original', 'original.held', rc.join(' · '));
    } else O = notRun('original', 'original.held');

    var Stt;
    var w = doc && Array.isArray(doc.warnings) ? doc.warnings : [];
    var state = doc ? doc.state : null;
    var cs = st('current_state');
    if (dep) Stt = obs('status', 'status.held', depCode);
    else if (!doc) Stt = notRun('status', 'status.held');
    else if (has(w, 'KEY_COMPROMISED')) Stt = obs('status', 'status.key_compromised', 'KEY_COMPROMISED');
    else if (state === 'REVOKED') Stt = obs('status', 'status.revoked', 'REVOKED');
    else if (has(w, 'ISSUER_SUSPENDED')) Stt = obs('status', 'status.issuer_suspended', 'ISSUER_SUSPENDED');
    else if (state === 'EXPIRED') Stt = obs('status', 'status.expired', 'EXPIRED');
    else if (state === 'SUPERSEDED') Stt = obs('status', 'status.superseded', 'state=SUPERSEDED · latestVersion=' + str(doc.latest_version), { latest_version: str(doc.latest_version) });
    else if (w.length) Stt = obs('status', 'status.held', w.join(' · '));     // 4.4-6
    else if (state === 'ACTIVE' && cs === 'PASSED') Stt = obs('status', 'status.active', 'ACTIVE');                                 // 4.4-2
    else if (cs === 'UNAVAILABLE' || vs === 'INCONCLUSIVE') Stt = obs('status', 'status.held', reasonOf('current_state') || 'current_state=' + cs);
    else Stt = obs('status', 'status.not_run', '');
    return { ledger: L, signature: S, original: O, status: Stt };
  }

  /* ---------------- 분석 결과 -> AI 말풍선 ---------------- */
  /* AnalysisJob.error_code 전부(계약: OP-AI연결-준비 apps/api/src/originproof_api/wallet_analyses.py process()·finish()·cleanup()).
     [말풍선 키, 쉬운 말(문구안 — 대표 확정 필요)]. 표에 없는 코드는 common.held_error + 코드 그대로(지어내지 않음). */
  var AI_FAIL = {
    ANALYZER_UNAVAILABLE: ['common.not_connected', '서버에 분석 처리기가 없어요.'],
    ANALYSIS_TIMEOUT: ['ai.timeout', '접수 후 180초 안에 끝나지 않았어요.'],
    TIMEOUT: ['ai.timeout', 'AI 제공처가 제한 시간 안에 답하지 않았어요.'],
    INPUT_EXPIRED: ['common.held_expired', ''],
    WORKER_STOPPED: ['common.held_dependency', '서버의 분석 작업이 중간에 멈췄어요.'],
    PROCESS_RESTARTED: ['common.held_dependency', '분석 중에 서버가 다시 시작됐어요.'],
    PROVIDER_UNAVAILABLE: ['common.held_dependency', 'AI 제공처에 연결하지 못했어요.'],
    RATE_LIMIT: ['ai.failed', 'AI 제공처의 요청 한도에 걸렸어요. 잠시 뒤 다시 해 보세요.'],
    REFUSAL: ['ai.failed', 'AI가 이 글의 분석을 거절했어요.'],
    INCOMPLETE_OUTPUT: ['ai.failed', 'AI 답이 끝까지 오지 않았어요.'],
    SCHEMA_MISMATCH: ['ai.failed', 'AI 답이 약속한 형식과 달라 쓰지 않았어요.'],
    ANALYZER_SCHEMA_MISMATCH: ['ai.failed', 'AI 답이 약속한 형식과 달라 쓰지 않았어요.'],
    GROUNDING_MISMATCH: ['ai.failed', 'AI가 든 근거 문장이 받은 글에서 확인되지 않아 결과를 쓰지 않았어요.'],
    ANALYZER_AUTHORITY_VIOLATION: ['ai.failed', 'AI 답에 발행 진위 판정 값이 들어 있어 결과를 쓰지 않았어요.'],
    LOW_CONFIDENCE: ['ai.failed', 'AI가 확신이 낮다고 답해 결과를 내지 않았어요.'],
    UNSUPPORTED_INPUT: ['ai.failed', '이 입력 형식은 AI 분석이 지원하지 않아요.'],
    MALFORMED_INPUT: ['ai.failed', '입력 형식이 올바르지 않아 분석하지 못했어요.']
  };
  function mapAnalysisJob(job) {
    if (!job || typeof job !== 'object') return { obs: obs('ai', 'common.held_error', 'UPSTREAM_SCHEMA_MISMATCH') };
    var s = job.status;
    var ec = typeof job.error_code === 'string' ? job.error_code : '';
    if (s === 'COMPLETED' && job.report && typeof job.report === 'object') return mapReport(job.report);
    if (s === 'FAILED') {
      var f = Object.prototype.hasOwnProperty.call(AI_FAIL, ec) ? AI_FAIL[ec] : null;
      if (f) return { obs: obs('ai', f[0], ec), why: f[1] };
      return { obs: obs('ai', 'common.held_error', ec || 'FAILED'), why: ec ? '화면이 모르는 실패 코드예요. 자세히에서 코드를 확인하세요.' : '' };
    }
    if (s === 'EXPIRED') return { obs: obs('ai', 'ai.result_expired', 'EXPIRED') };
    if (s === 'CANCELLED') return { obs: obs('ai', 'ai.cancelled', 'CANCELLED') };
    return { obs: obs('ai', 'common.held_error', 'status=' + str(s)) };
  }
  /* 계약 AnalysisReport(wallet_contract.py 425-438)·AnalysisEvidence(407-422) 중 화면이 쓰는 것만 골라 옮김.
     모양이 틀린 근거 항목은 버리고(화면이 깨지지 않게), 몇 개 버렸는지 dropped 에 남김. 값은 바꾸지 않음. */
  function cleanReport(rep) {
    var dropped = 0;
    var ev = (Array.isArray(rep.evidence) ? rep.evidence : []).slice(0, 50).filter(function (e) {
      var ok = e && typeof e === 'object' && typeof e.quote === 'string' && e.quote.length > 0;
      if (!ok) dropped++;
      return ok;
    }).map(function (e) {
      return { rule_id: str(e.rule_id), quote: e.quote, start_offset: e.start_offset == null ? null : e.start_offset, end_offset: e.end_offset == null ? null : e.end_offset, source: str(e.source) };
    });
    return {
      risk_level: str(rep.risk_level), evidence: ev, dropped: dropped,
      limitations: (Array.isArray(rep.limitations) ? rep.limitations : []).slice(0, 20).map(str),
      verification_not_run_reason: rep.verification_not_run_reason == null ? null : str(rep.verification_not_run_reason)
    };
  }
  function mapReport(raw) {
    var rep = cleanReport(raw);
    var lim = rep.limitations;
    var rules = lim.filter(function (x) { return /^phishing-rules-/.test(x); })[0] || '';      // G4
    var unran = lim.some(function (x) { return /^LLM_ANALYSIS_UNAVAILABLE/.test(x); });
    var mock = has(lim, 'MOCK_REPLAY_NOT_MODEL_PERFORMANCE');
    var ev = rep.evidence[0] || null;
    var quote = ev ? T().maskPersonal(ev.quote).slice(0, 80) : '';
    var key = { NO_CLEAR_INDICATORS: 'ai.no_clear', CAUTION: 'ai.caution', HIGH: 'ai.high', UNDETERMINED: 'ai.undetermined' }[rep.risk_level];
    if (!key) return { obs: obs('ai', 'common.held_error', 'risk_level=' + rep.risk_level) };
    if ((key === 'ai.caution' || key === 'ai.high') && !quote) quote = '(근거 문장 없음)';
    var line3 = unran ? 'AI 상세 분석 미실행' : (mock ? '모의 응답' : '');
    return {
      obs: obs('ai', key, [rep.risk_level, rules].filter(Boolean).join(' · '), { quote: quote }, line3),
      quote: quote, unran: unran, report: rep,
      detail: 'risk_level=' + rep.risk_level + ' · evidence ' + rep.evidence.length + '건' + (rep.dropped ? '(모양 틀린 ' + rep.dropped + '건 버림)' : '') +
        rep.evidence.map(function (e, i) { return ' · [' + (i + 1) + '] source=' + e.source + ' rule_id=' + e.rule_id + ' offset=' + (e.start_offset == null ? '-' : e.start_offset + '~' + e.end_offset); }).join('') +
        (lim.length ? ' · limitations: ' + lim.join(' | ') : '') + (rep.verification_not_run_reason ? ' · verification_not_run_reason=' + rep.verification_not_run_reason : '')
    };
  }

  /* ---------------- AI 근거 위치(형광펜) ----------------
     계약: AnalysisEvidence.start_offset·end_offset 은 서버가 받은 글(이 화면이 보낸 '개인정보 가린 글' = 답의 input.text)의
     파이썬 str 위치 = 유니코드 코드포인트 단위, end 미포함, text[start:end] == quote (wallet_analyses.py ground_report 82줄).
     JS 문자열은 UTF-16 이라 코드포인트 → UTF-16 위치로 바꿔 씀. 두 값 다 없으면 서버와 같은 규칙(글 안에 딱 한 번 나올 때만)으로 찾음.
     한쪽만 있음·정수 아님·음수·역순·범위 밖·quote 불일치·겹침이면 칠하지 않고 skipped 에 사유를 남김(오류를 던지지 않음). */
  function cpTable(text) {      // 코드포인트 위치 i → UTF-16 위치. 길이 = 코드포인트 수 + 1
    var t = [0];
    for (var i = 0; i < text.length; i++) {
      var c = text.charCodeAt(i);
      if (c >= 0xd800 && c <= 0xdbff && i + 1 < text.length) { var d = text.charCodeAt(i + 1); if (d >= 0xdc00 && d <= 0xdfff) i++; }
      t.push(i + 1);
    }
    return t;
  }
  function evidenceSpans(text, evidence) {
    text = typeof text === 'string' ? text : '';
    var list = Array.isArray(evidence) ? evidence.slice(0, 50) : [];
    var table = null, found = [], skipped = [];
    list.forEach(function (e, i) {
      var q = e && typeof e.quote === 'string' ? e.quote : '';
      if (!q) return skipped.push({ index: i, reason: 'NO_QUOTE' });
      var s = e.start_offset, n = e.end_offset, a, b;
      if (s == null && n == null) {
        a = text.indexOf(q);
        if (a < 0) return skipped.push({ index: i, reason: 'QUOTE_NOT_FOUND' });
        if (text.indexOf(q, a + 1) >= 0) return skipped.push({ index: i, reason: 'QUOTE_NOT_UNIQUE' });
        b = a + q.length;
      } else {
        if (!Number.isInteger(s) || !Number.isInteger(n) || s < 0 || n < 0) return skipped.push({ index: i, reason: 'BAD_RANGE' });
        if (s >= n) return skipped.push({ index: i, reason: 'REVERSED' });
        table = table || cpTable(text);
        if (n > table.length - 1) return skipped.push({ index: i, reason: 'OUT_OF_RANGE' });
        a = table[s]; b = table[n];
        if (text.slice(a, b) !== q) return skipped.push({ index: i, reason: 'QUOTE_MISMATCH' });
      }
      found.push({ index: i, start: a, end: b, source: str(e.source), rule_id: str(e.rule_id) });
    });
    found.sort(function (x, y) { return x.start - y.start || x.index - y.index; });
    var spans = [], at = 0;
    found.forEach(function (sp) {
      if (sp.start < at) return skipped.push({ index: sp.index, reason: 'OVERLAP' });
      spans.push(sp); at = sp.end;
    });
    skipped.sort(function (x, y) { return x.index - y.index; });
    return { spans: spans, skipped: skipped };
  }
  var SPAN_WHY = { NO_QUOTE: '근거 문장 없음', QUOTE_NOT_FOUND: '받은 글에 없는 문장', QUOTE_NOT_UNIQUE: '같은 문장이 여러 번 있어 위치를 못 정함', BAD_RANGE: '위치 값 형식이 틀림', REVERSED: '위치 앞뒤가 바뀜', OUT_OF_RANGE: '위치가 글 길이를 넘음', QUOTE_MISMATCH: '위치의 글과 근거 문장이 다름', OVERLAP: '다른 근거와 위치가 겹침' };

  /* 분석 경로의 HTTP 오류 detail(계약: wallet_analyses.py input_text·analysis·job·report 의 HTTPException) → 쉬운 말(문구안).
     INPUT_SUPPORT_UNDECIDED 는 아래 fromErr 에서 '연결 전', INPUT_EXPIRED(410)은 errorInfo 에서 입력 보관 시간 보류로 감. */
  var AI_HTTP = {
    EMPTY_INPUT: '빈 글은 분석할 수 없어요.',
    INPUT_NOT_FOUND: '서버가 보낸 입력을 찾지 못했어요.',
    ANALYSIS_NOT_FOUND: '서버가 이 분석 기록을 찾지 못했어요.',
    INPUT_ALREADY_ANALYZED: '이미 분석을 맡긴 입력이에요.',
    REQUEST_ID_CONFLICT: '같은 요청 번호로 다른 내용이 들어왔어요.',
    ANALYSIS_LIMIT: '분석은 계정당 동시에 1건, 10분에 5건까지 받아요.',
    VERIFICATION_SESSION_NOT_FOUND: '연결할 검증 기록을 찾지 못했어요.',
    VERIFICATION_SESSION_EXPIRED: '연결할 검증 기록의 보관 시간이 지났어요.',
    RESULT_EXPIRED: '분석 결과 보관 시간이 지났어요.'
  };

  /* ---------------- 오류 응답 -> 말풍선 ---------------- */
  // res: call() 결과. 돌려줌: { key, line2, why(쉬운 말) }
  function errorInfo(res) {
    if (res.error === 'timeout') return { key: 'common.held_timeout', line2: 'UPSTREAM_TIMEOUT', why: '' };
    if (res.error === 'no_proxy') return { key: 'common.held_error', line2: 'NO_PROXY · HTTP ' + res.status, why: '이 페이지는 중계 프로그램 없이 열려 있어 서버에 보낼 수 없어요.' };
    if (res.error === 'proxy_unreachable') return { key: 'common.held_error', line2: 'UPSTREAM_UNAVAILABLE', why: '서버가 꺼져 있거나 주소가 틀렸어요.' };
    if (res.error === 'bad_url') return { key: 'common.held_error', line2: 'BAD_SERVER_URL', why: '서버 주소 형식이 맞지 않아요.' };
    if (res.error === 'target_not_allowed') return { key: 'common.held_error', line2: 'TARGET_NOT_ALLOWED', why: '이 컴퓨터(127.0.0.1·localhost) 주소로만 보낼 수 있어요.' };
    if (res.error === 'network') return { key: 'common.held_error', line2: 'NETWORK_ERROR · ' + str(res.detail), why: '서버에 닿지 못했어요. 서버가 꺼져 있거나, 브라우저가 다른 주소로 보내는 요청을 막았어요.' };
    var detail = res.data && (res.data.detail || res.data.error) ? str(res.data.detail || res.data.error) : '';
    var line2 = 'HTTP ' + res.status + (detail ? ' · ' + detail : '');
    if (res.status === 429) {
      var ra = res.retryAfter;
      return { key: 'common.held_error', line2: line2 + (ra ? ' · ' + ra + '초 뒤 가능' : ''), why: '요청이 많아 잠시 막혔어요.' + (ra ? ' ' + ra + '초 뒤에 다시 해 보세요.' : '') };
    }
    if (res.status === 410 && detail === 'INPUT_EXPIRED') return { key: 'common.held_expired', line2: line2, why: '' };
    if (res.status === 422) return { key: 'common.held_error', line2: line2, why: '보낸 항목 형식을 서버가 받지 않았어요.' };
    if (res.status >= 500) return { key: 'common.held_error', line2: line2, why: '서버가 지금 처리하지 못했어요.' };
    return { key: 'common.held_error', line2: line2 || 'UPSTREAM_SCHEMA_MISMATCH', why: '' };
  }

  /* ---------------- 주소·연결 ---------------- */
  function isLoopback(url) {
    var m = /^https?:\/\/([^/:]+|\[[^\]]+\])(:\d+)?$/.exec(url || '');
    return !!m && LOOPBACK.indexOf(m[1]) >= 0;
  }

  /* opts: { fetch, serverUrl, viaProxy, timeoutMs, healthTimeoutMs, pollMs, pollLimitMs, sleep, now } */
  function makeCaller(opts) {
    var fetchFn = opts.fetch;
    var serverUrl = T().normalizeServerUrl(opts.serverUrl || '');
    var sleep = opts.sleep || function (ms) { return new Promise(function (r) { setTimeout(r, ms); }); };

    var base = typeof opts.base === 'string' ? opts.base : null;   // 5안 확장
    function call(method, path, body, ms) {
      if (base != null) return callBase(method, path, body, ms);
      if (!serverUrl) return Promise.resolve({ error: 'bad_url' });
      if (!isLoopback(serverUrl)) return Promise.resolve({ error: 'target_not_allowed' });
      var url = opts.viaProxy ? '/api' + path : serverUrl + path;
      var headers = { Accept: 'application/json' };
      if (body != null) headers['Content-Type'] = 'application/json';
      if (opts.viaProxy) headers['X-Jjin-Target'] = serverUrl;
      var ctl = typeof AbortController === 'function' ? new AbortController() : null;
      var timer = null;
      var timedOut = false;
      var timeout = new Promise(function (resolve) {
        timer = setTimeout(function () { timedOut = true; if (ctl) ctl.abort(); resolve({ error: 'timeout' }); }, ms);
      });
      var req = Promise.resolve().then(function () {
        return fetchFn(url, { method: method, headers: headers, body: body == null ? undefined : JSON.stringify(body), signal: ctl ? ctl.signal : undefined, credentials: 'omit', redirect: 'error', cache: 'no-store' });
      }).then(function (res) {
        return Promise.resolve(res.text()).then(function (txt) {
          var data = null;
          try { data = JSON.parse(txt); } catch (e) { data = null; }
          var get = function (h) { try { return res.headers.get(h); } catch (e) { return null; } };
          var out = { status: res.status, data: data, retryAfter: get('Retry-After'), requestId: get('X-Request-ID') };
          if (opts.viaProxy && get('X-Jjin-Proxy') !== '1') { out.error = 'no_proxy'; return out; }
          var pe = data && data.proxy_error;
          if (pe === 'UPSTREAM_UNREACHABLE') out.error = 'proxy_unreachable';
          else if (pe === 'UPSTREAM_TIMEOUT') out.error = 'timeout';
          else if (pe === 'TARGET_NOT_ALLOWED') out.error = 'target_not_allowed';
          return out;
        });
      }, function (e) {
        return timedOut ? { error: 'timeout' } : { error: 'network', detail: e && e.name ? e.name : 'Error' };
      });
      return Promise.race([req, timeout]).then(function (r) { clearTimeout(timer); return r; });
    }
    /* 5안 확장: 같은 출처 /api(또는 이 컴퓨터 주소)로 로그인 쿠키와 함께 보냄. 쓰기(POST·DELETE)는 opts.csrf() 로 받은
       X-CSRF-Token 을 붙임(로그인·공개 검증 경로 제외). 토큰이 없으면(로그인 안 함) 보내지 않고 401 로 돌려줌. */
    function callBase(method, path, body, ms) {
      var headers = { Accept: 'application/json' };
      if (body != null) headers['Content-Type'] = 'application/json';
      var needCsrf = method !== 'GET' && path !== '/v1/auth/login' && path !== '/v3/verifications' && path !== '/v3/document-lookups' && path !== '/v1/mvp/card-notices/verify';
      var pre = needCsrf && typeof opts.csrf === 'function' ? Promise.resolve().then(opts.csrf) : Promise.resolve(null);
      return pre.then(function (token) {
        if (needCsrf && typeof opts.csrf === 'function' && !token) return { status: 401, data: { detail: 'AUTH_REQUIRED' }, local: true };
        if (token) headers['X-CSRF-Token'] = token;
        var ctl = typeof AbortController === 'function' ? new AbortController() : null;
        var timer = null;
        var timedOut = false;
        var timeout = new Promise(function (resolve) {
          timer = setTimeout(function () { timedOut = true; if (ctl) ctl.abort(); resolve({ error: 'timeout' }); }, ms);
        });
        var req = Promise.resolve().then(function () {
          return fetchFn(base + path, { method: method, headers: headers, body: body == null ? undefined : JSON.stringify(body), signal: ctl ? ctl.signal : undefined, credentials: /^\//.test(base) ? 'same-origin' : 'include', redirect: 'error', cache: 'no-store' });
        }).then(function (res) {
          return Promise.resolve(res.text()).then(function (txt) {
            var data = null;
            try { data = JSON.parse(txt); } catch (e) { data = null; }
            var get = function (h) { try { return res.headers.get(h); } catch (e) { return null; } };
            return { status: res.status, data: data, text: typeof txt === 'string' ? txt : '', contentType: get('Content-Type'), retryAfter: get('Retry-After'), requestId: get('X-Request-ID') };
          });
        }, function (e) {
          return timedOut ? { error: 'timeout' } : { error: 'network', detail: e && e.name ? e.name : 'Error' };
        });
        return Promise.race([req, timeout]).then(function (r) { clearTimeout(timer); return r; });
      });
    }
    return { call: call, serverUrl: base != null ? base : serverUrl, sleep: sleep, opts: opts };
  }

  /* 연결 확인: GET /health/ready. 돌려줌 { kind, ok, message, detail } */
  var READY_MSG = {
    ready: '연결됐어요. 검증 서버가 준비돼 있어요.',
    not_ready: '서버는 켜져 있지만 아직 준비가 안 됐어요. 준비 항목(장부 연결·계정 등)이 남아 있어요. 꺼진 것과는 달라요.',
    ready_failed: '서버는 응답했지만 준비 확인에 실패했어요. 서버 쪽 데이터베이스 등을 확인해 주세요.',
    unexpected: '서버가 예상과 다른 답을 보냈어요. 주소가 검증 서버가 맞는지 확인해 주세요.',
    slow: '서버가 제한 시간 안에 답하지 않았어요. 서버가 느리거나 멈춰 있을 수 있어요. 잠시 뒤 다시 눌러 보세요.',
    down: '서버에 연결하지 못했어요. 서버가 꺼져 있거나 주소가 틀렸어요. 주소와 서버 실행 여부를 확인해 주세요.',
    cors: '서버는 켜져 있지만 브라우저가 답을 읽지 못하게 막았어요(다른 주소 요청 차단). 중계 프로그램(tools/local_proxy.py)으로 이 페이지를 열어 주세요.',
    blocked_or_down: '서버에 닿지 못했어요. 서버가 꺼져 있거나, 브라우저가 다른 주소로 보내는 요청을 막았어요. 중계 프로그램(tools/local_proxy.py)으로 페이지를 열어 주세요.',
    no_proxy: '이 페이지는 중계 프로그램 없이 열려 있어요. tools/local_proxy.py 로 페이지를 열어 주세요.',
    target_not_allowed: '지금은 이 컴퓨터 주소(127.0.0.1·localhost)로만 연결할 수 있어요.',
    bad_url: '서버 주소 형식이 맞지 않아요. 예: http://127.0.0.1:8000'
  };
  /* 직접 연결에서 fetch 가 실패하면(TypeError) 꺼진 서버와 CORS 차단을 구별할 수 없음.
     그래서 같은 주소를 mode:'no-cors' 로 한 번 더 부름: 답(읽을 수 없는 응답)이 오면 서버는 켜져 있고
     브라우저가 막은 것(cors), 그것도 실패하면 꺼짐·주소 틀림(down). 본문은 읽지 않음. */
  function probeNoCors(opts, ms) {
    var url = T().normalizeServerUrl(opts.serverUrl || '') + '/health/ready';
    var timer = null;
    var timeout = new Promise(function (r) { timer = setTimeout(function () { r('down'); }, ms); });
    var req = Promise.resolve().then(function () {
      return opts.fetch(url, { method: 'GET', mode: 'no-cors', credentials: 'omit', cache: 'no-store' });
    }).then(function () { return 'cors'; }, function () { return 'down'; });
    return Promise.race([req, timeout]).then(function (k) { clearTimeout(timer); return k; });
  }

  function checkConnection(opts) {
    var c = makeCaller(opts);
    var ms = opts.healthTimeoutMs || HEALTH_TIMEOUT_MS;
    return c.call('GET', '/health/ready', null, ms).then(function (res) {
      if (res.error === 'network' && !opts.viaProxy) {
        return probeNoCors(opts, ms).then(function (k) { res.probe = k; return res; });
      }
      return res;
    }).then(function (res) {
      var k;
      if (res.error === 'timeout') k = 'slow';
      else if (res.error === 'network') k = res.probe || 'blocked_or_down';
      else if (res.error === 'proxy_unreachable') k = 'down';
      else if (res.error) k = res.error;
      else if (res.status === 200 && res.data && res.data.status === 'ready') k = 'ready';
      else if (res.status === 503 && res.data && res.data.detail === 'RUNTIME_NOT_READY') k = 'not_ready';     // G9
      else if (res.status === 500) k = 'ready_failed';
      else k = 'unexpected';
      var detail = res.error ? str(res.error) + (res.detail ? ' · ' + res.detail : '') + (res.probe ? ' · no-cors 재시도 ' + res.probe : '') : 'HTTP ' + res.status + (res.data && res.data.detail ? ' · ' + res.data.detail : '');
      return { kind: k, ok: k === 'ready', message: READY_MSG[k] || READY_MSG.unexpected, detail: detail, url: (opts.viaProxy ? '/api' : c.serverUrl) + '/health/ready' };
    });
  }

  function rid() {
    var s = '';
    try {
      var a = new Uint8Array(8);
      (self.crypto || window.crypto).getRandomValues(a);
      for (var i = 0; i < a.length; i++) s += ('0' + a[i].toString(16)).slice(-2);
    } catch (e) { s = Math.random().toString(36).slice(2, 14); }
    return 'req_jjin_' + s;
  }

  /* Track B(#88): 검증 코드 없는 문자에서 기관·금액·계좌(또는 공문 번호)를 읽어 POST /v3/document-lookups 본문을 만든다.
     기관 ID = identifier_hash("iss_…")(keccak256). 합성 명부(wallet_onboarding.ROSTER) 두 곳만 안다. 못 읽으면 null(보내지 않음). */
  var LOOKUP_ISSUERS = [
    { re: /origin\s*mock\s*bank|iss_origin_mock_bank/i, id: '0x9d6e623a821f35508c0c970540013aa75041537806d71a2e318ac7ca5358a217' },
    { re: /origin\s*mock\s*office|iss_origin_mock_office/i, id: '0xa079131abb1c9fafcee45cedda0cb5ae9a0aa8d8e2f3112e1ad0e85da89a9bbe' }
  ];
  /* 값을 고를 수 없으면 null(조회 안 함). 맞을 것 같은 일부 숫자를 보내지 않음: 틀린 값의 UNVERIFIED·다른 값의 MATCHED 모두 사실과 달라짐. */
  var LOOKUP_UNIT = '십백천만억조';
  var LOOKUP_RE = {
    hidden: /[­​-‏‪-‮⁠-⁤﻿]/,
    hangulAmount: new RegExp('(?:^|[^가-힣])[일이삼사오육칠팔구' + LOOKUP_UNIT + ']*[' + LOOKUP_UNIT + '][ \\t]?원'),
    foreignBefore: /(?:₩|￦|\$|€|¥|£|KRW|USD|EUR|JPY)[ \t]*$/i,
    foreignAfter: /^[ \t]*(?:KRW|USD|EUR|JPY|달러|유로|위안|파운드|엔(?![가-힣]))/i,
    unitAfter: new RegExp('^[ \\t]?[' + LOOKUP_UNIT + '][0-9,' + LOOKUP_UNIT + ' \\t]*원'),
    unitBefore: new RegExp('[' + LOOKUP_UNIT + '][ \\t]?$'),
    signBefore: /(?:[-−–—+△▲±~∼〜～]|\([-−+]\))[ \t]*$/,
    gluedBefore: /[A-Za-z_,.\/#]$/,
    approxBefore: /(?:약|최대|최소|최고|최저|대략|평균)[ \t]*$/,
    rangeAfter: /^[ \t]*(?:이상|이하|미만|초과|내외|가량|정도|상당|안팎|부터|까지|[-~∼〜～])/,
    wonEnd: /^(?:정|을|이|은|의|으로|입니다|이며|이고|이니|이므로|이에요|예요|임)?(?![가-힣A-Za-z0-9])/,
    won: /^[ \t ]*원/,
    amount: /^(?:[1-9][0-9]*|[1-9][0-9]{0,2}(?:,[0-9]{3})+)$/,
    payLabel: /(?:납부|납입|결제|청구|입금|이체|송금)[ \t]*(?:금액|액)[ \t]*(?:은|는|이|:|：|=)?[ \t]*$/,
    feeLabel: /(?:수수료|부가세|부가가치세|할인|연체료|가산금|이자|배송비)(?:[ \t]*(?:금액|액))?[ \t]*(?:은|는|이|:|：|=)?[ \t]*$/,
    accountLabel: /계좌(?:[ \t]*번호)?([^0-9]{0,15})$/,
    depositLabel: /입금[ \t]*[:：]?[ \t]*$/,
    notAccountGap: /문의|상담|연락|전화|콜센터|고객|아님|아닌|말고|이전|변경|잔액|만료|기한|일자/,
    gluedLeft: /[A-Za-z0-9_\-−–—－.,\/#]$/,
    gluedRight: /^(?:[A-Za-z_\-−–—－\/#]|[.,][0-9])/
  };
  function lookupDistinct(list) { return list.filter(function (x, i) { return list.indexOf(x) === i; }); }
  // 돌려줌: 금액(원) · 고를 수 없으면 null. found: 금액처럼 보이는 것이 하나라도 있으면 true(공문 판단에 씀)
  function lookupAmount(s) {
    var R = LOOKUP_RE, re = /[0-9](?:[0-9,.]*[0-9])?/g, m, bad = R.hangulAmount.test(s), pay = [], fee = [], other = [];
    while ((m = re.exec(s))) {
      var before = s.slice(0, m.index), after = s.slice(m.index + m[0].length);
      if (R.foreignBefore.test(before) || R.foreignAfter.test(after) || R.unitAfter.test(after)) { bad = true; continue; }
      var won = R.won.exec(after);
      if (!won) continue;
      var rest = after.slice(won[0].length), n = Number(m[0].replace(/,/g, ''));
      if (!R.amount.test(m[0]) || !Number.isSafeInteger(n) || R.unitBefore.test(before) || R.signBefore.test(before) || R.gluedBefore.test(before) ||
        R.approxBefore.test(before) || R.rangeAfter.test(rest) || !R.wonEnd.test(rest)) { bad = true; continue; }
      (R.payLabel.test(before) ? pay : R.feeLabel.test(before) ? fee : other).push(n);
    }
    var found = bad || pay.length + fee.length + other.length > 0;
    pay = lookupDistinct(pay); other = lookupDistinct(other);
    var value = null;
    if (!bad) {
      // 납부 표시가 하나면 수수료처럼 용도가 적힌 금액만 함께 허용, 표시가 없으면 금액이 한 가지이고 용도 금액이 없을 때만
      if (pay.length === 1 && other.every(function (x) { return x === pay[0]; })) value = pay[0];
      else if (!pay.length && !fee.length && other.length === 1) value = other[0];
    }
    return { value: value, found: found };
  }
  function lookupNotAccount(token, digits) {
    var mm = +digits.slice(4, 6), dd = +digits.slice(6, 8);
    if (/^(?:19|20)[0-9]{6}$/.test(digits) && /^[0-9]{4}-?[0-9]{1,2}-?[0-9]{1,2}$/.test(token) && mm >= 1 && mm <= 12 && dd >= 1 && dd <= 31) return true;   // 날짜
    if (/^(?:19|20)[0-9]{2}-[0-9]{1,2}-[0-9]{1,2}$/.test(token)) return true;
    if (/^01[016789][0-9]{7,8}$/.test(digits) || /^0(?:2|[3-6][1-5]|70|50[0-9])[0-9]{7,8}$/.test(digits) || /^1[5-9][0-9]{6}$/.test(digits)) return true;   // 전화
    return /^[0-9]{6}-[1-8][0-9]{6}$/.test(token) || /^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{4}$/.test(token);   // 주민번호·카드번호 모양은 보내지 않음
  }
  function lookupAccount(s) {
    var R = LOOKUP_RE, re = /[0-9][0-9-]*[0-9]/g, m, labelled = [], all = [];
    while ((m = re.exec(s))) {
      var t = m[0], digits = t.replace(/-/g, ''), before = s.slice(0, m.index), after = s.slice(m.index + t.length);
      if (digits.length < 6 || R.won.test(after)) continue;
      var a = R.accountLabel.exec(before);
      var isLabel = (a && !R.notAccountGap.test(a[1])) || R.depositLabel.test(before);
      var notAcc = lookupNotAccount(t, digits);
      var glued = R.gluedLeft.test(before) || R.gluedRight.test(after);
      if (isLabel && (notAcc || glued || digits.length > 32)) return null;
      if (notAcc) continue;
      all.push(digits);
      if (isLabel) labelled.push(digits);
    }
    labelled = lookupDistinct(labelled); all = lookupDistinct(all);
    return labelled.length === 1 && all.length === 1 ? labelled[0] : null;
  }
  // 돌려줌: undefined(공문 번호 표시 없음) · null(표시는 있으나 값을 못 정함) · 문자열
  function lookupDocNumber(s) {
    var re = /(?:공문|문서)[ \t]*번호/g, m, out = [];
    while ((m = re.exec(s))) {
      var after = s.slice(m.index + m[0].length).replace(/^\s*(?:는|은|:|：|=)?\s*/, '');
      var raw = /^[^\s,;()\[\]{}<>"'「」『』]*/.exec(after)[0];
      var token = raw.replace(/\.$/, '').replace(/(?:입니다|이에요|이며|이고|으로|로|을|를|임)$/, '');
      if (!/^[A-Za-z0-9가-힣][A-Za-z0-9가-힣_\-\/.]{0,119}$/.test(token) || !/[0-9]/.test(token)) return null;
      // '문서번호 2026 17' 처럼 띄어 쓴 번호일 수 있으면 앞 조각만 쓰지 않음(날짜는 제외)
      var next = /^\s+([0-9A-Za-z][0-9A-Za-z_\-\/.]*)(?=\s|$)/.exec(after.slice(raw.length));
      if (next && !/^(?:19|20)[0-9]{2}[-.\/][0-9]{1,2}[-.\/][0-9]{1,2}$/.test(next[1])) return null;
      out.push(token);
    }
    if (!out.length) return undefined;
    out = lookupDistinct(out);
    return out.length === 1 ? out[0] : null;
  }
  function lookupKey(text) {
    var s = String(text || '');
    var iss = LOOKUP_ISSUERS.filter(function (x) { return x.re.test(s); });
    if (iss.length !== 1) return null;
    if (LOOKUP_RE.hidden.test(s) || /\p{Nd}/u.test(s.replace(/[0-9]/g, ''))) return null;   // 전각·보이지 않는 글자가 숫자를 가르면 일부만 읽게 됨
    var amount = lookupAmount(s), doc = lookupDocNumber(s);
    if (doc !== undefined) {
      // 공문 번호와 납부 정보가 함께 있으면 번호만 맞춰 보고 다른 계좌를 놓칠 수 있어 고르지 않음
      if (doc === null || amount.found || /계좌|입금/.test(s)) return null;
      return { issuer_id: iss[0].id, key: { notice_type: 'OFFICIAL_DOCUMENT', document_number: doc } };
    }
    var digits = lookupAccount(s);
    if (amount.value === null || digits === null) return null;
    return { issuer_id: iss[0].id, key: { notice_type: 'PAYMENT_REQUEST', amount_minor: amount.value, currency: 'KRW', payee_account_number: digits } };
  }
  var LOOKUP_WHY = {
    UNVERIFIED: '문자에서 읽은 값으로 찾았지만 보관 중인 발행 기록과 맞는 것이 없어요. 가짜라는 뜻은 아니니 기관 공식 번호로 직접 확인해 주세요.',
    AMBIGUOUS: '문자에서 읽은 값과 맞는 발행 기록이 여러 개라 하나로 정하지 않았어요. 기관 공식 번호나 검증 링크로 다시 확인해 주세요.'
  };

  /* ---------------- ApiAdapter ---------------- */
  function createApiAdapter(opts) {
    var c = makeCaller(opts);
    var ms = opts.timeoutMs || VERIFY_TIMEOUT_MS;
    var pollMs = opts.pollMs || POLL_MS;
    var pollLimit = opts.pollLimitMs || POLL_LIMIT_MS;
    var now = opts.now || function () { return Date.now(); };
    var sample = Hk.sampleAdapter;

    // 검증: v3(문서 ID가 있을 때) -> 연결 전 신호면 v1 -> 그래도 없으면 연결 전
    function verify(p, log) {
      var tryV1 = function (v3note) {
        if (!p.proofId) return Promise.resolve({ kind: 'offline', why: v3note || '', reason: v3note ? 'V3_NOT_CONNECTED' : 'NO_PROOF_ID' });
        // confidence: 필수 칸(0~1), 판정에는 쓰이지 않음(verification.py). 항목 입력은 사람이 직접 넣은 값이라 1,
        // 자유 문자는 항목을 뽑지 않아 0 + missing_fields 에 7개 항목 전부(models.py CardPaymentNoticeCandidate)
        var cand = p.structured ? { confidence: 1 } : { confidence: 0, missing_fields: V1_FIELDS.slice() };
        Object.keys(p.candidate).forEach(function (k) { cand[k] = p.candidate[k]; });
        var body = { proof_id: p.proofId, request_id: rid(), candidate: cand };
        var sentKeys = Object.keys(p.candidate);
        log.push({ label: '보낸 요청', value: 'POST /v1/mvp/card-notices/verify · request_id ' + body.request_id + ' · proof_id ' + p.proofId + ' · 후보 항목 ' + (sentKeys.length ? sentKeys.join(', ') : '없음(비교 근거 없음)') });
        return c.call('POST', '/v1/mvp/card-notices/verify', body, ms).then(function (res) {
          if (!res.error && res.status === 200 && res.data && typeof res.data.verification_status === 'string') {
            return { kind: 'result', api: 'v1', data: res.data, res: res, v3note: v3note };
          }
          if (!res.error && res.status === 200) return { kind: 'error', err: { key: 'common.held_error', line2: 'UPSTREAM_SCHEMA_MISMATCH', why: '서버 응답 모양이 예상과 달라요.' }, res: res };
          return { kind: 'error', err: errorInfo(res), res: res };
        });
      };
      if (!p.documentId) return tryV1('');
      var body = { request_id: rid(), document_id: p.documentId, scope: p.protectedFields ? 'PROTECTED_FIELDS' : 'ID_ONLY' };
      if (p.version) body.version = p.version;
      if (p.protectedFields) body.candidate = p.protectedFields;
      log.push({ label: '보낸 요청', value: 'POST /v3/verifications · request_id ' + body.request_id + ' · scope ' + body.scope });
      return c.call('POST', '/v3/verifications', body, ms).then(function (res) {
        var d = res.data || {};
        if (!res.error && res.status === 503 && d.detail === 'WALLET_REGISTRY_NOT_CONFIGURED') {
          log.push({ label: 'v3 검증', value: '연결 전 · HTTP 503 WALLET_REGISTRY_NOT_CONFIGURED' });
          return tryV1('v3 검증은 장부 설정이 없어 연결 전이에요.');
        }
        if (!res.error && res.status === 200 && d.verification_status === 'INCONCLUSIVE' && has(d.reason_codes, 'CHAIN_UNAVAILABLE')) {
          log.push({ label: 'v3 검증', value: '연결 전 · INCONCLUSIVE + CHAIN_UNAVAILABLE · session ' + str(d.session_id) });
          return tryV1('v3 검증은 장부 연결부가 없어 연결 전이에요.');
        }
        if (!res.error && (res.status === 404 || res.status === 405)) {
          log.push({ label: 'v3 검증', value: '경로 없음 · HTTP ' + res.status });
          return tryV1('이 서버에는 v3 검증 경로가 없어요.');
        }
        if (!res.error && res.status === 200 && typeof d.verification_status === 'string') return { kind: 'result', api: 'v3', data: d, res: res };
        return { kind: 'error', err: errorInfo(res), res: res };
      });
    }

    // Track B: 코드 없는 문자 → POST /v3/document-lookups. 읽을 값이 없거나 경로가 없으면 기존처럼 'none'
    function lookup(text, log) {
      var k = lookupKey(text);
      if (!k) return Promise.resolve({ kind: 'none' });
      var body = { request_id: rid(), issuer_id: k.issuer_id, key: k.key };
      log.push({ label: '보낸 요청', value: 'POST /v3/document-lookups · request_id ' + body.request_id + ' · ' + k.key.notice_type });
      return c.call('POST', '/v3/document-lookups', body, ms).then(function (res) {
        var d = res.data || {};
        if (!res.error && (res.status === 404 || res.status === 405)) { log.push({ label: '원본 찾기', value: '경로 없음 · HTTP ' + res.status }); return { kind: 'none' }; }
        if (res.error || res.status !== 200 || typeof d.lookup_status !== 'string') return { kind: 'error', err: errorInfo(res), res: res };
        log.push({ label: '원본 찾기', value: d.lookup_status + ' · 일치 ' + str(d.match_count) + '건' + (d.reason_codes && d.reason_codes.length ? ' · ' + d.reason_codes.join(', ') : '') });
        if (d.lookup_status === 'MATCHED' && d.verification && typeof d.verification.verification_status === 'string') return { kind: 'result', api: 'v3', data: d.verification, res: res, lookup: d.lookup_status };
        if (!Object.prototype.hasOwnProperty.call(LOOKUP_WHY, d.lookup_status)) return { kind: 'error', err: { key: 'common.held_error', line2: 'UPSTREAM_SCHEMA_MISMATCH', why: '서버 응답 모양이 예상과 달라요.' }, res: res };
        return { kind: 'none', lookup: d.lookup_status, why: LOOKUP_WHY[d.lookup_status] };
      });
    }

    // AI: POST /v3/inputs -> POST /v3/analyses -> GET /v3/analyses/{id} 폴링. 로그인 없이 부르면 401 → 연결 전
    // onIntake: /v3/inputs 답이 오는 순간 접수 직원 말풍선을 넘김(직원 패널은 도착 순서대로 갱신)
    // image: { media_type, base64 } 이면 글 대신 문서 사진(DOCUMENT_IMAGE, #92)으로 접수
    function analyze(text, log, onIntake, image) {
      var offline = function (code, why) {
        return { ai: { obs: obs('ai', 'common.not_connected', code), why: why }, intake: obs('intake', 'common.not_connected', code) };
      };
      var fromErr = function (res, step) {
        var d = res.data || {};
        log.push({ label: 'AI ' + step, value: res.error ? str(res.error) : 'HTTP ' + res.status + (d.detail ? ' · ' + d.detail : '') });
        if (!res.error && (res.status === 401 || res.status === 403)) return offline(str(d.detail || res.status), opts.loginWhy || '분석은 로그인이 필요한데 이 화면은 로그인하지 않아요.');
        var known = !res.error && typeof d.detail === 'string' && Object.prototype.hasOwnProperty.call(AI_HTTP, d.detail);
        if (!res.error && (res.status === 404 || res.status === 405) && !known) return offline('ROUTE_MISSING', '이 서버에는 분석 경로가 없어요.');
        if (!res.error && res.status === 409 && d.detail === 'INPUT_SUPPORT_UNDECIDED') return offline('INPUT_SUPPORT_UNDECIDED', '서버가 입력 받기를 아직 켜지 않았어요.');
        var e = errorInfo(res);
        if (known) e.why = AI_HTTP[d.detail] + (res.status === 429 && res.retryAfter ? ' ' + res.retryAfter + '초 뒤에 다시 해 보세요.' : '');
        return { ai: { obs: obs('ai', e.key, e.line2), why: e.why }, intake: step === '입력' ? obs('intake', e.key, e.line2) : null };
      };
      var input;
      if (image) {
        input = { kind: 'DOCUMENT_IMAGE', image_media_type: image.media_type, image_base64: image.base64 };
        log.push({ label: '보낸 요청', value: 'POST /v3/inputs · 문서 사진 ' + image.media_type + ' ' + Math.round(image.base64.length * 3 / 4 / 1024) + 'KB' });
      } else {
        var masked = T().maskPersonal(text);
        input = { kind: 'TEXT', text: masked };
        log.push({ label: '보낸 요청', value: 'POST /v3/inputs · 개인정보를 가린 글 ' + masked.length + '자' });
      }
      return c.call('POST', '/v3/inputs', input, ms).then(function (res) {
        if (res.error || res.status !== 201 || !res.data || !res.data.input_ref) {
          var x0 = fromErr(res, '입력');
          if (onIntake) onIntake(x0.intake);
          return x0;
        }
        var intake = obs('intake', 'intake.received', 'input_ref ' + str(res.data.input_ref));
        if (onIntake) onIntake(intake);
        var keep = typeof opts.retain === 'function' ? (opts.retain() || {}) : {};   // 5안 확장: 보관 선택
        var body = { request_id: rid(), input_ref: res.data.input_ref, retain_report: keep.report === true, retain_original: keep.original === true, verification_session_id: null };
        return c.call('POST', '/v3/analyses', body, ms).then(function (r2) {
          if (r2.error || r2.status !== 202 || !r2.data) { var x = fromErr(r2, '접수'); x.intake = intake; return x; }
          var id = str(r2.data.analysis_id);
          if (!/^ana_[A-Za-z0-9_-]{1,128}$/.test(id)) return { ai: { obs: obs('ai', 'common.held_error', 'UPSTREAM_SCHEMA_MISMATCH') }, intake: intake };
          if (typeof opts.onAnalysis === 'function') { try { opts.onAnalysis(id, body); } catch (e) { /* 화면 오류가 요청을 멈추지 않게 */ } }
          // 5안 확장: 사용자가 지운 분석이면 늦게 온 응답은 쓰지 않음(서버도 CANCELLED 를 먼저 저장)
          var gone = function () { return typeof opts.isDeleted === 'function' && opts.isDeleted(id); };
          var dropped = function () {
            log.push({ label: 'AI 결과', value: 'analysis_id ' + id + ' · 사용자가 지움 · 늦은 응답 무시' });
            return { ai: { obs: obs('ai', 'ai.cancelled', 'DELETED_BY_USER'), why: '내가 지운 분석이라 늦게 온 결과는 쓰지 않았어요.' }, intake: intake, analysisId: id, deleted: true };
          };
          var deadline = now() + pollLimit;
          var done = function (job) {
            var m = mapAnalysisJob(job);
            log.push({ label: 'AI 결과', value: 'analysis_id ' + id + ' · status=' + str(job.status) + (job.error_code ? ' · ' + job.error_code : '') + (m.detail ? ' · ' + m.detail : '') });
            return { ai: m, intake: intake };
          };
          var loop = function (job) {
            if (gone()) return dropped();
            if (job && ['COMPLETED', 'FAILED', 'CANCELLED', 'EXPIRED'].indexOf(job.status) >= 0) { var out = done(job); out.analysisId = id; out.analysisStatus = String(job.status); return out; }
            if (now() >= deadline) {
              log.push({ label: 'AI 결과', value: 'analysis_id ' + id + ' · ANALYSIS_POLL_TIMEOUT' });
              return { ai: { obs: obs('ai', 'ai.timeout', 'ANALYSIS_POLL_TIMEOUT') }, intake: intake };
            }
            return c.sleep(pollMs).then(function () { return gone() ? null : c.call('GET', '/v3/analyses/' + id, null, ms); }).then(function (r3) {
              if (r3 === null || gone()) return dropped();
              if (r3.error || r3.status !== 200 || !r3.data) { var y = fromErr(r3, '조회'); y.intake = intake; return y; }
              return loop(r3.data);
            });
          };
          return loop(r2.data);
        });
      });
    }

    // 검증 결과 -> 기록관·감정사·대조관·상태 확인관 말풍선 (응답 값을 표대로 옮기기만 함)
    function fourOf(v, p) {
      var four;
      if (v.kind === 'result') {
        four = v.api === 'v1' ? mapV1(v.data) : mapV3(v.data);
        /* 비교 근거 없음: v1 은 비교할 후보 항목이 0개여도 candidate_match=PASS 를 줌(verification.py:76-80,
           _candidate_mismatch 는 모든 값이 None 이면 None). 응답에 무엇을 비교했는지가 없으므로 이 PASS 는
           근거가 아님 → 4.1 표의 기존 키 common.not_connected("연결 전")로 둠. verification_status 등 판정 값은 그대로. */
        if (v.api === 'v1' && !Object.keys(p.candidate || {}).length && four.original.bubble_key === 'original.same') {
          four.original = obs('original', 'common.not_connected', 'NO_COMPARISON_BASIS · candidate_match=' + str(v.data.checks && v.data.checks.candidate_match) + ' · 보낸 비교 항목 0개');
          four.original.noBasis = true;
        }
      }
      else if (v.kind === 'error') {
        four = {};
        ['ledger', 'signature', 'original', 'status'].forEach(function (s) { four[s] = obs(s, v.err.key, v.err.line2); });
      } else if (v.kind === 'none') {
        four = {
          ledger: obs('ledger', 'ledger.not_run', ''), signature: obs('signature', 'signature.no_source', ''),
          original: obs('original', 'original.no_source', ''), status: obs('status', 'status.no_source', '')
        };
      } else {
        four = {};
        ['ledger', 'signature', 'original', 'status'].forEach(function (s) { four[s] = obs(s, 'common.not_connected', v.reason); });
      }
      return four;
    }

    /* 금액 비교 카드: 응답이 준 금액만 씀. v1·v3 응답 스키마에는 원본 금액도 받은 금액도 없음
       (v1 VerificationResult: models.py:107-116, v3 VerificationResult: wallet_contract.py:369-396).
       그래서 두 칸 모두 "확인 불가". 보낸 후보 값은 서버가 확인해 준 값이 아니라 넣지 않고,
       필드 이름을 짐작해 읽지도 않음(응답에 금액 필드가 생기면 그 스키마 근거로 여기만 고침). */
    var COMPARE_NONE = '확인 불가 (응답에 금액이 없어요)';
    function compareOf() {
      return [
        { label: '원본 금액', value: COMPARE_NONE },
        { label: '받은 안내 금액', value: COMPARE_NONE, changed: true }
      ];
    }

    function build(text, p, v, four, a, log, order) {
      var holdExtra = v.kind === 'error' ? v.err.why : '';
      var ai = a.ai.obs;
      var report = obs('report', 'report.ready', v.kind === 'result' ? str(v.data.verification_status) : '');
      nameOf(report);
      // 직원 순서 = 답이 도착한 순서(order). 빠진 직원이 있으면(있으면 안 됨) 정해진 순서로 뒤에 붙임
      var staff = order.slice();
      [a.intake || obs('intake', p.structured ? 'intake.fixture' : 'common.not_connected', ''), four.ledger, four.signature, four.original, four.status, ai].forEach(function (o) {
        if (!staff.some(function (x) { return x.staff === o.staff; })) staff.push(nameOf(o));
      });
      staff.push(report);

      var compare = null;
      if (four.original.bubble_key === 'original.changed' && four.original.line2.indexOf('AMOUNT_MISMATCH') >= 0) compare = compareOf(v);
      var sent = p.structured ? Object.keys(p.candidate).length : 0;
      var axes = [
        officialAxis(four.ledger, four.signature, holdExtra),
        originalAxis(four.original, compare, v.kind === 'result' && v.api === 'v1' ? sent : 0, holdExtra),
        statusAxis(four.status, holdExtra),
        aiAxis(ai, a.ai.quote || '', a.ai.unran, a.ai.why || '')
      ];
      // 원본 찾기 MATCHED 는 문자에서 읽은 항목만 맞춘 것(서버 PARTIAL_COMPARISON): 문자 전체가 그 안내문이라고 말하지 않음
      if (v.lookup === 'MATCHED') {
        if (axes[0].tone === 'ok') axes[0].body = '문자에서 읽은 항목과 맞는 발행 기록과 기관 서명이 있어요. 문자 전체가 그 안내문이라는 뜻은 아니에요.';
        if (axes[2].tone === 'ok') axes[2].body = '찾은 발행 기록은 지금 유효해요. 문자의 나머지 내용은 확인하지 않았어요.';
      }
      if (four.original.noBasis) axes[1].body = '이 확인 기능은 아직 연결 전이에요. 받은 문자에서 비교할 항목을 뽑지 않아 원본과 맞춰 볼 근거가 없어요.';
      if (v.kind === 'offline') axes.slice(0, 3).forEach(function (x) {
        x.body = '이 확인 기능은 아직 연결 전이에요.' + (v.why ? ' ' + v.why : '');
      });
      if (v.kind === 'none') axes.slice(0, 3).forEach(function (x) {
        x.status = '확인할 수 없음'; x.tone = 'none'; x.icon = 'dash';
        x.body = v.why || (p.image ? '사진에서는 검증 링크를 읽지 않아 공식 기록과 맞춰 볼 수 없어요.' : '검증 링크가 없어 공식 기록과 맞춰 볼 수 없어요.');
      });

      var conclusion;
      var next = NEXT_DEFAULT;
      var vs = v.kind === 'result' ? v.data.verification_status : null;
      if (v.kind === 'result') {
        var m = VS[vs];
        conclusion = m ? { badge: m.badge, text: m.text } : { badge: { tone: 'none', icon: 'dash', text: '쉬운 설명 없음' }, text: '쉬운 설명이 없는 결과예요. 자세히에서 값을 확인하세요.' };
        // 1.8 합성 규칙 1: 발행 기록이 확인돼도 현재 상태 칸에 문제가 있으면 그 칸 배지를 앞에
        var sAx = axes[2];
        if (vs === 'VERIFIED' && (sAx.tone === 'fail' || sAx.tone === 'caution')) conclusion.badge = { tone: sAx.tone, icon: sAx.icon, text: sAx.status };
        if (vs === 'TAMPERED' || vs === 'NOT_REGISTERED' || axes.some(function (x) { return x.axis !== 'ai' && x.tone === 'fail'; })) next = NEXT_BAD;
      } else if (v.kind === 'error') {
        conclusion = { badge: { tone: 'pending', icon: 'question', text: '판단 보류' }, text: '서버 응답을 받지 못해 판단을 보류했어요.' + (v.err.why ? ' ' + v.err.why : '') };
      } else if (v.kind === 'none') {
        conclusion = { badge: { tone: 'none', icon: 'dash', text: '확인할 수 없음' }, text: v.why || '공식 기록으로 확인할 수 없는 문자예요.' };
      } else {
        conclusion = { badge: { tone: 'offline', icon: 'plug', text: '연결 전' }, text: v.reason === 'NO_PROOF_ID_IN_LINK'
          ? '검증 링크는 찾았지만 링크 안에 Proof ID가 없어 공식 기록을 확인하지 못했어요.'
          : '검증 엔진이 아직 연결 전이라 공식 기록을 확인하지 못했어요.' };
      }

      var details = [{ label: '연결 방식', value: typeof c.opts.base === 'string' ? '5안 연결 ' + c.opts.base + ' (로그인 쿠키·CSRF)' : (c.opts.viaProxy ? '중계 프로그램 /api → ' : '직접 → ') + c.serverUrl }];
      details.push({ label: '입력 종류', value: p.image ? '문서 사진' : p.structured ? '항목 입력(JSON)' : (p.first ? (p.first.type === 'proof' ? 'Proof ID 가 든 문자' : '검증 링크가 든 문자') : (v.lookup ? '코드 없는 문자(원본 찾기 ' + v.lookup + ')' : '문자')) });
      if (p.structured && p.ignored.length) details.push({ label: '보내지 않은 키', value: p.ignored.join(', ') });
      // 찾은 링크·Proof ID: 첫 번째만 쓰고, 나머지는 '더 찾은 … (쓰지 않음)'으로 자세히에만(adapter.js refDetails)
      if (!p.structured && p.refs.length) details = details.concat(Hk.refDetails({ refs: p.refs }));
      if (!p.structured && !p.refs.length) details.push({ label: '찾은 검증 링크·Proof ID', value: '없음' });
      if (v.kind === 'offline') details.push({ label: '검증 연결 상태', value: 'common.not_connected · ' + v.reason + (v.why ? ' · ' + v.why : '') });
      if (four.original.noBasis) details.push({ label: '원본 일치 근거', value: '없음 · ' + four.original.line2 + ' · 비교 없이 나온 값이라 일치로 보지 않음' });
      details = details.concat(log);
      if (v.kind === 'result') {
        var d = v.data;
        details.push({ label: '검증 엔진 결과', value: str(vs) + (v.api === 'v3' ? ' · ' + str(d.comparison_scope) : '') + ' (' + v.api + ')' });
        details.push({ label: 'reason_codes', value: (d.reason_codes || []).join(', ') || '없음' });
        if (v.api === 'v1') {
          details.push({ label: 'lifecycle_status', value: str(d.lifecycle_status) || '없음' });
          details.push({ label: 'checks', value: Object.keys(d.checks || {}).map(function (k) { return k + '=' + d.checks[k]; }).join(', ') });
        } else {
          details.push({ label: 'checks', value: (d.checks || []).map(function (x) { return x.name + '=' + x.status + (x.reason_code ? '(' + x.reason_code + ')' : ''); }).join(', ') });
          if (d.document) details.push({ label: 'document', value: 'state=' + str(d.document.state) + ' · warnings=' + (d.document.warnings || []).join('|') + ' · key_id=' + str(d.document.key_id) + ' · version=' + str(d.document.version) + '/' + str(d.document.latest_version) });
          details.push({ label: 'block_number', value: str(d.block_number) || '없음' });
        }
        details.push({ label: 'session_id · request_id', value: str(d.session_id) + ' · ' + str(d.request_id || (v.res && v.res.requestId) || '') });
        if (v.v3note) details.push({ label: 'v3 검증', value: v.v3note + ' 그래서 v1 결과를 씀' });
        details.push({ label: '쉬운 설명', value: VS[vs] ? VS[vs].text : '쉬운 설명 없음' });
      }
      if (v.kind === 'error') details.push({ label: '오류', value: v.err.line2 });

      return {
        id: 'api_' + Date.now().toString(36),
        analysis_id: a.analysisId || null,          // 5안 확장: 보관/삭제 단추용
        analysis_deleted: a.deleted === true,
        analysis_status: a.analysisStatus || null,
        label: '실제 서버 응답',
        sample: false,
        assumption: 'OriginProof 서버 응답을 웹_설계.md 4.1·1.8 표대로 옮겼어요. 판정 값은 서버가 준 그대로이고, 응답에 없는 값은 지어내지 않았어요.',
        verification_status: vs,
        input: p.image ? { kind: 'image', text: '' } : { kind: 'message', text: T().maskPersonal(text) },     // = 서버에 보낸 글(근거 위치의 기준 글)
        ai_report: a.ai.report || null,                                // 계약 AnalysisReport 중 화면용(cleanReport). 형광펜·근거 줄에 씀
        ref: p.first || null,
        // 체인에서 직접 확인(js/chain_check.js)이 비교할 서버 값: v3 응답의 document·chain_id·verifying_contract 만. 없으면 null
        chain_claim: v.kind === 'result' && v.api === 'v3' && Hk.chain ? Hk.chain.claimFrom(v.data) : null,
        conclusion: conclusion,
        axes: axes,
        next_action: { text: next },
        details: details,
        staff: staff
      };
    }

    /* opts.onStaff(obs): 직원 한 명의 결과가 정해지는 순간(응답이 도착한 순간) 부름.
       직원 패널은 이 순서대로 갱신하고, 돌려주는 답의 staff 도 같은 순서(기록 다시 보기도 그 순서). */
    function check(text, opts) {
      opts = opts || {};
      var p;
      if (opts.image) p = { structured: false, first: null, refs: [], image: true };   // 문서 사진: 검증 링크를 읽을 글이 없음
      else try { p = parse(text); } catch (e) { return Promise.reject(e); }
      var log = [];
      var order = [];
      var emit = function (o) {
        if (!o || order.some(function (x) { return x.staff === o.staff; })) return;
        order.push(nameOf(o));
        if (typeof opts.onStaff === 'function') { try { opts.onStaff(o); } catch (e) { /* 화면 오류가 요청을 멈추지 않게 */ } }
      };
      var vP;
      if (p.structured) { emit(obs('intake', 'intake.fixture', '')); vP = verify(p, log); }
      else if (p.first && p.first.proofId) {
        // 자유 문자: 첫 참조(Proof ID 또는 링크 안 Proof ID) 하나만 v1 검증에 보냄. 두 번째 이후 참조는 보내지 않고 자세히에만.
        // 문자에서 비교 항목은 뽑지 않음 → 후보 항목 0개, 원본 일치 칸은 fourOf 에서 "연결 전"(근거 없음)
        vP = verify({ structured: false, proofId: p.first.proofId, documentId: '', candidate: {} }, log);
      }
      else if (p.first) vP = Promise.resolve({ kind: 'offline', reason: 'NO_PROOF_ID_IN_LINK', why: '첫 번째 링크 안에 Proof ID가 없어 검증을 요청하지 않았어요.' });
      else if (p.image) vP = Promise.resolve({ kind: 'none' });
      else vP = lookup(text, log);
      var aP = p.structured
        ? Promise.resolve({ ai: { obs: obs('ai', 'ai.none', 'NO_TEXT'), why: '항목 입력에는 문자 원문이 없어 AI 분석은 하지 않았어요.' } })
        : analyze(text, log, emit, opts.image);
      var vDone = vP.then(function (v) {
        var four = fourOf(v, p.structured ? p : { candidate: {} });
        ['ledger', 'signature', 'original', 'status'].forEach(function (s) { emit(four[s]); });
        return { v: v, four: four };
      });
      var aDone = aP.then(function (a) { emit(a.intake); emit(a.ai.obs); return a; });
      return Promise.all([vDone, aDone]).then(function (r) { return build(text, p, r[0].v, r[0].four, r[1], log, order); });
    }

    return {
      mode: 'api',
      serverUrl: c.serverUrl,
      list: function () { return sample ? sample.list() : []; },
      get: function (id) { return sample ? sample.get(id) : null; },
      check: check
    };
  }

  Hk.createApiAdapter = createApiAdapter;
  Hk.checkConnection = checkConnection;
  Hk.DEMO_TERM = DEMO_TERM;
  Hk.demoTermRows = demoTermRows;
  Hk.api = { mapV1: mapV1, mapV3: mapV3, mapAnalysisJob: mapAnalysisJob, isLoopback: isLoopback, READY_MSG: READY_MSG, errorInfo: errorInfo, makeCaller: makeCaller, rid: rid,
    lookupKey: lookupKey, evidenceSpans: evidenceSpans, SPAN_WHY: SPAN_WHY, AI_FAIL: AI_FAIL, AI_HTTP: AI_HTTP };
})();
