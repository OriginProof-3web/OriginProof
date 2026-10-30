// AI 칸 연결 준비 시험(T2): 계약 AnalysisJob/AnalysisReport 예시(시험/fixtures/ai_analysis_examples.json, '예시 — 실서버 응답 아님')를
// 화면 값으로 옮긴 결과와 형광펜 범위를 출력해 확인. 설치 없음(node 내장 node:test).
//   node --test 시험/ai_analysis.test.js        (출력을 보려면: node --test --test-reporter=spec 시험/ai_analysis.test.js)
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { loadWeb, fakeFetch, CODE_RE } = require('./가져온/regression/_load.js');
const { makeDom, Ev } = require('./_dom.js');

const EX = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'ai_analysis_examples.json'), 'utf8'));
const CONTRACT = path.join(__dirname, '..', '..', 'api', 'src', 'originproof_api', 'wallet_analyses.py');   // 저장소 안 계약 원본(읽기만)
const URL0 = 'http://127.0.0.1:8000';
const log = (...a) => console.log('  [출력]', ...a);
const j = x => JSON.parse(JSON.stringify(x));   // vm 안 배열을 이 쪽 배열로(deepEqual 용)

function run(Hk, job, text) {
  const f = fakeFetch((url, init) => {
    if (url.endsWith('/v3/inputs')) return { status: 201, body: { input_ref: 'inp_ex', expires_at: 1 } };
    if (url.endsWith('/v3/analyses') && init.method === 'POST') return { status: 202, body: job };
    if (url.includes('/v3/analyses/')) return { status: 200, body: job };
    return null;
  });
  return Hk.createApiAdapter({ fetch: f, serverUrl: URL0, pollMs: 1, timeoutMs: 200 }).check(text);
}

test('예시 표시: 파일에 "예시 — 실서버 응답 아님", 등급 4종 + 실패 코드 3종', () => {
  assert.match(EX._example, /^예시 — 실서버 응답 아님/);
  const levels = Object.values(EX.jobs).filter(j => j.report).map(j => j.report.risk_level).sort();
  assert.deepEqual(levels, ['CAUTION', 'HIGH', 'NO_CLEAR_INDICATORS', 'UNDETERMINED']);
  const codes = Object.values(EX.jobs).filter(j => j.status === 'FAILED').map(j => j.error_code);
  assert.ok(codes.length >= 2 && codes.includes('ANALYZER_UNAVAILABLE') && codes.includes('ANALYSIS_TIMEOUT'));
  log('등급', levels.join(', '), '/ 실패 코드', codes.join(', '));
});

test('매핑: 예시 작업 7개 → AI 칸(상태·본문)·AI 직원 말풍선, 화면 글에 영문 코드 없음', async () => {
  const Hk = loadWeb();
  const text = EX.text;
  assert.equal(Hk.text.maskPersonal(text), text, '예시 글이 개인정보 가림으로 바뀌면 위치 기준이 달라짐');
  const want = {
    HIGH: ['위험 신호', 'fail', 'ai.high'], CAUTION: ['주의', 'caution', 'ai.caution'],
    NO_CLEAR_INDICATORS: ['뚜렷한 신호 없음', 'info', 'ai.no_clear'], UNDETERMINED: ['판단하기 어려움', 'pending', 'ai.undetermined'],
    FAILED_ANALYZER_UNAVAILABLE: ['AI 분석 연결 전', 'offline', 'common.not_connected'],
    FAILED_ANALYSIS_TIMEOUT: ['보류', 'pending', 'ai.timeout'], FAILED_GROUNDING_MISMATCH: ['보류', 'pending', 'ai.failed']
  };
  for (const [k, job] of Object.entries(EX.jobs)) {
    const a = await run(Hk, job, text);
    const ax = a.axes.find(x => x.axis === 'ai'), st = a.staff.find(s => s.staff === 'ai');
    log(k.padEnd(28), '| 칸:', ax.status, '|', ax.body, '| 말풍선:', st.line1, '/', st.line2);
    assert.equal(ax.status, want[k][0], k); assert.equal(ax.tone, want[k][1], k); assert.equal(st.bubble_key, want[k][2], k);
    for (const t of [ax.status, ax.body, ax.note, st.line1]) assert.ok(!CODE_RE.test(t), k + ' 화면 글에 영문 코드: ' + t);
    if (job.report) assert.equal(a.ai_report.evidence.length, job.report.evidence.length, k + ' 근거 개수');
    else assert.equal(a.ai_report, null);
  }
});

test('실패 코드 전부(계약 process·finish·cleanup) → 말풍선 키·쉬운 말 있음, 모르는 코드는 코드 그대로 보류', async () => {
  const Hk = loadWeb();
  const codes = Object.keys(Hk.api.AI_FAIL);
  for (const c of codes) {
    const m = Hk.api.mapAnalysisJob({ analysis_id: 'ana_x', status: 'FAILED', error_code: c, report: null });
    log(c.padEnd(30), '→', m.obs.bubble_key.padEnd(24), m.obs.line1, '·', m.why || '(보류 기본 문장만)');
    assert.equal(m.obs.line2, c);
  }
  const u = Hk.api.mapAnalysisJob({ status: 'FAILED', error_code: 'NEW_CODE_X', report: null });
  assert.equal(u.obs.bubble_key, 'common.held_error'); assert.equal(u.obs.line2, 'NEW_CODE_X');
  for (const [s, k] of [['EXPIRED', 'ai.result_expired'], ['CANCELLED', 'ai.cancelled']]) assert.equal(Hk.api.mapAnalysisJob({ status: s }).obs.bubble_key, k);
});

test('계약 원본과 대조: wallet_analyses.py 의 오류 코드 문자열이 화면 표에 모두 있음(빠진 것 0)', () => {
  const Hk = loadWeb();
  const src = fs.readFileSync(CONTRACT, 'utf8');
  const all = new Set([...src.matchAll(/"([A-Z][A-Z_]{3,})"/g)].map(m => m[1]));
  const NOT_CODES = new Set(['QUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED', 'EXPIRED', 'TEXT', 'LEGACY']);       // 상태·입력 종류
  const ELSEWHERE = { INPUT_SUPPORT_UNDECIDED: 'fromErr → AI 분석 연결 전', INPUT_EXPIRED: 'errorInfo 410 + AI_FAIL', ORIGINAL_UNAVAILABLE: 'op5_client CODE_TEXT(원본 받기)', NO_DOCUMENT_REFERENCE: 'verification_not_run_reason(자세히)', WORKER_STORAGE_UNAVAILABLE: '응답 코드 아님(app.state)', MAINTENANCE_STORAGE_UNAVAILABLE: '응답 코드 아님(app.state)' };
  const missing = [];
  for (const c of all) {
    if (NOT_CODES.has(c)) continue;
    const where = Hk.api.AI_FAIL[c] ? 'AI_FAIL' : Hk.api.AI_HTTP[c] ? 'AI_HTTP' : ELSEWHERE[c];
    if (!where) missing.push(c);
    log(c.padEnd(32), where || '빠짐');
  }
  assert.deepEqual(missing, []);
});

test('형광펜 위치: 코드포인트 → UTF-16(이모지 앞), 잘린 글이 quote 와 같음', () => {
  const Hk = loadWeb();
  const r = Hk.api.evidenceSpans(EX.text, EX.jobs.HIGH.report.evidence);
  r.spans.forEach(s => log('근거', s.index + 1, s.source, s.rule_id, '코드포인트', EX.jobs.HIGH.report.evidence[s.index].start_offset + '~' + EX.jobs.HIGH.report.evidence[s.index].end_offset, '→ UTF-16', s.start + '~' + s.end, JSON.stringify(EX.text.slice(s.start, s.end))));
  assert.equal(r.skipped.length, 0);
  assert.deepEqual(j(r.spans.map(s => [s.start, s.end])), [[30, 41], [43, 59]]);
  r.spans.forEach(s => assert.equal(EX.text.slice(s.start, s.end), EX.jobs.HIGH.report.evidence[s.index].quote));
  const c = Hk.api.evidenceSpans(EX.text, EX.jobs.CAUTION.report.evidence);
  assert.deepEqual(j(c.spans.map(s => [s.start, s.end])), [[10, 18]]);
  // 위치 없는 근거(서버 grounding 전 모양): 글 안에 한 번만 있으면 찾고, 여러 번이면 안 칠함
  const n = Hk.api.evidenceSpans('가나 가나', [{ quote: '가나' }, { quote: '나 가' }]);
  assert.deepEqual(j(n.skipped.map(s => s.reason)), ['QUOTE_NOT_UNIQUE']); assert.deepEqual(j(n.spans.map(s => [s.start, s.end])), [[1, 4]]);
});

test('형광펜 방어: 범위 밖·역순·quote 불일치·UTF-16 위치로 잘못 보냄·한쪽만·겹침·빈 quote → 안 칠함, 오류 안 던짐', () => {
  const Hk = loadWeb();
  const ev = EX.jobs.HIGH.report.evidence.concat(EX.bad_evidence);
  const r = Hk.api.evidenceSpans(EX.text, ev);
  r.skipped.forEach(s => log('안 칠함', ev[s.index].rule_id.padEnd(14), s.reason.padEnd(16), Hk.api.SPAN_WHY[s.reason]));
  assert.deepEqual(j(r.skipped.map(s => [ev[s.index].rule_id, s.reason])), [
    ['X_OUT', 'OUT_OF_RANGE'], ['X_REV', 'REVERSED'], ['X_MISMATCH', 'QUOTE_MISMATCH'], ['X_UTF16', 'QUOTE_MISMATCH'],
    ['X_HALF', 'BAD_RANGE'], ['X_OVERLAP', 'OVERLAP'], ['X_NOQUOTE', 'NO_QUOTE']]);
  assert.equal(r.spans.length, 2);
  for (const junk of [null, undefined, 'x', 3, [null, 5, 'a', { quote: 7 }, { quote: 'a', start_offset: 1.5, end_offset: 2 }]]) assert.doesNotThrow(() => Hk.api.evidenceSpans(EX.text, junk));
  assert.deepEqual(j(Hk.api.evidenceSpans(null, ev).spans), []);
});

test('예시 모드 회귀: data/sample_data.js 의 근거 위치가 모두 맞아 예전처럼 칠해짐', () => {
  const Hk = loadWeb();
  let n = 0;
  for (const s of Hk.sampleAdapter.list()) {
    const ev = s.ai_report && s.ai_report.evidence;
    if (!Array.isArray(ev) || !ev.length) continue;
    const r = Hk.api.evidenceSpans(s.input.text, ev);
    assert.deepEqual(j(r.skipped), [], s.id + ' 근거 위치 틀림'); n += r.spans.length;
  }
  log('예시 자료 근거', n, '건 위치 일치');
  assert.ok(n > 0);
});

/* ---------- 화면(가짜 DOM): business.html 안쪽 스크립트 + 연결 스크립트 ---------- */
const WEB = path.resolve(__dirname, '../페이지');
const HTML = fs.readFileSync(path.join(WEB, 'business.html'), 'utf8');
const SCRIPTS = [...HTML.matchAll(/<script src="((?:data|js)\/[^"]+)"><\/script>/g)].map(m => m[1]);
const INLINE = (() => { const i = HTML.indexOf('function selectAction'); return HTML.slice(HTML.lastIndexOf('<script>', i) + 8, HTML.indexOf('</script>', i)); })();
function page(job) {
  const d = makeDom('?mode=api');
  const { win, doc, El } = d;
  const e = (tag, attrs, parent) => { const n = new El(tag, doc); Object.entries(attrs || {}).forEach(([k, v]) => (k === 'class' ? (n.className = v) : n.setAttribute(k, v))); if (parent) parent.append(n); return n; };
  const app = e('div', { class: 'app', id: 'app' }, doc.body);
  e('div', { id: 'sidebar-root' }, app);
  const main = e('main', {}, app);
  e('button', { id: 'themeBtn' }, main);
  const sc = e('section', { id: 'chatScroll' }, main);
  e('div', { id: 'chatEmpty' }, e('div', { id: 'chatThread' }, sc));
  const form = e('form', { id: 'composer' }, main);
  e('textarea', { id: 'chatInput' }, form); e('button', { id: 'attachBtn' }, form); e('span', { id: 'attachNote' }, form); e('button', { id: 'sendBtn' }, form);
  e('p', { id: 'composerHint' }, main);
  const aside = e('aside', { id: 'sidePanel' }, app);
  ['sideClose', 'addFileBtn', 'sideOpen'].forEach(id => e('button', { id }, aside));
  e('ol', { id: 'staffList' }, aside); e('span', { id: 'staffCount' }, aside); e('p', { id: 'staffNote' }, aside); e('span', { id: 'fileCount' }, aside);
  e('div', { id: 'dropZone' }, aside); e('input', { id: 'fileInput' }, aside); e('ul', { id: 'fileList' }, aside); e('div', { id: 'sideScrim' }, app);
  win.matchMedia = q => ({ matches: /reduce/.test(q), addEventListener() {} });
  win.fetch = fakeFetch((url, init) => {
    if (url === '/api/v1/auth/me') return { status: 200, body: { csrf_token: 'fixture' } };
    if (url === '/api/v3/inputs') return { status: 201, body: { input_ref: 'inp_ex', expires_at: 1 } };
    if (url === '/api/v3/analyses' && init.method === 'POST') return { status: 202, body: job };
    return { status: 404, body: { detail: 'Not Found' } };
  });
  for (const k of ['addEventListener', 'removeEventListener']) win[k] = win[k].bind(win);
  vm.createContext(win);
  vm.runInContext(INLINE, win);
  for (const f of SCRIPTS) vm.runInContext(fs.readFileSync(path.join(WEB, f), 'utf8'), win, { filename: f });
  return d;
}
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function render(job, text) {
  const d = page(job);
  const i = d.doc.getElementById('chatInput'); i.value = text;
  d.doc._dispatch(i, new Ev('keydown', { key: 'Enter' }));
  await sleep(60);
  const zone = d.doc.querySelectorAll('section.op-ai').pop();
  assert.ok(zone, 'AI 위험 설명 칸이 그려지지 않음');
  return zone;
}

test('화면: HIGH 예시 → 형광펜 2곳(글자 일치), 근거 줄에 규칙 검사/AI 모델 칩 구분, 규칙 번호', async () => {
  const zone = await render(EX.jobs.HIGH, EX.text);
  const marks = zone.querySelectorAll('mark');
  log('형광펜', marks.map(m => JSON.stringify(m.textContent) + ' title=' + m.getAttribute('title')).join(' | '));
  assert.deepEqual(marks.map(m => m.textContent), ['인증번호를 입력하세요', '원격 지원 앱을 설치해 주세요']);
  const rows = zone.querySelectorAll('.op-row').map(r => r.textContent);
  rows.forEach(r => log('줄', r));
  const chips = zone.querySelectorAll('.op-row .op-chip').map(c => c.className + ' ' + c.textContent);
  assert.ok(chips.includes('op-chip t-info 규칙 검사') && chips.includes('op-chip t-none AI 모델'), chips.join(' / '));
  assert.ok(rows.some(r => r.includes('규칙 번호 R_OTP_REQUEST')) && rows.some(r => r.includes('규칙 번호 L_REMOTE_APP')));
});

test('화면: ANALYZER_UNAVAILABLE → AI 칸 "AI 분석 연결 전", 형광펜 없음', async () => {
  const zone = await render(EX.jobs.FAILED_ANALYZER_UNAVAILABLE, EX.text);
  log('AI 칸', zone.textContent.slice(0, 140));
  assert.match(zone.textContent, /AI 분석 연결 전/);
  assert.equal(zone.querySelectorAll('mark').length, 0);
});

// 감사 재작업 T1(1회차): 머리표가 현재 제공 기능으로 오인되지 않는지(연결 전 표기, 결과 값 없음, class·인라인 스타일 그대로)
test('화면: ANALYZER_UNAVAILABLE → 머리표 "연결 전", AI 칸에 위험 등급·근거 결과 값 없음', async () => {
  const zone = await render(EX.jobs.FAILED_ANALYZER_UNAVAILABLE, EX.text);
  const tag = zone.querySelector('span.op-zone-tag');
  log('머리표', JSON.stringify(tag.textContent), '| class=' + tag.className, '| style 키', Object.keys(tag.style).length, '| style 속성', tag.getAttribute('style'));
  log('AI 칸 전체', zone.textContent);
  assert.equal(tag.className, 'op-zone-tag');                      // class 그대로
  assert.equal(Object.keys(tag.style).length, 0); assert.equal(tag.getAttribute('style'), null);   // 인라인 스타일 없음(변경 전과 같음)
  assert.match(tag.textContent, /연결 전/);
  assert.doesNotMatch(tag.textContent, /Hybrid|Analyzer/);           // 옛 '작동 중' 인상 문구 없음
  assert.match(zone.textContent, /AI 분석 연결 전/);
  // 결과 값 없음: 위험 등급 4종 화면 글·영문 등급 코드, 근거 줄·규칙 번호·출처 칩, 형광펜, 수법 ID
  for (const w of ['위험 신호', '주의', '뚜렷한 신호 없음', '판단하기 어려움', 'HIGH', 'CAUTION', 'NO_CLEAR_INDICATORS', 'UNDETERMINED',
    '근거 1', '규칙 번호', '규칙 검사', 'AI 모델', '일치한 공개 피싱 수법', '위험 요구 문장을 칠했어요']) {
    assert.ok(!zone.textContent.includes(w), '결과 값처럼 보이는 글: ' + w);
  }
  assert.equal(zone.querySelectorAll('mark').length, 0);
  assert.equal(zone.querySelectorAll('.op-row').filter(r => /^근거/.test(r.textContent)).length, 0);
});

test('화면: 위치가 틀린 근거가 섞여도 깨지지 않고 맞는 곳만 칠함, 못 칠한 사유를 근거 줄에 표시', async () => {
  const job = JSON.parse(JSON.stringify(EX.jobs.HIGH));
  job.report.evidence = job.report.evidence.concat(EX.bad_evidence);
  const zone = await render(job, EX.text);
  assert.equal(zone.querySelectorAll('mark').length, 2);
  const rows = zone.querySelectorAll('.op-row').map(r => r.textContent);
  assert.ok(rows.some(r => /X_REV.*위치 앞뒤가 바뀜/.test(r)) && rows.some(r => /X_OUT.*위치가 글 길이를 넘음/.test(r)));
  log('모양 틀린 근거(빈 quote) 안내', zone.querySelectorAll('.op-tech').map(p => p.textContent).filter(t => /모양이 틀린/.test(t)).join(''));
});
