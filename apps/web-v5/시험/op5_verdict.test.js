// 최종 판단 카드: 블록체인 세 칸으로만 진짜 / 가짜·변조 / 확인 불가를 한눈에. AI 주의는 덧붙이는 한 줄. 'RAG 연결 전' 문구 없음.
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { build, threadText, enter, sleep, serverDouble, buttons, press } = require('./_review_harness.js');

async function run(id) {
  const d = build('?mode=sample', serverDouble({}));
  await sleep(10);
  const s = d.win.SAMPLE_DATA.filter(x => x.id === id)[0];
  enter(d, s.input.text); await sleep(3500);
  return threadText(d);
}

test('정상 예시 → 최종 판단 진짜', async () => {
  const t = await run('normal');
  assert.match(t, /요약\s*✓ 진짜 안내문이에요\s*진짜/);
  assert.ok(!/RAG/.test(t));
});
test('금액 1원 변조 예시 → 최종 판단 가짜·변조', async () => {
  const t = await run('tamper');
  assert.match(t, /요약\s*✕ 가짜이거나 바뀐 안내문이에요\s*가짜·변조/);
});
test('구버전 예시 → 발행·원본은 맞으니 가짜 의심이 아니라 새 버전 확인으로', async () => {
  const t = await run('superseded');
  assert.match(t, /요약\s*! 예전 버전 안내문이에요 · 새 버전을 확인하세요\s*새 버전 있음/);
  assert.ok(!/공식 기록으로 확인되지 않아요/.test(t));
});

test('답 화면: 기다리는 동안 스피너, 자세히는 그 답 안에서 열고 닫기, 보고서 받기 없음', async () => {
  const d = build('?mode=sample', serverDouble({}));
  await sleep(10);
  const text = id => d.win.SAMPLE_DATA.filter(x => x.id === id)[0].input.text;
  enter(d, text('normal'));
  assert.match(threadText(d), /확인하고 있어요/, '보낸 직후(응답 전)');
  await sleep(3500);
  assert.doesNotMatch(threadText(d), /확인하고 있어요/);
  enter(d, text('tamper')); await sleep(3500);
  const answers = d.doc.querySelectorAll('#chatThread .msg-ai');
  assert.equal(answers.length, 2);
  const first = answers[0], btn = first.querySelectorAll('button').filter(b => b.textContent === '자세히 보기')[0];
  await press(d, btn);
  assert.equal(first.querySelectorAll('.op-more').length, 1, '첫 답 안에 상자');
  assert.equal(answers[1].querySelectorAll('.op-more').length, 0);
  assert.equal(btn.textContent, '자세히 닫기');
  await press(d, btn);
  assert.equal(first.querySelectorAll('.op-more')[0].hidden, true);
  assert.equal(btn.textContent, '자세히 보기');
  assert.ok(!buttons(d).some(b => /보고서 받기|이 분석 지우기/.test(b.textContent)));
});
test('미등록 기관 사칭 예시 → 진짜라고도 가짜라고도 하지 않고 등록된 기록이 없어 확인할 수 없음 + AI 위험 한 줄', async () => {
  const t = await run('unregistered');
  assert.ok(!/✓ 진짜 안내문이에요/.test(t));
  assert.match(t, /요약\s*· 확인할 수 없어요 · 등록된 발행 기록이 없어요\s*확인 불가/);
  assert.ok(!/가짜이거나 바뀐|가짜 의심/.test(t));
  assert.match(t, /AI .*위험 문장이 있어요/);
});

test('실서버에서 원본을 못 찾은 문자 → 가짜 의심이 아니라 등록된 기관 기록에서 찾지 못해 확인할 수 없음', async () => {
  const { serverDouble: sd } = require('./_review_harness.js');
  const f = sd({ persona: { role: 'recipient', issuer_id: null, username: 'kim' }, over: u => /document-lookups$/.test(u) ? { status: 200, body: { lookup_status: 'UNVERIFIED', match_count: 0, reason_codes: ['NO_MATCH'] } } : null });
  const d = build('?mode=api', f);
  await sleep(20);
  enter(d, '[오리진 목 은행] 카드 대금 85,001원 청구 안내입니다. 입금계좌 001-234-500003'); await sleep(400);
  const t = threadText(d);
  assert.match(t, /요약\s*· 확인할 수 없어요 · 등록된 기관의 기록에서 찾지 못했어요\s*확인 불가/);
  assert.ok(!/가짜 의심/.test(t));
  // 걸린 시간: 답 이름 옆은 합(N.N s), 직원 확인 현황 아래는 블록체인·AI 각각
  const shown = d.doc.querySelectorAll('#chatThread .op-time').filter(x => !x.hidden).map(x => x.textContent);
  assert.equal(shown.length, 1);
  assert.match(shown[0], /^\d+\.\d s$/);
  assert.match(d.doc.getElementById('staffTime').textContent, /^블록체인 검증 \d+\.\d s · AI 분석 (\d+\.\d s|안 함)$/);
});

test('원본 찾기로 금액·계좌가 맞으면, 그 계좌로 납부하라는 문장만 근거로 든 AI 주의는 빼고 진짜로(앱 설치 등은 그대로 주의)', async () => {
  for (const [quote, dropped] of [['납부 계좌 (계좌번호 가림) 으로 11/10까지 입금 바랍니다.', true], ['11/10까지 입금 바랍니다.', true], ["결제 대행 앱 '페이헬퍼'를 받아 로그인하시면 자동으로 납부돼요.", false]]) {
  const { serverDouble: sd } = require('./_review_harness.js');
  const V = { session_id: 'vs_1', verification_status: 'INCONCLUSIVE', reason_codes: ['PARTIAL_COMPARISON'], comparison_scope: 'PARTIAL', lifecycle_status: 'ACTIVE' };
  const job = { analysis_id: 'ana_1', status: 'COMPLETED', input_kind: 'TEXT', retain_report: false, retain_original: false,
    report: { risk_level: 'CAUTION', evidence: [{ quote, source: 'LLM', reason: 'PAYMENT_REQUEST' }], limitations: ['phishing-rules-0.2'] } };
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
  if (!dropped) { assert.match(t, /AI 위험주의/, quote); continue; }
  assert.ok(!/AI 주의/.test(t), 'AI 주의 줄 없음: ' + quote);
  assert.ok(!/위험 요구 문장을 칠했어요/.test(t), '형광펜 없음');
  assert.match(t, /AI 위험뚜렷한 신호 없음/);
  assert.match(t, /그 계좌로 입금하라는 문장은 위험으로 보지 않았어요/);
  }
});

test('블록체인 증거 한 줄(확인 블록·계약·기관 키), 금액이 다르면 받은 글의 그 금액에 밑줄', async () => {
  const { serverDouble: sd } = require('./_review_harness.js');
  const V = { session_id: 'vs_1', verification_status: 'INCONCLUSIVE', reason_codes: ['PARTIAL_COMPARISON'], comparison_scope: 'PARTIAL_COMPARISON', chain_id: 31337, verifying_contract: '0x' + '11'.repeat(20), block_number: '123', document: { key_id: '0x' + 'cd'.repeat(32), state: 'ACTIVE', version: 1, latest_version: 1, warnings: [] }, checks: [] };
  let miss = false;
  const f = sd({ persona: { role: 'recipient', issuer_id: null, username: 'kim' }, over: u => /document-lookups$/.test(u)
    ? { status: 200, body: miss ? { lookup_status: 'UNVERIFIED', match_count: 0, document_ids: [], reason_codes: ['NO_MATCHING_RETAINED_RECORD', 'AMOUNT_DIFFERS_FOR_ACCOUNT'] } : { lookup_status: 'MATCHED', match_count: 1, document_ids: ['0x' + 'ab'.repeat(32)], reason_codes: [], verification: V } } : null });
  const d = build('?mode=api', f);
  await sleep(20);
  enter(d, '[오리진 목 은행] 카드 대금 85,000원 청구 안내입니다. 입금계좌 001-234-500003'); await sleep(500);
  assert.match(threadText(d), /로컬 체인\(Anvil\) · 블록 #123 기준 · 계약 0x1111…1111 · 기관 키 0xcdcd…cdcd/);
  miss = true;
  enter(d, '[오리진 목 은행] 카드 대금 86,000원 청구 안내입니다. 입금계좌 001-234-500003'); await sleep(500);
  const marks = d.doc.querySelectorAll('#chatThread .op-diff').map(m => m.textContent);
  assert.deepEqual(marks, ['86,000원']);
  assert.match(threadText(d), /기관 기록과 다른 값은 빨간 밑줄로 표시했어요/);
});
test('진짜 안내문에 AI 위험·주의가 나오면 요약도 진짜 · 위험 요구/주의로, AI가 짚은 문장을 요약에 보여 줌', async () => {
  const { page, REAL, Ev } = require('./_review_common.js');
  for (const [level, chip, head] of [['HIGH', '진짜 · 위험 요구', '! 진짜 안내문이지만 위험한 요구가 붙어 있어요'], ['CAUTION', '진짜 · 주의', '! 진짜 안내문이에요 · 덧붙은 요구는 확인하세요'], ['NO_CLEAR_INDICATORS', '진짜', '✓ 진짜 안내문이에요']]) {
    const job = { analysis_id: 'ana_v', status: 'COMPLETED', input_kind: 'TEXT', retain_report: false, retain_original: false,
      report: { risk_level: level, evidence: level === 'NO_CLEAR_INDICATORS' ? [] : [{ quote: '다른 곳에는 문의하지 마세요', source: 'LLM' }], limitations: [] } };
    const d = page(u => u === '/api/v1/auth/me' ? { status: 200, body: { account_id: 'a', username: 'u', role: 'recipient', issuer_id: null, csrf_token: 'tok' } }
      : u === '/api/v3/document-lookups' ? { status: 200, body: REAL } : u === '/api/v3/inputs' ? { status: 201, body: { input_ref: 'inp_v', expires_at: 1 } } : u.startsWith('/api/v3/analyses') ? { status: u === '/api/v3/analyses' ? 202 : 200, body: job } : null);
    await sleep(10);
    const i = d.doc.getElementById('chatInput');
    i.value = '[오리진 목 은행] 합성 지방세 납부 안내입니다. 납부 금액: 120,000원, 입금 계좌: 합성 은행 001234567890. 다른 곳에는 문의하지 마세요.';
    d.doc._dispatch(i, new Ev('keydown', { key: 'Enter' }));
    await sleep(900);
    const v = d.doc.querySelectorAll('#chatThread .op-verdict')[0];
    assert.ok(v, level + ': 요약 카드');
    const t = v.textContent;
    assert.ok(t.includes(head) && t.includes(chip), level + ': ' + t);
    if (level !== 'NO_CLEAR_INDICATORS') assert.ok(t.includes('AI는 “다른 곳에는 문의하지 마세요”를') && !/AI (위험 신호|주의):/.test(t), level + ': ' + t);
  }
});

