// node --test tools/t1_free_input.test.js   (설치 없음, node 기본 모듈만. 외부 네트워크 호출 없음: fetch 는 가짜)
// 감사 재작업 T1: 자유 입력의 첫 참조(검증 링크 안 Proof ID 또는 Proof ID)로 실제 검증 요청(v1)을 보내는지.
//  (a) 참조 2개 이상 → 검증 요청 정확히 1회
//  (b) 검증 요청 본문·URL 에 첫 참조만, 두 번째 이후 참조 문자열 없음
//  (c) 두 번째 이후 참조는 '자세히'(details) 데이터에
//  (d) prf_demo_001 회귀: 인식 + 요청 1회
//  (e) 비교 근거 없는 응답 → 원본 일치 칸이 통과(일치·초록)가 아님
//  (f) 화면 판정 = 응답값 그대로(재계산 없음). 문장은 docs/웹_설계.md 1.8 표에서 직접 읽어 비교
// 응답 본문: v1 VerificationResult 모양(origin/integration packages/python/originproof_core/models.py:107-116)을 따른 합성 값.
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { loadWeb, fakeFetch, PII, noRaw, CODE_RE, BANNED, visibleTexts } = require('./_load.js');

const URL0 = 'http://127.0.0.1:8000';
const j = x => JSON.parse(JSON.stringify(x));   // vm 안 배열을 이쪽 배열로(deepStrictEqual 용)
const VERIFY_RE = /\/v1\/mvp\/card-notices\/verify$|\/v3\/verifications$|\/v2\/proofs\//;

// 합성 v1 응답(비교 항목 0개로 보냈을 때 엔진이 주는 모양: candidate_match=PASS, verification.py:76-80)
function v1(status, over) {
  return Object.assign({
    session_id: 'vsn_t1_synthetic',
    verification_status: status,
    lifecycle_status: 'ACTIVE',
    reason_codes: [],
    checks: { proof_repository: 'FOUND', payload_hash: 'PASS', expiry: 'PASS', candidate_match: 'PASS', issuer: 'ACTIVE', signature: 'PASS' },
    verified_at: '2026-10-19T00:00:00Z',
    request_id: 'req_t1_synthetic'
  }, over || {});
}

function setup(resp) {
  const Hk = loadWeb();
  const f = fakeFetch(url => {
    if (url.endsWith('/v3/inputs')) return { status: 401, body: { detail: 'AUTH_REQUIRED' } };
    if (url.endsWith('/v1/mvp/card-notices/verify')) return { status: 200, body: resp || v1('VERIFIED') };
    return null;
  });
  const a = Hk.createApiAdapter({ fetch: f, serverUrl: URL0, pollMs: 1, timeoutMs: 500 });
  return { Hk, a, f, verifyCalls: () => f.calls.filter(c => VERIFY_RE.test(c.url)) };
}

const FIRST = 'https://verify.example/p/prf_demo_001';
const SECOND = 'prf_a0ef1f66db9845ebb3ee2fe81c729136';
const THIRD = 'https://other.example/x/prf_Second_Link-02';
const MULTI = '카드 승인 안내 ' + FIRST + ' 확인, 또 ' + SECOND + ' 그리고 ' + THIRD + ' 문의 ' + PII.mobile;

test('(a)(b) 참조 3개: 검증 요청 정확히 1회, 본문·URL 에 첫 참조(prf_demo_001)만', async () => {
  const { a, verifyCalls } = setup();
  const ans = await a.check(MULTI);
  const calls = verifyCalls();
  assert.equal(calls.length, 1, '검증 요청 횟수');
  const c = calls[0];
  assert.equal(c.url, URL0 + '/v1/mvp/card-notices/verify');
  assert.equal(c.init.method, 'POST');
  const body = JSON.parse(c.body);
  assert.equal(body.proof_id, 'prf_demo_001');
  assert.match(body.request_id, /^req_[A-Za-z0-9_-]{1,124}$/);
  assert.deepEqual(Object.keys(body).sort(), ['candidate', 'proof_id', 'request_id']);
  // 비교 항목은 지어내지 않음: 후보는 confidence·missing_fields 뿐
  assert.deepEqual(Object.keys(body.candidate).sort(), ['confidence', 'missing_fields']);
  assert.equal(body.candidate.confidence, 0);
  for (const s of [SECOND, THIRD, 'prf_Second_Link-02', 'other.example', 'prf_a0ef']) {
    assert.ok(!c.body.includes(s), '검증 요청 본문에 두 번째 이후 참조: ' + s);
    assert.ok(!c.url.includes(s), '검증 요청 URL 에 두 번째 이후 참조: ' + s);
  }
  noRaw(assert, c.body, '검증 요청');
  assert.equal(ans.ref.proofId, 'prf_demo_001');
  assert.equal(ans.verification_status, 'VERIFIED');
});

test('(a)(b) 순서를 바꿔도 첫 참조만: Proof ID 먼저, 링크 뒤', async () => {
  const { a, verifyCalls } = setup();
  await a.check('먼저 ' + SECOND + ' 다음 ' + FIRST);
  const calls = verifyCalls();
  assert.equal(calls.length, 1);
  assert.equal(JSON.parse(calls[0].body).proof_id, SECOND);
  assert.ok(!calls[0].body.includes('prf_demo_001'));
});

test('(a) 첫 참조가 Proof ID 없는 링크면 검증 요청 0회, 두 번째 참조로 넘어가지 않음', async () => {
  const { a, verifyCalls } = setup();
  const ans = await a.check('https://nolink.example/abc 그리고 ' + SECOND);
  assert.equal(verifyCalls().length, 0);
  assert.equal(ans.conclusion.badge.text, '연결 전');
  assert.ok(ans.details.some(d => /^더 찾은 Proof ID 1/.test(d.label) && d.value === SECOND));
});

test('(c) 두 번째 이후 참조는 자세히 데이터에 "더 찾은 … (쓰지 않음)"으로', async () => {
  const { a } = setup();
  const ans = await a.check(MULTI);
  const d = ans.details;
  assert.ok(d.some(x => x.label === '확인에 쓸 링크' && x.value === FIRST));
  assert.ok(d.some(x => x.label === '링크 안 Proof ID' && x.value === 'prf_demo_001'));
  assert.ok(d.some(x => x.label === '더 찾은 Proof ID 1 (쓰지 않음)' && x.value === SECOND));
  assert.ok(d.some(x => x.label === '더 찾은 링크 2 (쓰지 않음)' && x.value === THIRD));
  assert.ok(d.some(x => x.label === '└ 링크 안 Proof ID' && x.value === 'prf_Second_Link-02'));
  // 화면에 바로 보이는 글(결론·칸·말풍선 1줄)에는 두 번째 이후 참조가 없음
  for (const t of visibleTexts(ans)) for (const s of [SECOND, THIRD]) assert.ok(!t.includes(s), '화면 글에 ' + s);
});

test('(d) prf_demo_001 회귀: 인식 + 검증 요청 1회 (단독·링크 안·문장부호 붙음)', async () => {
  const Hk = loadWeb();
  const T = Hk.text;
  assert.deepEqual(j(T.findRefs('번호 prf_demo_001 입니다').map(r => [r.type, r.value, r.proofId])), [['proof', 'prf_demo_001', 'prf_demo_001']]);
  assert.equal(T.findRefs('prf_demo_001.')[0].proofId, 'prf_demo_001');
  assert.equal(T.findRefs('(prf_demo_001)')[0].proofId, 'prf_demo_001');
  assert.equal(T.findRefs('번호prf_demo_001이에요')[0].proofId, 'prf_demo_001');
  assert.equal(T.findRefs(FIRST)[0].proofId, 'prf_demo_001');
  assert.equal(T.findRefs('https://v.example/check?proof=prf_demo_001&x=1')[0].proofId, 'prf_demo_001');
  // 대소문자 그대로(스키마가 대소문자를 구별)
  assert.equal(T.findRefs('prf_Demo_001')[0].proofId, 'prf_Demo_001');
  // 형식 밖: prf_ 만, 앞에 글자 붙음, 125자 이상은 잘라 쓰지 않음
  assert.deepEqual(j(T.findRefs('prf_ 와 xprf_demo_001')), []);
  assert.deepEqual(j(T.findRefs('prf_' + 'a'.repeat(125))), []);
  assert.equal(T.findRefs('prf_' + 'a'.repeat(124))[0].proofId.length, 128);
  for (const text of ['확인 prf_demo_001 부탁', FIRST + ' 이에요']) {
    const { a, verifyCalls } = setup();
    const ans = await a.check(text);
    const calls = verifyCalls();
    assert.equal(calls.length, 1, text);
    assert.equal(JSON.parse(calls[0].body).proof_id, 'prf_demo_001', text);
    assert.equal(ans.ref.proofId, 'prf_demo_001');
  }
});

test('(e) 비교 근거 없는 응답(candidate_match=PASS, 보낸 비교 항목 0개): 원본 일치 칸이 통과가 아님', async () => {
  const { a } = setup(v1('VERIFIED'));
  const ans = await a.check('확인 prf_demo_001');
  const ax = ans.axes.find(x => x.axis === 'original');
  assert.notEqual(ax.status, '일치');
  assert.notEqual(ax.tone, 'ok');
  assert.notEqual(ax.icon, 'check');
  assert.ok(['연결 전', '근거 없음'].includes(ax.status), ax.status);
  assert.match(ax.body, /근거가 없어요/);
  const st = ans.staff.find(x => x.staff === 'original');
  assert.notEqual(st.bubble_key, 'original.same');
  assert.notEqual(st.line1, '원본 그대로');
  assert.notEqual(st.tone, 'ok');
  assert.ok(ans.details.some(d => d.label === '원본 일치 근거' && /^없음/.test(d.value)));
  // 응답이 실제로 확인한 칸(공식 발행·현재 상태)은 응답대로
  assert.equal(ans.axes.find(x => x.axis === 'official').status, '확인됨');
  assert.equal(ans.axes.find(x => x.axis === 'status').status, '유효');
  // 화면 글 규칙(영문 코드·금지 단어 0)
  for (const t of visibleTexts(ans)) {
    assert.ok(!CODE_RE.test(t), '화면 영문 코드: ' + t);
    for (const w of BANNED) assert.ok(!t.includes(w), '금지 단어: ' + t);
  }
  noRaw(assert, JSON.stringify(ans), '답');
});

test('(e) 대조: 항목 입력(JSON)으로 비교 항목을 보내 PASS 면 그때만 "일치"', async () => {
  const { a } = setup(v1('VERIFIED'));
  const ans = await a.check(JSON.stringify({ proof_id: 'prf_demo_001', amount_minor: 154000 }));
  assert.equal(ans.axes.find(x => x.axis === 'original').status, '일치');
});

/* (f) 1.8 표를 문서에서 직접 읽음 */
function vsTable() {
  const md = fs.readFileSync(path.resolve(__dirname, '../../../..', 'docs', '웹_설계.md')   /* 5안: 해커톤 직원/docs 읽기만 */, 'utf8');
  const sec = md.split('### 1.8 ')[1].split('**`VERIFIED`가 실제로')[0];
  const t = {};
  for (const line of sec.split('\n')) {
    const m = /^\|\s*`([A-Z_]+)`\s*\|\s*(.+?)\s*\|\s*$/.exec(line);
    if (m) t[m[1]] = m[2];
  }
  return t;
}

test('(f) 화면 판정 = 응답값 그대로: 서로 모순인 checks 를 줘도 verification_status·문장은 응답·1.8 표 그대로', async () => {
  const table = vsTable();
  assert.deepEqual(Object.keys(table).sort(), ['ERROR', 'INCONCLUSIVE', 'NOT_REGISTERED', 'TAMPERED', 'VERIFIED']);
  // 상태 값 × checks 모양(정상·모순)을 엇갈리게 넣음. 재계산이 있으면 문장이 바뀌어 실패함
  const checkSets = [
    { proof_repository: 'FOUND', payload_hash: 'PASS', expiry: 'PASS', candidate_match: 'PASS', issuer: 'ACTIVE', signature: 'PASS' },
    { proof_repository: 'FOUND', payload_hash: 'FAIL', expiry: 'PASS', candidate_match: 'FAIL', signature: 'FAIL' },
    {}
  ];
  for (const vs of Object.keys(table)) {
    for (const checks of checkSets) {
      const { a } = setup(v1(vs, { checks }));
      const ans = await a.check('확인 prf_demo_001');
      assert.equal(ans.verification_status, vs, vs + ' 값');
      assert.equal(ans.conclusion.text, table[vs], vs + ' 문장');
      assert.ok(ans.details.some(d => d.label === '검증 엔진 결과' && d.value.startsWith(vs + ' ')), vs + ' 자세히');
      const rep = ans.staff.find(x => x.staff === 'report');
      assert.equal(rep.line2, vs, vs + ' 보고 말풍선');
    }
  }
  // 표에 없는 값: 값 그대로 + "쉬운 설명 없음"
  const { a } = setup(v1('SOMETHING_NEW'));
  const ans = await a.check('확인 prf_demo_001');
  assert.equal(ans.verification_status, 'SOMETHING_NEW');
  assert.equal(ans.conclusion.badge.text, '쉬운 설명 없음');
});

test('(f) 정적 확인: api_adapter.js 는 verification_status 를 응답에서만 읽고 직접 만들어 넣지 않음', () => {
  const src = fs.readFileSync(path.resolve(__dirname, '../../../페이지', 'js', 'api_adapter.js'), 'utf8');
  // "verification_status: 'VERIFIED'" 처럼 값을 직접 쓰는 곳이 없어야 함
  assert.equal((src.match(/verification_status\s*[:=]\s*['"]/g) || []).length, 0);
  // 답의 verification_status 는 vs 한 곳(= v.data.verification_status)에서만 옴
  assert.match(src, /var vs = v\.kind === 'result' \? v\.data\.verification_status : null;/);
  assert.equal((src.match(/verification_status: vs,/g) || []).length, 1);
});
