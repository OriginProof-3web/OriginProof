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
