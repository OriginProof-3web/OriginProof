'use strict';
// 원본 찾기는 회원만 + lookup 결과 표시. 화면 시험은 가짜 DOM(브라우저 아님)
const test = require('node:test'); const assert = require('node:assert/strict');
const { load, adapter, page, sleep, REAL, Ev } = require('./_review_common.js');
const MSG = '[Origin Mock Bank] 카드대금 154,000원을 입금계좌 001-234-567890 로 보내주세요';
const ME_OK = { status: 200, body: { account_id: 'a', username: 'u', role: 'recipient', issuer_id: null, csrf_token: 'tok' } };
const LOGOUT = { status: 401, body: { detail: 'AUTH_REQUIRED' } };
const lk = (f) => f.calls.filter(c => c.url === '/api/v3/document-lookups');

for (const [name, me] of [['/me=401', LOGOUT], ['/me=500', { status: 500, body: {} }], ['/me 네트워크 실패', { reject: 'x' }]]) {
  test('T4 ' + name + ': 비회원은 원본 찾기를 보내지 않고 로그인 안내', async () => {
    const { f, a } = adapter(load(), (u) => u === '/api/v1/auth/me' ? me : u === '/api/v3/document-lookups' ? { status: 200, body: REAL } : null);
    const r = await a.check(MSG, {});
    assert.equal(lk(f).length, 0);
    assert.match(JSON.stringify(r.axes), /회원만 쓸 수 있어요/);
    assert.doesNotMatch(JSON.stringify(r.details), /보낸 요청[^}]*document-lookups/);
    assert.notEqual(r.axes.find(x => x.axis === 'status').status, '유효');
  });
}
test('T4 로그인 상태: 조회 전송, AI 입력도 CSRF 를 그대로 붙임(회귀)', async () => {
  const { f, a } = adapter(load(), (u) => u === '/api/v1/auth/me' ? ME_OK : u === '/api/v3/document-lookups' ? { status: 200, body: REAL } : u === '/api/v3/inputs' ? { status: 409, body: { detail: 'INPUT_SUPPORT_UNDECIDED' } } : null);
  await a.check(MSG, {});
  assert.equal(lk(f).length, 1);
  assert.equal(f.calls.find(c => c.url === '/api/v3/inputs').init.headers['X-CSRF-Token'], 'tok');
});
test('T4 회원 UNVERIFIED: 가짜라 하지 않음', async () => {
  const { a } = adapter(load(), (u) => u === '/api/v1/auth/me' ? ME_OK : u === '/api/v3/document-lookups' ? { status: 200, body: { lookup_status: 'UNVERIFIED', match_count: 0, document_ids: [], reason_codes: ['NO_MATCHING_RETAINED_RECORD'] } } : null);
  const r = await a.check(MSG, {});
  assert.match(r.conclusion.text, /가짜라는 뜻은 아니/);
});
test('T4 화면(가짜 DOM): 비회원은 로그인 확인 뒤 예시 모드로 돌아가 조회가 나가지 않음(op5_auth.js 설계)', async () => {
  const d = page((u) => u === '/api/v1/auth/me' ? LOGOUT : u === '/api/v3/document-lookups' ? { status: 200, body: REAL } : { status: 404, body: { detail: 'Not Found' } });
  await sleep(40);
  const i = d.doc.getElementById('chatInput'); i.value = MSG;
  d.doc._dispatch(i, new Ev('keydown', { key: 'Enter' }));
  await sleep(120);
  assert.equal(d.win.fetch.calls.filter(c => c.url === '/api/v3/document-lookups').length, 0);
  assert.ok(d.doc.querySelectorAll('.tag-offline').some(x => x.textContent === '예시 모드'));
});

const NULL_MATCH = { lookup_status: 'MATCHED', match_count: 1, document_ids: ['0x' + 'ab'.repeat(32)], reason_codes: [], verification: null };
for (const [name, body] of [['MATCHED+verification null', NULL_MATCH], ['모르는 lookup_status', { lookup_status: 'NEW', match_count: 0, document_ids: [], reason_codes: [] }]]) {
  test('추가 ' + name + ': "링크가 없어" 대신 판단 보류', async () => {
    const { a } = adapter(load(), (u) => u === '/api/v1/auth/me' ? ME_OK : u === '/api/v3/document-lookups' ? { status: 200, body } : null);
    const r = await a.check(MSG, {});
    assert.equal(r.conclusion.badge.text, '판단 보류');
    assert.doesNotMatch(r.axes[0].body, /검증 링크가 없어/);
  });
}
test('추가 실서버 MATCHED(부분 비교): "이 안내문을 발행"·"유효한 안내"로 문자 전체를 확인한 듯 말하지 않음', async () => {
  const { a } = adapter(load(), (u) => u === '/api/v1/auth/me' ? ME_OK : u === '/api/v3/document-lookups' ? { status: 200, body: REAL } : null);
  const r = await a.check(MSG + ' 그리고 인증번호를 알려 주세요', {});
  const off = r.axes.find(x => x.axis === 'official'), st = r.axes.find(x => x.axis === 'status');
  assert.doesNotMatch(off.body, /이 안내문을 발행/);
  assert.doesNotMatch(st.body, /유효한 안내/);
  assert.match(off.body, /문자 전체/);
});
test('추가 공문 번호 조회의 안내 글이 금액·계좌를 말하지 않음', async () => {
  for (const [st, re] of [['UNVERIFIED', /금액·계좌로 찾았지만/], ['AMBIGUOUS', /문서 번호로 다시/]]) {
    const { a } = adapter(load(), (u) => u === '/api/v1/auth/me' ? ME_OK : u === '/api/v3/document-lookups' ? { status: 200, body: { lookup_status: st, match_count: 0, document_ids: [], reason_codes: [] } } : null);
    const r = await a.check('Origin Mock Office 공문 번호: OMO-17', {});
    assert.doesNotMatch(r.conclusion.text, re);
  }
});
