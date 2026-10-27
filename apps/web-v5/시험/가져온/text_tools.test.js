// node --test web-prototype/tools/text_tools.test.js  (설치 없음, node 기본 모듈만)
// js/text_tools.js 순수 함수 + adapter.js 자유 입력 흐름 시험.
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const ROOT = path.resolve(__dirname, '../../페이지');   // 5안 위치
const T = require(path.join(ROOT, 'js', 'text_tools.js'));

// 시험용 개인정보 예시(모두 지어낸 값)
const PII = {
  mobile: '010-1234-5678',
  mobilePlain: '01098765432',
  mobileIntl: '+82 10-2222-3333',
  seoul: '02-123-4567',
  local: '031-987-6543',
  account: '110-123-456789',
  account2: '1002-345-678901',
  accountPlain: '3333012345678',
  card: '1234 5678 9012 3456',
  rrn: '900101-1234567',
  rrnPlain: '8505052345678'
};
const RAW_VALUES = Object.values(PII);
const SAMPLE_TEXT = '[OO은행] 김OO님 연락처 ' + PII.mobile + ', 주민번호 ' + PII.rrn +
  ', 입금 계좌 ' + PII.account + ' 로 보내세요. 문의 ' + PII.seoul + ' 확인: https://verify.example/p/prf_1b2c3d4e5f60718293a4b5c6d7e8f901';

function noRaw(s, where) {
  for (const v of RAW_VALUES) assert.ok(!String(s).includes(v), where + ' 에 원문 개인정보가 남음: ' + v);
}

test('개인정보 가림: 전화번호·계좌번호·주민번호 형태를 모두 가림', () => {
  for (const [k, v] of Object.entries(PII)) {
    const out = T.maskPersonal('번호 ' + v + ' 입니다');
    assert.ok(!out.includes(v), k + ' 가 남음: ' + out);
    assert.match(out, /\((전화번호|계좌번호|주민번호) 가림\)/, k);
  }
  assert.equal(T.maskPersonal(PII.mobile), T.MASK.phone);
  assert.equal(T.maskPersonal(PII.account), T.MASK.account);
  assert.equal(T.maskPersonal(PII.rrn), T.MASK.rrn);
});

test('개인정보 가림: 날짜·금액·대표번호·Proof ID·링크는 그대로', () => {
  const keep = [
    '2026-10-19', '85,000원', '42,300원', '1588-1234', '10월 결제',
    'prf_1b2c3d4e5f60718293a4b5c6d7e8f901', 'prf_a0ef1f66db9845ebb3ee2fe81c729136',
    'https://verify.example/p/prf_4d5e6f708192a3b4c5d6e7f8091a2b3c', 'http://oo-card-check.example/a1'
  ];
  for (const k of keep) assert.equal(T.maskPersonal('값 ' + k + ' 끝'), '값 ' + k + ' 끝', k);
  assert.equal(T.maskPersonal(''), '');
  assert.equal(T.maskPersonal(null), '');
});

test('개인정보 가림: 예시 문자 계좌번호도 가림, 같은 글을 두 번 가려도 같음', () => {
  const s = '[OO카드] 납부 계좌: OO은행 123-456-789012 (예금주 OO카드). 검증 링크: https://verify.example/p/prf_1b2c3d4e5f60718293a4b5c6d7e8f901';
  const once = T.maskPersonal(s);
  assert.ok(!once.includes('123-456-789012'));
  assert.ok(once.includes('prf_1b2c3d4e5f60718293a4b5c6d7e8f901'));
  assert.equal(T.maskPersonal(once), once);
  const all = T.maskPersonal(SAMPLE_TEXT);
  noRaw(all, '가린 글');
  assert.equal(T.hasPersonal(all), false);
});

test('링크·Proof ID 찾기: 나온 차례, 링크 안 Proof ID 는 하나로, 끝 문장부호 뗌', () => {
  const t = '먼저 prf_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa 그리고 https://verify.example/p/prf_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb. 또 (https://x.example/q?a=1)';
  const refs = T.findRefs(t);
  assert.equal(refs.length, 3);
  assert.deepEqual(refs.map(r => r.type), ['proof', 'link', 'link']);
  assert.equal(refs[0].value, 'prf_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa');
  assert.equal(refs[1].value, 'https://verify.example/p/prf_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb');
  assert.equal(refs[1].proofId, 'prf_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb');
  assert.equal(refs[2].value, 'https://x.example/q?a=1');
  assert.deepEqual(T.findRefs('링크 없는 문자예요. 010-1234-5678'), []);
  assert.deepEqual(T.findRefs('javascript:alert(1) ftp://x.example'), []);
  // Proof ID 형식은 OriginProof 스키마 ^prf_[A-Za-z0-9_-]+$ (models.py:124) → prf_123·prf_demo_001 도 인식
  assert.deepEqual(T.findRefs('ftp://x.example prf_123').map(r => r.value), ['prf_123']);
  assert.deepEqual(T.findRefs('번호 prf_demo_001 입니다').map(r => r.value), ['prf_demo_001']);
  assert.equal(T.findRefs('같은 https://a.example 두 번 https://a.example').length, 1);
});

test('지난 기록: 21번째를 넣으면 가장 오래된 것이 빠짐(최대 20개)', () => {
  let list = [];
  for (let i = 1; i <= 21; i++) list = T.addHistory(list, { id: 'h' + i, date: '2026-10-19', title: '기록 ' + i, tone: 'none', icon: 'dash', label: '확인할 수 없음', text: '문자 ' + i });
  assert.equal(list.length, 20);
  assert.equal(list[0].id, 'h21');
  assert.equal(list[19].id, 'h2');
  assert.ok(!list.some(h => h.id === 'h1'), '가장 오래된 h1 이 남음');
  list = T.removeHistory(list, 'h10');
  assert.equal(list.length, 19);
  assert.ok(!list.some(h => h.id === 'h10'));
});

test('지난 기록: 저장되는 글에 원문 개인정보가 없음(넣을 때·읽을 때 모두 가림)', () => {
  const list = T.addHistory([], { id: 'x1', date: '2026-10-19', title: '연락처 ' + PII.mobile, tone: 'fail', icon: 'warn', label: '연결 전', text: SAMPLE_TEXT });
  const stored = JSON.stringify(list);
  noRaw(stored, '저장 글');
  // 누가 저장소에 원문을 직접 넣어 두어도 읽을 때 다시 가림
  const tampered = JSON.stringify([{ id: 'y', date: '2026-10-19', title: 't', tone: 'evil', icon: '<img>', label: 'l', text: SAMPLE_TEXT }]);
  const read = T.parseHistory(tampered);
  noRaw(JSON.stringify(read), '읽은 기록');
  assert.equal(read[0].tone, 'none');
  assert.equal(read[0].icon, 'dash');
  assert.equal(T.parseHistory('{깨진'), null);
  assert.equal(T.parseHistory(null), null);
  assert.equal(T.parseHistory('{"a":1}'), null);
  assert.equal(T.parseHistory(JSON.stringify(new Array(30).fill({ sampleId: 'normal' }))).length, 20);
});

test('설정: 기본값·서버 주소 자리·잘못된 값 버림', () => {
  const d = T.parseSettings(null);
  assert.deepEqual(d, { large: false, reduce: null, theme: null, present: false, panel: null, serverUrl: 'http://127.0.0.1:8000', mode: 'sample' });
  const s = T.normalizeSettings({ large: true, reduce: false, theme: 'dark', present: true, panel: 'strip', serverUrl: 'https://Api.Example:443/', mode: 'api' });
  assert.deepEqual(s, { large: true, reduce: false, theme: 'dark', present: true, panel: 'strip', serverUrl: 'https://api.example:443', mode: 'api' });
  assert.equal(T.normalizeSettings({ mode: 'evil' }).mode, 'sample');
  assert.equal(T.normalizeSettings({ large: 'yes', theme: 'blue', panel: 1, serverUrl: 'javascript:alert(1)' }).serverUrl, 'http://127.0.0.1:8000');
  assert.equal(T.normalizeSettings({ large: 'yes' }).large, false);
  assert.equal(T.normalizeServerUrl('http://user:pw@host'), '');
  assert.equal(T.normalizeServerUrl('http://127.0.0.1:99999'), '');
  assert.equal(T.normalizeServerUrl('http://localhost:8000/v3?x=1'), '');
  assert.equal(T.normalizeServerUrl(' http://localhost:8000 '), 'http://localhost:8000');
});

test('설정 저장·복원: 가짜 저장소로 왕복, 저장소가 막혀도 오류 없음', () => {
  const mem = {};
  const store = { getItem: k => (k in mem ? mem[k] : null), setItem: (k, v) => { mem[k] = String(v); } };
  const want = T.normalizeSettings({ large: true, theme: 'light', present: true, panel: 'strip' });
  assert.equal(T.storageSet(store, T.KEYS.settings, JSON.stringify(want)), true);
  assert.deepEqual(T.parseSettings(T.storageGet(store, T.KEYS.settings)), want);
  const broken = { getItem() { throw new Error('SecurityError'); }, setItem() { throw new Error('QuotaExceeded'); } };
  assert.equal(T.storageGet(broken, 'k'), null);
  assert.equal(T.storageSet(broken, 'k', 'v'), false);
  assert.equal(T.storageGet(null, 'k'), null);
  assert.deepEqual(T.parseSettings(T.storageGet(broken, T.KEYS.settings)), T.normalizeSettings(null));
});

/* ---------- adapter.js 자유 입력 흐름(브라우저 없이 vm 으로) ---------- */
function loadApp() {
  const sandbox = { console };
  sandbox.window = sandbox;
  sandbox.self = sandbox;
  vm.createContext(sandbox);
  for (const f of ['data/sample_data.js', 'js/text_tools.js', 'js/op5_staff.js', 'js/adapter.js']) {
    vm.runInContext(fs.readFileSync(path.join(ROOT, f), 'utf8'), sandbox, { filename: f });
  }
  return sandbox.Hk;
}
const CODE_RE = /\b[A-Z][A-Z0-9_]{2,}\b/;
const BANNED = ['안' + '전', '사' + '기'];
function visibleTexts(a) {
  const out = [a.conclusion.text, a.conclusion.badge.text, a.next_action.text, a.input.text];
  a.axes.forEach(ax => out.push(ax.name, ax.status, ax.body, ax.note || ''));
  a.staff.forEach(st => out.push(st.line1, st.line3 || '', st.shape));
  return out;
}

test('자유 입력: 링크·Proof ID 없음 → 공식 기록으로 확인할 수 없는 문자, 공식 세 칸 확인 불가, AI 칸만 남음', async () => {
  const Hk = loadApp();
  const a = await Hk.adapter.check('엄마 나 폰 고장났어 이 번호로 문자 줘 ' + PII.mobile + ' 급해 ' + PII.account + ' 로 보내줘');
  assert.equal(a.id, 'no_reference');
  assert.equal(a.conclusion.text, '공식 기록으로 확인할 수 없는 문자예요.');
  assert.equal(JSON.stringify(a.axes.filter(x => x.axis !== 'ai').map(x => x.status)), JSON.stringify(['확인할 수 없음', '확인할 수 없음', '확인할 수 없음']));
  assert.equal(a.axes.find(x => x.axis === 'ai').tone, 'offline');
  assert.equal(a.staff.length, 7);
  noRaw(JSON.stringify(a), '답 전체');
  noRaw(T.buildCopyText(a), '복사 글');
  for (const t of visibleTexts(a)) {
    assert.ok(!CODE_RE.test(t), '화면 글에 영문 코드: ' + t);
    for (const w of BANNED) assert.ok(!t.includes(w), '금지 단어: ' + t);
  }
  assert.ok(!a.axes.some(x => x.axis === 'ai' && x.tone === 'ok'));
});

test('자유 입력: 여러 개면 첫 번째를 쓰고 나머지는 자세히에', async () => {
  const Hk = loadApp();
  const text = '안내 https://verify.example/p/prf_1b2c3d4e5f60718293a4b5c6d7e8f901 와 prf_a0ef1f66db9845ebb3ee2fe81c729136 , 상담 ' + PII.mobile;
  const a = await Hk.adapter.check(text);
  assert.equal(a.id, 'not_connected');
  assert.equal(a.ref.type, 'link');
  assert.equal(a.ref.proofId, 'prf_1b2c3d4e5f60718293a4b5c6d7e8f901');
  const labels = a.details.map(d => d.label);
  assert.ok(labels.includes('확인에 쓸 링크'));
  assert.ok(labels.some(l => l.startsWith('더 찾은 Proof ID 1')));
  assert.ok(a.details.some(d => d.value === 'prf_a0ef1f66db9845ebb3ee2fe81c729136'));
  noRaw(JSON.stringify(a), '답 전체');
  for (const t of visibleTexts(a)) assert.ok(!CODE_RE.test(t), '화면 글에 영문 코드: ' + t);
});

test('자유 입력: 예시 문자와 같으면 예시 답, 입력 상한 하나로 통일(2000, maxlength 는 그 2배)', async () => {
  const Hk = loadApp();
  const s = Hk.adapter.list()[0];
  assert.equal(await Hk.adapter.check(s.input.text), s);
  assert.equal(Hk.MAX_INPUT, 2000);
  assert.equal(Hk.MAX_PASTE, 4000);
  assert.equal(Hk.validateInput('가'.repeat(2000)).ok, true);
  assert.equal(Hk.validateInput('가'.repeat(2001)).ok, false);
  assert.equal(Hk.validateInput('   ').ok, false);
  assert.equal(Hk.validateInput(42).ok, false);
  const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
  assert.ok(!/maxlength=/.test(html), 'index.html 에 숫자 maxlength 가 다시 생김');
});

test('결과 복사 글: 예시 5개 모두 원문·AI 인용·개인정보 없음, 결론·네 칸·다음 행동은 있음', () => {
  const Hk = loadApp();
  for (const s of Hk.adapter.list()) {
    const c = T.buildCopyText(s);
    assert.ok(c.includes(s.conclusion.text));
    assert.ok(c.includes(s.next_action.text));
    s.axes.forEach(ax => assert.ok(c.includes(ax.name + ': ' + ax.status)));
    assert.ok(!c.includes(s.input.text), s.id + ': 원문이 들어감');
    const ai = s.axes.find(x => x.axis === 'ai');
    const quote = (ai.body.match(/"([^"]+)"/) || [])[1];
    if (quote) assert.ok(!c.includes(quote), s.id + ': AI 인용이 들어감');
    assert.equal(T.hasPersonal(c), false, s.id);
  }
});

test('화면 말풍선·기록이 가림 함수를 거침(app.js 연결 확인)', {skip:'5안 미사용: web-2안 화면 전용 파일(app.js·index.html·staff.js) 정적 확인'}, () => {
  const app = fs.readFileSync(path.join(ROOT, 'js', 'app.js'), 'utf8');
  assert.match(app, /b\.textContent = T\.maskPersonal\(text\)/);
  assert.match(app, /var masked = T\.maskPersonal\(answer\.input\.text\)/);
  assert.match(app, /T\.buildCopyText\(answer\)/);
  assert.ok(!/localStorage\.(get|set)Item/.test(app), 'app.js 가 localStorage 를 try/catch 없이 직접 씀');
});
