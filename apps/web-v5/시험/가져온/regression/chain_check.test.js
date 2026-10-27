// 체인에서 직접 확인(web-prototype/js/chain_check.js) 시험. node 기본 모듈만(설치 없음), 브라우저를 띄우지 않음.
//   node --test tools/chain_check.test.js
// 체인 응답은 가짜 RPC 노드(아래 fakeNode)가 만듦. 값은 모두 지어낸 것이며 실제 체인 기록이 아님.
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { fakeFetch, memStorage, WEB } = require('./_load.js');

const C = require('../../../페이지/js/chain_check.js');
const VEC = JSON.parse(fs.readFileSync(path.join(__dirname, '../../fixtures', 'chain_abi_vectors.json'), 'utf8'));
const read = f => fs.readFileSync(path.join(WEB, f), 'utf8');

/* ---------------- 가짜 체인 값 ---------------- */
const h32 = b => '0x' + b.repeat(32);
const REG = '0x' + 'ab'.repeat(20);
const DOC = {
  document_id: h32('11'), issuer_id: h32('22'), doc_key: h32('33'), key_id: h32('44'),
  original_hash: h32('a1'), protected_hash: h32('b2'), content_schema: h32('c3'),
  version: 1, latest_version: 1, state: 'ACTIVE', warnings: [], issued_at: 1700000000, expires_at: 1900000000, original_available: false
};
function v3Response(over) {
  return Object.assign({
    session_id: 'vsn_test', verification_status: 'INCONCLUSIVE', comparison_scope: 'ID_ONLY',
    document: Object.assign({}, DOC), checks: [{ name: 'current_state', status: 'PASSED' }], reason_codes: [],
    checked_at: 1800000000, chain_id: '31337', verifying_contract: REG, block_number: '120', block_hash: h32('99')
  }, over || {});
}
const w = n => BigInt(n).toString(16).padStart(64, '0');
const b = h => h.slice(2);
const STATE_NO = { ACTIVE: 1, REVOKED: 2, SUPERSEDED: 3 };
function docHex(d) {
  return '0x' + [b(d.issuer_id), b(d.doc_key), w(d.version), b(d.key_id), b(d.original_hash), b(d.protected_hash), b(d.content_schema),
    w(d.issued_at), w(d.expires_at), w(1700000100), w(100), w(STATE_NO[d.state] || d.state)].join('');
}

// 가짜 RPC 노드: eth_chainId·eth_call(3 함수)·eth_getTransactionReceipt 만 앎. 모르는 방법은 -32601
function fakeNode(o) {
  o = Object.assign({ chainId: '0x7a69', doc: DOC, latest: 1, issuerState: 1, receipt: null }, o || {});
  return fakeFetch((url, init) => {
    if (o.down) return { reject: 'TypeError' };
    if (o.http) return { status: o.http, body: {} };
    const req = JSON.parse(init.body);
    const ok = result => ({ status: 200, body: { jsonrpc: '2.0', id: o.badId ? 999 : req.id, result } });
    const revert = sel => ({ status: 200, body: { jsonrpc: '2.0', id: req.id, error: { code: 3, message: 'execution reverted', data: sel } } });
    if (req.method === 'eth_chainId') return ok(o.chainId);
    if (req.method === 'eth_getTransactionReceipt') return ok(o.receipt);
    if (req.method !== 'eth_call') return { status: 200, body: { jsonrpc: '2.0', id: req.id, error: { code: -32601, message: 'method not found' } } };
    const data = req.params[0].data;
    if (req.params[0].to !== REG) return ok('0x');
    if (data.startsWith(C.SELECTORS.getDocument)) return o.doc ? ok(docHex(o.doc)) : revert(C.SELECTORS.UnknownDocument);
    if (data.startsWith(C.SELECTORS.latestVersion)) return ok('0x' + w(o.latest));
    if (data.startsWith(C.SELECTORS.getIssuer)) return o.issuerState ? ok('0x' + w(o.issuerState) + b(DOC.key_id) + '0'.repeat(24) + '5e'.repeat(20) + w(0)) : revert(C.SELECTORS.UnknownIssuer);
    return ok('0x');
  });
}
const ANVIL = { rpcUrl: 'http://127.0.0.1:8545', registry: REG, chainId: '31337' };
const SEP = { rpcUrl: 'https://rpc.sepolia.example', registry: REG, chainId: '11155111' };
const liveAnswer = (resp) => ({ sample: false, chain_claim: C.claimFrom(resp || v3Response()) });
const methods = f => f.calls.map(c => JSON.parse(c.body).method);

/* ---------------- ABI ---------------- */
test('selector 상수 = 파이썬 순수 keccak256 값(tools/chain_abi_check.py), 함수·오류 5개', () => {
  assert.deepEqual(C.SELECTORS, VEC.selectors);
  assert.equal(VEC.keccak_empty, '0xc5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470');   // 알려진 keccak256('')
  assert.equal(VEC.keccak_transfer_sig, '0xa9059cbb');                                                     // 알려진 ERC-20 transfer
});

test('인코딩: 호출 데이터가 파이썬 계산 값과 같음, 범위 밖·형식 틀림은 거절', () => {
  assert.equal(C.encodeCall('latestVersion', [VEC.inputs.documentId]), VEC.calls.latestVersion);
  assert.equal(C.encodeCall('getDocument', [VEC.inputs.documentId, VEC.inputs.version]), VEC.calls.getDocument_v2);
  assert.equal(C.encodeCall('getIssuer', [VEC.inputs.issuerId]), VEC.calls.getIssuer);
  assert.throws(() => C.encodeCall('getDocument', [VEC.inputs.documentId, 2n ** 64n]));
  assert.throws(() => C.encodeCall('getDocument', [VEC.inputs.documentId, -1]));
  assert.throws(() => C.encodeCall('latestVersion', ['0x1234']));
  assert.throws(() => C.encodeCall('transfer', []));
});

test('디코딩: struct 12칸·uint64·(uint8,bytes32,address,bytes32)가 파이썬 값과 같음, 길이·위쪽 비트 틀리면 거절', () => {
  assert.deepEqual(C.decodeDocument(VEC.returns.getDocument), VEC.returns.getDocument_fields);
  assert.equal(C.decodeLatestVersion(VEC.returns.latestVersion_3), 3);
  assert.deepEqual(C.decodeIssuer(VEC.returns.getIssuer), VEC.returns.getIssuer_fields);
  assert.throws(() => C.decodeDocument('0x'));                                     // 계약 없는 주소의 빈 응답
  assert.throws(() => C.decodeDocument(VEC.returns.getDocument + '00'.repeat(32))); // 13칸
  assert.throws(() => C.decodeLatestVersion('0x' + 'f'.repeat(64)));                // uint64 범위 밖
  assert.throws(() => C.decodeIssuer('0x' + w(256) + '00'.repeat(96)));             // uint8 범위 밖
  assert.throws(() => C.decodeIssuer('0x' + w(1) + '00'.repeat(32) + '01' + '00'.repeat(31) + '00'.repeat(32))); // address 위쪽 바이트
});

/* ---------------- 설정 ---------------- */
test('설정: 기본 빈칸, 입력 검증(바깥 http·계정 정보·# 거절, https 허용), 따로 저장(jjin.chain.v1)', () => {
  assert.deepEqual(C.normalizeSettings(null), { rpcUrl: '', registry: '', chainId: '' });
  assert.equal(C.checkRpcUrl('http://127.0.0.1:8545').value, 'http://127.0.0.1:8545/');
  assert.equal(C.checkRpcUrl('https://rpc.sepolia.example/v1').ok, true);
  for (const bad of ['http://rpc.example.com', 'ftp://127.0.0.1', 'javascript:alert(1)', 'https://u:p@rpc.example', 'https://rpc.example/#x', 'x'.repeat(301), 42]) {
    assert.equal(C.checkRpcUrl(bad).ok, false, String(bad));
  }
  assert.equal(C.checkRegistry('0x' + 'AB'.repeat(20)).value, REG);
  for (const bad of ['0x123', '0x' + '0'.repeat(40), 'ab'.repeat(20), '0x' + 'g'.repeat(40)]) assert.equal(C.checkRegistry(bad).ok, false, bad);
  assert.equal(C.checkChainId(' 31337 ').value, '31337');
  for (const bad of ['0', '-1', '1.5', 'abc', '99999999999999999']) assert.equal(C.checkChainId(bad).ok, false, bad);
  const ls = memStorage();
  const s = C.createStore(ls);
  assert.deepEqual(s.get(), { rpcUrl: '', registry: '', chainId: '' });
  assert.equal(s.set('rpcUrl', 'http://evil.example').ok, false);
  assert.equal(s.get().rpcUrl, '');                                                // 틀린 값은 저장 안 함
  assert.equal(s.set('rpcUrl', 'http://127.0.0.1:8545').ok, true);
  assert.equal(s.set('chainId', '31337').ok, true);
  assert.deepEqual(Object.keys(ls.mem), ['jjin.chain.v1']);                          // 기존 설정 키(jjin.settings.v1)를 건드리지 않음
  assert.deepEqual(C.createStore(ls).get(), { rpcUrl: 'http://127.0.0.1:8545/', registry: '', chainId: '31337' });
  assert.deepEqual(C.createStore({ getItem() { throw new Error('x'); }, setItem() { throw new Error('y'); } }).get(), { rpcUrl: '', registry: '', chainId: '' });
});

/* ---------------- 호출하지 않는 경우 ---------------- */
test('예시 응답: "예시라 체인 확인 불가", RPC 0회(설정이 다 있어도)', async () => {
  const f = fakeNode();
  for (const ans of [{ id: 'normal' }, { sample: true }, {}]) {
    const r = await C.verify({ answer: ans, settings: ANVIL, fetch: f });
    assert.equal(r.kind, 'sample');
    assert.equal(r.headline, '예시라 체인 확인 불가');
    assert.equal(r.rows.length, 0);
  }
  assert.equal(f.calls.length, 0);
});

test('설정 빈칸: "연결 전", RPC 0회, 빠진 칸 이름 안내', async () => {
  const f = fakeNode();
  const r = await C.verify({ answer: liveAnswer(), settings: { rpcUrl: '', registry: REG, chainId: '31337' }, fetch: f });
  assert.equal(r.kind, 'not_configured');
  assert.equal(r.headline, '연결 전');
  assert.match(r.body, /체인 RPC 주소/);
  const r2 = await C.verify({ answer: liveAnswer(), settings: null, fetch: f });
  assert.match(r2.body, /체인 RPC 주소·레지스트리 주소·체인 ID/);
  // 저장된 값이 틀려도(직접 고친 저장소) 정리 뒤 빈칸이면 부르지 않음
  const r3 = await C.verify({ answer: liveAnswer(), settings: { rpcUrl: 'http://evil.example', registry: REG, chainId: '31337' }, fetch: f });
  assert.equal(r3.kind, 'not_configured');
  assert.equal(f.calls.length, 0);
});

test('서버 응답에 체인 값이 없음(v1 등): 판단 보류, RPC 0회', async () => {
  const f = fakeNode();
  const r = await C.verify({ answer: { sample: false, chain_claim: null }, settings: ANVIL, fetch: f });
  assert.equal(r.kind, 'no_claim');
  assert.equal(f.calls.length, 0);
  assert.equal(C.claimFrom(v3Response({ document: null })), null);
  assert.equal(C.claimFrom(v3Response({ verifying_contract: 'nope' })), null);
  assert.equal(C.claimFrom(Object.assign(v3Response(), { document: Object.assign({}, DOC, { original_hash: '0xZZ' }) })), null);
});

/* ---------------- 호출하는 경우 ---------------- */
test('일치: "체인 기록과 일치(독립 확인)", 부른 방법은 eth_chainId·eth_call 만, 받는 주소는 설정한 레지스트리', async () => {
  const f = fakeNode();
  const r = await C.verify({ answer: liveAnswer(), settings: ANVIL, fetch: f });
  assert.equal(r.kind, 'match', JSON.stringify(r.rows));
  assert.equal(r.headline, '체인 기록과 일치(독립 확인)');
  assert.equal(r.say, '체인 기록과 일치(독립 확인)');
  assert.deepEqual(methods(f), ['eth_chainId', 'eth_call', 'eth_call', 'eth_call']);
  for (const c of f.calls) {
    assert.equal(c.url, 'http://127.0.0.1:8545/');
    assert.equal(c.init.method, 'POST');
    assert.equal(c.init.credentials, 'omit');
    const p = JSON.parse(c.body);
    if (p.method === 'eth_call') { assert.equal(p.params[0].to, REG); assert.deepEqual(Object.keys(p.params[0]).sort(), ['data', 'to']); assert.equal(p.params[1], 'latest'); }
  }
  for (const k of ['버전', '최신 버전', '원본 해시', '보호 항목 해시', '상태', '발행 기관 ID', '발행 기관 상태', '체인 ID', '레지스트리 주소']) assert.ok(r.checked.includes(k), k);
  assert.deepEqual(r.links, []);                     // 31337: Etherscan 없음
});

test('불일치: 다른 항목을 서버값 vs 체인값으로 나열, 기록관 말풍선에 같은 항목 이름', async () => {
  const f = fakeNode({ doc: Object.assign({}, DOC, { state: 'REVOKED', original_hash: h32('ee') }), latest: 2, issuerState: 2 });
  const r = await C.verify({ answer: liveAnswer(), settings: ANVIL, fetch: f });
  assert.equal(r.kind, 'mismatch');
  assert.equal(r.headline, '체인 기록과 다름');
  const by = Object.fromEntries(r.rows.map(x => [x.label, x]));
  assert.deepEqual(by['상태'], { label: '상태', server: '유효', chain: '철회됨' });
  assert.deepEqual(by['원본 해시'], { label: '원본 해시', server: DOC.original_hash, chain: h32('ee') });
  assert.deepEqual(by['최신 버전'], { label: '최신 버전', server: '1', chain: '2' });
  assert.deepEqual(by['발행 기관 상태'], { label: '발행 기관 상태', server: '활성', chain: '정지' });
  assert.equal(r.rows.length, 4);
  assert.equal(r.say, '체인 기록과 다름: ' + r.rows.map(x => x.label).join(', '));
  // 서버가 말한 체인 ID·컨트랙트가 설정과 다르면 그것도 항목으로
  const r2 = await C.verify({ answer: liveAnswer(v3Response({ chain_id: '1', verifying_contract: '0x' + 'cd'.repeat(20) })), settings: ANVIL, fetch: fakeNode() });
  assert.deepEqual(r2.rows.map(x => x.label), ['체인 ID', '레지스트리 주소']);
});

test('체인에 문서·기관이 없음(UnknownDocument·UnknownIssuer 되돌림): 불일치로 나열', async () => {
  const r = await C.verify({ answer: liveAnswer(), settings: ANVIL, fetch: fakeNode({ doc: null, latest: 0, issuerState: 0 }) });
  assert.equal(r.kind, 'mismatch');
  assert.deepEqual(r.rows.map(x => x.label), ['문서 기록', '최신 버전', '발행 기관']);
  assert.deepEqual(r.rows[0], { label: '문서 기록', server: '있음 (버전 1)', chain: '없음' });
});

test('만료는 계산: 체인 ACTIVE + 확인 시각 >= 만료 시각 = 만료 (서버 규칙과 같음)', async () => {
  const exp = v3Response({ checked_at: 1950000000, document: Object.assign({}, DOC, { state: 'EXPIRED' }) });
  assert.equal((await C.verify({ answer: liveAnswer(exp), settings: ANVIL, fetch: fakeNode() })).kind, 'match');
  const r = await C.verify({ answer: liveAnswer(), settings: ANVIL, fetch: fakeNode({ doc: Object.assign({}, DOC, { expires_at: 1750000000 }) }) });
  assert.ok(r.rows.some(x => x.label === '상태' && x.chain === '만료'));
});

test('RPC 실패: 꺼짐·HTTP 오류·JSON-RPC 모양 틀림·모르는 되돌림·계약 없는 주소 → "체인에 연결하지 못함 — 판단 보류"', async () => {
  const cases = [
    fakeNode({ down: true }), fakeNode({ http: 500 }), fakeNode({ badId: true }),
    fakeFetch((u, i) => { const q = JSON.parse(i.body); return q.method === 'eth_chainId' ? { status: 200, body: { jsonrpc: '2.0', id: q.id, result: '0x7a69' } } : { status: 200, body: { jsonrpc: '2.0', id: q.id, error: { code: 3, message: 'execution reverted', data: '0xdeadbeef' } } }; })
  ];
  for (const f of cases) {
    const r = await C.verify({ answer: liveAnswer(), settings: ANVIL, fetch: f });
    assert.equal(r.kind, 'rpc_fail');
    assert.equal(r.headline, '체인에 연결하지 못함 — 판단 보류');
    assert.equal(r.rows.length, 0);
  }
  const other = await C.verify({ answer: liveAnswer(), settings: Object.assign({}, ANVIL, { registry: '0x' + 'cd'.repeat(20) }), fetch: fakeNode() });
  assert.equal(other.kind, 'rpc_fail');               // 빈 응답 '0x' 는 값으로 만들지 않음
});

test('RPC 시간 초과도 판단 보류', async () => {
  const r = await C.verify({ answer: liveAnswer(), settings: ANVIL, fetch: fakeFetch(() => ({ hang: true })), timeoutMs: 30 });
  assert.equal(r.kind, 'rpc_fail');
});

test('eth_chainId 가 설정 체인 ID와 다르면 판단 보류, 그 뒤 호출 없음', async () => {
  const f = fakeNode({ chainId: '0xaa36a7' });
  const r = await C.verify({ answer: liveAnswer(), settings: ANVIL, fetch: f });
  assert.equal(r.kind, 'chain_hold');
  assert.match(r.headline, /판단 보류/);
  assert.deepEqual(methods(f), ['eth_chainId']);
});

test('Anvil·Sepolia 같은 코드: 설정만 바꾸면 같은 호출 순서, Etherscan 링크는 11155111 일 때만', async () => {
  const fa = fakeNode();
  const fs1 = fakeNode({ chainId: '0xaa36a7' });
  const ra = await C.verify({ answer: liveAnswer(), settings: ANVIL, fetch: fa });
  const rs = await C.verify({ answer: liveAnswer(v3Response({ chain_id: '11155111' })), settings: SEP, fetch: fs1 });
  assert.equal(ra.kind, 'match');
  assert.equal(rs.kind, 'match');
  assert.deepEqual(methods(fa), methods(fs1));
  assert.deepEqual(fa.calls.map(c => JSON.parse(c.body).params), fs1.calls.map(c => JSON.parse(c.body).params));
  assert.equal(fs1.calls[0].url, 'https://rpc.sepolia.example/');
  assert.deepEqual(ra.links, []);
  assert.deepEqual(rs.links, [{ label: 'Etherscan(Sepolia)에서 레지스트리 보기', href: 'https://sepolia.etherscan.io/address/' + REG }]);
  assert.deepEqual(C.explorerLinks('1', REG, null), []);
  assert.deepEqual(C.explorerLinks('31337', REG, h32('77')), []);
  // 판단 보류·예시·연결 전에는 링크 없음
  const bad = await C.verify({ answer: liveAnswer(), settings: SEP, fetch: fakeNode({ down: true }) });
  assert.deepEqual(bad.links, []);
});

test('거래 해시: 서버 응답에 있을 때만 eth_getTransactionReceipt, 영수증 실패·없음은 불일치', async () => {
  const withTx = v3Response({ tx_hash: h32('77') });
  const f1 = fakeNode({ receipt: { status: '0x1', to: REG } });
  const r1 = await C.verify({ answer: liveAnswer(withTx), settings: ANVIL, fetch: f1 });
  assert.equal(r1.kind, 'match');
  assert.ok(methods(f1).includes('eth_getTransactionReceipt'));
  const r2 = await C.verify({ answer: liveAnswer(withTx), settings: ANVIL, fetch: fakeNode({ receipt: { status: '0x0', to: REG } }) });
  assert.deepEqual(r2.rows.map(x => x.label), ['거래 결과']);
  const r3 = await C.verify({ answer: liveAnswer(withTx), settings: ANVIL, fetch: fakeNode({ receipt: null }) });
  assert.deepEqual(r3.rows.map(x => x.label), ['거래 영수증']);
  const f4 = fakeNode();
  await C.verify({ answer: liveAnswer(), settings: ANVIL, fetch: f4 });
  assert.ok(!methods(f4).includes('eth_getTransactionReceipt'));
});

/* ---------------- 정적 검사 ---------------- */
test('읽기 전용: 개인키·서명·거래 보내기·외부 라이브러리·CDN 0건, 허용 방법 3개만', () => {
  const src = read('js/chain_check.js');
  const code = src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');   // 주석 블록·주석 줄만 뺌(문자열 안 주소는 남김)
  for (const re of [/privateKey|private_key|mnemonic|개인키/i, /eth_sendTransaction|eth_sendRawTransaction|eth_sign|personal_sign|signTypedData|['"]wallet_/, /\brequire\(|\bimport\b|<script|https?:\/\/(?!sepolia\.etherscan\.io\/|127\.0\.0\.1:8545)/, /\bviem\b|\bethers\b|\bweb3\b/i]) {
    assert.ok(!re.test(code), String(re));
  }
  assert.deepEqual(C.METHODS, ['eth_chainId', 'eth_call', 'eth_getTransactionReceipt']);
  const all = fs.readdirSync(path.join(WEB, 'js')).map(n => read('js/' + n)).join('\n') + read('index.html');
  assert.ok(!/eth_sendTransaction|eth_sendRawTransaction|privateKey|\bviem\b|\bethers\b|cdn\.|unpkg|jsdelivr/i.test(all));
  assert.ok(!fs.existsSync(path.join(WEB, 'package.json')) && !fs.existsSync(path.join(WEB, '..', 'package.json')));
});

test('rpc 함수는 허용 밖 방법을 막음(eth_sendTransaction 은 fetch 까지 가지 않음)', async () => {
  // verify 안의 rpc 는 밖으로 내보내지 않으므로, 허용 목록 검사 코드가 있는지 소스로 확인
  const src = read('js/chain_check.js');
  assert.ok(src.includes("if (METHODS.indexOf(method) < 0) return Promise.reject(new RpcError('blocked'"));
});

test('화면 연결: 단추·결과 카드·기록관 말풍선이 같은 결과(r.say)를 씀, 스크립트 순서', {skip:'5안 미사용: web-2안 화면 전용 파일(app.js·index.html·staff.js) 정적 확인'}, () => {
  const app = read('js/app.js');
  assert.ok(app.includes("Hk.office.say('ledger', r.say, r.tone);"));
  assert.ok(app.includes("card.appendChild(el('p', 'chain-result-head', r.headline));"));
  assert.ok(app.includes("chain.zone.appendChild(chainBtn);"));
  const html = read('index.html');
  assert.ok(html.indexOf('js/chain_check.js') > 0 && html.indexOf('js/chain_check.js') < html.indexOf('js/api_adapter.js'));
  for (const id of ['chainRpc', 'chainRegistry', 'chainIdInput', 'chainStatus']) assert.ok(html.includes('id="' + id + '"'), id);
  assert.ok(read('js/op5_staff.js').includes('function say(id, text, tone)'));
});

test('문구 4종이 대표 명령 글자와 정확히 같음', () => {
  assert.equal(C.TEXT.match, '체인 기록과 일치(독립 확인)');
  assert.equal(C.TEXT.rpc_fail, '체인에 연결하지 못함 — 판단 보류');
  assert.equal(C.TEXT.sample, '예시라 체인 확인 불가');
  assert.equal(C.TEXT.mismatch, '체인 기록과 다름');
});

/* ---------------- 서버 응답 → chain_claim (api_adapter.js) ---------------- */
test('실제 서버 v3 응답이면 답에 chain_claim 이 붙고, 그 값으로 체인 확인이 일치', async () => {
  const sb = { console, setTimeout, clearTimeout, AbortController, crypto: globalThis.crypto, Promise, URL };
  sb.window = sb; sb.self = sb;
  vm.createContext(sb);
  for (const f of ['data/sample_data.js', 'js/text_tools.js', 'js/adapter.js', 'js/op5_staff.js', 'js/chain_check.js', 'js/api_adapter.js']) vm.runInContext(read(f), sb, { filename: f });
  const resp = v3Response();
  const server = fakeFetch((url) => url.endsWith('/v3/verifications') ? { status: 200, body: resp } : { status: 401, body: { detail: 'AUTH_REQUIRED' } });
  const api = sb.Hk.createApiAdapter({ fetch: server, serverUrl: 'http://127.0.0.1:8000', viaProxy: false, timeoutMs: 500 });
  const a = await api.check(JSON.stringify({ document_id: DOC.document_id, version: 1 }));
  assert.equal(a.sample, false);
  assert.equal(a.chain_claim.document.document_id, DOC.document_id);
  assert.equal(a.chain_claim.verifying_contract, REG);
  const r = await C.verify({ answer: JSON.parse(JSON.stringify(a)), settings: ANVIL, fetch: fakeNode() });
  assert.equal(r.kind, 'match');
  // v1 결과에는 chain_claim 없음
  const v1 = fakeFetch((url) => url.endsWith('/v1/mvp/card-notices/verify') ? { status: 200, body: { verification_status: 'VERIFIED', checks: { issuer: 'ACTIVE', signature: 'PASS', payload_hash: 'PASS', candidate_match: 'PASS' }, reason_codes: [], lifecycle_status: 'ACTIVE' } } : { status: 401, body: {} });
  const a1 = await sb.Hk.createApiAdapter({ fetch: v1, serverUrl: 'http://127.0.0.1:8000', viaProxy: false, timeoutMs: 500 }).check(JSON.stringify({ proof_id: 'prf_demo_001', amount_minor: 85000 }));
  assert.equal(a1.chain_claim, null);
});
