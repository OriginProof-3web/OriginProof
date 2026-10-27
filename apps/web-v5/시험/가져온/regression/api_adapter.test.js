// node --test tools/api_adapter.test.js   (설치 없음, node 기본 모듈만)
// ApiAdapter 응답 -> 화면 변환 시험(T7) + 패널 갱신 순서·금액 비교 카드(T2).
// 응답은 OriginProof 저장소에서 옮긴 fixture(tools/fixtures/originproof/, 각 파일 _source 에 브랜치·경로·줄).
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { loadWeb, fixture, fakeFetch, noRaw, CODE_RE, BANNED, visibleTexts } = require('./_load.js');

const URL0 = 'http://127.0.0.1:8000';
const j = x => JSON.parse(JSON.stringify(x));

function api(Hk, route, more) {
  const f = fakeFetch(route);
  const a = Hk.createApiAdapter(Object.assign({ fetch: f, serverUrl: URL0, pollMs: 1, timeoutMs: 200 }, more || {}));
  return { a, f };
}
function screenChecks(a, where) {
  for (const t of visibleTexts(a)) {
    assert.ok(!CODE_RE.test(t), where + ' 화면 글에 영문 코드: ' + t);
    for (const w of BANNED) assert.ok(!t.includes(w), where + ' 금지 단어: ' + t);
  }
  assert.ok(!a.axes.some(x => x.axis === 'ai' && x.tone === 'ok'), where + ' AI 칸 초록');
  assert.ok(!a.staff.some(x => x.staff === 'ai' && x.tone === 'ok'), where + ' AI 말풍선 초록');
  assert.equal(a.staff.length, 7, where + ' 직원 7명');
}

test('v1 금액 변조 응답(e2e fixture): 판정은 응답 그대로, 원본 칸 불일치, 비교 카드는 확인 불가(숫자 없음)', async () => {
  const Hk = loadWeb();
  const input = fixture('v1_card_notice_amount_tampered.input.json');
  const resp = fixture('v1_verify_tampered.response.json');
  const { a, f } = api(Hk, url => url.endsWith('/v1/mvp/card-notices/verify') ? { status: 200, body: resp } : null);
  const ans = await a.check(JSON.stringify(input));
  // 요청: v1 경로 하나, 설명·기대값 키는 보내지 않음, confidence 필수 칸
  assert.equal(f.calls.length, 1);
  assert.equal(f.calls[0].url, URL0 + '/v1/mvp/card-notices/verify');
  const body = JSON.parse(f.calls[0].body);
  assert.equal(body.proof_id, 'prf_demo_001');
  assert.ok(!('source' in body.candidate) && !Object.keys(body.candidate).some(k => k.startsWith('expected_')));
  assert.equal(body.candidate.confidence, 1);
  // 판정 재계산 없음: 응답의 verification_status 그대로
  assert.equal(ans.verification_status, 'TAMPERED');
  assert.equal(ans.conclusion.badge.text, '원본과 다름');
  const orig = ans.axes.find(x => x.axis === 'original');
  assert.equal(orig.status, '불일치');
  assert.equal(orig.tone, 'fail');
  // 금액 필드가 응답에 없음 → 두 칸 모두 확인 불가, 숫자 0개(보낸 1,540,000 도 넣지 않음)
  assert.equal(orig.compare.length, 2);
  for (const c of orig.compare) {
    assert.match(c.value, /^확인 불가/);
    assert.ok(!/\d/.test(c.value), '비교 카드에 숫자: ' + c.value);
  }
  assert.ok(!JSON.stringify(orig).includes('1,540,000') && !JSON.stringify(orig).includes('1540000'));
  assert.equal(ans.staff.find(s => s.staff === 'original').bubble_key, 'original.changed');
  assert.match(ans.staff.find(s => s.staff === 'original').line2, /AMOUNT_MISMATCH/);
  screenChecks(ans, 'v1 변조');
});

test('금액 비교 카드: 응답에 금액 필드가 없으면 늘 확인 불가 — 다른 금액 넣어도 같은 결과(재계산·짐작 없음)', async () => {
  const Hk = loadWeb();
  const resp = fixture('v1_verify_tampered.response.json');
  const vals = [];
  for (const amt of [1, 85001, 999999999]) {
    const { a } = api(Hk, () => ({ status: 200, body: resp }));
    const ans = await a.check(JSON.stringify({ proof_id: 'prf_demo_001', amount_minor: amt, currency: 'KRW' }));
    vals.push(JSON.stringify(ans.axes.find(x => x.axis === 'original').compare));
  }
  assert.equal(new Set(vals).size, 1);
  assert.ok(!/\d/.test(vals[0]));
});

test('v3 재구성 응답(체인 없음 INCONCLUSIVE+CHAIN_UNAVAILABLE): v3 를 연결 전으로 보고 v1 로 넘어감, 결과는 v1 값', async () => {
  const Hk = loadWeb();
  const v3 = fixture('v3_verification_chain_unavailable.reconstructed.json');
  const v1 = fixture('v1_verify_tampered.response.json');
  const { a, f } = api(Hk, url => url.endsWith('/v3/verifications') ? { status: 200, body: v3 } : url.endsWith('/v1/mvp/card-notices/verify') ? { status: 200, body: v1 } : null);
  const ans = await a.check(JSON.stringify({ proof_id: 'prf_demo_001', document_id: '0x' + 'a'.repeat(64), amount_minor: 1540000 }));
  assert.deepEqual(f.calls.map(c => c.url.replace(URL0, '')), ['/v3/verifications', '/v1/mvp/card-notices/verify']);
  assert.equal(JSON.parse(f.calls[0].body).scope, 'ID_ONLY');
  assert.equal(ans.verification_status, 'TAMPERED');
  assert.ok(ans.details.some(d => d.label === 'v3 검증' && /연결 전/.test(d.value)));
  screenChecks(ans, 'v3→v1');
});

test('v3 재구성 응답만 있고 Proof ID 없음: 결과를 지어내지 않고 네 칸 연결 전', async () => {
  const Hk = loadWeb();
  const v3 = fixture('v3_verification_chain_unavailable.reconstructed.json');
  const { a, f } = api(Hk, () => ({ status: 200, body: v3 }));
  const ans = await a.check(JSON.stringify({ document_id: '0x' + 'b'.repeat(64) }));
  assert.equal(f.calls.length, 1);
  assert.equal(ans.verification_status, null);
  assert.equal(ans.conclusion.badge.text, '연결 전');
  for (const ax of ans.axes.slice(0, 3)) assert.equal(ax.status, '연결 전');
  screenChecks(ans, 'v3 연결 전');
});

test('v3 503 WALLET_REGISTRY_NOT_CONFIGURED: 연결 전 처리 후 v1', async () => {
  const Hk = loadWeb();
  const v1 = fixture('v1_verify_tampered.response.json');
  const { a } = api(Hk, url => url.endsWith('/v3/verifications') ? { status: 503, body: { detail: 'WALLET_REGISTRY_NOT_CONFIGURED' } } : { status: 200, body: v1 });
  const ans = await a.check(JSON.stringify({ proof_id: 'prf_demo_001', document_id: '0x' + 'c'.repeat(64), amount_minor: 1 }));
  assert.equal(ans.verification_status, 'TAMPERED');
});

test('AI: 재구성 분석 작업(FAILED+ANALYZER_UNAVAILABLE) → AI 칸 연결 전, 판정에 영향 없음', async () => {
  const Hk = loadWeb();
  const job = fixture('v3_analysis_job_analyzer_unavailable.reconstructed.json');
  const queued = Object.assign({}, job, { status: 'QUEUED', error_code: null });
  const { a } = api(Hk, (url, init) => {
    if (url.endsWith('/v3/inputs')) return { status: 201, body: { input_ref: 'inp_x1', expires_at: 1 } };
    if (url.endsWith('/v3/analyses') && init.method === 'POST') return { status: 202, body: queued };
    if (url.includes('/v3/analyses/ana_')) return { status: 200, body: job };
    return null;
  });
  const ans = await a.check('검증 링크 없는 문자예요. 연락 주세요.');
  const ai = ans.axes.find(x => x.axis === 'ai');
  assert.equal(ai.status, 'AI 분석 연결 전');   // T2(2026-10-27): ANALYZER_UNAVAILABLE 정직 표기
  assert.equal(ans.staff.find(s => s.staff === 'ai').line2, 'ANALYZER_UNAVAILABLE');
  assert.equal(ans.staff.find(s => s.staff === 'intake').bubble_key, 'intake.received');
  screenChecks(ans, 'AI 처리기 없음');
});

test('AI: 합성 보고서(DG01 HIGH) → 위험 신호, 인용은 화면에, 영문 등급 코드는 말풍선 2줄·자세히에만', async () => {
  const Hk = loadWeb();
  const rep = fixture('v3_analysis_report_DG01.synthetic.json').report;
  const done = { analysis_id: 'ana_dg01', status: 'COMPLETED', retain_report: false, retain_original: false, report: rep, error_code: null };
  const { a } = api(Hk, (url, init) => {
    if (url.endsWith('/v3/inputs')) return { status: 201, body: { input_ref: 'inp_x2', expires_at: 1 } };
    if (url.endsWith('/v3/analyses') && init.method === 'POST') return { status: 202, body: done };
    return null;
  });
  const ans = await a.check('합성 안내: 인증번호를 알려주세요.');
  const ai = ans.axes.find(x => x.axis === 'ai');
  assert.equal(ai.status, '위험 신호');
  assert.match(ai.body, /인증번호를 알려주세요/);
  assert.ok(!/HIGH|CAUTION/.test(ai.body + ai.note), 'AI 칸 본문·note 에 영문 등급 코드');
  assert.match(ans.staff.find(s => s.staff === 'ai').line2, /^HIGH/);
  screenChecks(ans, 'AI HIGH');
});

test('AI: 로그인 없이 401 → 연결 전(지어내지 않음)', async () => {
  const Hk = loadWeb();
  const { a } = api(Hk, url => url.endsWith('/v3/inputs') ? { status: 401, body: { detail: 'AUTH_REQUIRED' } } : null);
  const ans = await a.check('아무 문자');
  assert.equal(ans.axes.find(x => x.axis === 'ai').status, 'AI 분석 연결 전');   // T2: AI 칸 연결 전 표기
  assert.equal(ans.staff.find(s => s.staff === 'intake').bubble_key, 'common.not_connected');
});

test('v3 ErrorResponse 모양(합성 fixture)을 422 본문으로 받으면 판단 보류, 판정 값 없음', async () => {
  const Hk = loadWeb();
  const err = fixture('v3_error_response.synthetic.json').error;
  const { a } = api(Hk, () => ({ status: 422, body: err }));
  const ans = await a.check(JSON.stringify({ proof_id: 'prf_demo_001', amount_minor: 1 }));
  assert.equal(ans.verification_status, null);
  assert.equal(ans.conclusion.badge.text, '판단 보류');
  assert.ok(ans.details.some(d => /HTTP 422 · REQUEST_ID_CONFLICT/.test(d.value)));
  screenChecks(ans, '422');
});

test('T2 패널 갱신 순서 = 응답 도착 순서 (fixture 응답을 늦게/빨리 보내 확인)', async () => {
  const Hk = loadWeb();
  const v1 = fixture('v1_verify_tampered.response.json');
  // (가) 항목 입력: 접수·AI(분석 안 함)는 바로, 검증 응답은 30ms 뒤
  {
    const seen = [];
    const { a } = api(Hk, () => ({ status: 200, body: v1, delay: 30 }));
    const ans = await a.check(JSON.stringify({ proof_id: 'prf_demo_001', amount_minor: 1 }), { onStaff: o => seen.push(o.staff) });
    assert.deepEqual(seen, ['intake', 'ai', 'ledger', 'signature', 'original', 'status']);
    assert.deepEqual(j(ans.staff.map(s => s.staff)), [...seen, 'report']);
  }
  // (나) 자유 문자: 공식 기록 네 칸(링크 없음)은 바로, 접수는 /v3/inputs 답(20ms), AI 는 분석 결과(그 뒤)
  {
    const seen = [];
    const job = fixture('v3_analysis_job_analyzer_unavailable.reconstructed.json');
    const { a } = api(Hk, (url, init) => {
      if (url.endsWith('/v3/inputs')) return { status: 201, body: { input_ref: 'inp_o', expires_at: 1 }, delay: 20 };
      if (url.endsWith('/v3/analyses') && init.method === 'POST') return { status: 202, body: job, delay: 20 };
      return null;
    });
    const ans = await a.check('링크 없는 문자', { onStaff: o => seen.push(o.staff) });
    assert.deepEqual(seen, ['ledger', 'signature', 'original', 'status', 'intake', 'ai']);
    assert.deepEqual(j(ans.staff.map(s => s.staff)), [...seen, 'report']);
  }
  // (다) 분석 접수 실패가 먼저 와도 그 순서
  {
    const seen = [];
    const { a } = api(Hk, url => url.endsWith('/v3/inputs') ? { status: 409, body: { detail: 'INPUT_SUPPORT_UNDECIDED' }, delay: 5 } : null);
    await a.check('글', { onStaff: o => seen.push(o.staff) });
    assert.deepEqual(seen, ['ledger', 'signature', 'original', 'status', 'intake', 'ai']);
  }
});

test('개인정보: 서버로 보내는 글·답 전체에 원문 개인정보 없음', async () => {
  const Hk = loadWeb();
  const { a, f } = api(Hk, url => url.endsWith('/v3/inputs') ? { status: 401, body: { detail: 'AUTH_REQUIRED' } } : null);
  const raw = '급해 010-1234-5678 로 전화, 110-123-456789 로 입금, 주민 900101-1234567';
  const ans = await a.check(raw);
  for (const c of f.calls) noRaw(assert, c.url + c.body, '보낸 요청');
  noRaw(assert, JSON.stringify(ans), '답');
});
