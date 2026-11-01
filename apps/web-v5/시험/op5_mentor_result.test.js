'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { build, enter, sleep, serverDouble, PID } = require('./_review_harness.js');

for (const id of ['normal', 'tamper', 'unregistered']) {
  test('멘토 결과 순서·기술 접기·RAG 없음: ' + id, async () => {
    const d = build('', serverDouble({}));
    const a = d.win.Hk.sampleAdapter.get(id);
    enter(d, a.input.text);
    await sleep(60);
    const bubble = d.doc.querySelector('#chatThread .msg-ai .bubble');
    const tech = bubble.querySelector('details.op-proof');
    assert.ok(tech);
    assert.equal(tech.getAttribute('open'), null);
    assert.equal(tech.querySelector('summary').textContent, '기술 증명 보기');
    assert.ok(tech.querySelector('button').textContent.includes('체인 직접'));
    assert.match(tech.textContent, /2-of-3 승인 기록.*제공되지/);
    assert.doesNotMatch(bubble.textContent, /수법 지식베이스|자세히 보기/);
    assert.ok(bubble.textContent.indexOf('다음 행동') < bubble.textContent.indexOf('블록체인 결정'));
    for (const row of a.details) assert.ok(tech.textContent.includes(row.label + ': ' + row.value));
    if (id === 'unregistered') {
      assert.match(bubble.textContent, /기관 대표번호나 공식 앱/);
      assert.equal(bubble.querySelector('.op-concl strong').className, 'op-chip t-none');
      assert.equal(a.verification_status, 'NOT_REGISTERED');
    }
    if (id === 'tamper') assert.match(bubble.textContent, /돈을 보내지 마세요/);
  });
}

test('실서버 응답 NOT_REGISTERED 중립 안내·엔진값 보존, TAMPERED 경고 유지', async () => {
  for (const status of ['NOT_REGISTERED', 'TAMPERED']) {
    const f = serverDouble({ over: u => u === '/v3/verifications' ? { status: 200, body: {
      verification_status: status, comparison_scope: 'ID_ONLY', document: null,
      reason_codes: [], checks: [], chain_id: '31337', block_number: null
    } } : null });
    const d = build('?mode=api', f);
    const a = await d.win.Hk.createApiAdapter({ base: '/api', fetch: f }).check(JSON.stringify({ document_id: PID }));
    assert.equal(a.verification_status, status);
    if (status === 'NOT_REGISTERED') {
      assert.equal(a.conclusion.badge.tone, 'none');
      assert.match(a.next_action.text, /기관 대표번호나 공식 앱/);
      assert.doesNotMatch(a.next_action.text, /돈을 보내지/);
    } else assert.match(a.next_action.text, /돈을 보내지/);
  }
});
