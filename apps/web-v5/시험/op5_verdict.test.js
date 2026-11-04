// 최종 판단 카드: 블록체인 세 칸으로만 진짜 / 가짜·변조 / 확인 불가를 한눈에. AI 주의는 덧붙이는 한 줄. 'RAG 연결 전' 문구 없음.
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { build, threadText, enter, sleep, serverDouble } = require('./_review_harness.js');

async function run(id) {
  const d = build('?mode=sample', serverDouble({}));
  await sleep(10);
  const s = d.win.SAMPLE_DATA.filter(x => x.id === id)[0];
  enter(d, s.input.text); await sleep(3500);
  return threadText(d);
}

test('정상 예시 → 최종 판단 진짜', async () => {
  const t = await run('normal');
  assert.match(t, /최종\s*✓ 진짜 안내문이에요\s*진짜/);
  assert.ok(!/RAG/.test(t));
});
test('금액 1원 변조 예시 → 최종 판단 가짜·변조', async () => {
  const t = await run('tamper');
  assert.match(t, /최종\s*✕ 가짜이거나 바뀐 안내문이에요\s*가짜·변조/);
});
test('미등록 기관 사칭 예시 → 진짜라고 하지 않음(가짜·변조 또는 확인 불가) + AI 위험 한 줄', async () => {
  const t = await run('unregistered');
  assert.ok(!/✓ 진짜 안내문이에요/.test(t));
  assert.match(t, /(가짜이거나 바뀐|가짜 의심)/);
  assert.match(t, /AI .*위험 문장이 있어요/);
});

test('실서버에서 원본을 못 찾은 문자 → 최종 판단 가짜 의심(확인 불가라고만 쓰지 않음)', async () => {
  const { serverDouble: sd } = require('./_review_harness.js');
  const f = sd({ persona: { role: 'recipient', issuer_id: null, username: 'kim' }, over: u => /document-lookups$/.test(u) ? { status: 200, body: { lookup_status: 'UNVERIFIED', match_count: 0, reason_codes: ['NO_MATCH'] } } : null });
  const d = build('?mode=api', f);
  await sleep(20);
  enter(d, '[오리진 목 은행] 카드 대금 85,001원 청구 안내입니다. 입금계좌 001-234-500003'); await sleep(400);
  const t = threadText(d);
  assert.match(t, /최종\s*! 가짜 의심/);
  assert.match(t, /가짜 의심/);
});

test('원본 찾기로 금액·계좌가 맞으면, 가린 계좌로 입금하라는 문장만 근거로 든 AI 주의는 빼고 진짜로', async () => {
  const { serverDouble: sd } = require('./_review_harness.js');
  const V = { session_id: 'vs_1', verification_status: 'INCONCLUSIVE', reason_codes: ['PARTIAL_COMPARISON'], comparison_scope: 'PARTIAL', lifecycle_status: 'ACTIVE' };
  const job = { analysis_id: 'ana_1', status: 'COMPLETED', input_kind: 'TEXT', retain_report: false, retain_original: false,
    report: { risk_level: 'CAUTION', evidence: [{ quote: '납부 계좌 (계좌번호 가림) 으로 11/10까지 입금 바랍니다.', source: 'LLM', reason: 'PAYMENT_REQUEST' }], limitations: ['phishing-rules-0.2'] } };
  const f = sd({ persona: { role: 'recipient', issuer_id: null, username: 'kim' }, over: (u, m) => {
    if (/document-lookups$/.test(u)) return { status: 200, body: { lookup_status: 'MATCHED', match_count: 1, document_ids: ['0x' + 'ab'.repeat(32)], reason_codes: [], verification: V } };
    if (u === '/v3/analyses' && m === 'POST') return { status: 202, body: job };
    return null;
  } });
  const d = build('?mode=api', f);
  await sleep(20);
  enter(d, '[Web발신]\n[오리진 목 은행] 카드 대금 85,000원 청구 안내입니다. 납부 계좌 001-234-500003 으로 11/10까지 입금 바랍니다.'); await sleep(500);
  const t = threadText(d);
  // 블록체인 칸은 이 대역이 원본 찾기 응답만 흉내 내서 보지 않음(진짜 판정은 op5_lookup_trackb 시험)
  assert.ok(!/AI 주의/.test(t), 'AI 주의 줄 없음');
  assert.ok(!/위험 요구 문장을 칠했어요/.test(t), '형광펜 없음');
  assert.match(t, /AI 위험뚜렷한 신호 없음/);
  assert.match(t, /그 계좌로 입금하라는 문장은 위험으로 보지 않았어요/);
});

// 리뷰 #139 P1: 발행 진위와 현재 상태를 최종 카드에서 구분(정상 발행된 구버전·철회 문서를 '가짜'라 하지 않음)
test('구버전(새 버전 있음) 예시 → 가짜 의심이 아니라 "기관이 발행한 예전 안내문"(구버전)', async () => {
  const t = await run('superseded');
  assert.match(t, /최종\s*! 기관이 발행한 예전 안내문이에요\s*구버전/);
  assert.ok(!/최종\s*! 가짜 의심/.test(t) && !/최종\s*✕ 가짜이거나/.test(t));
});

test('철회 예시 → 가짜·변조가 아니라 "기관이 발행했다가 철회한 안내문"(철회됨)', async () => {
  const t = await run('revoked');
  assert.match(t, /최종\s*! 기관이 발행했다가 철회한 안내문이에요\s*철회됨/);
  assert.ok(!/최종\s*✕ 가짜이거나/.test(t));
});

test('판단 규칙: 정상 키 교체(서명·원본 확인, 상태 유효)는 진짜, 원본 불일치는 상태와 상관없이 가짜·변조', () => {
  const d = build('?mode=sample', serverDouble({}));
  const v = d.win.Hk.op5verdictOf;
  const ax = (official, original, status, label) => [
    { axis: 'official', tone: official, status: '확인됨' },
    { axis: 'original', tone: original, status: '일치' },
    { axis: 'status', tone: status, status: label }
  ];
  assert.equal(v({}, ax('ok', 'ok', 'ok', '유효'), null).head, '✓ 진짜 안내문이에요', '정상 키 교체 뒤 새 키 서명');
  assert.equal(v({}, ax('ok', 'fail', 'caution', '새 버전 있음'), null).head, '✕ 가짜이거나 바뀐 안내문이에요');
  const leak = v({}, ax('ok', 'ok', 'fail', '서명 키 유출'), null);
  assert.equal(leak.chip, '사용 중지');
  assert.doesNotMatch(leak.head, /가짜/);
  assert.equal(v({}, ax('ok', 'ok', 'caution', '만료'), null).chip, '만료');
});
