'use strict';
// 2026-11-04 클린트 기능시험 2-3·2-4·2-5(A1~A8) 회귀: 코드 없는 문자 원본 찾기(Track B)
// 문장은 qa/t2_lookup.js 의 G·V·W 그대로. 발행 값은 build/rc-local/bulk-docs.jsonl(bank 001234500001~10, office OMO-2026-0101~0110)
const test = require('node:test'); const assert = require('node:assert/strict');
const { load, adapter, REAL } = require('./_review_common.js'); const why = t => Hk.api.lookupExplain(t).why;
const Hk = load(); const k = t => JSON.parse(JSON.stringify(Hk.api.lookupKey(t)));   // vm 안 객체라 같은 모양으로 바꿔 비교 const why = t => Hk.api.lookupExplain(t).why;
const BANK = '0x9d6e623a821f35508c0c970540013aa75041537806d71a2e318ac7ca5358a217', OFF = '0xa079131abb1c9fafcee45cedda0cb5ae9a0aa8d8e2f3112e1ad0e85da89a9bbe';
const P = (a, acc, iss) => ({ issuer_id: iss || BANK, key: { notice_type: 'PAYMENT_REQUEST', amount_minor: a, currency: 'KRW', payee_account_number: acc } });
const D = (n, iss) => ({ issuer_id: iss || OFF, key: { notice_type: 'OFFICIAL_DOCUMENT', document_number: n } });
const ME_OK = { status: 200, body: { account_id: 'a', username: 'u', role: 'recipient', issuer_id: null, csrf_token: 'tok' } };

const ROWS = [
  // 정상(이미 통과하던 것 — 그대로 유지)
  ['G1', '[Origin Mock Bank] 자동차세 32,500원 납부 안내입니다. 입금계좌 001-234-500001 (합성 은행)', P(32500, '001234500001')],
  ['G3', '[Web발신]\n[Origin Mock Bank]\n카드대금 청구 안내\n납부금액: 85,000원\n입금계좌: 001-234-500003', P(85000, '001234500003')],
  ['G5', '[Origin Mock Office] 민원 처리 결과 회신 (문서번호 OMO-2026-0101)', D('OMO-2026-0101')],
  ['G6', 'Origin Mock Office 알림: 주정차 위반 사전 통지, 공문번호: OMO-2026-0102 입니다.', D('OMO-2026-0102')],
  ['V1', '[Origin Mock Bank] 대출 이자 납입 안내\n금액: 210,000원\n계좌: 001-234-500005', P(210000, '001234500005')],
  ['V14', 'Origin Mock Bank 등록금 1,250,000원을 납부하세요.\n\n입금 계좌번호는\n001-234-500008\n입니다.', P(1250000, '001234500008')],
  ['V24', 'Origin Mock Bank 자동차세 납부금액 32,500원 납부기한 2026-11-30 입금계좌 001-234-500001', P(32500, '001234500001')],
  // 기능시험 2-3 실패 문장(이번에 읽게 된 것)
  ['V2', '[오리진 목 은행] 건강보험료 67,300원, 입금계좌 001-234-500006', P(67300, '001234500006')],                       // A2
  ['V19', '[오리진 목 오피스] 보조금 지급 결정 통지 문서번호 OMO-2026-0107', D('OMO-2026-0107')],                            // A2
  ['V13', 'Origin-Mock-Bank 과태료 5,500원 계좌 001-234-500007', P(5500, '001234500007')],                                   // A2
  ['V3', '(Origin Mock Bank) 과태료 5,500원 납부 바랍니다. 합성은행 001-234-500007', P(5500, '001234500007')],               // A4 은행명 뒤
  ['V9', 'Origin Mock Bank 카드대금 85,000원 이체: 001-234-500003', P(85000, '001234500003')],                               // A4
  ['V10', 'Origin Mock Bank 통신요금 12,900원 입금처 합성은행 001234500004', P(12900, '001234500004')],                       // A4
  ['V4', 'Origin Mock Bank 등록금 1,250,000원 납부. 가상계좌 001 234 500008', P(1250000, '001234500008')],                   // A4 공백
  ['V26', 'Origin Mock Bank 재산세 48,000 원 계좌 : 001 - 234 - 500002', P(48000, '001234500002')],                          // A4 공백
  ['V6', 'Origin Mock Bank 보험료 43만원 계좌 001-234-500010', P(430000, '001234500010')],                                   // 한글 단위
  ['V25', 'Origin Mock Bank 자동차세 3만2천5백원 계좌 001-234-500001', P(32500, '001234500001')],                            // 한글 단위
  ['V8', 'Origin Mock Bank 재산세 ₩48,000 계좌 001-234-500002', P(48000, '001234500002')],                                   // ₩
  ['V11', 'Origin Mock Bank 대출이자 210,000원 계좌 001-234-500005 문의 1588-0000', P(210000, '001234500005')],              // A6
  ['V16', '[Origin Mock Office] 주민세 고지 문서번호 OMO-2026-0104, 납부금액 15,000원', D('OMO-2026-0104')],                 // A8
  ['V23', '[Origin Mock Office] 체납 처분 예고 통지 문서번호 OMO-2026-0110 체납액은 지정 계좌로 납부', D('OMO-2026-0110')],   // A8
  ['V17', '[Origin Mock Office] 전입 신고 확인서(OMO-2026-0105)를 보내드립니다.', D('OMO-2026-0105')],                       // A5 괄호
  ['V18', '[Origin Mock Office] 예비군 훈련 안내 / 접수번호 OMO-2026-0106', D('OMO-2026-0106')],                             // A5 접수번호
  ['V20', '[Origin Mock Office] 정보공개 청구 회신 문서번호: OMO-2026-0108호', D('OMO-2026-0108')],                          // A5 '호'
  ['V21', '[Origin Mock Office] 선거 투표소 안내 문서번호 omo-2026-0109', D('OMO-2026-0109')],                               // A5 대문자
  ['V5', 'Origin Mock Bank 연회비 99,000원 청구. 계좌 001-234-500009 자세히 보기 https://bank.example.invalid/pay', P(99000, '001234500009')],   // A3
  ['V22', '[Origin Mock Office] 체납 처분 예고 통지 (문서번호 OMO-2026-0110) 상세: https://office.example.invalid/docs', D('OMO-2026-0110')],     // A3
  ['추가', 'Origin Mock Bank 자동차세 32,500원 계좌 001-234-500001 고객번호 123456789', P(32500, '001234500001')],
  // 틀린 문자: 파서는 문자에 적힌 (틀린) 값을 그대로 보냄 → 서버 UNVERIFIED. 정본 값으로 '고쳐서' 보내면 안 됨
  ['W1', '[Origin Mock Bank] 자동차세 32,501원 입금계좌 001-234-500001', P(32501, '001234500001')],
  ['W2', '[Origin Mock Bank] 재산세 48,000원 입금계좌 001-234-500012', P(48000, '001234500012')],
  ['W3', '[Origin Mock Bank] 카드대금 85,000원 입금계좌 001-234-500004', P(85000, '001234500004')],
  ['W4', '자동차세 32,500원 입금계좌 001-234-500001 (합성 은행)', null],
  ['W5', '[Origin Mock Office] 민원 처리 결과 회신 문서번호 OMO-2026-0111', D('OMO-2026-0111')],
  ['W6', '[Origin Mock Office] 자동차세 32,500원 입금계좌 001-234-500001', P(32500, '001234500001', OFF)],
  ['W7', '[Origin Mock Bank] 민원 처리 결과 회신 문서번호 OMO-2026-0101', D('OMO-2026-0101', BANK)],
  ['W8', '[Origin Mock Bank] 지방세 120,000원 입금계좌 001-234-567891', P(120000, '001234567891')],
  ['W10', '[Origin Mock Office] 문서번호 OMO-2026-101', D('OMO-2026-101')],
];
for (const [id, text, want] of ROWS) test('파서 ' + id + ': ' + text.slice(0, 40), () => assert.deepEqual(k(text), want));

// 정본 발행 값 목록: 틀린 문자(W)가 정본 키가 되면 안 됨(다른 값의 MATCHED 금지)
const ISSUED = new Set([].concat(
  [[32500, 1], [48000, 2], [85000, 3], [12900, 4], [210000, 5], [67300, 6], [5500, 7], [1250000, 8], [99000, 9], [430000, 10]].map(([a, n]) => BANK + '|' + a + '|00123450' + String(n).padStart(4, '0')),
  [BANK + '|154000|001234567890'],
  Array.from({ length: 10 }, (_, i) => OFF + '|OMO-2026-' + String(101 + i).padStart(4, '0'))));
const keyId = r => r.issuer_id + '|' + (r.key.document_number || r.key.amount_minor + '|' + r.key.payee_account_number);
test('틀린 문자 W1~W8·W10 은 정본 발행 키가 되지 않음', () => {
  for (const [id, text] of ROWS.filter(r => /^W(?!9)/.test(r[0]))) { const r = k(text); if (r) assert.equal(ISSUED.has(keyId(r)), false, id); }
});

const NULLS = [
  ['V7 금액 두 개(가산금) — 고르지 않음(보수적 설계 유지)', 'Origin Mock Bank 자동차세 32,500원(기한 후 가산금 포함 33,475원) 입금계좌 001-234-500001', 'AMOUNT_UNCLEAR'],
  ['억 뒤 만 없이 작은 값', 'Origin Mock Bank 1억5000원 계좌 001-234-500001', 'AMOUNT_UNCLEAR'],
  ['끝 숫자가 가장 작은 단위 이상', 'Origin Mock Bank 3만2천5000원 계좌 001-234-500001', 'AMOUNT_UNCLEAR'],
  ['소수점 단위', 'Origin Mock Bank 1.5만원 계좌 001-234-500001', 'AMOUNT_UNCLEAR'],
  ['쉼표+단위', 'Origin Mock Bank 1,000만원 계좌 001-234-500001', 'AMOUNT_UNCLEAR'],
  ['₩ 뒤 한글 단위', 'Origin Mock Bank ₩43만원 계좌 001-234-500001', 'AMOUNT_UNCLEAR'],
  ['₩ 소수', 'Origin Mock Bank ₩48,000.50 계좌 001-234-500001', 'AMOUNT_UNCLEAR'],
  ['공문번호 + 계좌번호(다른 계좌를 놓칠 수 있음)', '[Origin Mock Office] 문서번호 OMO-2026-0104 납부금액 15,000원 입금계좌 001-234-500001', 'DOC_WITH_ACCOUNT'],
  ['공문번호 + 은행명 뒤 계좌', '[Origin Mock Office] (OMO-2026-0105) 합성은행 001-234-500001', 'DOC_WITH_ACCOUNT'],
  ['기관 없음', '자동차세 32,500원 입금계좌 001-234-500001', 'NO_ISSUER'],
  ['기관 둘', '[오리진 목 은행] [Origin Mock Office] 32,500원 계좌 001-234-500001', 'MANY_ISSUERS'],
  ['계좌 없음', 'Origin Mock Bank 자동차세 32,500원 납부 안내', 'NO_ACCOUNT'],
  ['금액 없음', 'Origin Mock Bank 입금계좌 001-234-500001', 'NO_AMOUNT'],
  ['계좌 후보 둘', 'Origin Mock Bank 32,500원 입금계좌 001-234-500001 또는 001-234-500002', 'ACCOUNT_UNCLEAR'],
  ['날짜를 띄어 써도 계좌가 아님', 'Origin Mock Bank 32,500원 입금기한 2026 11 30', 'NO_ACCOUNT'],
  ['전화를 띄어 써도 계좌가 아님', 'Origin Mock Bank 32,500원 이체 문의 010 1234 5678', 'NO_ACCOUNT'],
  ['공문번호 두 개', '[Origin Mock Office] 문서번호 OMO-2026-0101 접수번호 OMO-2026-0102', 'DOC_UNCLEAR'],
];
for (const [name, text, code] of NULLS) test('보내지 않음 ' + name, () => { assert.equal(k(text), null); assert.equal(why(text), code); });
test('돈이 아닌 단위(3만 명)는 금액 판단을 막지 않음', () => assert.deepEqual(k('Origin Mock Bank 회원 3만 명 대상 자동차세 32,500원 계좌 001-234-500001'), P(32500, '001234500001')));
test('뒤 한 자리 숫자를 계좌에 붙이지 않음', () => assert.deepEqual(k('Origin Mock Bank 32,500원 계좌 001234500001 2 회차'), P(32500, '001234500001')));
test('연체이자는 여전히 덧붙는 금액', () => assert.equal(k('Origin Mock Bank 대출금 210,000원 연체이자 3,000원 계좌 001-234-500005'), null));
test('모든 못 읽은 이유에 쉬운 문구가 있음', () => {
  for (const [, , code] of NULLS) assert.ok(Hk.api.LOOKUP_SKIP[code], code);
});

// ---- 화면 결론 ----
const MSG = '[Origin Mock Bank] 자동차세 32,500원 납부 안내. 입금계좌 001-234-500001';
const run = async (text, body, extra) => {
  const { f, a } = adapter(load(), (u) => u === '/api/v1/auth/me' ? ME_OK : u === '/api/v3/document-lookups' ? { status: 200, body } : (extra && extra(u)) || null);
  const r = await a.check(text, {});
  return { f, r, sent: f.calls.filter(c => c.url === '/api/v3/document-lookups').map(c => JSON.parse(c.body)) };
};
const clone = o => JSON.parse(JSON.stringify(o));
test('A1 MATCHED + 부분 비교: 결론은 "읽은 항목 일치", 판정 값은 INCONCLUSIVE 그대로', async () => {
  const { r } = await run(MSG, REAL);
  assert.equal(r.verification_status, 'INCONCLUSIVE');
  assert.equal(r.conclusion.badge.text, '읽은 항목 일치');
  assert.equal(r.conclusion.badge.tone, 'ok');
  assert.match(r.conclusion.text, /문자에서 읽은 항목\(금액·계좌\)이 기관 발행 기록과 일치해요 · 나머지 문구는 비교하지 않았어요/);
  const o = r.axes.find(x => x.axis === 'original');
  assert.equal(o.status, '읽은 항목 일치');
  assert.match(o.body, /나머지 문구는 비교하지 않았어요/);
  assert.ok(r.details.some(d => d.label === '검증 엔진 결과' && /^INCONCLUSIVE · PARTIAL_COMPARISON/.test(d.value)));
  assert.ok(r.details.some(d => d.label === '화면 결론'));
  assert.equal(r.staff.find(s => s.staff === 'original').bubble_key, 'original.lookup_match');
});
test('A1 공문 번호로 찾으면 항목 이름이 "공문번호"', async () => {
  const { r, sent } = await run('[Origin Mock Office] 주민세 고지 문서번호 OMO-2026-0104, 납부금액 15,000원', REAL);
  assert.deepEqual(sent[0].key, { notice_type: 'OFFICIAL_DOCUMENT', document_number: 'OMO-2026-0104' });
  assert.match(r.conclusion.text, /항목\(공문번호\)/);
});
test('A1 구버전(SUPERSEDED): 배지는 "새 버전 있음"이 앞', async () => {
  const b = clone(REAL); b.verification.document.state = 'SUPERSEDED'; b.verification.document.latest_version = 2;
  const { r } = await run(MSG, b);
  assert.equal(r.conclusion.badge.text, '새 버전 있음');
  assert.match(r.conclusion.text, /일치해요/);
});
test('A1 실패한 검사가 있거나 서명이 확인되지 않으면 긍정 결론을 쓰지 않음', async () => {
  const b1 = clone(REAL); b1.verification.checks.find(c => c.name === 'signature').status = 'UNAVAILABLE';
  const b2 = clone(REAL); b2.verification.checks.find(c => c.name === 'original_hash').status = 'FAILED';
  const b3 = clone(REAL); b3.verification.checks.find(c => c.name === 'current_state').status = 'UNAVAILABLE';
  for (const b of [b1, b2, b3]) {
    const { r } = await run(MSG, b);
    assert.notEqual(r.conclusion.badge.text, '읽은 항목 일치');
    assert.notEqual(r.axes.find(x => x.axis === 'original').status, '읽은 항목 일치');
  }
});
test('W 틀린 값: UNVERIFIED 면 긍정 결론 없음, 가짜라 하지 않고 확인할 수 없음(이유와 함께)', async () => {
  const { r } = await run('[Origin Mock Bank] 자동차세 32,501원 입금계좌 001-234-500001', { lookup_status: 'UNVERIFIED', match_count: 0, document_ids: [], reason_codes: ['NO_MATCHING_RETAINED_RECORD'] });
  assert.equal(r.conclusion.badge.text, '확인할 수 없음');
  assert.doesNotMatch(r.conclusion.text, /가짜 의심/);
  assert.equal(r.conclusion.verdict.head, '· 확인할 수 없어요 · 등록된 기관의 기록에서 찾지 못했어요');
});
test('A3 Proof ID 없는 링크 + 읽을 값: 원본 찾기를 보냄(링크 주소는 보내지 않음)', async () => {
  const { r, sent } = await run('Origin Mock Bank 연회비 99,000원 청구. 계좌 001-234-500009 자세히 보기 https://bank.example.invalid/pay', REAL);
  assert.equal(sent.length, 1);
  assert.deepEqual(sent[0].key, P(99000, '001234500009').key);
  assert.equal(r.conclusion.badge.text, '읽은 항목 일치');
  assert.ok(r.details.some(d => d.label === '입력 종류' && /원본 찾기 MATCHED/.test(d.value)));
});
test('A3 Proof ID 없는 링크 + 읽을 값 없음: 예전처럼 연결 전 + 못 읽은 이유', async () => {
  const { r, sent } = await run('자세히 보기 https://bank.example.invalid/pay', REAL);
  assert.equal(sent.length, 0);
  assert.equal(r.conclusion.badge.text, '연결 전');
  assert.match(r.conclusion.text, /Proof ID가 없어/);
  assert.match(r.conclusion.text, /기관 이름을 찾지 못했어요/);
});
test('A7 못 읽은 이유를 구체적으로, "검증 링크가 없어" 문구 없음', async () => {
  for (const [text, re] of [['Origin Mock Bank 자동차세 32,500원 납부 안내', /입금 계좌번호를 찾지 못했어요/], ['Origin Mock Bank 32,500원(가산금 포함 33,475원) 계좌 001-234-500001', /하나로 고를 수 없었어요/], ['자동차세 32,500원 계좌 001-234-500001', /기관 이름을 찾지 못했어요/]]) {
    const { r, sent } = await run(text, REAL);
    assert.equal(sent.length, 0);
    assert.match(r.conclusion.text, re);
    assert.doesNotMatch(r.conclusion.text + JSON.stringify(r.axes), /검증 링크가 없어/);
    assert.ok(r.details.some(d => d.label === '원본 찾기' && /^보내지 않음 · /.test(d.value)));
  }
});

test('원본을 못 찾은 이유를 보여 줌: 같은 계좌 금액 다름 / 기관 계좌 아님 / 공문번호 없음(저장된 값은 말하지 않음)', async () => {
  const cases = [
    ['[Origin Mock Bank] 카드 대금 85,001원 입금계좌 001-234-500003', 'AMOUNT_DIFFERS_FOR_ACCOUNT', /이 계좌로 발행한 안내문은 있지만 금액이 달라요/],
    ['[Origin Mock Bank] 카드 대금 85,000원 입금계좌 001-234-599999', 'ACCOUNT_NOT_IN_RECORDS', /이 계좌로 돈을 받는 것은 없어요/]
  ];
  for (const [msg, code, re] of cases) {
    const { r } = await run(msg, { lookup_status: 'UNVERIFIED', match_count: 0, document_ids: [], reason_codes: ['NO_MATCHING_RETAINED_RECORD', code] });
    assert.equal(r.conclusion.badge.text, '기록과 다름', code);
    assert.equal(r.conclusion.verdict.chip, '기록과 다름', code);
    assert.match(r.conclusion.text, re, code);
  }
});
