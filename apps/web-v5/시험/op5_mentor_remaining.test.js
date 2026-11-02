'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { build, enter, menu, sleep, press, serverDouble, PID, Ev, WEB } = require('./_review_harness.js');

function outsideTech(node) {
  if (node.tagName === 'DETAILS') return '';
  if (!node.childNodes || !node.childNodes.length) return node.textContent || '';
  return Array.from(node.childNodes).map(outsideTech).join('');
}
for (const status of ['NOT_REGISTERED', 'TAMPERED']) {
  test('직원 패널의 미등록 중립 및 변조 경고: ' + status, async () => {
    const f = serverDouble({ over: u => u === '/v3/verifications' ? { status: 200, body: {
      verification_status: status, comparison_scope: 'ID_ONLY', document: null,
      reason_codes: [], checks: status === 'TAMPERED' ? [{ name: 'signature', status: 'FAILED' }] : [], chain_id: '31337'
    } } : null });
    const d = build('?mode=api', f);
    enter(d, JSON.stringify({ document_id: PID }));
    await sleep(100);
    const panel = d.doc.getElementById('staffList');
    if (status === 'NOT_REGISTERED') {
      assert.equal(panel.querySelectorAll('.st')[1].textContent, '정보');
      assert.doesNotMatch(panel.textContent, /문제 찾음/);
    } else {
      assert.match(panel.textContent, /문제 찾음/);
      assert.match(d.doc.getElementById('chatThread').textContent, /돈을 보내지 마세요/);
    }
  });
}
test('실제 응답 증명 값은 접힘 안에, hash 없으면 Sepolia 레지스트리 링크만 표시', async () => {
  const values = { document_id: PID, original_hash: '0x' + '12'.repeat(32), protected_hash: '0x' + '34'.repeat(32) };
  const contract = '0x' + '56'.repeat(20), block = '0x' + '78'.repeat(32);
  const f = serverDouble({ over: u => u === '/v3/verifications' ? { status: 200, body: {
    verification_status: 'VERIFIED', comparison_scope: 'ID_ONLY', document: Object.assign({ state: 'ACTIVE' }, values),
    checks: [], reason_codes: [], chain_id: '11155111', verifying_contract: contract, block_hash: block
  } } : null });
  const d = build('?mode=api', f);
  enter(d, JSON.stringify({ document_id: PID })); await sleep(100);
  const thread = d.doc.getElementById('chatThread'), tech = thread.querySelector('details.op-proof');
  assert.ok(tech); assert.equal(tech.getAttribute('open'), null);
  for (const value of [...Object.values(values), contract, block]) assert.ok(tech.textContent.includes(value));
  assert.match(tech.textContent, /signature: 제공되지 않음/);
  assert.match(tech.textContent, /tx_hash: 제공되지 않음/);
  assert.equal(tech.querySelectorAll('a').length, 1);
  assert.equal(tech.querySelector('a').href, 'https://sepolia.etherscan.io/address/' + contract);
  assert.ok(!outsideTech(thread).includes(contract));
});
test('기관 목록·검색·검증 자료의 기술 값은 접힘 안에만 표시', async () => {
  const raw = { proof_id: 'prf_test', proof_type: 'OFFICIAL_DOCUMENT', registration_status: 'REGISTERED', expires_at: '2027-01-01' };
  const f = serverDouble({ over: u => {
    if (u === '/v2/issuer/proofs') return { status: 200, body: [raw] };
    if (u.endsWith('/verification-material')) return { status: 200, body: { original_hash: 'original_marker', signature: 'signature_marker' } };
    return null;
  } });
  const d = build('?mode=api', f); menu(d, 'proofs'); await sleep(50);
  const thread = d.doc.getElementById('chatThread');
  assert.match(outsideTech(thread), /공식 문서.*등록됨/);
  assert.doesNotMatch(outsideTech(thread), /OFFICIAL_DOCUMENT|REGISTERED/);
  const input = d.doc.querySelector('#sidebar-root input'); input.value = PID;
  d.doc._dispatch(input, new Ev('keydown', { key: 'Enter' })); await sleep(50);
  assert.match(outsideTech(thread), /상태 유효/);
  assert.doesNotMatch(outsideTech(thread), /ACTIVE/);
  await press(d, '검증 자료 보기');
  assert.doesNotMatch(outsideTech(thread), /original_hash|signature_marker|verification-material/);
  assert.match(thread.textContent, /signature_marker/);
  for (const tech of thread.querySelectorAll('details.op-proof')) assert.equal(tech.getAttribute('open'), null);
});
test('근거 규칙 번호는 기술 증명으로 이동하고 이전 자세히 안내 제거', () => {
  const source = fs.readFileSync(path.join(WEB, 'js/op5_connect.js'), 'utf8');
  const evidenceRows = source.slice(source.indexOf('function evidenceRows'), source.indexOf('function chainButton'));
  assert.doesNotMatch(evidenceRows, /rule_id/);
  assert.match(source, /tech.append.*규칙 번호/);
  for (const file of ['js/api_adapter.js', 'data/sample_data.js']) assert.doesNotMatch(fs.readFileSync(path.join(WEB, file), 'utf8'), /자세히/);
});

test('예시 미등록도 기록관 패널은 중립 정보', async () => {
  const d = build('', serverDouble({}));
  enter(d, d.win.Hk.sampleAdapter.get('unregistered').input.text); await sleep(80);
  assert.equal(d.doc.getElementById('staffList').querySelectorAll('.st')[1].textContent, '정보');
});

function assertCollapsed(d, raw, korean) {
  const thread = d.doc.getElementById('chatThread');
  assert.doesNotMatch(outsideTech(thread), /ACTIVE|APPROVED|CONFIRMED|SUBMITTED|PUBLISH|RESIGN|RECONCILE|AUDIT_ERROR|HTTP|GET \/|\/v1\/|anvil|issuer/);
  if (korean) assert.match(outsideTech(thread), korean);
  const details = thread.querySelectorAll('details.op-proof');
  for (const value of raw) assert.ok(details.some(n => n.textContent.includes(value)), '접힘 안 원문 누락: ' + value);
  for (const n of details) assert.equal(n.getAttribute('open'), null);
}
function lookup(d, value) {
  const input = d.doc.querySelector('#sidebar-root input'); input.value = value;
  d.doc._dispatch(input, new Ev('keydown', { key: 'Enter' }));
}
test('기관 상태·신청·역할·체인과 공개키 상태는 한국어, 원문은 접힘', async () => {
  const f = serverDouble({ over: u => u === '/v1/issuer/keys' ? { status: 200, body: [{ key_id: 'public_key_fixture', status: 'ACTIVE', signer: 'public_signer', selected: true }] } : null });
  const d = build('?mode=api', f);
  menu(d, 'status'); await sleep(50);
  assertCollapsed(d, ['ACTIVE', 'APPROVED', 'issuer', 'anvil'], /기관 담당자.*유효.*승인됨/);
  menu(d, 'keys'); await sleep(50);
  assertCollapsed(d, ['ACTIVE', 'public_key_fixture'], /유효.*사용 중/);
});
test('기관 작업 목록·검색·복구·내 확인 기록은 한국어, 알 수 없는 값은 확인 필요', async () => {
  const op = { operation_id: 'op_1', status: 'CONFIRMED', action: 'PUBLISH', next_action: 'RESIGN', error_code: 'AUDIT_ERROR' };
  const f = serverDouble({ over: u => {
    if (u.startsWith('/v1/operations')) return { status: 200, body: [op, { operation_id: 'op_other', action: 'FUTURE_ACTION', status: 'FUTURE_STATUS', next_action: 'FUTURE_NEXT' }] };
    if (u === '/v3/operations/op_1') return { status: 200, body: op };
    return null;
  } });
  const d = build('?mode=api', f, w => w.sessionStorage.setItem('op5.ops.v1', JSON.stringify([{ operation_id: 'op_1', kind: 'PUBLISH', status: 'SUBMITTED', next_action: 'RECONCILE' }])));
  menu(d, 'operations'); await sleep(50);
  assertCollapsed(d, ['PUBLISH', 'SUBMITTED', 'RESIGN', 'FUTURE_STATUS'], /발행/);
  assert.match(outsideTech(d.doc.getElementById('chatThread')), /확인 필요/);
  lookup(d, 'op_1'); await sleep(50);
  assertCollapsed(d, ['CONFIRMED', 'AUDIT_ERROR'], /상태 확인됨 · 다음 다시 서명/);
  await press(d, '복구 조회 op_1');
  assertCollapsed(d, ['NONE'], /다음 없음/);
  await press(d, '내 확인 기록(보관한 분석) 보기');
  assertCollapsed(d, ['COMPLETED'], /완료/);
});
for (const status of [404, 500]) {
  for (const route of ['status', 'keys', 'operations', 'search']) {
    test('기관 ' + route + ' 오류 ' + status + ': 안내만 펼침 밖, 코드와 HTTP는 접힘 안', async () => {
      const f = serverDouble({ over: u => {
        if ((route === 'status' && u === '/v1/issuer/status') || (route === 'keys' && u === '/v1/issuer/keys') || (route === 'operations' && u.startsWith('/v1/operations')) || (route === 'search' && u === '/v3/operations/op_1')) return { status, body: { detail: 'AUDIT_ERROR' } };
        return null;
      } });
      const d = build('?mode=api', f);
      if (route === 'search') lookup(d, 'op_1'); else menu(d, route);
      await sleep(50);
      assertCollapsed(d, ['AUDIT_ERROR', 'HTTP ' + status]);
      assert.match(outsideTech(d.doc.getElementById('chatThread')), /없|못|오류|처리|찾/);
    });
  }
}

for (const action of ['보고서 받기', '원본 받기', '지우기']) {
  test(action + ' 500 오류의 코드와 HTTP는 접힌 기술 증명 안에만 표시', async () => {
    const d = build('?mode=api', serverDouble({ over: u => u.startsWith('/v3/analyses/ana_k') ? { status: 500, body: { detail: 'AUDIT_ERROR' } } : null }));
    menu(d, 'operations'); await sleep(50);
    await press(d, '내 확인 기록(보관한 분석) 보기');
    await press(d, action + ' ana_k');
    if (action === '지우기') await press(d, '정말 지울까요? 한 번 더 누르기');
    assertCollapsed(d, ['AUDIT_ERROR', 'HTTP 500']);
    assert.match(outsideTech(d.doc.getElementById('chatThread')), new RegExp(action));
  });
}
test('기관 상태의 보관 선택과 키 저장 꺼짐 안내는 한국어', async () => {
  const d = build('?mode=api', serverDouble({ over: u => u === '/v1/auth/ai-key' ? { status: 200, body: { storage_enabled: false } } : null }));
  menu(d, 'status'); await sleep(50);
  const visible = () => outsideTech(d.doc.getElementById('chatThread'));
  assert.doesNotMatch(visible(), /retain_report|retain_original|API_AI_KEY_SECRET/);
  assert.match(visible(), /보고서 보관 끔\(끝난 뒤 10분\) · 원본 보관 끔\(처리 직후 삭제\)/);
  assert.match(visible(), /이 서버는 키 저장을 켜 두지 않았어요\./);
  await press(d, '보관 선택 바꾸기');
  await press(d, '보고서 보관 켜기/끄기');
  await press(d, '원본 보관 켜기/끄기');
  assert.match(visible(), /보고서 보관 켬\(7일\) · 원본 보관 켬\(7일\)/);
  assert.doesNotMatch(visible(), /retain_report|retain_original/);
});
for (const route of ['issue', 'proofs', 'keys']) {
  test('지갑 없는 기관 ' + route + ' 안내에 기술 객체명 숨김', async () => {
    const d = build('?mode=api', serverDouble({}), w => { w.ethereum = undefined; });
    menu(d, route); await sleep(50);
    const visible = outsideTech(d.doc.getElementById('chatThread'));
    assert.match(visible, /이 브라우저에는 지갑이 없어요/);
    assert.doesNotMatch(visible, /window\.ethereum/);
  });
}
test('모든 오류 안내 호출은 기술 증명을 받을 메시지를 전달', () => {
  const source = fs.readFileSync(path.join(WEB, 'js/op5_connect.js'), 'utf8');
  assert.doesNotMatch(source, /errLines\([^,()]+\)/);
});
