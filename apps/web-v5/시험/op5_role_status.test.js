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

test('비로그인: 로그인 확인 뒤 예시 모드로 돌아가 예전 예시 화면 그대로(서버 요청은 로그인 확인뿐)', async () => {
  const f = serverDouble({ over: u => u === '/v1/auth/me' ? { status: 401, body: { detail: 'AUTH_REQUIRED' } } : null });
  const d = build('?mode=api', f);
  await sleep(10);
  menu(d, 'status'); await sleep(60);
  assert.deepEqual(f.calls.map(c => c.url).filter(u => !/auth\/me$/.test(u)), []);
  const t = threadText(d);
  assert.match(t, /연결 설정/);
  assert.match(t, /기관 활성화 · 2-of-3 공동승인 \(예시 진행\)/);
  assert.ok(find(d, '실서버 모드로 바꾸기'));
  assert.ok(find(d, '로그인 화면 열기'));
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
