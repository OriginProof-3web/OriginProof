'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { build, enter, sleep, serverDouble, PID, TX, WEB, Ev, press } = require('./_review_harness.js');
const html = fs.readFileSync(path.join(WEB, 'business.html'), 'utf8');
function rule(selector) {
  const start = html.indexOf(selector + '{');
  assert.ok(start >= 0, selector);
  return html.slice(start + selector.length + 1, html.indexOf('}', start));
}
test('상단 계정·테마는 스크롤 밖 정상 흐름, 320/375/1280 공통 높이 확보', () => {
  assert.match(html, /<div class="chat-tools"[^>]*>[\s\S]*id="authBtn"[\s\S]*id="themeBtn"[\s\S]*<\/div>\s*<section class="chat-scroll"/);
  assert.match(rule('.chat-tools'), /flex:none;min-height:60px;display:flex/);
  assert.match(rule('.chat-tools'), /gap:8px/);
  assert.doesNotMatch(html, /\.auth-btn,\s*\}/);
  for (const cls of ['.auth-btn', '.theme-btn']) assert.doesNotMatch(rule(cls), /position:|top:|right:/);
  assert.match(html, /@media\(max-width:1100px\)\{\.chat-tools\{padding-right:58px\}\}/);
  assert.match(html, /\.app.side-collapsed \.chat-tools\{padding-right:58px\}/);
});
function luminance(hex) {
  const rgb = hex.match(/\w\w/g).map(x => parseInt(x, 16) / 255).map(x => x <= .04045 ? x / 12.92 : ((x + .055) / 1.055) ** 2.4);
  return rgb[0] * .2126 + rgb[1] * .7152 + rgb[2] * .0722;
}
function contrast(a, b) { const x = luminance(a), y = luminance(b); return (Math.max(x, y) + .05) / (Math.min(x, y) + .05); }
test('밝은 결과·기술 증명·기관 메뉴의 텍스트 색 대비와 테마 연결', () => {
  const light = [...html.matchAll(/html\[data-theme="light"\]\{([^}]+)\}/g)].map(x => x[1]).join(';');
  const vars = Object.fromEntries([...light.matchAll(/--([\w-]+):#([\da-f]{6})/g)].map(x => [x[1], x[2]]));
  for (const [ink, bg] of [['c-ink','c-panel'], ['c-muted2','c-sunk'], ['c-faint','c-panel'], ['t-info','c-panel'], ['c-ink','z-fact-bg'], ['c-ink','z-ai-bg'], ['c-ink','c-field']]) {
    assert.ok(contrast(vars[ink], vars[bg]) >= 4.5, ink + '/' + bg);
  }
  for (const [ink, bg] of [['z-ai', 'z-ai-bg'], ...['t-ok', 't-fail', 't-caution', 't-info', 't-none', 'c-faint'].flatMap(ink => ['z-fact-bg', 'z-ai-bg', 'c-panel'].map(bg => [ink, bg]))]) {
    assert.ok(contrast(vars[ink], vars[bg]) >= 4.5, ink + '/' + bg);
  }
  assert.ok(contrast(vars['c-line-strong'], vars['c-field']) >= 3, '밝은 입력칸·단추 경계');
  assert.match(rule('.op-proof a'), /color:var\(--t-info\)/);
  assert.match(rule('.op-proof pre'), /color:var\(--c-muted2\);background:var\(--c-sunk\)/);
  assert.match(rule('.op-report,.op-gov'), /color:var\(--c-ink\)/);
  assert.match(rule('.op-input'), /background:var\(--c-field\);color:var\(--c-ink\)/);
  assert.match(rule('.op-proof summary'), /height:auto;min-height:34px/);
});
for (const chain of ['11155111', 11155111, '31337', '1', null]) {
  for (const tx of [TX, undefined, '', 'invalid']) {
    test('결과 Etherscan 거래 링크: chain=' + chain + ', hash=' + (tx ? (tx === TX ? 'valid' : 'invalid') : 'absent'), async () => {
      const d = build('?mode=api', serverDouble({ over: u => u === '/v3/verifications' ? { status: 200, body: {
        verification_status: 'VERIFIED', comparison_scope: 'ID_ONLY', document: { document_id: PID, state: 'ACTIVE' },
        checks: [], reason_codes: [], chain_id: chain, verifying_contract: '0x' + '56'.repeat(20), tx_hash: tx
      } } : null }));
      enter(d, JSON.stringify({ document_id: PID })); await sleep(90);
      const tech = d.doc.querySelector('details.op-proof'); assert.ok(tech);
      const links = tech.querySelectorAll('a');
      assert.equal(links.length, String(chain) === '11155111' ? (tx === TX ? 2 : 1) : 0);
      if (links.length) assert.equal(links[0].href, 'https://sepolia.etherscan.io/address/' + '0x' + '56'.repeat(20));
      for (const a of links) assert.equal(a.rel, 'noopener noreferrer');
      assert.match(tech.textContent, /2-of-3 승인 기록: 제공되지 않음/);
      assert.equal(tech.getAttribute('open'), null);
      assert.equal(tech.querySelector('pre'), null); // 결과에는 원문 JSON을 넣지 않습니다.
      d.win.Hk.chain.verify = () => Promise.resolve({ shape: '확인', headline: '대조', body: '', links: d.win.Hk.chain.explorerLinks(String(chain), '0x' + '56'.repeat(20), tx) });
      await press(d, '내 브라우저에서 체인 직접 대조하기');
      const after = tech.querySelectorAll('a').map(a => a.href);
      assert.equal(after.length, links.length);
      assert.equal(new Set(after).size, after.length);

    });
  }
}
test('체인 대조가 새 거래 링크를 추가하고 반복 대조에도 href는 유일하다', async () => {
  const registry = '0x' + '56'.repeat(20);
  const d = build('?mode=api', serverDouble({ over: u => u === '/v3/verifications' ? { status: 200, body: {
    verification_status: 'VERIFIED', comparison_scope: 'ID_ONLY', document: { document_id: PID, state: 'ACTIVE' },
    checks: [], reason_codes: [], chain_id: 11155111, verifying_contract: registry
  } } : null }));
  enter(d, JSON.stringify({ document_id: PID })); await sleep(90);
  const tech = d.doc.querySelector('details.op-proof');
  assert.equal(tech.querySelectorAll('a').length, 1);
  assert.equal(tech.querySelector('a').href, 'https://sepolia.etherscan.io/address/' + registry);
  d.win.Hk.chain.verify = () => Promise.resolve({ shape: '확인', headline: '대조', body: '',
    links: d.win.Hk.chain.explorerLinks('11155111', registry, TX) });
  for (let i = 0; i < 2; i++) {
    await press(d, '내 브라우저에서 체인 직접 대조하기');
    const links = tech.querySelectorAll('a');
    assert.equal(links.length, 2, '대조 결과의 새 거래 링크 유지');
    assert.equal(new Set(links.map(a => a.href)).size, 2);
    const tx = links.find(a => a.href === 'https://sepolia.etherscan.io/tx/' + TX);
    assert.ok(tx); assert.equal(tx.target, '_blank'); assert.equal(tx.rel, 'noopener noreferrer');
  }
});
test('기술 증명 summary → 시연 button → textarea → 보내기: 기본 키보드 요소와 문서 순서', async () => {
  const d = build('', serverDouble({}));
  enter(d, d.win.Hk.sampleAdapter.get('unregistered').input.text); await sleep(90);
  const summary = d.doc.querySelector('details.op-proof summary'); assert.ok(summary);
  assert.equal(summary.getAttribute('tabindex'), null);
  const presets = d.doc.querySelectorAll('#presetBar button'); assert.ok(presets.length > 0);
  for (const b of presets) { assert.equal(b.type, 'button'); assert.notEqual(b.getAttribute('tabindex'), '-1'); assert.ok(!b.disabled); }
  const input = d.doc.getElementById('chatInput'), send = d.doc.getElementById('sendBtn');
  assertKeyboardTags(html);
  input.value = '다음 확인'; d.doc._dispatch(input, new Ev('input'));
  assert.equal(send.disabled, false);
  assert.ok(html.indexOf('id="chatThread"') < html.indexOf('id="presetBar"'));
  assert.ok(html.indexOf('id="presetBar"') < html.indexOf('id="chatInput"'));
  assert.ok(html.indexOf('id="chatInput"') < html.indexOf('id="sendBtn"'));
  assert.match(html, /<textarea id="chatInput"/); assert.match(html, /<button type="submit"[^>]*id="sendBtn"/);
  assert.match(html, /:focus-visible\{outline:2px solid var\(--c-accent\)/);
});

// 실제 business.html의 시작 태그를 검사합니다(가짜 DOM 하네스는 속성을 복사하지 않습니다).
function assertKeyboardTags(source) {
  for (const [tag, id] of [['textarea', 'chatInput'], ['button', 'sendBtn']]) {
    const element = [...source.matchAll(/<[a-z]+\b[^>]*>/gi)].map(x => x[0]).find(x => new RegExp('\\bid=["\']' + id + '["\']').test(x));
    assert.ok(element && element.startsWith('<' + tag), id);
    const tabindex = element.match(/\btabindex\s*=\s*(?:"([^" ]+)"|'([^' ]+)'|([^\s>]+))/i);
    if (tabindex) assert.ok(Number(tabindex[1] || tabindex[2] || tabindex[3]) >= 0, id + ' 음수 tabindex');
  }
}
test('실제 HTML 검사와 음수 tabindex 메모리 사본 거부', () => {
  assertKeyboardTags(html);
  for (const id of ['chatInput', 'sendBtn']) {
    const mutated = html.replace(new RegExp('<[a-z]+\\b[^>]*id="' + id + '"[^>]*>'), tag => tag.replace('>', ' tabindex="-1">'));
    assert.notEqual(mutated, html);
    assert.throws(() => assertKeyboardTags(mutated), /음수 tabindex/);
  }
});
const vm = require('node:vm');
const auth = fs.readFileSync(path.join(WEB, 'js/op5_auth.js'), 'utf8');
for (const width of [320, 375, 759, 760, 761, 1280]) {
  test('foldNarrow 실제 함수: 폭 ' + width, () => {
    assert.match(html, /src="js\/op5_auth.js"/);
    assert.match(auth, /function start\(\)\s*{\s*foldNarrow\(20\)/);
    const fn = auth.slice(auth.indexOf('  function foldNarrow('), auth.indexOf('  function start()'));
    let clicks = 0, ready = false;
    const timers = [];
    const ctx = { root: { matchMedia: q => { assert.equal(q, '(max-width:760px)'); return { matches: width <= 760 }; } }, document: { querySelector: q => { assert.equal(q, '#sidebar-root .sidebar-collapse-control'); return ready ? { click() { clicks++; } } : null; } }, setTimeout: f => timers.push(f) };
    vm.runInNewContext(fn + ';foldNarrow(20)', ctx);
    assert.equal(clicks, 0);
    ready = true;
    while (timers.length) timers.shift()();
    assert.equal(clicks, width <= 760 ? 1 : 0);
  });
}
for (const registry of ['0x' + '56'.repeat(20), 'invalid', '', '0x12']) {
  test('Etherscan 주소·hash 경계 및 체인 대조 후 중복 제거: ' + registry, async () => {
    const d = build('?mode=api', serverDouble({ over: u => u === '/v3/verifications' ? { status: 200, body: {
      verification_status: 'VERIFIED', comparison_scope: 'ID_ONLY', document: { document_id: PID, state: 'ACTIVE' }, checks: [], reason_codes: [], chain_id: '11155111', verifying_contract: registry, tx_hash: TX
    } } : null }));
    enter(d, JSON.stringify({ document_id: PID })); await sleep(90);
    const tech = d.doc.querySelector('details.op-proof');
    const expected = registry.length === 42 ? 2 : 1;
    assert.equal(tech.querySelectorAll('a').length, expected);
    const chain = d.win.Hk.chain;
    for (const hash of [TX, null, '0x12', 'invalid']) {
      const links = chain.explorerLinks('11155111', registry, hash);
      assert.equal(links.length, (registry.length === 42 ? 1 : 0) + (hash === TX ? 1 : 0));
      assert.equal(chain.explorerLinks('31337', registry, hash).length, 0);
      chain.verify = () => Promise.resolve({ shape: '확인', headline: '대조', body: '', links });
      await press(d, '내 브라우저에서 체인 직접 대조하기');
      const hrefs = tech.querySelectorAll('a').map(a => a.href);
      assert.equal(new Set(hrefs).size, hrefs.length);
      assert.equal(hrefs.length, expected);
    }
  });
}
test('모든 예시·연결 전·링크 없는 응답과 복사 글의 작업 메모·파일 경로 미노출', async () => {
  const d = build('', serverDouble({}));
  const internal = /A 화면|B 시안|시안|docs\/|웹_설계|디자인_비교|가져왔습니다|표 값을 조합|멘토 명령|피터가|[\w가-힣-]+\.(?:html|md|png)(?=$|[^\w.-])/;
  // 사용자 원문과 그 원문에서 찾은 참조는 검사에서 제외합니다.
  // 정상 도메인의 .com/.org 및 일반 예시 입력은 내부 파일 경로가 아닙니다.
  for (const text of ['https://example.com/notice', '예시 안내 문자입니다']) assert.doesNotMatch(text, internal);
  const inputs = d.win.Hk.sampleAdapter.list().map(s => s.input.text).concat([
    'prf_w6_unknown_document', '검증 링크 없이 받은 일반 안내 문자입니다'
  ]);
  const answers = [];
  for (const input of inputs) {
    const answer = await d.win.Hk.sampleAdapter.check(input);
    answers.push(answer);
    const { input: original, ref, ...display } = answer;
    assert.doesNotMatch(JSON.stringify(display), internal, answer.id);
    assert.doesNotMatch(d.win.Hk.text.buildCopyText(answer), internal, answer.id + ' 복사 글');
    enter(d, input); await sleep(50);
  }
  assert.equal(answers[answers.length - 2].id, 'not_connected');
  assert.equal(answers[answers.length - 1].id, 'no_reference');
  assert.doesNotMatch(d.doc.getElementById('chatThread').textContent, internal);
});
for (const outcome of [200, 403, 410, 500, 'reject', 'pending', 'mismatch']) {
  test('발행 서명 보조 조회 ' + outcome + ': 결과 비차단·승인과 구분', async () => {
    const signature = '0x' + 'ab'.repeat(65);
    let calls = 0, release;
    const d = build('?mode=api', serverDouble({ over: u => {
      if (u === '/v3/verifications') return { status: 200, body: {
        verification_status: 'VERIFIED', comparison_scope: 'ID_ONLY', document: { document_id: PID, version: 2, state: 'ACTIVE' }, checks: [], reason_codes: []
      } };
      return null;
    } }));
    // 실제 기존 클라이언트의 fetch 경계에서 실패·응답 지연을 주입합니다.
    const fetch = d.win.fetch;
    d.win.fetch = (u, init) => {
      if (!String(u).includes('/verification-material')) return fetch(u, init);
      calls++;
      assert.ok(String(u).endsWith('/v3/documents/' + PID + '/verification-material?version=2'));
      if (outcome === 'reject') return Promise.reject(new Error('network'));
      if (outcome === 'pending') return new Promise(resolve => { release = resolve; });
      return Promise.resolve({ status: typeof outcome === 'number' ? outcome : 200, ok: outcome === 200 || outcome === 'mismatch', headers: { get() { return 'application/json'; } }, text: async () => JSON.stringify({ signature, signing_request: { message: { documentId: PID, version: outcome === 'mismatch' ? 1 : 2 } } }) });
    };
    enter(d, JSON.stringify({ document_id: PID })); await sleep(100);
    const tech = d.doc.querySelector('details.op-proof');
    assert.ok(tech, '보조 요청보다 결과를 먼저 표시');
    assert.equal(calls, 1);
    assert.match(d.doc.getElementById('chatThread').textContent, /진짜/);
    assert.match(tech.textContent, /2-of-3 승인 기록: 제공되지 않음/);
    if (outcome === 200) assert.ok(tech.textContent.includes('signature: ' + signature + ' · 기관 발행 서명'));
    else assert.match(tech.textContent, /signature: 제공되지 않음/);
    if (release) { release({ status: 410, ok: false, headers: { get() { return 'application/json'; } }, text: async () => '{}' }); await sleep(10); }
  });
}
