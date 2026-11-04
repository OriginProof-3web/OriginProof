// 기관 상태 화면 역할별 구분(대표 지시 2026-11-04): 운영자만 연결 설정·서버 상태·4단추·2-of-3 패널,
// 개인·기관은 아이디·공개 블록체인 연결 정보·이용 가능한 기관.   node --test 시험/op5_role_status.test.js
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { build, threadText, menu, find, sleep, serverDouble, ROOT } = require('./_review_harness.js');

const STAFF_BUTTONS = ['예시 모드로 바꾸기', '연결 다시 확인', '연결 주소 바꾸기', '보관 선택 바꾸기'];
const SEPOLIA_NET = { status: 200, body: { chain_target: 'sepolia', chain_id: 11155111, rpc_fallback_configured: false, approver_nodes: [] } };

async function open(persona, over) {
  const f = serverDouble({ persona, over });
  const d = build('?mode=api', f);
  await sleep(10);
  menu(d, 'status'); await sleep(60);
  return { d, f, text: threadText(d) };
}

for (const persona of [
  { role: 'recipient', issuer_id: null, username: 'kim_tester' },
  { role: 'issuer', issuer_id: 'iss_origin_mock_bank', username: 'bank_staff' }
]) {
  test('개인·기관(' + persona.role + '): 연결 설정·서버 상태·4단추·2-of-3 패널 없음, 아이디·공개 체인·이용 가능한 기관', async () => {
    const { d, f, text } = await open(persona);
    for (const l of STAFF_BUTTONS) assert.equal(find(d, l), undefined, l);
    for (const t of ['연결 설정', '서버 상태', 'live:', '기관 활성화 · 2-of-3', '승인 노드 #1', '참여 효과', '역할 ']) assert.ok(!text.includes(t), t);
    assert.equal(f.calls.filter(c => /\/health\//.test(c.url)).length, 0, '서버 상태를 묻지 않음');
    assert.match(text, persona.role === 'recipient' ? /아이디 kim_tester/ : /아이디 bank_staff/);
    assert.match(text, /공개 블록체인 연결 정보/);
    assert.match(text, /연결된 블록체인: 시연용 블록체인/);
    assert.match(text, /이용 가능한 기관/);
    assert.match(text, /이용 가능한 기관 · 2곳\s*1\s*Origin Mock Bank\s*활성 · 블록체인 확인[\s\S]*2\s*Origin Mock Office\s*활성 · 블록체인 확인/);
    assert.equal(d.doc.querySelectorAll('#chatThread .op-gov-row').length, 2, '기관마다 카드 한 줄');
    assert.ok(f.calls.some(c => /\/v1\/chain\/issuers$/.test(c.url)), '활성 기관 목록은 서버에서 받음');
    menu(d, 'operations'); await sleep(30);
    assert.equal(find(d, '보관 선택 바꾸기'), undefined, '작업 이력 화면에도 없음');
  });
}

test('운영자: 예전 내용(연결 설정·서버 상태·4단추·2-of-3 패널·공동승인 단추) 그대로, 역할 글자는 없음', async () => {
  const { d, text } = await open({ role: 'operator', issuer_id: null, username: 'originproof' });
  for (const l of STAFF_BUTTONS.concat(['공동승인 제안 조회', '로그아웃'])) assert.ok(find(d, l), l);
  for (const t of ['연결 설정', '서버 상태(/health/live · /health/ready)', 'live: ', '기관 활성화 · 2-of-3 공동승인', '승인 노드 #3', '체인 네트워크', '아이디 originproof']) assert.ok(text.includes(t), t);
  assert.ok(!text.includes('역할 '), '역할 표시 없음');
  assert.ok(!text.includes('이용 가능한 기관'), '운영자 화면은 공동승인 패널');
  menu(d, 'operations'); await sleep(30);
  assert.ok(find(d, '보관 선택 바꾸기'));
});

test('Sepolia 이면 등록부 주소와 Etherscan 링크, 주소는 배포 기록 파일과 같음', async () => {
  const dep = JSON.parse(fs.readFileSync(path.join(ROOT, '../../packages/contracts/deployments/11155111.wallet.json'), 'utf8'));
  const addr = dep.contracts.OriginProofWalletRegistry.address.toLowerCase();
  const { d, text } = await open({ role: 'recipient', issuer_id: null }, u => u === '/v1/chain/network' ? SEPOLIA_NET : null);
  assert.match(text, /연결된 블록체인: 이더리움 Sepolia 공개 테스트넷/);
  assert.ok(text.includes('등록부 주소(전문가용): ' + addr.slice(0, 8) + '…' + addr.slice(-4)));
  const a = d.doc.querySelectorAll('#chatThread a').filter(x => x.href === 'https://sepolia.etherscan.io/address/' + addr);
  assert.equal(a.length, 1);
  assert.equal(a[0].rel, 'noopener noreferrer');
});

test('로컬 Anvil 이면 Etherscan 링크 없음', async () => {
  const { d } = await open({ role: 'recipient', issuer_id: null });
  assert.equal(d.doc.querySelectorAll('#chatThread a').filter(x => /etherscan/.test(String(x.href))).length, 0);
  assert.match(threadText(d), /시연용 블록체인이라 공개 탐색기\(Etherscan\)에서는 볼 수 없어요/);
});

test('비로그인: 개인 화면과 같음(운영자 연결 설정·2-of-3·모드 단추 없음), 공개 목록만 읽고 기관 전용 메뉴는 숨김', async () => {
  const f = serverDouble({ over: u => u === '/v1/auth/me' ? { status: 401, body: { detail: 'AUTH_REQUIRED' } } : null });
  const d = build('?mode=api', f, w => { const b = w.document.createElement('button'); b.id = 'authBtn'; w.document.body.append(b); });
  const side = d.doc.getElementById('sidebar-root');
  for (const t of ['공개키 관리', '발행 목록', '기관 상태']) { const b = d.doc.createElement('button'); b.textContent = t; side.append(b); }
  await sleep(10);
  menu(d, 'status'); await sleep(60);
  assert.deepEqual(f.calls.map(c => c.url).filter(u => !/auth\/me$/.test(u)).sort(), ['/api/v1/chain/issuers', '/api/v1/chain/network'], '공개 목록 GET 두 개만');
  assert.ok(f.calls.every(c => (c.init.method || 'GET') === 'GET'));
  const t = threadText(d);
  for (const x of ['연결 설정', '2-of-3', '서버 상태']) assert.ok(!t.includes(x), x);
  assert.match(t, /로그인하지 않았어요/);
  assert.match(t, /이용 가능한 기관 · 2곳/);
  assert.match(t, /공개 블록체인 연결 정보/);
  for (const l of STAFF_BUTTONS) assert.equal(find(d, l), undefined, l);
  assert.equal(find(d, '실서버 모드로 바꾸기'), undefined);
  assert.ok(find(d, '로그인 화면 열기'));
  const shown = side.querySelectorAll('button').filter(b => b.style.display !== 'none').map(b => b.textContent);
  for (const x of ['공개키 관리', '발행 목록']) assert.ok(!shown.includes(x), x);
  assert.ok(shown.includes('기관 상태'));   // '새 Proof 발행'→'새 대화' 글자 바꾸기는 번들 DOM(글자 노드)에서만 확인 가능
});

test('?demo= 시연 화면은 비로그인이어도 예전 예시 화면 그대로(연결 설정·2-of-3)', async () => {
  const f = serverDouble({ over: u => u === '/v1/auth/me' ? { status: 401, body: { detail: 'AUTH_REQUIRED' } } : null });
  const d = build('?mode=sample', f, w => { w.Hk = w.Hk || {}; });
  await sleep(10);
  d.win.Hk.auth.demo = true;
  menu(d, 'status'); await sleep(40);
  assert.match(threadText(d), /연결 설정/);
  assert.match(threadText(d), /2-of-3/);
});

test('로그인한 기관이 ?mode=sample 로 보면: 예시 화면이어도 운영자 단추·2-of-3 패널 없음', async () => {
  const f = serverDouble({});
  const d = build('?mode=sample', f);
  await sleep(10);
  menu(d, 'status'); await sleep(40);
  const t = threadText(d);
  for (const l of STAFF_BUTTONS) assert.equal(find(d, l), undefined, l);
  assert.ok(!t.includes('2-of-3'));
  assert.ok(find(d, '실서버 모드로 바꾸기'));
});

test('서버가 등록부 주소를 주면 그 값을 씀(로컬 Anvil 도 주소 표시, Etherscan 링크는 Sepolia 만)', async () => {
  const addr = '0x' + '12'.repeat(20);
  const net = { status: 200, body: { chain_target: 'anvil', chain_id: 31337, rpc_fallback_configured: false, registry_address: addr, approver_nodes: [] } };
  const { d, text } = await open({ role: 'recipient', issuer_id: null }, u => u === '/v1/chain/network' ? net : null);
  assert.ok(text.includes('등록부 주소(전문가용): ' + addr.slice(0, 8) + '…' + addr.slice(-4)));
  assert.equal(d.doc.querySelectorAll('#chatThread a').filter(x => /etherscan/.test(String(x.href))).length, 0);
});

test('활성 기관 목록을 못 받으면 지어내지 않고 오류를 보여 줌', async () => {
  const { text } = await open({ role: 'recipient', issuer_id: null }, u => u === '/v1/chain/issuers' ? { status: 503, body: { detail: 'WALLET_REGISTRY_UNAVAILABLE' } } : null);
  assert.ok(!/Origin Mock Office/.test(text));
});

test('기관 화면: API 경로·영문 상태 코드·신청 번호 대신 쉬운 말', async () => {
  const { text } = await open({ role: 'issuer', issuer_id: 'iss_origin_mock_bank', username: 'bank_staff' });
  assert.match(text, /내 기관 상태 · 신청/);
  for (const t of ['/v1/issuer/status', 'PENDING_REVIEW', 'APPROVED_PENDING_CHAIN', 'app_', 'v1 장부', 'wallet 장부']) assert.ok(!text.includes(t), t);
});

test('화면 나누기: 메뉴를 바꾸면 앞 메뉴 내용이 남지 않고, 개인 계정의 맨 위 단추(issue)는 빈 새 대화 화면', async () => {
  const { d } = await open({ role: 'recipient', issuer_id: null, username: 'kim_tester' });
  assert.match(threadText(d), /이용 가능한 기관/);
  menu(d, 'operations'); await sleep(40);
  assert.ok(!threadText(d).includes('이용 가능한 기관'), '작업 이력 화면에 기관 상태가 남지 않음');
  menu(d, 'issue'); await sleep(20);
  const th = d.doc.getElementById('chatThread');
  assert.equal(th.children.length, 1, '빈 화면 하나만');
  assert.equal(th.children[0].id, 'chatEmpty');
  assert.ok(!/작업 이력|새 Proof 발행/.test(threadText(d)));
});

test('작업 이력: 서버 작업을 카드 한 줄씩(쉬운 말 종류·상태), 작업 번호는 앞부분만', async () => {
  const ops = { status: 200, body: [
    { operation_id: 'op_f4b35149b69447fbbd676c19ff929f50', action: 'wallet_propose', status: 'CONFIRMED', next_action: 'NONE' },
    { operation_id: 'op_0628ddbbbc1d4e708130cd2279049771', action: 'wallet_publish', status: 'UNKNOWN', next_action: 'RECONCILE' }
  ] };
  const { d } = await open({ role: 'recipient', issuer_id: null, username: 'kim_tester' }, u => /^\/v1\/operations/.test(u) ? ops : null);
  menu(d, 'operations'); await sleep(60);
  const t = threadText(d);
  assert.equal(d.doc.querySelectorAll('#chatThread .op-gov-row').length, 2);
  assert.match(t, /서버 작업 이력 · 2건/);
  assert.match(t, /기관 등록 제안\s*완료/);
  assert.match(t, /안내문 발행\s*확인 필요/);
  assert.match(t, /복구 조회 필요/);
  assert.ok(!t.includes('op_f4b35149b69447fbbd676c19ff929f50'), '작업 번호 전체를 늘어놓지 않음');
});

test('대화 보관: 확인한 대화는 메뉴를 다녀와도 같은 자리로 다시 열 수 있음(화면 말풍선 그대로)', async () => {
  const { d } = await open({ role: 'recipient', issuer_id: null, username: 'kim_tester' });
  const { enter } = require('./_review_harness.js');
  menu(d, 'issue'); await sleep(10);
  enter(d, '일반 안내문입니다'); await sleep(80);
  const before = d.doc.querySelectorAll('#chatThread .msg').length;
  assert.ok(before >= 1);
  menu(d, 'status'); await sleep(40);
  assert.ok(!threadText(d).includes('일반 안내문입니다'));
  const back = d.win.Hk && d.win.Hk.op5sessions ? d.win.Hk.op5sessions() : null;
  assert.ok(back && back.length === 1, '대화 하나가 보관됨');
  back[0].open(); await sleep(10);
  assert.ok(threadText(d).includes('일반 안내문입니다'));
  assert.equal(d.doc.querySelectorAll('#chatThread .msg').length >= before, true);
});
