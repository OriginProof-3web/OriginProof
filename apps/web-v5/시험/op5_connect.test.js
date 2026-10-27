// 5안 화면 연결 시험: business.html 안쪽 스크립트 + 연결 스크립트를 작은 가짜 DOM(시험/_dom.js)에서 돌림.
//   node --test 시험/op5_connect.test.js
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');
const { makeDom, snapshot, Ev } = require('./_dom.js');
const { fakeFetch } = require('./가져온/regression/_load.js');

const WEB = path.resolve(__dirname, '../페이지');
const read = f => fs.readFileSync(path.join(WEB, f), 'utf8');
const HTML = read('business.html');
const SCRIPTS = [...HTML.matchAll(/<script src="((?:data|js)\/[^"]+)"><\/script>/g)].map(m => m[1]);
const INLINE = (() => { const i = HTML.indexOf('function selectAction'); return HTML.slice(HTML.lastIndexOf('<script>', i) + 8, HTML.indexOf('</script>', i)); })();
const ALLOWED = ['대기', '확인 중', '확인됨', '연결 전', '문제 찾음'];
const sleep = ms => new Promise(r => setTimeout(r, ms));

function build(search, fetchFn) {
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
  win.fetch = fetchFn || fakeFetch(() => assert.fail('첫 화면에서 서버를 부름'));
  for (const k of ['addEventListener', 'removeEventListener']) win[k] = win[k].bind(win);
  vm.createContext(win);
  vm.runInContext(INLINE, win, { filename: 'business.html(inline)' });
  return d;
}
function load(d) { for (const f of SCRIPTS) vm.runInContext(read(f), d.win, { filename: f }); }
const texts = (d, sel) => d.doc.querySelectorAll(sel).map(n => n.textContent);
const enter = (d, text) => { const i = d.doc.getElementById('chatInput'); i.value = text; return d.doc._dispatch(i, new Ev('keydown', { key: 'Enter' })); };

test('첫 화면 그대로: 연결 스크립트를 불러와도 DOM·문구 변화 0, 서버 호출 0', () => {
  const d = build('');
  const before = snapshot(d.doc.documentElement);
  d.arm(); load(d); d.disarm();
  assert.equal(d.mutations(), 0);
  assert.equal(snapshot(d.doc.documentElement), before);
  assert.equal(d.win.fetch.calls.length, 0);
  assert.equal(d.doc.getElementById('composerHint').textContent, 'Enter 보내기 · Shift+Enter 줄바꿈 · AI 답변은 아직 연결 전이에요');
  assert.equal(texts(d, '#staffList li.staff .st').join(','), '대기,대기,대기,대기,대기,대기,대기');
});

test('예시 모드: Enter → 사용자 말풍선 + AI 말풍선(블록체인 결정 / AI 설명), 안쪽 "연결 전" 답은 안 나옴, 칩은 기존 상태만', async () => {
  const d = build('');
  load(d);
  const s = vm.runInContext('Hk.sampleAdapter.get("tamper").input.text', d.win);
  enter(d, s);
  await sleep(30);
  const ai = d.doc.querySelectorAll('#chatThread .msg-ai .bubble');
  assert.equal(d.doc.querySelectorAll('#chatThread .msg-user').length, 1);
  assert.equal(ai.length, 1);
  assert.match(ai[0].textContent, /블록체인 결정/);
  assert.match(ai[0].textContent, /AI 설명/);
  assert.ok(!/받은 내용을 받았어요/.test(d.doc.getElementById('chatThread').textContent));
  assert.equal(texts(d, '#chatThread .tag-offline')[0], '예시 모드');
  const chips = texts(d, '#staffList li.staff .st');
  chips.forEach(c => assert.ok(ALLOWED.includes(c), c));
  assert.ok(chips.includes('문제 찾음'), '변조 예시인데 문제 찾음이 없음: ' + chips);
  assert.equal(d.doc.getElementById('chatInput').value, '');
});

test('실서버 모드: /api 같은 출처로 보내고, 로그인 없으면 분석은 연결 전(지어내지 않음)', async () => {
  const f = fakeFetch(url => url === '/api/v1/auth/me' ? { status: 401, body: { detail: 'AUTH_REQUIRED' } } : { status: 404, body: { detail: 'NOT_FOUND' } });
  const d = build('?mode=api', f);
  load(d);
  enter(d, '[OO카드] 결제 안내입니다.');
  await sleep(40);
  assert.equal(f.calls.filter(c => c.url === '/api/v3/inputs').length, 0, '로그인 없이 쓰기를 보냄');
  const bubble = texts(d, '#chatThread .msg-ai .bubble').join('\n');
  assert.match(bubble, /분석은 로그인이 필요해요/);
  assert.equal(texts(d, '#chatThread .tag-offline')[0], '실서버 모드');
  texts(d, '#staffList li.staff .st').forEach(c => assert.ok(ALLOWED.includes(c), c));
});

test('같은 글을 연달아 보내면 진행 중인 것은 다시 보내지 않음', async () => {
  let n = 0;
  const f = fakeFetch(url => { if (url === '/api/v1/auth/me') return { status: 200, body: { csrf_token: 'fixture' } }; if (url === '/api/v3/inputs') { n++; return { status: 201, body: { input_ref: 'inp_x', expires_at: 1 }, delay: 30 }; } return { status: 409, body: { detail: 'INPUT_SUPPORT_UNDECIDED' } }; });
  const d = build('?mode=api', f);
  load(d);
  enter(d, '같은 안내문'); enter(d, '같은 안내문');
  await sleep(80);
  assert.equal(n, 1);
  assert.match(d.doc.getElementById('chatThread').textContent, /같은 내용을 이미 확인하고 있어요/);
});

test('왼쪽 메뉴(selectAction 이벤트) → 말풍선, 도움말은 알림창 대신 말풍선, 검색칸 Enter', async () => {
  const d = build('');
  load(d);
  let reached = 0;
  d.doc.getElementById('sidebar-root')._l.push({ type: 'click', fn: () => reached++, cap: false });
  vm.runInContext('selectAction("status")', d.win);
  vm.runInContext('selectAction("issue")', d.win);
  d.doc.querySelectorAll('#sidebar-root button')[0].click();
  const box = d.doc.querySelector('#sidebar-root input');
  box.value = 'ana_fixture';
  d.doc._dispatch(box, new Ev('keydown', { key: 'Enter' }));
  await sleep(20);
  const all = d.doc.getElementById('chatThread').textContent;
  assert.match(all, /연결 설정/);
  assert.match(all, /새 Proof 발행\(기관 지갑\)/);
  assert.match(all, /도움말/);
  assert.match(all, /발행 기록 검색: ana_fixture/);
  assert.equal(reached, 0, '도움말 클릭이 번들(알림창)까지 감');
  assert.ok(d.doc.querySelectorAll('#chatThread .add-btn').length > 0);
});

test('장면 재현은 ?demo= 일 때만: wallet 장면은 503 WALLET_REGISTRY_UNAVAILABLE 에서 멈춤, retention 장면은 지우기 뒤 목록', async () => {
  const d = build('?demo=wallet', null);
  load(d);
  await sleep(60);
  const t = d.doc.getElementById('chatThread').textContent;
  assert.match(t, /WALLET_REGISTRY_UNAVAILABLE/);
  assert.match(t, /장면 재현 · 가짜 응답/);
  const r = build('?demo=retention', null);
  load(r);
  await sleep(60);
  const rt = r.doc.getElementById('chatThread').textContent;
  assert.match(rt, /ana_scene_keep2 를 지웠어요/);
  for (const n of ['example', 'api']) { const x = build('?demo=' + n, null); load(x); await sleep(80); assert.ok(x.doc.querySelectorAll('#chatThread .msg-ai').length > 0, n); }
});

/* ---------------- 정적 확인 ---------------- */
const sha = s => crypto.createHash('sha256').update(s).digest('hex');
test('business.html 은 스크립트 연결 줄만 더함, 사이드바·번들·CSS 는 그대로', () => {
  const start = HTML.indexOf('<!-- 5안 기술 연결(2026-10-26)');
  const end = HTML.indexOf('</body>');
  assert.ok(start > 0);
  const added = HTML.slice(start, end).trim().split('\n').slice(1);
  added.forEach(l => assert.match(l, /^<script src="(data|js)\/[a-z0-9_]+\.js"><\/script>$/, l));
  // 더한 부분을 뺀 내용 = 작업 전 business.html (sha256, 작업 시작 때 잰 값)
  assert.equal(sha(HTML.slice(0, start) + HTML.slice(end)), '84fe9af8264568ed51b308cb1baf2b6dfebd1f56c6a329c4ddb6ae6d1a739c7b');
  assert.equal(sha(fs.readFileSync(path.join(WEB, 'business.bundle.js'))), '0a329cb58e6430f910fcd6b2b2a6ae2509ea5bf66ad16342d83194199e97bc45');
  assert.equal(sha(fs.readFileSync(path.join(WEB, 'sidebar.bundle.js'))), '74222a3ab62779066b0bbb159fd41c674b9fd21c03d10f614e35b8eb160161eb');
  assert.equal(sha(fs.readFileSync(path.join(WEB, 'business-workspace.css'))), '4c105ee44ae27b0966e02ba9216878ad77180488dd4d58a2e1824211bd50afb1');
});

test('연결 스크립트는 기존 CSS 클래스만 쓰고, 인라인 스타일·innerHTML 없음', () => {
  const style = HTML.slice(HTML.indexOf('<style>'), HTML.indexOf('</style>'));
  for (const f of ['js/op5_connect.js', 'js/op5_client.js', 'js/op5_scenes.js', 'js/op5_staff.js']) {
    const src = read(f);
    assert.ok(!/\.style\.|innerHTML|insertAdjacentHTML|document\.write/.test(src), f);
    if (f !== 'js/op5_connect.js') continue;
    const cls = new Set();
    for (const m of src.matchAll(/el\('[a-z0-9]+', '([^']+)'/g)) m[1].split(' ').forEach(c => cls.add(c));
    for (const m of src.matchAll(/(?:wait|run|ok|off|bad): '(st[^']*)'/g)) m[1].split(' ').forEach(c => cls.add(c));
    assert.ok(cls.size >= 6);
    for (const c of cls) assert.ok(new RegExp('\\.' + c + '(?![\\w-])').test(style), '없는 클래스: ' + c);
  }
});
