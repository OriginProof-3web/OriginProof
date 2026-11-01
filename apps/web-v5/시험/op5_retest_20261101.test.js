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
    if (u === '/api/v1/auth/ai-key' && n < 2) return { status: 200, body: { provider: null, storage_enabled: true, input_tokens: 0, output_tokens: 0, analyses: 0 } };
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

test('K1: 실서버 모드의 예시 버튼은 서버에 보내지 않고 이유를 알림', async () => {
  const d = page(u => u === '/api/v1/auth/me' ? ME('issuer') : { status: 404, body: {} });
  await sleep(10);
  const before = d.win.fetch.calls.length;
  presetBtn(d, '정상 안내문').click();
  await sleep(30);
  assert.equal(d.win.fetch.calls.length, before);
  assert.match(d.doc.getElementById('chatThread').textContent, /예시 자료라 실서버 기록과 맞지 않아 보내지 않았어요/);
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
  presetBtn(d, 'DB 직접 조작').click();
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
