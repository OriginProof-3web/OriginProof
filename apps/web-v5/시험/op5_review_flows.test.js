'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const H = require('./_review_harness.js');
const { build, threadText, enter, menu, buttons, find, press, toSample, sleep, serverDouble, posted, reqs, eth, APP, PID, ISS, TX, TX2, Ev, fakeFetch } = H;
const OPERATOR = { persona: { role: 'operator', issuer_id: null } };
const API = '?mode=api';
const ready = async d => { await sleep(10); };
const inputs = f => posted(f, /\/v3\/inputs$/);

/* ---------- T5 ---------- */
test('T5-1 예시 모드 기관 상태 메뉴: 페이지 로드 뒤 서버 요청 0건', async () => {
  const f = serverDouble({});
  const d = build('', f);
  await ready(d);
  const n = f.calls.length;
  menu(d, 'status'); await sleep(40);
  assert.deepEqual(reqs(f).slice(n), []);
});
test('T5-2 예시 모드: issuer 응답 뒤 생긴 단추로 email-codes·suspensions POST 가 나가지 않음', async () => {
  const f = serverDouble({});
  const d = build('', f);
  await ready(d);
  menu(d, 'status'); await sleep(40);
  if (find(d, '업무 메일 코드 받기')) { await press(d, '업무 메일 코드 받기'); enter(d, 'staff@bank.example.invalid'); await sleep(30); }
  if (find(d, '긴급 정지 거래 알리기')) { await press(d, '긴급 정지 거래 알리기'); enter(d, ISS); await sleep(20); enter(d, TX); await sleep(30); }
  assert.equal(posted(f, /email-codes|suspensions/).length, 0);
});
test('T5-3 실서버에서 만든 승인 단추를 예시 모드 전환 뒤 눌러도 approvals POST 0건', async () => {
  const f = serverDouble(OPERATOR);
  const d = build(API, f);
  await ready(d);
  menu(d, 'status'); await sleep(40);
  await press(d, '공동승인 제안 조회'); enter(d, PID); await sleep(30);
  const btn = find(d, '승인 거래 알리기');
  await toSample(d);
  const n = f.calls.length;
  await press(d, btn);
  enter(d, TX); await sleep(30);
  assert.deepEqual(reqs(f).slice(n), []);
});
test('T5-4 입력 대기 중 예시 모드 전환: 대기 해제, 뒤 입력은 POST 안 됨', async () => {
  const f = serverDouble(OPERATOR);
  const d = build(API, f);
  await ready(d);
  menu(d, 'status'); await sleep(40);
  await press(d, '공동승인 제안 조회'); enter(d, PID); await sleep(30);
  await press(d, '승인 거래 알리기');
  const modeBtn = find(d, '예시 모드로 바꾸기');
  await press(d, modeBtn);
  const n = f.calls.length;
  enter(d, TX); await sleep(30);
  assert.deepEqual(reqs(f).slice(n), []);
});
test('T5-5 저장된 작업 복구 단추: 예시 모드에서 조회·reconcile 요청 0건', async () => {
  const f = serverDouble({});
  const d = build('', f, win => win.sessionStorage.setItem('op5.ops.v1', JSON.stringify([{ operation_id: 'op_1', request_id: 'r', kind: 'publish', status: 'UNKNOWN', next_action: 'RECONCILE', at: 1 }])));
  await ready(d);
  const n = f.calls.length;
  menu(d, 'operations'); await sleep(30);
  await press(d, /^작업 상태 조회 op_1/);
  await press(d, /^복구 조회\(reconcile\) op_1/);
  assert.deepEqual(reqs(f).slice(n), []);
});
test('T5-6 전수 훑기: 실서버에서 만든 모든 단추를 예시 모드 전환 뒤 눌러도 요청 0건', async () => {
  const f = serverDouble({});
  const d = build(API, f, win => { win.ethereum = eth(); win.sessionStorage.setItem('op5.ops.v1', JSON.stringify([{ operation_id: 'op_1', request_id: 'r', kind: 'publish', status: 'UNKNOWN', next_action: 'RECONCILE', at: 1 }])); });
  await ready(d);
  for (const k of ['status', 'issue', 'keys', 'proofs', 'operations']) { menu(d, k); await sleep(40); }
  await press(d, '내 확인 기록(보관한 분석) 보기', 40);
  const box = d.doc.querySelector('#sidebar-root input'); box.value = PID; d.doc._dispatch(box, new Ev('keydown', { key: 'Enter' })); await sleep(30);
  enter(d, '일반 안내문입니다'); await sleep(60);
  const all = buttons(d).filter(b => !/모드로 바꾸기|로그인 화면/.test(b.textContent));
  await toSample(d);
  const n = f.calls.length;
  const walked = [];
  for (const b of all) {
    b.disabled = false; delete b.dataset.done;
    walked.push(b.textContent);
    d.doc._dispatch(b, new Ev('click')); await sleep(6);
    d.doc._dispatch(b, new Ev('click')); await sleep(6);
    enter(d, TX); await sleep(6);
  }
  assert.ok(walked.length >= 15, '훑은 단추 수 ' + walked.length);
  assert.deepEqual(reqs(f).slice(n), [], '훑은 단추: ' + walked.join(' | '));
});
test('T5-7 실서버 응답 대기 중 예시 모드로 전환: 뒤따르는 기관 상태·신청 조회 0건', async () => {
  const f = serverDouble({ over: (u) => u === '/v1/auth/me' ? { status: 200, delay: 30, body: { account_id: 'acct_me', username: 'u', role: 'issuer', issuer_id: 'iss_origin_mock_bank', csrf_token: 'c' } } : null });
  const d = build(API, f);
  await sleep(60);
  menu(d, 'status');
  await press(d, '예시 모드로 바꾸기', 80);
  assert.equal(f.calls.filter(c => /issuer\/status|applications\/mine/.test(c.url)).length, 0);
});
test('T5-8 예시 모드 전환 뒤 실서버 응답의 체인 대조 단추: 바깥 요청 0건', async () => {
  const f = serverDouble({});
  const d = build(API, f);
  await ready(d);
  enter(d, '일반 안내문입니다'); await sleep(60);
  const b = find(d, '내 브라우저에서 체인 직접 대조하기');
  assert.ok(b);
  let called = 0;
  d.win.Hk.chain.verify = () => { called++; return Promise.resolve({ shape: 'x', headline: 'x', body: 'x' }); };
  await toSample(d);
  await press(d, b);
  assert.equal(called, 0);
});

test('T5-9 이전 서버 단추는 누르는 순간 예시 모드로 안내하고 입력 대기를 열지 않음(요청 관문과 별개)', async () => {
  const f = serverDouble(OPERATOR);
  const d = build(API, f);
  await ready(d);
  menu(d, 'status'); await sleep(40);
  await press(d, '공동승인 제안 조회'); enter(d, PID); await sleep(30);
  const btn = find(d, '승인 거래 알리기');
  await toSample(d);
  const cancels = buttons(d).filter(b => b.textContent === '입력 취소').length;
  await press(d, btn);
  assert.equal(buttons(d).filter(b => b.textContent === '입력 취소').length, cancels, '예시 모드에서 입력 대기가 열림');
  assert.match(threadText(d).slice(-200), /예시 모드라 서버에 보내지 않아요/);
  assert.equal(btn.disabled, false, '실서버로 돌아오면 다시 쓸 수 있어야 함');
});

/* ---------- T6 ---------- */
async function approveAsk(d) {
  menu(d, 'status'); await sleep(40);
  await press(d, '공동승인 제안 조회'); enter(d, PID); await sleep(30);
  await press(d, '승인 거래 알리기');
}
test('T6-1 승인 거래에 0xabc 뒤 올바른 해시 재입력 → approvals 로, /v3/inputs 0건', async () => {
  const f = serverDouble(OPERATOR);
  const d = build(API, f);
  await ready(d);
  await approveAsk(d);
  enter(d, '0xabc'); await sleep(20);
  enter(d, TX); await sleep(30);
  assert.equal(inputs(f).length, 0, '해시가 분석 입력으로 감');
  assert.equal(posted(f, /\/approvals$/).length, 1);
  assert.equal(JSON.parse(posted(f, /\/approvals$/)[0].body).tx_hash, TX);
});
for (const [name, bad] of [['형식 틀림', '123'], ['서버 거부(422)', '111111']]) {
  test('T6-2 메일 코드 ' + name + ' 뒤 재입력 → email-verifications 로, 분석기로 비밀값 유출 없음', async () => {
    const f = serverDouble({});
    const d = build(API, f);
    await ready(d);
    menu(d, 'status'); await sleep(40);
    await press(d, '메일 코드 확인');
    enter(d, bad); await sleep(30);
    enter(d, '654321'); await sleep(40);
    assert.equal(f.calls.filter(c => /inputs|analyses|document-lookups/.test(c.url) && c.body.includes('654321')).length, 0, '확인 코드가 분석 경로로 감');
    assert.equal(inputs(f).length, 0);
    assert.ok(posted(f, /email-verifications$/).some(c => JSON.parse(c.body).code === '654321'));
  });
}
test('T6-3 메일 코드 형식 틀림은 서버에 보내지 않음, 사용자 말풍선에 코드 안 보임', async () => {
  const f = serverDouble({});
  const d = build(API, f);
  await ready(d);
  menu(d, 'status'); await sleep(40);
  await press(d, '메일 코드 확인');
  enter(d, '123'); await sleep(30);
  assert.equal(posted(f, /email-verifications$/).length, 0);
  enter(d, '654321'); await sleep(30);
  const users = d.doc.querySelectorAll('#chatThread .msg-user').map(x => x.textContent).join('|');
  assert.ok(!/654321/.test(users), users);
});
test('T6-4 처리 중 다시 Enter: 뒤 입력이 분석으로 새지 않음', async () => {
  const f = serverDouble({ over: (u, m) => u.endsWith('/email-verifications') ? { status: 200, delay: 40, body: { application_id: APP, roster_matched: true, email_verified: true, internally_approved: false } } : null });
  const d = build(API, f);
  await ready(d);
  menu(d, 'status'); await sleep(40);
  await press(d, '메일 코드 확인');
  enter(d, '654321');
  await sleep(1);
  enter(d, '111111'); await sleep(70);
  assert.equal(inputs(f).length, 0);
  assert.equal(posted(f, /email-verifications$/).length, 1, '처리 중 입력이 또 제출됨');
  assert.equal(d.doc.getElementById('chatInput').value, '111111', '처리 중 입력칸 글 유지');
});
test('T6-5 내부 승인 사유 대기 중 작업 이력 메뉴 이동 → 일반 입력이 reason 으로 제출되지 않음', async () => {
  const f = serverDouble({ applicant: 'acct_other', approver: 'acct_me' });
  const d = build(API, f);
  await ready(d);
  menu(d, 'status'); await sleep(40);
  await press(d, '내부 승인하기(지정된 다른 계정)');
  menu(d, 'operations'); await sleep(30);
  enter(d, '이번 달 결제 안내입니다'); await sleep(40);
  assert.equal(posted(f, /internal-approvals$/).length, 0);
  assert.equal(inputs(f).length, 1);
});
test('T6-6 도움말·프리셋 단추도 입력 대기를 해제', async () => {
  for (const act of ['help', 'preset']) {
    const f = serverDouble({ applicant: 'acct_other', approver: 'acct_me' });
    const d = build(API, f);
    await ready(d);
    menu(d, 'status'); await sleep(40);
    await press(d, '내부 승인하기(지정된 다른 계정)');
    if (act === 'help') { d.doc.querySelectorAll('#sidebar-root button')[0].click(); await sleep(10); enter(d, '일반 글'); }
    else d.doc.getElementById('presetBar').querySelectorAll('button')[0].click();
    await sleep(40);
    assert.equal(posted(f, /internal-approvals$/).length, 0, act);
  }
});
test('T6-7 취소 단추는 자기 대기만 취소: 이전 대기의 취소가 새 대기를 끊지 않음', async () => {
  const f = serverDouble(OPERATOR);
  const d = build(API, f);
  await ready(d);
  await approveAsk(d);
  const firstCancel = find(d, '입력 취소');
  await press(d, '실행 거래 알리기');
  await press(d, firstCancel);
  enter(d, TX); await sleep(30);
  assert.equal(inputs(f).length, 0);
  assert.equal(posted(f, /\/transactions$/).length, 1);
});
test('T6-8 서버 실패(500) 뒤 재입력: 같은 곳·같은 request_id, /v3/inputs 0건', async () => {
  let k = 0;
  const f = serverDouble(Object.assign({}, OPERATOR, { over: (u, m) => u.endsWith('/approvals') && m === 'POST' && ++k === 1 ? { status: 500, body: { detail: 'INTERNAL' } } : null }));
  const d = build(API, f);
  await ready(d);
  await approveAsk(d);
  enter(d, TX); await sleep(30);
  enter(d, TX); await sleep(30);
  assert.equal(inputs(f).length, 0);
  const a = posted(f, /\/approvals$/).map(c => JSON.parse(c.body));
  assert.equal(a.length, 2);
  assert.equal(a[0].request_id, a[1].request_id);
});
test('T6-9 권한 거부(403)는 재시도 대기로 남기지 않음(회귀 보호)', async () => {
  const f = serverDouble({ applicant: 'acct_other', approver: 'acct_someone' });
  const d = build(API, f);
  await ready(d);
  menu(d, 'status'); await sleep(40);
  await press(d, '내부 승인하기(지정된 다른 계정)');
  enter(d, '사유'); await sleep(30);
  enter(d, '일반 글'); await sleep(40);
  assert.equal(posted(f, /internal-approvals$/).length, 1);
  assert.equal(inputs(f).length, 1);
});

test('T6-10a op5_auth 가 직접 모드를 되돌려도(비회원) 기다리던 입력에 안 들어감, 입력칸 글 유지', async () => {
  const f = serverDouble({ over: (u) => u === '/v1/auth/me' ? { status: 401, delay: 30, body: { detail: 'AUTH_REQUIRED' } } : null });
  const d = build(API, f);
  menu(d, 'status');
  await press(d, '연결 주소 바꾸기', 1);
  await sleep(60);
  enter(d, '/api2'); await sleep(10);
  assert.equal(d.win.localStorage.getItem('op5.apiBase'), null);
  assert.equal(d.doc.getElementById('chatInput').value, '/api2');
});
test('T6-10b 단추를 거치지 않고 모드가 바뀌어도 기다리던 입력에 안 들어감, 입력칸 글 유지(submit 관문)', async () => {
  let conn = null;
  const f = serverDouble({});
  const d = build(API, f, win => { win.Hk = new Proxy({}, { set(t, k, v) { t[k] = k === 'createConnection' ? (o => (conn = v(o))) : v; return true; } }); });
  menu(d, 'status');
  await press(d, '연결 주소 바꾸기', 1);
  assert.ok(conn);
  conn.setMode('sample');
  enter(d, '/api2'); await sleep(10);
  assert.equal(d.win.localStorage.getItem('op5.apiBase'), null);
  assert.equal(d.doc.getElementById('chatInput').value, '/api2');
});
test('T6-11 서버 실패(503) 뒤 재입력: 같은 request_id 로 재시도', async () => {
  let k = 0;
  const f = serverDouble(Object.assign({}, OPERATOR, { over: (u, m) => u.endsWith('/approvals') && m === 'POST' && ++k === 1 ? { status: 503, body: { detail: 'WALLET_REGISTRY_UNAVAILABLE' } } : null }));
  const d = build(API, f);
  await ready(d);
  await approveAsk(d);
  enter(d, TX); await sleep(30);
  enter(d, TX); await sleep(30);
  const a = posted(f, /\/approvals$/).map(c => JSON.parse(c.body));
  assert.equal(a.length, 2);
  assert.equal(a[0].request_id, a[1].request_id);
});

test('T6-12 client.write: 503 응답 뒤 같은 내용은 같은 request_id(서버가 작업을 먼저 저장했을 수 있음)', async () => {
  const f = fakeFetch((url) => url === '/api/v1/auth/me' ? { status: 200, body: { csrf_token: 'c', username: 'u' } } : { status: 503, body: { detail: 'WALLET_REGISTRY_UNAVAILABLE' } });
  const d = build(API, f);
  const c = d.win.Hk.op5.createClient({ fetch: f, base: '/api', timeoutMs: 500 });
  await c.write('POST', '/v3/x', { tx_hash: TX }); await c.write('POST', '/v3/x', { tx_hash: TX });
  const a = posted(f, /\/v3\/x$/).map(x => JSON.parse(x.body).request_id);
  assert.equal(a[0], a[1]);
});

/* ---------- T7 ---------- */
const UNK = { operation_id: 'op_1', request_id: 'req_x', status: 'UNKNOWN', recovery_required: true, next_action: 'RECONCILE' };
function t7double(rec) {
  let n = 0;
  return serverDouble(Object.assign({}, OPERATOR, { over: (u, m) => {
    if (u.endsWith('/approvals') && m === 'POST') return { status: 202, body: UNK };
    if (u === '/v3/operations/op_1/reconcile') return rec(++n);
    return null;
  } }));
}
for (const [name, rec, code] of [
  ['503 오류 본문', () => ({ status: 503, body: { detail: 'WALLET_REGISTRY_UNAVAILABLE' } }), /WALLET_REGISTRY_UNAVAILABLE/],
  ['2xx 인데 Operation 아님', () => ({ status: 202, body: { foo: 1 } }), /UPSTREAM_SCHEMA_MISMATCH/],
  ['2xx 인데 다른 작업 번호', () => ({ status: 202, body: Object.assign({}, UNK, { operation_id: 'op_2', status: 'CONFIRMED' }) }), /UPSTREAM_SCHEMA_MISMATCH/],
  ['연결 실패', () => ({ reject: 'boom' }), /NETWORK/]
]) {
  test('T7-1 승인 거래 UNKNOWN → reconcile ' + name + ': 기존 번호·UNKNOWN 유지, 오류·재조회 단추', async () => {
    const f = t7double(rec);
    const d = build(API, f);
    await ready(d);
    await approveAsk(d);
    enter(d, TX); await sleep(30);
    const t = threadText(d);
    assert.ok(!/undefined/.test(t), '화면에 undefined');
    assert.match(t, /작업 op_1 · 상태 UNKNOWN/);
    assert.ok(!/op_2/.test(t));
    assert.match(t, code);
    assert.ok(find(d, '작업 상태 조회 op_1'), '재조회 단추 없음');
    assert.ok(find(d, '복구 조회(reconcile) op_1'), '복구 단추 없음');
    const saved = JSON.parse(d.win.sessionStorage.getItem('op5.ops.v1'));
    assert.equal(saved[0].operation_id, 'op_1'); assert.equal(saved[0].status, 'UNKNOWN');
    assert.equal(posted(f, /\/approvals$/).length, 1, '다시 보내면 안 됨');
  });
}
test('T7-2 복구 단추 재시도 → 같은 작업 reconcile, 성공하면 CONFIRMED', async () => {
  const f = t7double(n => n === 1 ? { status: 503, body: { detail: 'WALLET_REGISTRY_UNAVAILABLE' } } : { status: 202, body: Object.assign({}, UNK, { status: 'CONFIRMED', next_action: 'NONE', recovery_required: false }) });
  const d = build(API, f);
  await ready(d);
  await approveAsk(d);
  enter(d, TX); await sleep(30);
  await press(d, '복구 조회(reconcile) op_1');
  assert.match(threadText(d), /복구 조회 op_1상태 CONFIRMED/);
  assert.equal(posted(f, /op_1\/reconcile$/).length, 2);
  assert.equal(posted(f, /\/approvals$/).length, 1);
});
test('T7-3 복구 단추 실패: 새 말풍선에도 재조회 단추, 저장 상태 유지, undefined 없음', async () => {
  const f = t7double(() => ({ status: 202, body: { nope: true } }));
  const d = build(API, f, win => win.sessionStorage.setItem('op5.ops.v1', JSON.stringify([{ operation_id: 'op_1', request_id: 'r', kind: 'publish', status: 'UNKNOWN', next_action: 'RECONCILE', at: 1 }])));
  await ready(d);
  menu(d, 'operations'); await sleep(30);
  const before = buttons(d).filter(b => b.textContent === '복구 조회(reconcile) op_1').length;
  await press(d, '복구 조회(reconcile) op_1');
  assert.ok(!/undefined/.test(threadText(d)));
  assert.ok(buttons(d).filter(b => b.textContent === '복구 조회(reconcile) op_1').length > before, '새 말풍선에 복구 단추 없음');
  assert.equal(JSON.parse(d.win.sessionStorage.getItem('op5.ops.v1'))[0].status, 'UNKNOWN');
});
const SR = { signing_request_id: 'wsr_1', primary_type: 'Publish', domain: { name: 'OriginProof', version: '1', chainId: 1, verifyingContract: '0x' + '22'.repeat(20) }, expected_signer: '0x' + '11'.repeat(20), message: { a: 1 } };
const DRAFT = JSON.stringify({ doc_key: '0x' + '0'.repeat(63) + '1', expected_version: 1, expires_at: 9999999999, content: { notice_type: 'OFFICIAL_DOCUMENT', institution_code: 'c', document_type: 't', document_number: 'n', title: 't', summary: 's' } });
function walletDouble() {
  return serverDouble({ over: (u, m) => {
    if (u === '/v3/document-drafts') return { status: 201, body: SR };
    if (u === '/v3/publications') return { status: 202, body: Object.assign({}, UNK, { status: 'PENDING_SUBMISSION', next_action: 'WAIT', recovery_required: false }) };
    if (u === '/v3/signing-requests/wsr_1/transactions') return { status: 202, body: UNK };
    if (u === '/v3/operations/op_1/reconcile') return { status: 503, body: { detail: 'WALLET_REGISTRY_UNAVAILABLE' } };
    return null;
  } });
}
test('T7-4 지갑 거래 알림(signing-requests) UNKNOWN + reconcile 503: 재조회 단추 유지, 잘못된 해시는 재입력', async () => {
  const f = walletDouble();
  const d = build(API, f, win => { win.ethereum = eth(); });
  await ready(d);
  menu(d, 'issue'); await sleep(20);
  await press(d, '초안 보내기 시작');
  enter(d, DRAFT); await sleep(50);
  await press(d, '지갑에서 보낸 거래 해시 알리기');
  enter(d, '0xabc'); await sleep(20);
  enter(d, TX); await sleep(40);
  assert.equal(inputs(f).length, 0, '해시가 분석으로 감');
  const t = threadText(d);
  assert.ok(!/undefined/.test(t));
  assert.match(t, /WALLET_REGISTRY_UNAVAILABLE/);
  const n = buttons(d).filter(b => b.textContent === '복구 조회(reconcile) op_1').length;
  assert.ok(n >= 1, '복구 단추 없음');
  enter(d, TX); await sleep(30);
  assert.equal(posted(f, /signing-requests\/wsr_1\/transactions$/).length, 1, 'UNKNOWN 뒤 거래 해시를 다시 보내면 안 됨');
});
test('T7-5 거래 해시 알리기 입력 취소 뒤 단추로 다시 시작 가능', async () => {
  const f = walletDouble();
  const d = build(API, f, win => { win.ethereum = eth(); });
  await ready(d);
  menu(d, 'issue'); await sleep(20);
  await press(d, '초안 보내기 시작');
  enter(d, DRAFT); await sleep(50);
  await press(d, '지갑에서 보낸 거래 해시 알리기');
  await press(d, '입력 취소');
  assert.equal(find(d, '지갑에서 보낸 거래 해시 알리기').disabled, false, '취소 뒤 영구 비활성');
});

for (const [name, body] of [['Operation 아님', { foo: 1 }], ['본문 없음', null]]) {
  test('T7-6 거래 알림 202 인데 ' + name + ': undefined 없이 오류, 재전송 대기 안 남김', async () => {
    const f = serverDouble(Object.assign({}, OPERATOR, { over: (u, m) => u.endsWith('/approvals') && m === 'POST' ? { status: 202, body } : null }));
    const d = build(API, f);
    await ready(d);
    await approveAsk(d);
    enter(d, TX); await sleep(30);
    const t = threadText(d);
    assert.ok(!/undefined/.test(t));
    assert.match(t, /UPSTREAM_SCHEMA_MISMATCH/);
  });
}

/* ---------- T8 ---------- */
test('T8-1 issuer: 제안 조회 단추 없음(서버 403), 긴급 정지는 유지', async () => {
  const f = serverDouble({});
  const d = build(API, f);
  await ready(d);
  menu(d, 'status'); await sleep(40);
  assert.equal(!!find(d, '공동승인 제안 조회'), false);
  assert.ok(find(d, '긴급 정지 거래 알리기'));
});
test('T8-2 operator: 제안 조회·승인 단추 표시', async () => {
  const f = serverDouble(OPERATOR);
  const d = build(API, f);
  await ready(d);
  await approveAsk(d);
  enter(d, TX); await sleep(30);
  assert.equal(posted(f, /\/approvals$/).length, 1);
});
test('T8-3 operator 인데 승인 지갑 미등록: 서버 403 APPROVER_REQUIRED 를 그대로 표시', async () => {
  const f = serverDouble(Object.assign({}, OPERATOR, { operatorAddress: false }));
  const d = build(API, f);
  await ready(d);
  menu(d, 'status'); await sleep(40);
  await press(d, '공동승인 제안 조회'); enter(d, PID); await sleep(30);
  assert.match(threadText(d), /APPROVER_REQUIRED/);
});
test('T8-4 신청자: 내부 승인 단추 없음(서버 SELF_APPROVAL_FORBIDDEN), 소유자 단추 4개', async () => {
  const f = serverDouble({});
  const d = build(API, f);
  await ready(d);
  menu(d, 'status'); await sleep(40);
  assert.equal(!!find(d, /^내부 승인/), false);
  for (const l of ['온보딩 상태 보기', '업무 메일 코드 받기', '데모 받은편지함 보기', '메일 코드 확인']) assert.ok(find(d, l), l);
});
test('T8-5 같은 기관의 다른 계정: 소유자 전용 단추 없음(서버 404), 내부 승인 단추만', async () => {
  const f = serverDouble({ applicant: 'acct_other', approver: 'acct_me' });
  const d = build(API, f);
  await ready(d);
  menu(d, 'status'); await sleep(40);
  for (const l of ['온보딩 상태 보기', '업무 메일 코드 받기', '데모 받은편지함 보기', '메일 코드 확인']) assert.equal(!!find(d, l), false, l);
  await press(d, '내부 승인하기(지정된 다른 계정)'); enter(d, '사유'); await sleep(30);
  assert.deepEqual(JSON.parse(posted(f, /internal-approvals$/)[0].body), { decision: 'APPROVE', reason: '사유' });
});
test('T8-6 지정되지 않은 다른 계정: 서버 403 을 쉬운 말과 코드로', async () => {
  const f = serverDouble({ applicant: 'acct_other', approver: 'acct_someone' });
  const d = build(API, f);
  await ready(d);
  menu(d, 'status'); await sleep(40);
  await press(d, '내부 승인하기(지정된 다른 계정)'); enter(d, '사유'); await sleep(30);
  const t = threadText(d);
  assert.match(t, /INTERNAL_APPROVER_REQUIRED/);
  assert.match(t, /지정된 승인자/);
});
test('T8-7 경로·본문이 openapi.json 과 일치(회귀 보호)', async () => {
  const spec = JSON.parse(fs.readFileSync(path.join(__dirname, '../../../packages/schemas/generated/openapi.json'), 'utf8'));
  const seen = [];
  const collect = f => f.calls.forEach(c => seen.push({ m: (c.init.method || 'GET').toLowerCase(), url: c.url.replace(/^\/api/, '').split('?')[0], body: c.body ? JSON.parse(c.body) : null }));
  { const f = serverDouble(OPERATOR); const d = build(API, f); await ready(d); await approveAsk(d); enter(d, TX); await sleep(30); await press(d, '실행 거래 알리기'); enter(d, TX2); await sleep(30); await press(d, '긴급 정지 거래 알리기'); enter(d, ISS); await sleep(20); enter(d, TX); await sleep(30); collect(f); }
  { const f = serverDouble({}); const d = build(API, f); await ready(d); menu(d, 'status'); await sleep(40); await press(d, '온보딩 상태 보기'); await press(d, '업무 메일 코드 받기'); enter(d, 'a@bank.example.invalid'); await sleep(30); await press(d, '데모 받은편지함 보기'); await press(d, '메일 코드 확인'); enter(d, '654321'); await sleep(30); collect(f); }
  { const f = serverDouble({ applicant: 'acct_other', approver: 'acct_me' }); const d = build(API, f); await ready(d); menu(d, 'status'); await sleep(40); await press(d, '내부 승인하기(지정된 다른 계정)'); enter(d, '사유'); await sleep(30); collect(f); }
  const ids = [[/\/v3\/issuer-applications\/[^/]+/, '/v3/issuer-applications/{application_id}'], [/\/v3\/proposals\/0x[0-9a-f]+/, '/v3/proposals/{proposal_id}'], [/\/v3\/issuers\/0x[0-9a-f]+/, '/v3/issuers/{issuer_id}']];
  const tpl = u => ids.reduce((s, [r, t]) => s.replace(r, t), u);
  const seenKeys = new Set();
  for (const s of seen) {
    if (s.url.startsWith('/health/')) continue;
    const p = spec.paths[tpl(s.url)];
    assert.ok(p && p[s.m], '계약에 없음: ' + s.m + ' ' + s.url);
    seenKeys.add(s.m + ' ' + tpl(s.url));
    const rb = p[s.m].requestBody;
    if (!s.body) continue;
    assert.ok(rb, '본문 없는 경로: ' + s.url);
    const sc = spec.components.schemas[rb.content['application/json'].schema.$ref.split('/').pop()];
    (sc.required || []).forEach(k => assert.ok(k in s.body, s.url + ' 필수 ' + k));
    Object.keys(s.body).forEach(k => assert.ok(k in sc.properties, s.url + ' 모르는 항목 ' + k));
  }
  assert.ok(seenKeys.size >= 10, [...seenKeys].join(', '));
});

/* ---------- T8 권한 대역(감사 재작업): POST /v3/issuers/{id}/suspensions. 여기 403·202 는 모두 대역 응답이며 서버 실제 응답이 아님.
   서버 코드 대조는 t8_asgi_suspension_test.py(ASGI) + t8_parity.js 가 따로 한다. ---------- */
const BANK_HASH = '0x9d6e623a821f35508c0c970540013aa75041537806d71a2e318ac7ca5358a217';     // identifier_hash("iss_origin_mock_bank")
const OFFICE_HASH = '0xa079131abb1c9fafcee45cedda0cb5ae9a0aa8d8e2f3112e1ad0e85da89a9bbe';   // identifier_hash("iss_origin_mock_office")
async function suspendDirect(o, id, init) {
  const f = serverDouble(o);
  const r = await f('/api/v3/issuers/' + id + '/suspensions', Object.assign({ method: 'POST', headers: { 'X-CSRF-Token': 'c' }, body: JSON.stringify({ request_id: 'req_t8', tx_hash: TX }) }, init || {}));
  return { status: r.status, body: await r.json() };
}
async function suspendScreen(o, id) {
  const f = serverDouble(o);
  const d = build(API, f);
  await ready(d);
  menu(d, 'status'); await sleep(40);
  await press(d, '긴급 정지 거래 알리기');
  enter(d, id); await sleep(20);
  enter(d, TX); await sleep(30);
  return { f, d, t: threadText(d), sent: posted(f, /\/suspensions$/) };
}
const NO_WALLET = Object.assign({}, OPERATOR, { operatorAddress: false });

test('T8-8 대역 해시: identifier_hash 와 같은 keccak256(서버 해시값으로 고정, SHA3-256·슬러그 아님)', () => {
  assert.equal(H.identifierHash(''), '0xc5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470');
  assert.equal(H.identifierHash('iss_origin_mock_bank'), BANK_HASH);
  assert.equal(H.identifierHash('iss_origin_mock_office'), OFFICE_HASH);
  assert.equal(H.identifierHash('x'.repeat(300)).length, 66);   // rate(136바이트)를 넘는 입력도 처리
});
test('T8-9 대역 직접: 다른 기관 issuer → 403 FORBIDDEN', async () => {
  const r = await suspendDirect({}, OFFICE_HASH);
  assert.equal(r.status, 403);
  assert.equal(r.body.detail, 'FORBIDDEN');
});
test('T8-10 대역 직접: 승인 지갑 없는 operator → 403 APPROVER_REQUIRED', async () => {
  const r = await suspendDirect(NO_WALLET, BANK_HASH);
  assert.equal(r.status, 403);
  assert.equal(r.body.detail, 'APPROVER_REQUIRED');
});
test('T8-11 대역 직접: 자기 기관 issuer(해시 일치) → 202', async () => {
  const r = await suspendDirect({}, BANK_HASH);
  assert.equal(r.status, 202);
  assert.equal(r.body.operation_id, 'op_1');
});
test('T8-12 대역 직접: 승인 지갑 있는 operator → 202(다른 기관 ID 도, 체인 기관이 없어도 이 단계는 통과)', async () => {
  for (const o of [OPERATOR, Object.assign({}, OPERATOR, { issuerOnChain: false })]) {
    const r = await suspendDirect(o, OFFICE_HASH);
    assert.equal(r.status, 202);
  }
});
test('T8-13 대역 직접: 자기 기관인데 체인에 기관 없음 → 404 ISSUER_NOT_FOUND', async () => {
  const r = await suspendDirect({ issuerOnChain: false }, BANK_HASH);
  assert.equal(r.status, 404);
  assert.equal(r.body.detail, 'ISSUER_NOT_FOUND');
});
test('T8-14 대역 직접: 수신자·기관 없는 issuer 는 403 FORBIDDEN', async () => {
  for (const persona of [{ role: 'recipient', issuer_id: null }, { role: 'issuer', issuer_id: null }]) {
    const r = await suspendDirect({ persona }, BANK_HASH);
    assert.deepEqual([r.status, r.body.detail], [403, 'FORBIDDEN'], JSON.stringify(persona));
  }
});
test('T8-15 대역 직접: 슬러그·대문자 URL 은 422, 본문 틀림 422, CSRF 없음 403 CSRF_REQUIRED', async () => {
  const code = r => [r.status, r.body.detail];
  assert.deepEqual(code(await suspendDirect({}, 'iss_origin_mock_bank')), [422, 'MALFORMED_INPUT']);
  assert.deepEqual(code(await suspendDirect({}, BANK_HASH.toUpperCase().replace('0X', '0x'))), [422, 'MALFORMED_INPUT']);
  assert.deepEqual(code(await suspendDirect({}, BANK_HASH, { body: JSON.stringify({ tx_hash: TX }) })), [422, 'MALFORMED_INPUT']);
  assert.deepEqual(code(await suspendDirect({}, BANK_HASH, { headers: {} })), [403, 'CSRF_REQUIRED']);
});
test('T8-16 화면: 다른 기관 issuer 입력 → 403 쉬운 말과 코드, 작업 번호 없음, 재전송 없음(대역 응답)', async () => {
  const { f, d, t, sent } = await suspendScreen({}, OFFICE_HASH);
  assert.equal(sent.length, 1);
  assert.match(sent[0].url, new RegExp(OFFICE_HASH + '/suspensions$'));
  assert.match(t, /이 계정으로는 할 수 없는 작업이에요/);
  assert.match(t, /FORBIDDEN/);
  assert.ok(!/작업 op_1/.test(t), '거부인데 작업 번호 표시');
  assert.ok(!/undefined/.test(t));
  enter(d, TX); await sleep(30);
  assert.equal(posted(f, /\/suspensions$/).length, 1, '권한 거부 뒤 입력이 또 정지 요청으로 감');
});
test('T8-17 화면: 승인 지갑 없는 operator → 403 APPROVER_REQUIRED 쉬운 말과 코드(대역 응답)', async () => {
  const { t, sent } = await suspendScreen(NO_WALLET, BANK_HASH);
  assert.equal(sent.length, 1);
  assert.match(t, /승인 지갑이 등록된 운영 계정만 할 수 있어요/);
  assert.match(t, /APPROVER_REQUIRED/);
  assert.ok(!/작업 op_1/.test(t));
});
test('T8-18 화면: 자기 기관 issuer 해시 입력 → 작업 번호 표시(대역 응답)', async () => {
  const { t, sent } = await suspendScreen({}, BANK_HASH);
  assert.equal(sent.length, 1);
  assert.match(t, /작업 op_1 · 상태/);
  assert.ok(!/FORBIDDEN/.test(t));
});
test('T8-19 화면: 승인 지갑 있는 operator → 작업 번호 표시(대역 응답)', async () => {
  const { t, sent } = await suspendScreen(OPERATOR, OFFICE_HASH);
  assert.equal(sent.length, 1);
  assert.match(t, /작업 op_1 · 상태/);
});
test('T8-20 화면: 자기 기관인데 체인에 없음 → 404 ISSUER_NOT_FOUND 쉬운 말과 코드(대역 응답)', async () => {
  const { t } = await suspendScreen({ issuerOnChain: false }, BANK_HASH);
  assert.match(t, /기관을 찾지 못했어요/);
  assert.match(t, /ISSUER_NOT_FOUND/);
  assert.ok(!/작업 op_1/.test(t));
});
test('T8-21 화면: 슬러그를 기관 ID 로 넣으면 형식 안내, 서버로 안 감. 화면은 슬러그만 보여 줌(제품 한계 기록)', async () => {
  const f = serverDouble({});
  const d = build(API, f);
  await ready(d);
  menu(d, 'status'); await sleep(40);
  assert.match(threadText(d), /기관 iss_origin_mock_bank/);
  assert.ok(!threadText(d).includes(BANK_HASH), '화면이 해시를 보여 주게 되었다면 보고 내용을 고칠 것');
  await press(d, '긴급 정지 거래 알리기');
  enter(d, 'iss_origin_mock_bank'); await sleep(20);
  assert.match(threadText(d), /기관 ID 형식이 맞지 않아요/);
  assert.equal(posted(f, /\/suspensions$/).length, 0);
});
test('T8-22 수신자 화면: 긴급 정지 단추 없음', async () => {
  const f = serverDouble({ persona: { role: 'recipient', issuer_id: null } });
  const d = build(API, f);
  await ready(d);
  menu(d, 'status'); await sleep(40);
  assert.equal(!!find(d, '긴급 정지 거래 알리기'), false);
});
test('T8-23 대역 직접: 다른 분기도 관대하지 않음(키·Proof·기관 상태·온보딩·CSRF)', async () => {
  const call = async (o, url, init) => { const r = await serverDouble(o)(url, init || {}); return [r.status, (await r.json()).detail]; };
  const NOISS = { persona: { role: 'issuer', issuer_id: null } };
  for (const o of [OPERATOR, NOISS]) {
    assert.deepEqual(await call(o, '/api/v1/issuer/keys'), [403, 'FORBIDDEN']);
    assert.deepEqual(await call(o, '/api/v2/issuer/proofs'), [403, 'FORBIDDEN']);
    assert.deepEqual(await call(o, '/api/v1/issuer/status'), [403, 'FORBIDDEN']);
    assert.deepEqual(await call(o, '/api/v3/issuer-applications/' + APP), [403, 'FORBIDDEN']);
  }
  assert.equal((await call({}, '/api/v1/issuer/keys'))[0], 200);
  assert.equal((await call({}, '/api/v2/issuer/proofs'))[0], 200);
  assert.deepEqual(await call({ applicationIssuer: 'iss_origin_mock_office' }, '/api/v3/issuer-applications/' + APP), [404, 'APPLICATION_NOT_FOUND']);
  const post = { method: 'POST', body: '{}' };
  assert.deepEqual(await call(OPERATOR, '/api/v3/proposals', post), [403, 'CSRF_REQUIRED']);
  assert.deepEqual(await call({}, '/api/v3/inputs', post), [403, 'CSRF_REQUIRED']);
  assert.deepEqual(await call({}, '/api/v3/operations/op_1/reconcile', post), [403, 'CSRF_REQUIRED']);
});

/* ---------- T9 ---------- */
const file = (name, b64, o) => Object.assign({ name, type: 'image/png', size: 100, lastModified: 1000, _b64: b64 }, o || {});
function imgBuild(f, opts = {}) {
  const d = build(API, f, win => {
    win.FileReader = class { readAsDataURL(file) { const go = () => { if (file._readFail && file._readFail()) return this.onerror(); this.result = 'data:' + file.type + ';base64,' + file._b64; this.onload(); }; if (opts.readDelay) setTimeout(go, opts.readDelay); else go(); } };
  });
  d.win.OP5Media = { inspect: opts.inspect || (async () => ({ kind: 'DOCUMENT_IMAGE', state: 'ok', code: 'READY', title: '읽을 준비가 됐어요', advice: 'a' })) };
  return d;
}
async function addFiles(d, files) {
  const fi = d.doc.getElementById('fileInput');
  fi.files = files;
  d.doc._dispatch(fi, new Ev('change'));
  await sleep(10);
}
const delFile = (d, i = 0) => d.doc.querySelectorAll('#fileList .fdel')[i].click();
const imgPosts = f => inputs(f).map(c => JSON.parse(c.body)).filter(b => b.kind === 'DOCUMENT_IMAGE');
const imgFlow = (o = {}) => serverDouble(Object.assign({}, o));

test('T9-1 사진을 ✕로 뺀 뒤 기존 단추를 눌러도 DOCUMENT_IMAGE 전송 0건', async () => {
  const f = imgFlow();
  const d = imgBuild(f);
  await sleep(10);
  await addFiles(d, [file('a.png', 'QUJD')]);
  const b = find(d, '이 사진 확인하기');
  assert.ok(b);
  delFile(d); await sleep(5);
  d.doc._dispatch(b, new Ev('click')); await sleep(40);
  assert.equal(imgPosts(f).length, 0);
});
test('T9-2 사진을 읽는 중 ✕로 빼면 전송 0건', async () => {
  const f = imgFlow();
  const d = imgBuild(f, { readDelay: 30 });
  await sleep(10);
  await addFiles(d, [file('a.png', 'QUJD')]);
  await press(d, '이 사진 확인하기', 1);
  delFile(d);
  await sleep(70);
  assert.equal(imgPosts(f).length, 0);
});
test('T9-3 검사 중 ✕로 뺀 사진은 단추가 생기지 않음', async () => {
  const f = imgFlow();
  let go;
  const d = imgBuild(f, { inspect: () => new Promise(r => { go = () => r({ kind: 'DOCUMENT_IMAGE', state: 'ok', code: 'READY', title: 't', advice: 'a' }); }) });
  await sleep(10);
  await addFiles(d, [file('a.png', 'QUJD')]);
  delFile(d); go(); await sleep(15);
  assert.equal(!!find(d, '이 사진 확인하기'), false);
});
test('T9-4 전송한 사진을 "서버로 보내지 않았어요"로 표시하지 않고, 안 보낸 첨부만 그렇게 표시', async () => {
  const f = imgFlow();
  const d = imgBuild(f);
  await sleep(10);
  await addFiles(d, [file('a.png', 'QUJD')]);
  await press(d, '이 사진 확인하기', 60);
  let t = threadText(d);
  assert.equal(imgPosts(f).length, 1);
  assert.ok(!/서버로 보내지 않았어요/.test(t), '보낸 사진을 안 보냈다고 표시');
  assert.match(t, /첨부 1개[^.]*서버로 보냈어요/);
  await addFiles(d, [file('b.png', 'REVG', { size: 7, lastModified: 2 })]);
  enter(d, '일반 안내문입니다'); await sleep(60);
  t = threadText(d);
  assert.match(t, /첨부 1개는 서버로 보내지 않았어요/);
});
test('T9-5 서버 실패 → 단추 다시 눌러 재시도 가능', async () => {
  let k = 0;
  const f = imgFlow({ over: (u, m) => u === '/v3/inputs' && ++k === 1 ? { status: 500, body: { detail: 'X' } } : null });
  const d = imgBuild(f);
  await sleep(10);
  await addFiles(d, [file('a.png', 'QUJD')]);
  const b = find(d, /이 사진/);
  await press(d, b, 60);
  assert.equal(b.disabled, false, '실패 뒤 비활성');
  assert.match(threadText(d), /첨부 1개는 서버로 보내지 않았어요/);
  await press(d, b, 60);
  assert.equal(imgPosts(f).length, 2);
  assert.ok(!/첨부 1개는 서버로 보내지 않았어요/.test(threadText(d).split('첨부 1개는 서버로 보내지 않았어요').pop()));
});
test('T9-6 파일 읽기 실패 → 재시도 가능', async () => {
  let k = 0;
  const f = imgFlow();
  const d = imgBuild(f);
  await sleep(10);
  await addFiles(d, [file('a.png', 'QUJD', { _readFail: () => ++k === 1 })]);
  const b = find(d, /이 사진/);
  await press(d, b, 30);
  assert.equal(b.disabled, false);
  await press(d, b, 60);
  assert.equal(imgPosts(f).length, 1);
});
test('T9-7 성공한 사진은 다시 보낼 수 없음(회귀 보호)', async () => {
  const f = imgFlow();
  const d = imgBuild(f);
  await sleep(10);
  await addFiles(d, [file('a.png', 'QUJD')]);
  const b = find(d, /이 사진/);
  await press(d, b, 60);
  assert.equal(b.disabled, true);
  d.doc._dispatch(b, new Ev('click')); await sleep(30);
  assert.equal(imgPosts(f).length, 1);
});
test('T9-8 이름·크기가 같아도 수정 시각이 다른 사진은 합쳐지지 않음', async () => {
  const f = imgFlow();
  const d = imgBuild(f);
  await sleep(10);
  await addFiles(d, [file('a.png', 'QUJD', { lastModified: 1 }), file('a.png', 'REVG', { lastModified: 2 })]);
  assert.equal(d.doc.querySelectorAll('#fileList .file').length, 2);
  assert.equal(buttons(d).filter(b => b.textContent === '이 사진 확인하기').length, 2);
});
test('T9-9 같은 이름·다른 크기 두 사진을 동시에 눌러도 각각 전송(진행 중 중복 처리로 안 합침)', async () => {
  const f = imgFlow({ over: (u, m) => u === '/v3/inputs' ? { status: 201, delay: 30, body: { input_ref: 'inp_' + Math.random(), expires_at: 1 } } : null });
  const d = imgBuild(f);
  await sleep(10);
  await addFiles(d, [file('a.png', 'QUJD', { size: 100 }), file('a.png', 'REVG', { size: 200 })]);
  const [x, y] = buttons(d).filter(b => b.textContent === '이 사진 확인하기');
  d.doc._dispatch(x, new Ev('click')); d.doc._dispatch(y, new Ev('click'));
  await sleep(90);
  assert.deepEqual(imgPosts(f).map(b => b.image_base64).sort(), ['QUJD', 'REVG']);
});
test('T9-10 하나를 빼도 같은 이름의 다른 사진 단추는 그대로 전송', async () => {
  const f = imgFlow();
  const d = imgBuild(f);
  await sleep(10);
  await addFiles(d, [file('a.png', 'QUJD', { size: 100 }), file('a.png', 'REVG', { size: 200 })]);
  const [x, y] = buttons(d).filter(b => b.textContent === '이 사진 확인하기');
  delFile(d, 0); await sleep(5);
  d.doc._dispatch(x, new Ev('click')); await sleep(30);
  d.doc._dispatch(y, new Ev('click')); await sleep(60);
  assert.deepEqual(imgPosts(f).map(b => b.image_base64), ['REVG']);
});
test('T9-11 같은 사진을 두 번 올리면 하나로(회귀 보호)', async () => {
  const f = imgFlow();
  const d = imgBuild(f);
  await sleep(10);
  await addFiles(d, [file('a.png', 'QUJD')]);
  await addFiles(d, [file('a.png', 'QUJD')]);
  assert.equal(d.doc.querySelectorAll('#fileList .file').length, 1);
});
test('T9-12 안내 문구가 사진 전송과 어긋나지 않음(도움말·오른쪽 패널)', async () => {
  const f = imgFlow();
  const d = imgBuild(f);
  await sleep(10);
  d.doc.querySelectorAll('#sidebar-root button')[0].click(); await sleep(5);
  assert.ok(!/서버 업로드는 아직 연결 전/.test(threadText(d)));
  assert.ok(!/서버 업로드·사진 글자 읽기는 아직 연결 전/.test(fs.readFileSync(path.join(H.WEB, 'business.html'), 'utf8')));
});
