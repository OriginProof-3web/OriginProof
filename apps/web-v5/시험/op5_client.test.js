// 5안 기술 연결 새 시험: 가짜 fetch·가짜 지갑으로 /v3 계약 흐름 확인(설치 없음, node 내장 node:test).
//   node --test 시험/op5_client.test.js
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { fakeFetch, memStorage } = require('./가져온/regression/_load.js');

const WEB = path.resolve(__dirname, '../페이지');
const FIX = path.join(__dirname, 'fixtures', 'originproof');
const FILES = ['data/sample_data.js', 'js/text_tools.js', 'js/op5_staff.js', 'js/adapter.js', 'js/chain_check.js', 'js/api_adapter.js', 'js/session.js', 'js/connection.js', 'js/op5_client.js'];
const j = x => JSON.parse(JSON.stringify(x));
const fixture = n => { const d = JSON.parse(fs.readFileSync(path.join(FIX, n), 'utf8')); delete d._source; return d; };
const ME = { account_id: 'acc_fixture', username: 'fixture', role: 'issuer', issuer_id: 'iss_fixture', csrf_token: 'fixture-csrf' };
const RID = /^req_[A-Za-z0-9_-]{1,124}$/;

function load() {
  const sb = { console, setTimeout, clearTimeout, AbortController, AbortSignal, TextEncoder, URL, crypto: globalThis.crypto, Promise };
  sb.window = sb; sb.self = sb;
  vm.createContext(sb);
  for (const f of FILES) vm.runInContext(fs.readFileSync(path.join(WEB, f), 'utf8'), sb, { filename: f });
  return sb.Hk;
}
const posts = (f, p) => f.calls.filter(c => (c.init.method || 'GET') === 'POST' && (!p || c.url === '/api' + p));
const bodyOf = c => JSON.parse(c.body);
function adapter(Hk, f, extra) {
  const client = Hk.op5.createClient({ fetch: f, base: '/api', timeoutMs: 500 });
  const api = Hk.createApiAdapter(Object.assign({ fetch: f, base: '/api', csrf: client.csrf, isDeleted: client.isDeleted, retain: () => ({ report: true, original: false }), timeoutMs: 500, pollMs: 5, pollLimitMs: 2000, loginWhy: '분석은 로그인이 필요해요.' }, extra || {}));
  return { client, api };
}

/* ---------------- /v3 정상 1건 ---------------- */
test('정상: 글 → /v3/inputs(TEXT) → /v3/analyses(request_id·보관 선택) → 폴링 → 보고서, 직원 칩은 응답 도착 순서', async () => {
  const Hk = load();
  const report = fixture('v3_analysis_report_DG01.synthetic.json');
  let polls = 0;
  const f = fakeFetch((url, init) => {
    if (url === '/api/v1/auth/me') return { status: 200, body: ME };
    if (url === '/api/v3/inputs') return { status: 201, body: { input_ref: 'inp_fixture', expires_at: 1 } };
    if (url === '/api/v3/analyses' && init.method === 'POST') return { status: 202, body: { analysis_id: 'ana_fixture', status: 'QUEUED', retain_report: true, retain_original: false } };
    if (url === '/api/v3/analyses/ana_fixture') { polls++; return { status: 200, body: polls < 2 ? { analysis_id: 'ana_fixture', status: 'RUNNING', retain_report: true, retain_original: false } : { analysis_id: 'ana_fixture', status: 'COMPLETED', retain_report: true, retain_original: false, report } }; }
  });
  const { api } = adapter(Hk, f);
  const order = [];
  const a = await api.check('[OO카드] 결제 안내 010-1234-5678 로 연락 주세요.', { onStaff: o => order.push(o.staff) });
  const input = posts(f, '/v3/inputs')[0];
  assert.equal(bodyOf(input).kind, 'TEXT');
  assert.ok(!bodyOf(input).text.includes('010-1234-5678'), '개인정보를 가리지 않고 보냄');
  assert.equal(input.init.credentials, 'same-origin');
  assert.equal(input.init.headers['X-CSRF-Token'], 'fixture-csrf');
  const an = bodyOf(posts(f, '/v3/analyses')[0]);
  assert.match(an.request_id, RID);
  assert.equal(an.input_ref, 'inp_fixture');
  assert.equal(an.retain_report, true);
  assert.equal(an.retain_original, false);
  // 링크가 없는 글은 검증 칸이 서버 없이 바로 정해져 먼저 오고, 접수(/v3/inputs 응답) → AI(폴링 결과) 순서
  assert.ok(order.indexOf('intake') >= 0 && order.indexOf('intake') < order.indexOf('ai'), order.join(','));
  assert.equal(a.analysis_id, 'ana_fixture');
  const ai = a.axes.find(x => x.axis === 'ai');
  assert.ok(ai && ai.status && ai.status !== '연결 전');
  assert.equal(a.staff.length, 7);
  assert.equal(a.staff[6].staff, 'report');
});

test('정상: 문서 ID → POST /v3/verifications(request_id 필수, ID_ONLY / PROTECTED_FIELDS), CSRF 없이 공개 검증', async () => {
  const Hk = load();
  const DOCID = '0x' + 'cd'.repeat(32);
  const verified = { session_id: 'vsn_fixture', verification_status: 'VERIFIED', comparison_scope: 'FULL_COMPARISON',
    document: { document_id: DOCID, issuer_id: DOCID, doc_key: DOCID, key_id: DOCID, version: 1, latest_version: 1, state: 'ACTIVE', warnings: [], original_hash: DOCID, protected_hash: DOCID, content_schema: DOCID, issued_at: 1, expires_at: 9, original_available: true },
    checks: [{ name: 'signature', status: 'PASSED' }, { name: 'protected_fields', status: 'PASSED' }, { name: 'current_state', status: 'PASSED' }],
    reason_codes: [], checked_at: 1, chain_id: '31337', verifying_contract: '0x' + '1'.repeat(40), block_number: '7', block_hash: null };
  const f = fakeFetch(url => url === '/api/v3/verifications' ? { status: 200, body: verified } : { status: 401, body: { detail: 'AUTH_REQUIRED' } });
  const { api } = adapter(Hk, f);
  const a = await api.check(JSON.stringify({ document_id: DOCID, version: 1 }));
  const v = posts(f, '/v3/verifications')[0];
  assert.match(bodyOf(v).request_id, RID);
  assert.equal(bodyOf(v).scope, 'ID_ONLY');
  assert.equal(v.init.headers['X-CSRF-Token'], undefined);
  assert.equal(a.verification_status, 'VERIFIED');
  assert.equal(a.axes[0].status, '확인됨');
  const a2 = await api.check(JSON.stringify({ document_id: DOCID, version: 1, protected_fields: { title: '안내' } }));
  assert.equal(bodyOf(posts(f, '/v3/verifications')[1]).scope, 'PROTECTED_FIELDS');
  assert.ok(a2.verification_status);
});

/* ---------------- 503 두 종류 + 준비 안 됨 ---------------- */
test('503 WALLET_REGISTRY_UNAVAILABLE: 지갑 단계가 지어내지 않고 그 코드로 멈추고 쉬운 말', async () => {
  const Hk = load();
  const f = fakeFetch(url => {
    if (url === '/api/v1/auth/me') return { status: 200, body: ME };
    if (url === '/api/v1/issuer-applications/mine') return { status: 200, body: { application_id: 'app_fixture' } };
    if (url === '/api/v3/key-challenges') return { status: 503, body: { detail: 'WALLET_REGISTRY_UNAVAILABLE' } };
  });
  const client = Hk.op5.createClient({ fetch: f, base: '/api', timeoutMs: 500 });
  const eth = { request: async q => q.method === 'eth_requestAccounts' ? ['0x' + '2'.repeat(40)] : assert.fail('서명까지 가면 안 됨') };
  const w = Hk.op5.createWallet({ client, ethereum: () => eth });
  const steps = [];
  const r = await w.keyProof(s => steps.push(s));
  assert.equal(r.ok, false);
  assert.equal(r.code, 'WALLET_REGISTRY_UNAVAILABLE');
  assert.equal(r.data.status, 503);
  assert.match(r.text, /장부\(Registry\) 연결부가 아직 붙지 않았어요/);
  assert.deepEqual(steps.map(s => s.step), ['application', 'wallet', 'challenge']);
  assert.equal(posts(f, '/v3/key-proofs').length, 0);
});

test('ANALYZER_UNAVAILABLE(FAILED) → AI 칸 연결 전 + 사유, 503 WALLET_REGISTRY_NOT_CONFIGURED → v1 로 넘어감, ready 503 RUNTIME_NOT_READY 쉬운 말', async () => {
  const Hk = load();
  const job = fixture('v3_analysis_job_analyzer_unavailable.reconstructed.json');
  const f = fakeFetch((url, init) => {
    if (url === '/api/v1/auth/me') return { status: 200, body: ME };
    if (url === '/api/v3/inputs') return { status: 201, body: { input_ref: 'inp_x', expires_at: 1 } };
    if (url === '/api/v3/analyses' && init.method === 'POST') return { status: 202, body: Object.assign({}, job, { status: 'QUEUED' }) };
    if (url.startsWith('/api/v3/analyses/')) return { status: 200, body: job };
    if (url === '/api/v3/verifications') return { status: 503, body: { detail: 'WALLET_REGISTRY_NOT_CONFIGURED' } };
    if (url === '/api/health/live') return { status: 200, body: { status: 'live' } };
    if (url === '/api/health/ready') return { status: 503, body: { detail: 'RUNTIME_NOT_READY' } };
  });
  const { api, client } = adapter(Hk, f);
  const a = await api.check('결제 안내입니다');
  const ai = a.axes.find(x => x.axis === 'ai');
  assert.equal(ai.status, 'AI 분석 연결 전');   // T2: ANALYZER_UNAVAILABLE 정직 표기
  assert.match(ai.body, /서버에 분석 처리기가 없어요/);
  const b = await api.check(JSON.stringify({ document_id: '0x' + 'ab'.repeat(32) }));
  assert.ok(b.details.some(d => /WALLET_REGISTRY_NOT_CONFIGURED/.test(d.value)));
  const h = await client.health();
  assert.equal(h.live.ok, true);
  assert.equal(h.ready.ok, false);
  assert.match(h.ready.text, /꺼진 것과는 달라요/);
  assert.match(h.ready.code, /RUNTIME_NOT_READY/);
  const e = Hk.op5.explain({ status: 503, data: { detail: 'WALLET_REGISTRY_UNAVAILABLE' } });
  assert.equal(e.code, 'WALLET_REGISTRY_UNAVAILABLE');
  assert.equal(Hk.op5.CODE_TEXT.ANALYZER_UNAVAILABLE, '서버에 AI 분석기가 아직 연결되지 않았어요.');
});

/* ---------------- 429 · 410 ---------------- */
test('429 ANALYSIS_LIMIT + Retry-After 600 → 기다릴 초를 그대로 보여 줌', async () => {
  const Hk = load();
  const f = fakeFetch((url, init) => {
    if (url === '/api/v1/auth/me') return { status: 200, body: ME };
    if (url === '/api/v3/inputs') return { status: 201, body: { input_ref: 'inp_x', expires_at: 1 } };
    if (url === '/api/v3/analyses') return { status: 429, body: { detail: 'ANALYSIS_LIMIT' }, headers: { 'Retry-After': '600' } };
  });
  const { api } = adapter(Hk, f);
  const a = await api.check('안내문');
  const ai = a.staff.find(s => s.staff === 'ai');
  assert.match(ai.line2, /HTTP 429 · ANALYSIS_LIMIT · 600초 뒤 가능/);
  assert.match(a.axes.find(x => x.axis === 'ai').body, /600초 뒤에 다시/);
  const e = Hk.op5.explain({ status: 429, data: { detail: 'RATE_LIMITED' }, retryAfter: '30' });
  assert.equal(e.retryAfter, 30);
  assert.match(e.text, /30초 뒤에 다시 해 주세요/);
});

test('410 만료: RESULT_EXPIRED(보고서)·INPUT_EXPIRED(분석) 를 그대로 쉬운 말로', async () => {
  const Hk = load();
  const f = fakeFetch((url, init) => {
    if (url === '/api/v1/auth/me') return { status: 200, body: ME };
    if (url === '/api/v3/analyses/ana_old/report') return { status: 410, body: { detail: 'RESULT_EXPIRED' } };
    if (url === '/api/v3/inputs') return { status: 201, body: { input_ref: 'inp_x', expires_at: 1 } };
    if (url === '/api/v3/analyses' && init.method === 'POST') return { status: 410, body: { detail: 'INPUT_EXPIRED' } };
  });
  const { api, client } = adapter(Hk, f);
  const r = await client.report('ana_old');
  const e = client.say(r);
  assert.equal(e.status, 410);
  assert.equal(e.code, 'RESULT_EXPIRED');
  assert.match(e.text, /결과 보관 시간이 지나/);
  const a = await api.check('안내문');
  assert.equal(a.staff.find(s => s.staff === 'ai').bubble_key, 'common.held_expired');
});

/* ---------------- 중복 POST 1회만 + request_id ---------------- */
test('같은 쓰기를 동시에 두 번 → POST 1번, 같은 request_id. 응답 유실 뒤 다시 하면 같은 request_id 를 씀', async () => {
  const Hk = load();
  let fail = true;
  const f = fakeFetch((url, init) => {
    if (url === '/api/v1/auth/me') return { status: 200, body: ME };
    if (url === '/api/v3/revoke-drafts') return { status: 201, body: {}, delay: 20 };
    if (url === '/api/v3/key-proofs') { if (fail) { fail = false; return { reject: 'TypeError' }; } return { status: 200, body: { signing_request_id: 'wsr_x', verified_at: 1, expires_at: 2 } }; }
  });
  const client = Hk.op5.createClient({ fetch: f, base: '/api', timeoutMs: 500 });
  const body = { document_id: '0x' + 'ab'.repeat(32), version: 1 };
  const [x, y] = await Promise.all([client.write('POST', '/v3/revoke-drafts', body), client.write('POST', '/v3/revoke-drafts', body)]);
  assert.equal(posts(f, '/v3/revoke-drafts').length, 1);
  assert.equal(x, y);
  assert.match(x.request_id, RID);
  assert.equal(bodyOf(posts(f, '/v3/revoke-drafts')[0]).request_id, x.request_id);
  const sub = { signing_request_id: 'wsr_x', signature: '0x' + 'a'.repeat(130) };
  const lost = await client.write('POST', '/v3/key-proofs', sub);
  assert.equal(lost.uncertain, true);
  const again = await client.write('POST', '/v3/key-proofs', sub);
  assert.equal(again.status, 200);
  const ids = posts(f, '/v3/key-proofs').map(c => bodyOf(c).request_id);
  assert.equal(ids.length, 2);
  assert.equal(ids[0], ids[1], '불확실한 뒤에는 같은 request_id 로만 다시 물음');
});

/* ---------------- 지갑 ---------------- */
function okWallet(Hk, f, signed) {
  const account = '0x' + '3'.repeat(40);
  const eth = { request: async q => {
    if (q.method === 'eth_requestAccounts') return [account];
    if (q.method === 'eth_signTypedData_v4') { signed.push(q.params); return '0x' + 'B'.repeat(130); }
    throw new Error('부르면 안 되는 지갑 방법: ' + q.method);
  } };
  const client = Hk.op5.createClient({ fetch: f, base: '/api', timeoutMs: 500 });
  return { client, account, w: Hk.op5.createWallet({ client, ethereum: () => eth }) };
}
function sr(type, signer) {
  const h = '0x' + 'ab'.repeat(32);
  const msg = { KeyProof: { action: 3, applicationId: h, issuerId: h, signer, challengeNonce: h, deadline: 9 },
    Publish: { action: 1, issuerId: h, docKey: h, documentId: h, version: 1, keyId: h, originalHash: h, protectedHash: h, contentSchema: h, signatureSchema: h, originalHashAlgorithm: 1, protectedHashAlgorithm: 1, issuedAt: 1, expiresAt: 9, nonce: '1', deadline: 5 } }[type];
  return { signing_request_id: 'wsr_' + type.toLowerCase(), primary_type: type, domain: { name: 'OriginProof', version: '1', chainId: '31337', verifyingContract: '0x' + '1'.repeat(40) }, message: msg, expected_signer: signer };
}

test('지갑 정상: key-challenges → EIP-712 서명(계약 형식) → key-proofs, 서버엔 서명 값만', async () => {
  const Hk = load();
  const signed = [];
  let acct;
  const f = fakeFetch(url => {
    if (url === '/api/v1/auth/me') return { status: 200, body: ME };
    if (url === '/api/v1/issuer-applications/mine') return { status: 200, body: { application_id: 'app_fixture' } };
    if (url === '/api/v3/key-challenges') return { status: 201, body: sr('KeyProof', acct) };
    if (url === '/api/v3/key-proofs') return { status: 200, body: { signing_request_id: 'wsr_keyproof', verified_at: 1, expires_at: 2 } };
  });
  const x = okWallet(Hk, f, signed); acct = x.account;
  const r = await x.w.keyProof();
  assert.equal(r.ok, true, r.text);
  const ch = bodyOf(posts(f, '/v3/key-challenges')[0]);
  assert.deepEqual(Object.keys(ch).sort(), ['application_id', 'request_id', 'signer']);
  assert.equal(ch.signer, acct);
  const typed = JSON.parse(signed[0][1]);
  assert.equal(typed.primaryType, 'KeyProof');
  assert.deepEqual(j(typed.types.KeyProof.map(t => t.name)), ['action', 'applicationId', 'issuerId', 'signer', 'challengeNonce', 'deadline']);
  const kp = bodyOf(posts(f, '/v3/key-proofs')[0]);
  assert.deepEqual(Object.keys(kp).sort(), ['request_id', 'signature', 'signing_request_id']);
  assert.match(kp.signature, /^0x[0-9a-f]{130}$/, '계약 형식(소문자)으로 보냄');
  for (const c of f.calls) assert.ok(!/private|mnemonic|secret/i.test(c.body), '비밀 값을 서버로 보냄');
});

test('지갑 없음(window.ethereum 없음) → "지갑 필요" 안내, 서버 쓰기 0건', async () => {
  const Hk = load();
  const f = fakeFetch(url => url === '/api/v1/auth/me' ? { status: 200, body: ME } : url === '/api/v1/issuer-applications/mine' ? { status: 200, body: { application_id: 'app_fixture' } } : { status: 500, body: {} });
  const client = Hk.op5.createClient({ fetch: f, base: '/api', timeoutMs: 500 });
  const w = Hk.op5.createWallet({ client, ethereum: () => undefined });
  const r = await w.keyProof();
  assert.equal(r.ok, false);
  assert.equal(r.code, 'WALLET_REQUIRED');
  assert.match(r.text, /브라우저 지갑이 필요해요/);
  const p = await w.publish({ doc_key: '0x' + '0'.repeat(64) });
  assert.equal(p.code, 'WALLET_REQUIRED');
  assert.equal(posts(f).length, 0);
});

test('UNKNOWN → 다시 보내지 않고 reconcile, 지갑 주소가 다르면 서명 요청 안 함', async () => {
  const Hk = load();
  const signed = [];
  let acct;
  const f = fakeFetch(url => {
    if (url === '/api/v1/auth/me') return { status: 200, body: ME };
    if (url === '/api/v3/document-drafts') return { status: 201, body: sr('Publish', acct) };
    if (url === '/api/v3/publications') return { status: 202, body: { operation_id: 'op_fixture', request_id: 'req_x', status: 'UNKNOWN', recovery_required: true, next_action: 'RECONCILE' } };
    if (url === '/api/v3/operations/op_fixture/reconcile') return { status: 202, body: { operation_id: 'op_fixture', request_id: 'req_x', status: 'SUBMITTED', recovery_required: true, next_action: 'RECONCILE' } };
  });
  const x = okWallet(Hk, f, signed); acct = x.account;
  const draft = Hk.op5.parseDraft(JSON.stringify({ doc_key: '0x' + '0'.repeat(63) + '1', expected_version: 1, expires_at: 2000000000, content: { notice_type: 'OFFICIAL_DOCUMENT', institution_code: 'c', document_type: 't', document_number: 'n', title: 'x', summary: 'y' } }), 1792000000);
  assert.equal(draft.ok, true, draft.message);
  const r = await x.w.publish(draft.body);
  assert.equal(r.ok, true, r.text);
  assert.equal(posts(f, '/v3/publications').length, 1, 'UNKNOWN 뒤에 다시 보냄');
  assert.equal(posts(f, '/v3/operations/op_fixture/reconcile').length, 1);
  assert.equal(r.data.reconciled, true);
  assert.equal(r.data.op.status, 'SUBMITTED');
  assert.equal(posts(f, '/v3/operations/op_fixture/reconcile')[0].init.headers['X-CSRF-Token'], 'fixture-csrf');
  // 작업 이력: 번호·상태만 남김
  // 다른 지갑 주소
  const s2 = await x.w.sign(sr('Publish', '0x' + '9'.repeat(40)), x.account);
  assert.equal(s2.code, 'SIGNER_MISMATCH');
  assert.equal(signed.length, 1);
});

test('거래 해시 알림: signing-requests/{id}/transactions 에 같은 signing_request_id·새 request_id, 해시 형식 검증', async () => {
  const Hk = load();
  const f = fakeFetch(url => {
    if (url === '/api/v1/auth/me') return { status: 200, body: ME };
    if (url === '/api/v3/signing-requests/wsr_publish/transactions') return { status: 202, body: { operation_id: 'op_tx', request_id: 'req_y', status: 'PENDING_SUBMISSION', recovery_required: true, next_action: 'RECONCILE' } };
  });
  const client = Hk.op5.createClient({ fetch: f, base: '/api', timeoutMs: 500, opStore: memStorage() });
  const w = Hk.op5.createWallet({ client, ethereum: () => undefined });
  const bad = await w.submitTx('wsr_publish', '0x12');
  assert.equal(bad.code, 'BAD_TX_HASH');
  const r = await w.submitTx('wsr_publish', '0x' + 'AB'.repeat(32), 'publish');
  assert.equal(r.ok, true);
  const b = bodyOf(posts(f, '/v3/signing-requests/wsr_publish/transactions')[0]);
  assert.equal(b.signing_request_id, 'wsr_publish');
  assert.equal(b.tx_hash, '0x' + 'ab'.repeat(32));
  assert.match(b.request_id, RID);
  assert.match(r.text, /아직 확정이 아니에요/);
  const ops = client.readOps();
  assert.equal(ops[0].operation_id, 'op_tx');
  assert.deepEqual(Object.keys(ops[0]).sort(), ['at', 'kind', 'next_action', 'operation_id', 'request_id', 'status']);
});

/* ---------------- CSRF ---------------- */
test('CSRF: 쓰기에는 /me 의 X-CSRF-Token, 로그인·공개 검증에는 없음, 로그인 안 했으면 쓰기를 보내지 않음', async () => {
  const Hk = load();
  let logged = true;
  const f = fakeFetch(url => {
    if (url === '/api/v1/auth/me') return logged ? { status: 200, body: ME } : { status: 401, body: { detail: 'AUTH_REQUIRED' } };
    if (url === '/api/v1/auth/login') return { status: 200, body: ME };
    if (url === '/api/v3/analyses/ana_x') return { status: 204 };
    return { status: 200, body: {} };
  });
  const client = Hk.op5.createClient({ fetch: f, base: '/api', timeoutMs: 500 });
  await client.login('fixture', 'fixture-password');
  const login = f.calls.find(c => c.url === '/api/v1/auth/login');
  assert.equal(login.init.headers['X-CSRF-Token'], undefined);
  assert.equal(login.init.credentials, 'same-origin');
  await client.removeAnalysis('ana_x');
  const del = f.calls.find(c => c.init.method === 'DELETE');
  assert.equal(del.init.headers['X-CSRF-Token'], 'fixture-csrf');
  logged = false;
  const before = f.calls.length;
  const r = await client.write('POST', '/v3/revoke-drafts', { document_id: '0x' + 'ab'.repeat(32), version: 1 });
  assert.equal(r.status, 401);
  assert.equal(client.say(r).code, 'AUTH_REQUIRED');
  assert.equal(f.calls.slice(before).filter(c => c.init.method === 'POST').length, 0, '로그인 없이 쓰기를 보냄');
  const bad = await client.login('', '');
  assert.equal(bad.error, 'bad_input');
});

/* ---------------- 삭제 후 늦은 응답 무시 ---------------- */
test('삭제 후 늦은 응답 무시: 폴링 중 지우면 완료 응답이 와도 결과를 쓰지 않음, 늦게 온 보고서도 버림', async () => {
  const Hk = load();
  const report = fixture('v3_analysis_report_DG01.synthetic.json');
  let client;
  const f = fakeFetch((url, init) => {
    if (url === '/api/v1/auth/me') return { status: 200, body: ME };
    if (url === '/api/v3/inputs') return { status: 201, body: { input_ref: 'inp_x', expires_at: 1 } };
    if (url === '/api/v3/analyses' && init.method === 'POST') return { status: 202, body: { analysis_id: 'ana_late', status: 'QUEUED', retain_report: true, retain_original: false } };
    if (url === '/api/v3/analyses/ana_late' && (init.method || 'GET') === 'GET') { client.removeAnalysis('ana_late'); return { status: 200, body: { analysis_id: 'ana_late', status: 'COMPLETED', retain_report: true, retain_original: false, report }, delay: 10 }; }
    if (url === '/api/v3/analyses/ana_late' && init.method === 'DELETE') return { status: 204 };
    if (url === '/api/v3/analyses/ana_slow/report') return { status: 200, body: report, delay: 30 };
    if (url === '/api/v3/analyses/ana_slow' && init.method === 'DELETE') return { status: 204 };
  });
  const x = adapter(Hk, f); client = x.client;
  x.api = Hk.createApiAdapter({ fetch: f, base: '/api', csrf: client.csrf, isDeleted: client.isDeleted, timeoutMs: 500, pollMs: 5 });
  const a = await x.api.check('안내문');
  assert.equal(a.analysis_deleted, true);
  assert.equal(a.staff.find(s => s.staff === 'ai').bubble_key, 'ai.cancelled');
  assert.ok(!a.axes.find(x => x.axis === 'ai').body.includes(report.evidence && report.evidence[0] ? report.evidence[0].quote : '@@없음@@'));
  // 늦게 오는 보고서
  const pending = client.report('ana_slow');
  await client.removeAnalysis('ana_slow');
  const late = await pending;
  assert.equal(late.ignored, true);
  const n = f.calls.length;
  const after = await client.report('ana_slow');
  assert.equal(after.ignored, true);
  assert.equal(f.calls.length, n, '지운 뒤에 서버를 다시 부름');
});

/* ---------------- 입력 검증 ---------------- */
test('입력 검증: 발행 초안·철회·거래 해시·연결 주소', () => {
  const Hk = load();
  const O = Hk.op5;
  const ok = { doc_key: '0x' + '0'.repeat(63) + '1', expected_version: 1, expires_at: 2000000000, content: { notice_type: 'PAYMENT_REQUEST', amount_minor: 85000, currency: 'KRW', payee_bank_name: '은행', payee_account_number: '123-456-789012', payee_account_holder: '예금주', payment_purpose: '결제', due_at: 1 } };
  assert.equal(O.parseDraft(JSON.stringify(ok), 1792000000).ok, true);
  for (const [patch, re] of [
    [{ doc_key: '0xAB' }, /doc_key/], [{ expected_version: 0 }, /expected_version/], [{ expires_at: 1 }, /지난 시각/],
    [{ request_id: 'req_x' }, /모르는 항목/], [{ content: Object.assign({}, ok.content, { currency: 'krw' }) }, /currency/],
    [{ content: Object.assign({}, ok.content, { official_url: 'http://x' }) }, /https/], [{ content: { notice_type: 'X' } }, /notice_type/]
  ]) assert.match(O.parseDraft(JSON.stringify(Object.assign({}, ok, patch)), 1792000000).message, re);
  assert.match(O.parseDraft('{oops', 0).message, /JSON/);
  assert.deepEqual(j(O.parseRevoke('0x' + 'AB'.repeat(32) + ' 2').body), { document_id: '0x' + 'ab'.repeat(32), version: 2 });
  assert.equal(O.parseRevoke('0x12 1').ok, false);
  assert.equal(O.parseTxHash('0x' + 'f'.repeat(64)).ok, true);
  assert.equal(O.parseTxHash('0x' + 'g'.repeat(64)).ok, false);
  assert.equal(O.parseBase('/api').value, '/api');
  assert.equal(O.parseBase('http://127.0.0.1:8000').value, 'http://127.0.0.1:8000');
  for (const bad of ['//evil.example', 'https://evil.example', 'javascript:alert(1)', '/a b', '']) assert.equal(O.parseBase(bad).ok, false, bad);
  assert.equal(O.RE.ana.test('ana_x/../y'), false);
});

test('첨부 업로드 자리: 계약에 경로가 없어 보내지 않고 연결 전', async () => {
  const Hk = load();
  const r = await Hk.op5.uploadAttachment({ name: 'a.png' });
  assert.equal(r.ok, false);
  assert.equal(r.code, 'UPLOAD_NOT_CONNECTED');
});


test('분석 표시: 실제 서버 보고서·규칙 fallback·기록 응답·예시·미연결을 구분', () => {
  const Hk = load(), caption = Hk.op5.analysisCaption;
  assert.match(caption({ analysis_status: 'COMPLETED', ai_report: { limitations: [] } }), /서버 보고서/);
  assert.ok(!caption({ analysis_status: 'COMPLETED', ai_report: { limitations: [] } }).includes('연결 전'));
  assert.match(caption({ analysis_status: 'COMPLETED', ai_report: { limitations: ['LLM_ANALYSIS_UNAVAILABLE:TIMEOUT'] } }), /규칙 검사 · AI 분석 사용 불가/);
  assert.match(caption({ analysis_status: 'COMPLETED', ai_report: { limitations: ['MOCK_REPLAY_NOT_MODEL_PERFORMANCE'] } }), /기록 응답/);
  assert.match(caption({ sample: true, analysis_status: 'COMPLETED', ai_report: { limitations: [] } }), /예시 응답/);
  assert.match(caption({ analysis_status: 'FAILED' }), /연결 전/);
});
