// 시연용 AI 지연 대체 응답 시험(5차 멘토 피드백, 기본 꺼짐).
//   node --test 시험/demo_ai_fallback.test.js
// 가짜 fetch·가짜 시계로만 돌림(실서버·실제 AI 호출 없음). 준비 응답 문구는 합성 시나리오 설명만 담음.
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { loadWeb, fakeFetch, fixture } = require('./가져온/regression/_load.js');
const { makeDom, Ev } = require('./_dom.js');

const URL0 = 'http://127.0.0.1:8000';
const LABEL = '준비된 시연 응답 · 실제 AI 결과 아님';
const wait = ms => new Promise(r => setTimeout(r, ms));
const j = x => JSON.parse(JSON.stringify(x));
const V1 = fixture('v1_verify_tampered.response.json');

// 실서버 흉내: 검증은 v1 응답, AI 작업은 state.done 이 true 가 될 때까지 RUNNING
function server(state) {
  return fakeFetch(url => {
    if (url.endsWith('/v1/mvp/card-notices/verify')) return { status: 200, body: V1 };
    if (url.endsWith('/v3/inputs')) return { status: 201, body: { input_ref: 'inp_demo', expires_at: 1 } };
    if (url.endsWith('/v3/analyses')) return { status: 202, body: { analysis_id: 'ana_demo1', status: 'QUEUED' } };
    if (url.includes('/v3/analyses/')) {
      state.polls = (state.polls || 0) + 1;
      if (state.deleted) return { status: 200, body: { analysis_id: 'ana_demo1', status: 'CANCELLED' } };
      if (!state.done) return { status: 200, body: { analysis_id: 'ana_demo1', status: 'RUNNING' } };
      return { status: 200, body: { analysis_id: 'ana_demo1', status: 'COMPLETED', error_code: null, report: state.report } };
    }
    return null;
  });
}
const REAL_HIGH = { risk_level: 'HIGH', evidence: [{ rule_id: 'R_REMOTE_APP', quote: '원격 지원 앱을 설치해 주세요', start_offset: null, end_offset: null, source: 'LLM' }], limitations: [], verification_not_run_reason: null };

/* 가짜 시계: 폴링 sleep(ms<1000)은 시계를 ms 만큼 당기고 바로 넘어감.
   1000ms 이상 sleep 은 시연 대체 대기라 gate 를 열 때까지 멈춤(초 값은 longSleeps 에 남김). */
function make(Hk, state, adapterOpts) {
  let t = 0;
  const longSleeps = [];
  let open;
  const gate = new Promise(r => { open = r; });
  const sleep = ms => {
    if (ms >= 1000) { longSleeps.push(ms); return gate; }
    t += ms; return new Promise(r => setTimeout(r, 1));
  };
  const f = server(state);
  const a = Hk.createApiAdapter(Object.assign({
    fetch: f, serverUrl: URL0, pollMs: 10, pollLimitMs: 1000, timeoutMs: 500, sleep, now: () => t,
    isDeleted: () => state.deleted === true
  }, adapterOpts || {}));
  return { a, f, longSleeps, open };
}
function sampleText(Hk, id) { return Hk.sampleAdapter.get(id).input.text; }
const ai = ans => ans.axes.find(x => x.axis === 'ai');
const facts = ans => j({ vs: ans.verification_status, axes: ans.axes.filter(x => x.axis !== 'ai'), conclusion: ans.conclusion, chain: ans.chain_claim });
function laterPromise() { let r; const p = new Promise(x => { r = x; }); return { p, fn: ev => r(ev) }; }

test('초 값: 없음·0·숫자 아님은 꺼짐, 값 없음은 기본 5초, 숫자는 3~10초로 제한', () => {
  const Hk = loadWeb();
  const f = Hk.api.demoFallbackSec;
  const cases = [[null, 0], [undefined, 0], ['0', 0], ['abc', 0], ['-5', 0], ['5.5', 0], ['1e3', 0], [' ', 5], ['', 5], ['1', 3], ['3', 3], ['5', 5], ['7', 7], ['10', 10], ['11', 10], ['999', 10], [5, 5], [0, 0], [NaN, 0]];
  for (const [raw, want] of cases) assert.equal(f(raw), want, JSON.stringify(raw));
  assert.deepEqual(j(Hk.api.DEMO_FALLBACK), { min: 3, max: 10, def: 5 });
});

test('어댑터에 넘긴 초 값도 같은 규칙: 1→3초, 99→10초, 기본 5초로 기다림', async () => {
  for (const [opt, ms] of [[1, 3000], [99, 10000], ['', 5000]]) {
    const Hk = loadWeb();
    const st = {};
    const { a, longSleeps, open } = make(Hk, st, { demoAiFallbackSec: opt });
    const p = a.check(sampleText(Hk, 'unregistered'));
    await wait(30); open(); await p;
    assert.deepEqual(longSleeps, [ms], 'opt=' + opt);
  }
});

test('꺼짐(기본): 시나리오 문자라도 준비 응답 없이 기존처럼 실제 결과를 기다리고, 0·잘못된 값도 같은 답', async () => {
  const answers = [];
  for (const opt of [{}, { demoAiFallbackSec: 0 }, { demoAiFallbackSec: 'abc' }]) {
    const Hk = loadWeb();
    const st = {};
    let later = 0;
    const { a, longSleeps } = make(Hk, st, opt);
    setTimeout(() => { st.done = true; st.report = REAL_HIGH; }, 40);
    const ans = await a.check(sampleText(Hk, 'unregistered'), { onAiLater: () => later++ });
    assert.equal(longSleeps.length, 0, '꺼짐인데 대체 대기를 걸었음');
    assert.equal(later, 0);
    assert.equal(ans.ai_prepared, null);
    assert.equal(ans.ai_replaced, false);
    assert.equal(ans.label, '실제 서버 응답');
    assert.equal(ans.analysis_status, 'COMPLETED');
    assert.ok(!JSON.stringify(ans).includes('준비된 시연'), '꺼짐인데 준비 응답 흔적');
    answers.push(j({ axes: ans.axes, conclusion: ans.conclusion, staff: ans.staff, ai_report: ans.ai_report, vs: ans.verification_status }));
  }
  assert.deepEqual(answers[1], answers[0]);
  assert.deepEqual(answers[2], answers[0]);
});

test('꺼짐: 실제 결과가 끝내 안 오면 기존 시간 초과(ai.timeout) 그대로', async () => {
  const Hk = loadWeb();
  const { a } = make(Hk, {}, {});
  const ans = await a.check(sampleText(Hk, 'unregistered'));
  assert.equal(ai(ans).status, '보류');
  assert.equal(ans.staff.find(s => s.staff === 'ai').bubble_key, 'ai.timeout');
  assert.ok(ans.details.some(d => /ANALYSIS_POLL_TIMEOUT/.test(d.value)));
});

test('켜짐 + 지연(원격 지원 사칭): N초 뒤 준비 응답을 AI 칸에만, 라벨·칩·자세히·기록에 표시, 발행 검증 칸은 그대로', async () => {
  const Hk = loadWeb();
  const st = {};
  const lp = laterPromise();
  const { a, open } = make(Hk, st, { demoAiFallbackSec: 5 });
  const p = a.check(sampleText(Hk, 'unregistered'), { onAiLater: lp.fn });
  await wait(30);
  assert.ok(st.polls >= 1, '폴링 중이어야 함');
  open();
  const ans = await p;
  assert.equal(ans.ai_prepared, 'unregistered');
  assert.match(ans.label, new RegExp(LABEL));
  const x = ai(ans);
  assert.equal(x.prepared, true);
  assert.equal(x.status, '준비된 시연 응답 · 위험 신호');
  assert.equal(x.tone, 'fail');
  assert.ok(x.body.startsWith('[' + LABEL + ']'), x.body);
  assert.match(x.body, /고위험: 원격 지원 앱 설치/);
  assert.match(x.note, new RegExp('^' + LABEL));
  const chip = ans.staff.find(s => s.staff === 'ai');
  assert.match(chip.line1, /^\[준비된 시연 응답\]/);
  assert.equal(chip.line3, LABEL);
  assert.ok(ans.details.some(d => d.label === '준비된 시연 응답' && /unregistered/.test(d.value) && /5초/.test(d.value)));
  assert.ok(ans.details.some(d => d.label === 'AI 결과' && /준비된 시연 응답\(unregistered\)/.test(d.value)));
  assert.equal(ans.ai_report.evidence[0].source, 'DEMO_PREPARED');
  assert.deepEqual(j(ans.ai_report.limitations), ['DEMO_PREPARED_RESPONSE_NOT_AI_RESULT']);
  assert.equal(ans.analysis_id, 'ana_demo1');
  // 근거 위치(형광펜)는 보낸 글 안에서 찾음
  const sp = Hk.api.evidenceSpans(ans.input.text, ans.ai_report.evidence);
  assert.equal(sp.spans.length, 1);
  // 발행 검증(4칸·결론)은 꺼짐일 때와 같음
  const Hk2 = loadWeb();
  const st2 = { done: true, report: REAL_HIGH };
  const off = await make(Hk2, st2, {}).a.check(sampleText(Hk2, 'unregistered'));
  assert.deepEqual(facts(ans), facts(off));
  for (const s of ['intake', 'ledger', 'signature', 'original', 'status']) assert.deepEqual(j(ans.staff.find(o => o.staff === s)), j(off.staff.find(o => o.staff === s)), s);
  // 실제 결과가 pollLimit 안에 안 오면 교체하지 않고 사유만 알림
  const ev = await lp.p;
  assert.deepEqual(j(ev), { replaced: false, reason: 'timeout' });
});

test('켜짐 + 정상·1원 변조 문자: 위험 신호 없음 준비 응답, 변조는 체인 대조가 판정한다고 적음', async () => {
  for (const id of ['normal', 'tamper']) {
    const Hk = loadWeb();
    const { a, open } = make(Hk, {}, { demoAiFallbackSec: 4 });
    const p = a.check(sampleText(Hk, id));
    await wait(30); open();
    const ans = await p;
    assert.equal(ans.ai_prepared, id);
    const x = ai(ans);
    assert.equal(x.status, '준비된 시연 응답 · 뚜렷한 신호 없음');
    assert.equal(x.tone, 'info');
    assert.match(x.body, /4초 안에 끝나지 않아/);
    if (id === 'tamper') assert.match(x.body, /블록체인 기록 대조\(원본 일치 칸\)가 판정/);
    else assert.ok(!/블록체인 기록 대조/.test(x.body));
    assert.equal(ans.ai_report.evidence.length, 0);
  }
});

test('켜짐 + 늦은 실제 결과: 준비 응답 뒤 실제 결과가 오면 AI 칸만 교체하고 교체 표시, 검증 칸은 같음', async () => {
  const Hk = loadWeb();
  const st = {};
  const lp = laterPromise();
  const { a, open } = make(Hk, st, { demoAiFallbackSec: 5 });
  const p = a.check(sampleText(Hk, 'unregistered'), { onAiLater: lp.fn });
  await wait(30); open();
  const first = await p;
  assert.equal(first.ai_prepared, 'unregistered');
  const pollsAtPrep = st.polls;
  st.done = true; st.report = REAL_HIGH;
  const ev = await lp.p;
  assert.ok(st.polls > pollsAtPrep, '준비 응답 뒤에도 폴링을 계속해야 함');
  assert.equal(ev.replaced, true);
  assert.equal(ev.reason, 'result');
  const b = ev.answer;
  assert.equal(b.ai_replaced, true);
  assert.equal(b.ai_prepared, null);
  assert.equal(b.label, '실제 서버 응답');
  assert.equal(b.analysis_status, 'COMPLETED');
  const x = ai(b);
  assert.equal(x.status, '위험 신호');
  assert.ok(!x.body.includes('준비된 시연'), x.body);
  assert.match(x.note, /^준비된 시연 응답을 서버 분석 결과로 교체했어요/);
  assert.equal(b.ai_report.evidence[0].source, 'LLM');
  assert.equal(ev.obs.bubble_key, 'ai.high');
  assert.ok(!/준비된 시연/.test(ev.obs.line1));
  assert.ok(b.details.some(d => d.label === '준비된 시연 응답' && /서버 분석 결과로 교체함/.test(d.value)));
  assert.ok(b.details.some(d => d.label === 'AI 결과' && /교체 · status=COMPLETED/.test(d.value)));
  assert.deepEqual(facts(b), facts(first));
  assert.equal(b.staff.filter(s => s.staff === 'ai').length, 1);
});

test('켜짐 + N초 안에 실제 결과: 준비 응답을 쓰지 않음', async () => {
  const Hk = loadWeb();
  let later = 0;
  const { a } = make(Hk, { done: true, report: REAL_HIGH }, { demoAiFallbackSec: 5 });
  const ans = await a.check(sampleText(Hk, 'unregistered'), { onAiLater: () => later++ });
  assert.equal(ans.ai_prepared, null);
  assert.equal(ai(ans).status, '위험 신호');
  await wait(20);
  assert.equal(later, 0);
});

test('켜짐 + 시나리오와 다른 글(한 글자만 달라도): 대체 대기 없이 기존처럼 기다리다 기존 시간 초과', async () => {
  const Hk = loadWeb();
  const t0 = sampleText(Hk, 'unregistered');
  for (const text of [t0.replace('384,000원', '384,001원'), '[OO카드] 결제 안내입니다. 검증 링크 없음']) {
    const { a, longSleeps } = make(Hk, {}, { demoAiFallbackSec: 5 });
    const ans = await a.check(text);
    assert.equal(longSleeps.length, 0);
    assert.equal(ans.ai_prepared, null);
    assert.equal(ans.staff.find(s => s.staff === 'ai').bubble_key, 'ai.timeout');
  }
  // 공백 차이만 있는 글은 같은 시나리오로 봄
  const Hk2 = loadWeb();
  const { a, open } = make(Hk2, {}, { demoAiFallbackSec: 5 });
  const p = a.check('  ' + t0.replace(/ /g, '  ') + '\n');
  await wait(30); open();
  assert.equal((await p).ai_prepared, 'unregistered');
});

test('켜짐 + 문서 사진 입력: 준비 응답 대상 아님', async () => {
  const Hk = loadWeb();
  const { a, longSleeps } = make(Hk, { done: true, report: REAL_HIGH }, { demoAiFallbackSec: 5 });
  const ans = await a.check(sampleText(Hk, 'unregistered'), { image: { media_type: 'image/png', base64: 'iVBORw0KGgo=' } });
  assert.equal(longSleeps.length, 0);
  assert.equal(ans.ai_prepared, null);
});

test('켜짐 + 사용자가 지운 분석: 준비 응답 전후 모두 기존 삭제 처리(늦은 응답 무시, 교체 없음)', async () => {
  // 준비 응답 뒤 지움
  let Hk = loadWeb();
  let st = {};
  const lp = laterPromise();
  let m = make(Hk, st, { demoAiFallbackSec: 5 });
  let p = m.a.check(sampleText(Hk, 'unregistered'), { onAiLater: lp.fn });
  await wait(30); m.open();
  const first = await p;
  assert.equal(first.ai_prepared, 'unregistered');
  st.deleted = true;
  assert.deepEqual(j(await lp.p), { replaced: false, reason: 'deleted' });
  assert.ok(first.details.length > 0);
  // 준비 응답 전에 지움 → 기존 '지운 분석' 답, 준비 응답 없음
  Hk = loadWeb(); st = {};
  m = make(Hk, st, { demoAiFallbackSec: 5 });
  p = m.a.check(sampleText(Hk, 'unregistered'));
  await wait(30); st.deleted = true; m.open();
  const ans = await p;
  assert.equal(ans.ai_prepared, null);
  assert.equal(ans.analysis_deleted, true);
  assert.equal(ans.staff.find(s => s.staff === 'ai').bubble_key, 'ai.cancelled');
});

test('준비 응답 문구: 합성 시나리오 설명만, 개인정보 형식(전화·계좌·주민번호) 없음', () => {
  const src = fs.readFileSync(path.join(__dirname, '..', '페이지', 'js', 'api_adapter.js'), 'utf8');
  const block = src.slice(src.indexOf('var PREPARED = {'), src.indexOf('function demoFallbackSec'));
  assert.ok(block.length > 100);
  assert.ok(!/\d{2,3}-\d{3,4}-\d{4}|\d{6}-\d{7}|\d{3}-\d{3}-\d{6}/.test(block), block);
});

test('실서버 시연 문자(시연 버튼·A1~A3·C1)도 준비 응답이 있고, 근거 문장은 서버로 보내는 글(가린 글) 안에 있음', () => {
  const Hk = loadWeb();
  const T = Hk.api.DEMO_TEXTS;
  assert.deepEqual(Object.keys(T).sort(), ['bank_account', 'bank_amount', 'bank_genuine', 'other_issuer', 'rc_normal', 'rc_risky']);
  for (const id of Object.keys(T)) {
    assert.equal(Hk.api.preparedScenario(T[id]), id);
    assert.equal(Hk.api.preparedScenario(T[id].replace(/^\[Web발신\]\n/, '')), id, id + ' [Web발신] 없이 붙여 넣어도');
  }
  const src = fs.readFileSync(path.join(__dirname, '..', '페이지', 'js', 'api_adapter.js'), 'utf8');
  for (const [id, quote] of [['rc_risky', '원격 지원 앱을 설치해 주세요'], ['bank_account', '오늘 정지 예정'], ['bank_account', '즉시 아래 계좌로 입금하세요'], ['other_issuer', '본인 확인 후 수령하세요']]) {
    assert.ok(src.includes("quote: '" + quote + "'"), quote);
    assert.ok(Hk.text.maskPersonal(T[id]).includes(quote), id + ': ' + quote);
  }
});

/* ---------- 화면(op5_connect.js) ---------- */
const WEB = path.resolve(__dirname, '../페이지');
const read = f => fs.readFileSync(path.join(WEB, f), 'utf8');
const HTML = read('business.html');
const SCRIPTS = [...HTML.matchAll(/<script src="((?:data|js)\/[^"]+)"><\/script>/g)].map(m => m[1]);
const INLINE = (() => { const i = HTML.indexOf('function selectAction'); return HTML.slice(HTML.lastIndexOf('<script>', i) + 8, HTML.indexOf('</script>', i)); })();
function screen(search, fetchFn) {
  const d = makeDom(search);
  const { win, doc, El } = d;
  const e = (tag, attrs, parent, text) => { const n = new El(tag, doc); Object.entries(attrs || {}).forEach(([k, v]) => (k === 'class' ? (n.className = v) : n.setAttribute(k, v))); if (text) n.textContent = text; if (parent) parent.append(n); return n; };
  const app = e('div', { class: 'app', id: 'app' }, doc.body);
  const side = e('div', { id: 'sidebar-root', class: 'dark' }, app);
  e('button', { type: 'button' }, side, '도움말');
  e('input', { 'aria-label': '최근 확인 검색' }, side);
  const main = e('main', { class: 'main chat-main' }, app);
  e('button', { class: 'theme-btn', id: 'themeBtn' }, main);
  const sc = e('section', { class: 'chat-scroll', id: 'chatScroll' }, main);
  const th = e('div', { class: 'chat-thread', id: 'chatThread' }, sc);
  const em = e('div', { class: 'chat-empty', id: 'chatEmpty' }, th);
  e('h1', null, em, '무엇을 확인할까요?');
  const wrap = e('div', { class: 'composer-wrap' }, main);
  const form = e('form', { class: 'composer', id: 'composer' }, wrap);
  e('textarea', { id: 'chatInput' }, form);
  const bar = e('div', { class: 'composer-bar' }, form);
  e('button', { class: 'composer-icon', id: 'attachBtn' }, bar, '＋');
  e('span', { class: 'composer-note', id: 'attachNote' }, bar);
  e('button', { class: 'composer-send', id: 'sendBtn' }, bar, '↑');
  e('p', { class: 'composer-hint', id: 'composerHint' }, wrap, 'Enter 보내기 · Shift+Enter 줄바꿈 · AI 답변은 아직 연결 전이에요');
  const aside = e('aside', { class: 'side', id: 'sidePanel' }, app);
  e('button', { class: 'side-close', id: 'sideClose' }, aside);
  e('ol', { class: 'staff-list', id: 'staffList' }, aside);
  e('span', { class: 'pcard-count', id: 'staffCount' }, aside, '0/7');
  e('p', { class: 'pcard-note', id: 'staffNote' }, aside, '문자를 보내면 직원 7명이 차례로 확인한 곳이 여기에 표시돼요.');
  e('span', { class: 'pcard-count', id: 'fileCount' }, aside, '0개');
  e('div', { class: 'drop', id: 'dropZone' }, aside);
  e('input', { id: 'fileInput', type: 'file' }, aside);
  e('button', { class: 'add-btn', id: 'addFileBtn' }, aside, '＋ 파일 추가');
  e('ul', { class: 'file-list', id: 'fileList' }, aside);
  e('button', { class: 'side-open', id: 'sideOpen' }, app);
  e('div', { class: 'side-scrim', id: 'sideScrim' }, app);
  win.matchMedia = q => ({ matches: /reduce/.test(q), addEventListener() {} });
  win.fetch = fetchFn;
  for (const k of ['addEventListener', 'removeEventListener']) win[k] = win[k].bind(win);
  vm.createContext(win);
  vm.runInContext(INLINE, win, { filename: 'business.html(inline)' });
  for (const f of SCRIPTS) vm.runInContext(read(f), win, { filename: f });
  return d;
}
function liveFetch(state) {
  const inner = server(state);
  const f = (url, init) => url === '/api/v1/auth/me' ? Promise.resolve({ status: 200, ok: true, headers: { get: () => null }, text: () => Promise.resolve(JSON.stringify({ username: 'fixture', csrf_token: 'fixture' })), json: () => Promise.resolve({ username: 'fixture', csrf_token: 'fixture' }) }) : inner(url, init);
  f.calls = inner.calls;
  return f;
}
const hintOf = d => d.doc.getElementById('composerHint').textContent;

test('화면: 주소 값이 없거나 잘못되면 꺼짐(안내 줄 그대로), ?demo_ai_fallback=5 면 안내 줄에 켜짐 표시', async () => {
  for (const [q, on] of [['?mode=api', ''], ['?mode=api&demo_ai_fallback=abc', ''], ['?mode=api&demo_ai_fallback=0', ''], ['?mode=api&demo_ai_fallback=5', '5'], ['?mode=api&demo_ai_fallback=30', '10']]) {
    const d = screen(q, liveFetch({}));
    await wait(10);
    const h = hintOf(d);
    if (on) assert.ok(h.includes('시연 AI 대체 ' + on + '초 켜짐(준비된 시연 응답)'), q + ' → ' + h);
    else assert.ok(!h.includes('시연 AI 대체'), q + ' → ' + h);
  }
});

test('화면(실제 시간 약 5초): 3초 지연 → AI 구역에 준비 응답 표시, 실제 결과 도착 → 교체 말풍선과 교체 표시', async () => {
  const st = {};
  const d = screen('?mode=api&demo_ai_fallback=3', liveFetch(st));
  await wait(10);
  const SAMPLE = vm.runInContext('window.SAMPLE_DATA.find(x => x.id === "unregistered").input.text', d.win);
  const i = d.doc.getElementById('chatInput'); i.value = SAMPLE;
  d.doc._dispatch(i, new Ev('keydown', { key: 'Enter' }));
  await wait(3300);
  let all = d.doc.getElementById('chatThread').textContent;
  assert.match(all, /준비된 시연 응답 · 실제 AI 결과 아님/);
  assert.match(all, /준비된 시연 응답 · 위험 신호/);
  assert.ok(!/AI 칸 교체/.test(all));
  st.done = true; st.report = REAL_HIGH;
  await wait(2300);
  all = d.doc.getElementById('chatThread').textContent;
  assert.match(all, /AI 칸 교체/);
  assert.match(all, /이 준비된 시연 응답은 아래 서버 분석 결과로 교체됐어요/);
  const zones = d.doc.querySelectorAll('#chatThread .op-ai');
  assert.equal(zones.length, 2);
  assert.match(zones[1].textContent, /규칙·AI 위험 분석 · 서버 보고서/);
  assert.ok(!/준비된 시연 응답 · 위험 신호/.test(zones[1].textContent));
});
