'use strict';
// 회원 AI 키: 말풍선에 키가 남지 않고, 접두어로 Claude/GPT 를 고름. 가짜 DOM(브라우저 아님)
const test = require('node:test'); const assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path');
const { page, sleep, WEB, Ev } = require('./_review_common.js');
const CLAUDE = 'sk-ant-' + 'a'.repeat(30) + 'WXYZ', GPT = 'sk-' + 'b'.repeat(30) + 'QRST';

function boot(usage) {
  let saved = { provider: null, hint: null, storage_enabled: true, input_tokens: 0, output_tokens: 0, analyses: 0 };
  const d = page((u, init) => {
    if (u === '/api/v1/auth/me') return { status: 200, body: { account_id: 'a', username: 'u', role: 'recipient', issuer_id: null, csrf_token: 'tok' } };
    if (u === '/api/v1/auth/ai-key') {
      if (init && init.method === 'POST') { const b = JSON.parse(init.body); saved = { provider: b.provider, hint: b.key.slice(-4), storage_enabled: true, input_tokens: 0, output_tokens: 0, analyses: 0 }; }
      if (init && init.method === 'DELETE') saved = { provider: null, hint: null, storage_enabled: true, input_tokens: 0, output_tokens: 0, analyses: 0 };
      if (usage && (!init || !init.method || init.method === 'GET')) { const r = usage.shift(); if (r) saved = r; }
      return { status: 200, body: saved };
    }
    return { status: 404, body: {} };
  });
  return d;
}
async function openStatus(d) { await sleep(10); d.win.selectAction('status'); await sleep(40); }
const button = (d, label) => d.doc.querySelectorAll('#chatThread button').find(b => b.textContent === label);

for (const [key, provider, name] of [[CLAUDE, 'anthropic', 'Claude'], [GPT, 'openai', 'GPT']]) {
  test(name + ' 키: 접두어로 공급자를 고르고 CSRF 와 함께 보내며 화면에는 끝 4자리만 남김', async () => {
    const d = boot();
    await openStatus(d);
    const box = d.doc.querySelector('#chatThread .op-input');
    box.value = key;
    button(d, 'AI 키 저장').click();
    await sleep(40);
    const put = d.win.fetch.calls.find(c => c.url === '/api/v1/auth/ai-key' && c.init.method === 'POST');
    assert.deepEqual(JSON.parse(put.init.body), { provider, key });
    assert.equal(put.init.headers['X-CSRF-Token'], 'tok');
    assert.equal(box.value, '');
    const all = d.doc.getElementById('chatThread').textContent;
    assert.ok(!all.includes(key), '화면에 키 전체가 남음');
    assert.match(all, new RegExp(name + ' · 끝자리 ' + key.slice(-4)));
  });
}

test('AI 키 지우기', async () => {
  const d = boot();
  await openStatus(d);
  d.doc.querySelector('#chatThread .op-input').value = CLAUDE;
  button(d, 'AI 키 저장').click(); await sleep(40);
  button(d, 'AI 키 지우기').click(); await sleep(40);
  assert.match(d.doc.getElementById('chatThread').textContent, /없음 · 서버 기본 설정으로 분석해요/);
});

const K = (i, o, n) => ({ provider: 'anthropic', hint: 'WXYZ', storage_enabled: true, input_tokens: i, output_tokens: o, analyses: n });
function withHelp(d) {
  const side = d.doc.getElementById('sidebar-root');
  const wrap = d.doc.createElement('div'), help = d.doc.createElement('button');
  help.textContent = '도움말'; wrap.append(help); side.append(wrap);
}

test('메뉴 카드: 도움말 위에 공급자·끝자리·토큰을 보여 주고 키 전체는 보이지 않음', async () => {
  const d = boot([K(1200, 34, 2)]);
  withHelp(d);
  await sleep(150);
  const card = d.doc.getElementById('aiUsageCard');
  assert.ok(card);
  assert.match(card.textContent, /Claude · 끝자리 WXYZ/);
  assert.match(card.textContent, /토큰 1,234 \(입력 1,200 · 출력 34\)/);
  assert.match(card.textContent, /분석 2건/);
  const side = d.doc.getElementById('sidebar-root').children;
  assert.ok(side.indexOf(card) < side.findIndex(n => n.textContent.includes('도움말')));
});

test('분석 뒤: 토큰이 늘면 AI 가 답했다고, 그대로면 못 했다고 알림', async () => {
  for (const [after, want] of [[K(150, 50, 1), /Claude 키로 AI 분석을 했어요. 이번에 토큰 200개\(입력 150 · 출력 50\)/], [K(0, 0, 0), /AI 분석을 하지 못해 규칙 검사 결과만/]]) {
    const d = boot([K(0, 0, 0), after]);
    withHelp(d);
    await sleep(120);
    const i = d.doc.getElementById('chatInput'); i.value = '[OO은행] 비밀번호를 입력하세요.';
    d.doc._dispatch(i, new Ev('keydown', { key: 'Enter' }));
    await sleep(1500);
    assert.match(d.doc.getElementById('chatThread').textContent, want);
  }
});

test('가입 화면: 키를 브라우저에 저장하지 않고 서버 저장 경로로 보내며 외부 AI 를 부르지 않음', () => {
  const html = fs.readFileSync(path.join(WEB, 'join.html'), 'utf8');
  assert.ok(!html.includes('V.save('));
  assert.match(html, /\/api\/v1\/auth\/ai-key/);
  assert.doesNotMatch(html, /api\.(openai|anthropic)\.com/);
  assert.doesNotMatch(html, /키는 OriginProof 서버로 보내지 않아요/);
});
