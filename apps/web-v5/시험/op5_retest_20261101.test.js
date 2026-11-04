'use strict';
// 2026-11-01 재시험 결함(A) 회귀 시험. 화면 시험은 가짜 DOM(브라우저 아님)
const test = require('node:test'); const assert = require('node:assert/strict');
const { load, adapter, page, sleep, Ev } = require('./_review_common.js');
const ME = (role) => ({ status: 200, body: { account_id: 'a', username: 'u', role, issuer_id: null, csrf_token: 'tok' } });
const memStore = (init) => { const m = new Map(Object.entries(init || {})); return { getItem: k => m.has(k) ? m.get(k) : null, setItem: (k, v) => m.set(k, String(v)), removeItem: k => m.delete(k) }; };
const SETTINGS = JSON.stringify({ mode: 'sample' });
const DOC = '0x' + 'a'.repeat(64);
const texts = (d, sel) => d.doc.querySelectorAll(sel).map(n => n.textContent);
function presetBtn(d, label) { return d.doc.querySelectorAll('#presetBar button').find(b => b.textContent === label); }

test('비회원 때 머문 예시 모드는 로그인 뒤 실서버 모드로 돌아감', async () => {
  const ls = memStore({ 'op5.guestSample': '1', 'jjin.settings.v1': SETTINGS });
  const probe = page(u => u === '/api/v1/auth/me' ? ME('recipient') : { status: 404, body: {} }, { localStorage: ls }, '');
  await sleep(10);
  assert.equal(ls.getItem('op5.guestSample'), null);
  assert.equal(probe.win.Hk.op5live(), true);
  assert.match(probe.doc.getElementById('composerHint').textContent, /실서버 모드/);
});

test('회원이 직접 고른 예시 모드는 유지', async () => {
  const d = page(u => u === '/api/v1/auth/me' ? ME('issuer') : { status: 404, body: {} }, { localStorage: memStore({ 'jjin.settings.v1': SETTINGS }) }, '');
  await sleep(10);
  assert.equal(d.doc.getElementById('authBtn').textContent, '로그아웃');
  assert.equal(d.win.Hk.op5live(), false);
});

test('비회원은 표시를 남겨 다음 로그인 때 되돌릴 수 있음', async () => {
  const ls = memStore();
  page(u => u === '/api/v1/auth/me' ? { status: 401, body: { detail: 'AUTH_REQUIRED' } } : null, { localStorage: ls }, '');
  await sleep(10);
  assert.equal(ls.getItem('op5.guestSample'), '1');
});

test('세션이 끊기면 다시 불러오기 전에도 단추가 로그인으로 바뀜', async () => {
  let n = 0;
  const d = page(u => {
    if (u === '/api/v1/auth/me') return n++ ? { status: 401, body: { detail: 'AUTH_REQUIRED' } } : ME('issuer');
    return { status: 401, body: { detail: 'AUTH_REQUIRED' } };
  });
  await sleep(10);
  const btn = d.doc.getElementById('authBtn');
  assert.equal(btn.textContent, '로그아웃');
  const i = d.doc.getElementById('chatInput'); i.value = '[OO카드] 결제 안내입니다.';
  d.doc._dispatch(i, new Ev('keydown', { key: 'Enter' }));
  await sleep(60);
  assert.equal(btn.textContent, '로그인');
  assert.equal(d.win.Hk.auth.state.member, false);
});

test('K1: 실서버 모드의 예시 버튼은 서버에 보내지 않고 예시 결과를 \'예시 자료\' 표시로 보여 줌', async () => {
  const d = page(u => u === '/api/v1/auth/me' ? ME('issuer') : { status: 404, body: {} });
  await sleep(10);
  const before = d.win.fetch.calls.length;
  presetBtn(d, '철회된 안내').click();
  await sleep(3000);
  assert.equal(d.win.fetch.calls.length, before, '서버 요청 없음');
  const t = d.doc.getElementById('chatThread').textContent;
  assert.match(t, /예시 자료 · 서버에 보내지 않음/);
  assert.match(t, /예시 응답이에요/);
});

test('시연 줄: 실서버 시연(DB 직접 조작 포함) / 예시 결과 / 설명만 으로 나뉘고, 좌우 이동 단추는 스크롤 줄 밖 양 끝에 고정', async () => {
  const d = page(u => u === '/api/v1/auth/me' ? ME('issuer') : { status: 404, body: {} });
  await sleep(10);
  const bar = d.doc.getElementById('presetBar');
  assert.deepEqual(bar.children.map(n => n.className), ['preset-nav preset-nav-l', 'preset-track', 'preset-nav preset-nav-r']);
  const order = bar.children[1].children.map(n => n.textContent);
  const at = s => order.indexOf(s);
  assert.ok(at('실서버 시연') < at('진짜 안내 + 위험 요구') && at('DB 직접 조작') < at('예시 결과') && at('미등록 기관 사칭') < at('예시 결과'), order.join(' | '));
  assert.ok(at('예시 결과') < at('철회된 안내') && at('철회된 안내') < at('설명만') && at('설명만') < at('타 기관 권한 도용'), order.join(' | '));
  const navs = d.doc.querySelectorAll('#presetBar button').map(b => b.getAttribute('aria-label')).filter(Boolean);
  assert.deepEqual(navs, ['시연 버튼 왼쪽으로', '시연 버튼 오른쪽으로']);
});

test('실서버 시연 버튼: 정상·위험 요구는 RC 시드와 같은 고정 문자를 보냄', async () => {
  const d = page(u => u === '/api/v1/auth/me' ? ME('issuer') : { status: 404, body: {} });
  await sleep(10);
  presetBtn(d, '진짜 안내 + 위험 요구').click();
  await sleep(30);
  const sent = d.win.fetch.calls.map(c => c.body).join('\n');
  assert.match(sent, /Origin Mock Bank/);
  assert.match(sent, /원격 지원 앱을 설치해 주세요/);
});

test('DB 직접 조작 버튼: rc_presets.json 의 db_target(원래 받은 안내문)으로 검증만 보냄, 비교 기준 줄 없음', async () => {
  const TARGET = { document_id: DOC, version: 1, protected_fields: { amount_minor: 430000, payee_account_number: '001234500010' } };
  const TAMPERED = { session_id: 'vsn_db', verification_status: 'TAMPERED', comparison_scope: 'PARTIAL_COMPARISON', checks: [{ name: 'protected_fields', status: 'FAILED', reason_code: 'STORED_CONTENT_MISMATCH' }], reason_codes: [], checked_at: 1, chain_id: 31337, verifying_contract: '0x' + '11'.repeat(20) };
  const d = page(u => u === '/api/v1/auth/me' ? ME('issuer') : u === 'data/rc_presets.json' ? { status: 200, body: { genuine: TARGET, db_target: TARGET } } : u.startsWith('/api/v3/verifications') ? { status: 200, body: TAMPERED } : { status: 404, body: {} });
  await sleep(10);
  presetBtn(d, 'DB 직접 조작').click();
  await sleep(60);
  const sent = d.win.fetch.calls.filter(c => c.url.startsWith('/api/v3/verifications')).map(c => JSON.parse(c.body));
  assert.equal(sent.length, 1);
  assert.equal(sent[0].document_id, DOC);
  assert.equal(sent[0].candidate.amount_minor, 430000);
  const shown = d.doc.getElementById('chatThread').textContent;
  assert.match(shown, /DB 직접 조작 안내문 · 문서 v1/);
  assert.match(shown, /납부 금액: 430,000원/);
  assert.doesNotMatch(shown, /다른 항목|⟵/);
  // 서버 DB가 체인 기록과 다르면(STORED_CONTENT_MISMATCH) 받은 글이 아니라 서버 기록이 바뀌었다고 말함
  await sleep(400);
  assert.match(d.doc.getElementById('chatThread').textContent, /서버 기록이 바뀌었어요 · 블록체인 기록과 달라요/);
  // 시연 계정이 아니면(서버 404) DB는 그대로 두고 검증만 했다고 알림
  assert.match(d.doc.getElementById('chatThread').textContent, /DB를 바꾸지 않았어요/);
});

test('DB 직접 조작(시연 계정): 시연용 공격 재현으로 DB 금액을 바꾼 걸 보여 주고, 되돌리기 단추가 db-restore 를 부름', async () => {
  const TARGET = { document_id: DOC, version: 1, protected_fields: { amount_minor: 430000, payee_account_number: '001234500010' } };
  const d = page(u => u === '/api/v1/auth/me' ? ME('recipient') : u === 'data/rc_presets.json' ? { status: 200, body: { genuine: TARGET, db_target: TARGET } }
    : u === '/api/v3/demo/db-tamper' ? { status: 200, body: { document_id: DOC, version: 1, amount_before: 430000, amount_after: 4300000 } }
    : u === '/api/v3/demo/db-restore' ? { status: 200, body: { document_id: DOC, version: 1, amount_before: 4300000, amount_after: 430000 } } : { status: 404, body: {} });
  await sleep(10);
  presetBtn(d, 'DB 직접 조작').click();
  await sleep(80);
  const shown = d.doc.getElementById('chatThread').textContent;
  assert.match(shown, /시연용 공격 재현 · 실서비스에는 없는 기능/);
  assert.match(shown, /430,000원 → 4,300,000원/);
  const calls = d.win.fetch.calls.map(c => c.url);
  assert.ok(calls.indexOf('/api/v3/demo/db-tamper') < calls.findIndex(u => u.startsWith('/api/v3/verifications')), '바꾼 뒤 검증');
  const undo = d.doc.querySelectorAll('#chatThread button').find(b => b.textContent === 'DB 되돌리기');
  undo.click(); await sleep(40);
  assert.ok(d.win.fetch.calls.some(c => c.url === '/api/v3/demo/db-restore'));
  assert.equal(undo.textContent, 'DB를 430,000원으로 되돌렸어요');
});

test('실서버 시연 버튼: 변조·구버전은 data/rc_presets.json 의 문서를 보내고, 파일이 없으면 보내지 않고 알림', async () => {
  const DOCJ = { document_id: DOC, version: 2, protected_fields: { amount_minor: 120001, payee_account_number: '001234567890' } };
  const GEN = { document_id: DOC, version: 2, protected_fields: { amount_minor: 120000, payee_account_number: '001234567890' } };
  const d = page(u => u === '/api/v1/auth/me' ? ME('issuer') : u === 'data/rc_presets.json' ? { status: 200, body: { genuine: GEN, tamper: DOCJ, superseded: DOCJ } } : { status: 404, body: {} });
  await sleep(10);
  presetBtn(d, '금액 1원 변조').click();
  await sleep(60);
  assert.ok(d.win.fetch.calls.some(c => c.url === 'data/rc_presets.json'));
  assert.ok(d.win.fetch.calls.some(c => c.body.includes(DOC)), '문서 ID를 보내지 않음');
  const shown = d.doc.getElementById('chatThread').textContent;
  assert.match(shown, /금액 1원 변조 안내문 · 문서 v2/);
  assert.match(shown, /발행 원본과 다른 항목: 납부 금액/);
  assert.match(shown, /납부 금액: 120,001원 +⟵ 발행 원본 120,000원/);
  assert.doesNotMatch(shown, /\[시연\]|001234567890/);
  assert.doesNotMatch(shown, /"document_id"/);
  assert.match(shown, /문서 입력은 분석하지 않음/);
  assert.doesNotMatch(shown, /서버 분석기 연결 전/);

  const e = page(u => u === '/api/v1/auth/me' ? ME('issuer') : { status: 404, body: {} });
  await sleep(10);
  presetBtn(e, '구버전 재사용').click();
  await sleep(60);
  assert.match(e.doc.getElementById('chatThread').textContent, /시연 데이터 파일\(data\/rc_presets\.json\)이 없어/);
  assert.ok(!e.win.fetch.calls.some(c => c.url.startsWith('/api/v3')));
});

test('K1: 미등록 사칭은 실서버에서도 그대로 보냄', async () => {
  const d = page(u => u === '/api/v1/auth/me' ? ME('issuer') : { status: 404, body: {} });
  await sleep(10);
  const before = d.win.fetch.calls.length;
  presetBtn(d, '미등록 기관 사칭').click();
  await sleep(30);
  assert.ok(d.win.fetch.calls.length > before);
});

test('K7: 로그인한 실서버 모드에서 "서버를 켜고 로그인" 안내를 하지 않음', async () => {
  const d = page(u => u === '/api/v1/auth/me' ? ME('issuer') : { status: 404, body: {} });
  await sleep(10);
  presetBtn(d, '타 기관 권한 도용').click();
  const all = d.doc.getElementById('chatThread').textContent;
  assert.doesNotMatch(all, /켜고 로그인한 뒤/);
  assert.match(all, /이 버튼으로 실행하지 않아요/);
  assert.equal(texts(d, '#chatThread .tag-offline').slice(-1)[0], '설명');
});

test('K8: 휴대폰 폭에서 메뉴를 접고, 넓은 화면에서는 건드리지 않음', async () => {
  for (const [matches, want] of [[true, 1], [false, 0]]) {
    let clicked = 0;
    const d = page(u => u === '/api/v1/auth/me' ? ME('issuer') : null, { matchMedia: () => ({ matches, addEventListener() {} }) });
    const c = d.doc.createElement('button'); c.className = 'sidebar-collapse-control';
    c.addEventListener('click', () => clicked++);
    d.doc.getElementById('sidebar-root').append(c);
    await sleep(150);
    assert.equal(clicked, want);
  }
});

test('K9: 체인 장애를 "연결 전"이 아니라 판단 보류로 알림', async () => {
  const body = { verification_status: 'INCONCLUSIVE', reason_codes: ['CHAIN_UNAVAILABLE'], session_id: 's' };
  const { a } = adapter(load(), (u) => u === '/api/v3/verifications' ? { status: 200, body } : u === '/api/v1/auth/me' ? ME('issuer') : { status: 404, body: {} });
  const r = await a.check(JSON.stringify({ document_id: DOC }), {});
  assert.equal(r.conclusion.badge.text, '판단 보류');
  assert.doesNotMatch(JSON.stringify(r), /장부 연결부가 없어/);
  assert.match(r.conclusion.text, /체인에 연결하지 못해/);
  r.axes.slice(0, 3).forEach(x => assert.equal(x.status, '확인 불가'));
});

test('개인 계정에는 기관 전용 메뉴를 숨기고 기관 계정은 그대로', async () => {
  for (const [role, want] of [['recipient', 'none'], ['issuer', undefined]]) {
    const d = page(u => u === '/api/v1/auth/me' ? ME(role) : null);
    const side = d.doc.getElementById('sidebar-root');
    const b = d.doc.createElement('button'); b.textContent = '공개키 관리'; side.append(b);
    await sleep(10);
    assert.equal(b.style && b.style.display || undefined, want);
  }
});
