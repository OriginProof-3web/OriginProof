// node --test tools/connection.test.js   (설치 없음, node 기본 모듈만)
// 설정의 모드·서버 주소·연결 확인(T2·T3·T5), 자유 입력 참조(T1), 지난 기록 스냅샷(T4).
// localStorage·fetch 는 가짜(tools/_load.js). 화면(DOM) 동작은 본부 실측 요청(docs/기능_연결_설명.md).
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { loadWeb, fixture, fakeFetch, memStorage, PII, noRaw, WEB } = require('./_load.js');

const KEY = 'jjin.settings.v1';
const HKEY = 'jjin.history.v1';
const j = x => JSON.parse(JSON.stringify(x));

function setup(route, storage) {
  const Hk = loadWeb();
  const ls = storage || memStorage();
  const f = fakeFetch(route || (() => null));
  const store = Hk.createSettingsStore(ls);
  const conn = Hk.createConnection({ store, fetch: f, viaProxy: false });
  return { Hk, ls, f, store, conn };
}

/* ------------------------------ T2 ------------------------------ */
test('T2 서버 주소를 바꾸면 ApiAdapter 요청 주소가 바뀜', async () => {
  const v1 = fixture('v1_verify_tampered.response.json');
  const { conn, f } = setup(() => ({ status: 200, body: v1 }));
  conn.setMode('api');
  const input = JSON.stringify({ proof_id: 'prf_demo_001', amount_minor: 1 });
  await conn.check(input);
  assert.equal(f.calls[0].url, 'http://127.0.0.1:8000/v1/mvp/card-notices/verify');
  assert.equal(conn.setServerUrl('http://localhost:9123/').ok, true);
  assert.equal(conn.adapter().serverUrl, 'http://localhost:9123');
  await conn.check(input);
  assert.equal(f.calls[1].url, 'http://localhost:9123/v1/mvp/card-notices/verify');
  // 틀린 주소·이 컴퓨터 밖 주소는 저장하지 않고 이전 주소 유지
  const bad = conn.setServerUrl('javascript:alert(1)');
  assert.equal(bad.ok, false);
  assert.match(bad.message, /형식이 맞지 않아요/);
  const far = conn.setServerUrl('http://example.com:8000');
  assert.equal(far.ok, false);
  assert.match(far.message, /이 컴퓨터 주소/);
  assert.equal(conn.serverUrl(), 'http://localhost:9123');
  await conn.check(input);
  assert.equal(f.calls[2].url, 'http://localhost:9123/v1/mvp/card-notices/verify');
});

test('T2 연결 확인: {주소}/health/ready 호출, 준비됨·실패·시간 초과·CORS·꺼짐이 각각 다른 안내', async () => {
  const cases = {
    ready: () => ({ status: 200, body: { status: 'ready' } }),
    not_ready: () => ({ status: 503, body: { detail: 'RUNTIME_NOT_READY' } }),
    ready_failed: () => ({ status: 500, raw: 'Internal Server Error' }),
    slow: () => ({ hang: true }),
    cors: (url, init) => (init.mode === 'no-cors' ? { status: 0, raw: '' } : { reject: 'Failed to fetch' }),
    down: () => ({ reject: 'Failed to fetch' })
  };
  const msgs = {};
  for (const [want, route] of Object.entries(cases)) {
    const Hk = loadWeb();
    const f = fakeFetch(route);
    const store = Hk.createSettingsStore(memStorage());
    store.get().serverUrl = 'http://127.0.0.1:8123';
    const r = await Hk.checkConnection({ fetch: f, serverUrl: store.get().serverUrl, healthTimeoutMs: 40 });
    assert.equal(r.kind, want, want);
    assert.equal(f.calls[0].url, 'http://127.0.0.1:8123/health/ready', want + ' 주소');
    assert.equal(r.ok, want === 'ready');
    msgs[want] = r.message;
  }
  assert.equal(new Set(Object.values(msgs)).size, Object.keys(msgs).length, '안내 문구가 겹침');
  assert.match(msgs.slow, /제한 시간/);
  assert.match(msgs.cors, /브라우저가 답을 읽지 못하게 막았어요/);
  assert.match(msgs.down, /연결하지 못했어요/);
  // 연결 객체 경유(설정 주소 사용)
  const { conn, f } = setup(() => ({ status: 200, body: { status: 'ready' } }));
  conn.setServerUrl('http://localhost:7001');
  const r = await conn.testConnection();
  assert.equal(r.ok, true);
  assert.equal(f.calls[0].url, 'http://localhost:7001/health/ready');
});

/* ------------------------------ T5 ------------------------------ */
test('T5 서버 주소 저장·복원: 재진입 때 입력창 값과 ApiAdapter 주소가 같음, 저장값 없으면 기본값', () => {
  const ls = memStorage();
  const a = setup(null, ls);
  assert.equal(a.conn.serverUrl(), 'http://127.0.0.1:8000');                 // 저장값 없음 → 기본값
  a.conn.setServerUrl('http://localhost:8800');
  assert.equal(JSON.parse(ls.mem[KEY]).serverUrl, 'http://localhost:8800');
  const b = setup(null, ls);                                                   // 재진입
  b.conn.setMode('api');
  assert.equal(b.conn.serverUrl(), 'http://localhost:8800');                  // app.js 가 입력창에 넣는 값
  assert.equal(b.conn.adapter().serverUrl, 'http://localhost:8800');          // ApiAdapter 주소
  // 저장값이 깨졌으면 기본값
  const c = setup(null, Object.assign(memStorage(), { getItem: () => '{깨진' }));
  assert.equal(c.conn.serverUrl(), 'http://127.0.0.1:8000');
  // 저장소가 막혀도 오류 없이 기본값
  const d = setup(null, { getItem() { throw new Error('SecurityError'); }, setItem() { throw new Error('Quota'); } });
  assert.equal(d.conn.serverUrl(), 'http://127.0.0.1:8000');
  assert.equal(d.conn.setServerUrl('http://localhost:1').ok, true);
});

test('T5 설정 6가지(글자·움직임·테마·발표·패널·서버 주소) 저장소 왕복', () => {
  const ls = memStorage();
  const a = setup(null, ls);
  Object.assign(a.store.get(), { large: true, reduce: true, theme: 'dark', present: true, panel: 'strip' });
  a.store.save();
  a.conn.setServerUrl('http://127.0.0.1:9000');
  const b = setup(null, ls);
  assert.deepEqual(j(b.store.get()), { large: true, reduce: true, theme: 'dark', present: true, panel: 'strip', serverUrl: 'http://127.0.0.1:9000', mode: 'sample' });
});

/* ------------------------------ T3 ------------------------------ */
test('T3 스위치가 실제면 check 대상이 ApiAdapter, 예시면 SampleAdapter', async () => {
  const { conn, Hk, f } = setup(() => ({ status: 401, body: { detail: 'AUTH_REQUIRED' } }));
  assert.equal(conn.adapter(), Hk.sampleAdapter);
  await conn.check('아무 문자');
  assert.equal(f.calls.length, 0, '예시 모드에서 서버를 부름');
  conn.setMode('api');
  assert.equal(conn.adapter().mode, 'api');
  assert.notEqual(conn.adapter(), Hk.sampleAdapter);
  const ans = await conn.check('아무 문자');
  assert.ok(f.calls.length > 0);
  assert.equal(ans.sample, false);
  assert.equal(ans.label, '실제 서버 응답');
});

test('T3 재진입 때 마지막 모드 복원', () => {
  const ls = memStorage();
  setup(null, ls).conn.setMode('api');
  assert.equal(setup(null, ls).conn.mode(), 'api');
  setup(null, ls).conn.setMode('sample');
  assert.equal(setup(null, ls).conn.mode(), 'sample');
  assert.equal(setup(null, ls).conn.setMode('evil'), 'sample');
});

test('T3 실제 연결 실패(꺼짐·시간 초과·500)여도 모드는 실제 유지, 사유 표시, 예시 자동 전환 0건', async () => {
  const routes = [() => ({ reject: 'Failed to fetch' }), () => ({ hang: true }), () => ({ status: 500, raw: 'x' })];
  let switched = 0;
  for (const route of routes) {
    const ls = memStorage();
    const Hk = loadWeb();
    const f = fakeFetch(route);
    const store = Hk.createSettingsStore(ls);
    const conn = Hk.createConnection({ store, fetch: f, createApi: o => Hk.createApiAdapter(Object.assign({ timeoutMs: 30 }, o)), checkConnection: o => Hk.checkConnection(Object.assign({ healthTimeoutMs: 30 }, o)) });
    conn.setMode('api');
    const ans = await conn.check(JSON.stringify({ proof_id: 'prf_demo_001', amount_minor: 1 }));
    const r = await conn.testConnection().catch(() => null);
    if (conn.mode() !== 'api' || JSON.parse(ls.mem[KEY]).mode !== 'api') switched++;
    if (ans.sample !== false || Hk.sampleAdapter.list().indexOf(ans) >= 0) switched++;
    assert.equal(ans.conclusion.badge.text, '판단 보류');
    assert.ok(/서버/.test(ans.conclusion.text), '사유 없음: ' + ans.conclusion.text);
    assert.ok(r && r.ok === false && r.message);
  }
  assert.equal(switched, 0);
  // 5안: web-2안 app.js 정적 확인 2줄은 뺌(5안 화면 연결은 시험/op5_connect.test.js 에서 확인)
});

/* ------------------------------ T1 ------------------------------ */
test('T1 참조 2개 이상: 첫 참조만 쓰고 나머지는 자세히에만, 요청에 두 번째 참조 없음', async () => {
  const { conn, f } = setup(url => url.endsWith('/v3/inputs') ? { status: 401, body: { detail: 'AUTH_REQUIRED' } } : null);
  conn.setMode('api');
  const first = 'https://verify.example/p/prf_1b2c3d4e5f60718293a4b5c6d7e8f901';
  const second = 'prf_a0ef1f66db9845ebb3ee2fe81c729136';
  const third = 'https://other.example/x';
  const ans = await conn.check('안내 ' + first + ' 그리고 ' + second + ' 또 ' + third + ' 연락 ' + PII.mobile);
  assert.equal(ans.ref.value, first);
  const labels = ans.details.map(d => d.label);
  assert.ok(labels.includes('확인에 쓸 링크'));
  assert.ok(ans.details.some(d => /^더 찾은 Proof ID 1/.test(d.label) && d.value === second));
  assert.ok(ans.details.some(d => /^더 찾은 링크 2/.test(d.label) && d.value === third));
  // 검증은 첫 참조(링크 안 Proof ID)로 정확히 1회. 두 번째 이후 참조는 검증 요청에 없음(자세한 시험: tools/t1_free_input.test.js)
  const vc = f.calls.filter(c => /verif/.test(c.url));
  assert.equal(vc.length, 1);
  assert.equal(JSON.parse(vc[0].body).proof_id, 'prf_1b2c3d4e5f60718293a4b5c6d7e8f901');
  assert.ok(!vc[0].body.includes(second) && !vc[0].body.includes(third));
  // 서버로 간 것은 가린 원문(AI 접수)뿐이고, 그 안의 참조 순서도 원문 그대로. 요청 주소에는 참조 없음
  for (const c of f.calls) { assert.ok(!c.url.includes(second) && !c.url.includes('prf_1b2c')); noRaw(assert, c.body, '요청'); }
  noRaw(assert, JSON.stringify(ans), '답');
});

test('T1 참조 없음: "공식 기록으로 확인할 수 없는 문자예요" + AI 분석만(요청은 /v3/inputs 하나부터)', async () => {
  const job = fixture('v3_analysis_job_analyzer_unavailable.reconstructed.json');
  const { conn, f } = setup((url, init) => {
    if (url.endsWith('/v3/inputs')) return { status: 201, body: { input_ref: 'inp_a', expires_at: 1 } };
    if (url.endsWith('/v3/analyses') && init.method === 'POST') return { status: 202, body: job };
    return null;
  });
  conn.setMode('api');
  const ans = await conn.check('엄마 나 폰 고장났어 ' + PII.mobile + ' 로 ' + PII.account + ' 에 보내줘 ' + PII.rrn);
  assert.equal(ans.conclusion.text, '공식 기록으로 확인할 수 없는 문자예요.');
  assert.deepEqual(j(ans.axes.slice(0, 3).map(x => x.status)), ['확인할 수 없음', '확인할 수 없음', '확인할 수 없음']);
  assert.deepEqual(f.calls.map(c => c.url.replace('http://127.0.0.1:8000', '')), ['/v3/inputs', '/v3/analyses']);
  assert.ok(ans.details.some(d => d.label === '찾은 검증 링크·Proof ID' && d.value === '없음'));
  // 개인정보 가림 유지: 서버로 보낸 글·답·기록 스냅샷 모두
  const sent = JSON.parse(f.calls[0].body).text;
  assert.match(sent, /\(전화번호 가림\)/);
  assert.match(sent, /\(계좌번호 가림\)/);
  assert.match(sent, /\(주민번호 가림\)/);
  for (const c of f.calls) noRaw(assert, c.body, '요청');
  noRaw(assert, JSON.stringify(ans), '답');
});

/* ------------------------------ T4 ------------------------------ */
function entry(Hk, i, answer) {
  return { id: 'h' + i, date: '2026-10-19', title: '기록 ' + i, tone: 'pending', icon: 'question', label: '판단 보류', text: answer.input.text, sampleId: '', snapshot: answer };
}

test('T4 가린 결과 스냅샷 최근 20개, 21번째 저장 때 가장 오래된 것이 빠짐, 저장 데이터에 원문 개인정보 0건', async () => {
  const { Hk, conn, ls } = setup(url => url.endsWith('/v3/inputs') ? { status: 401, body: { detail: 'AUTH_REQUIRED' } } : null);
  const T = Hk.text;
  conn.setMode('api');
  let list = [];
  for (let i = 1; i <= 21; i++) {
    const ans = await conn.check('기록 ' + i + ' 연락 ' + PII.mobile + ' 계좌 ' + PII.account + ' ' + PII.rrn);
    list = T.addHistory(list, entry(Hk, i, ans));
    T.storageSet(ls, HKEY, JSON.stringify(list));                      // app.js saveHistory 와 같은 저장
    if (i === 20) assert.equal(T.parseHistory(ls.mem[HKEY]).length, 20);
  }
  const saved = T.parseHistory(ls.mem[HKEY]);
  assert.equal(saved.length, 20);
  assert.equal(saved[0].id, 'h21');
  assert.equal(saved[19].id, 'h2');
  assert.ok(!saved.some(h => h.id === 'h1'), '가장 오래된 기록이 남음');
  assert.ok(saved.every(h => h.snapshot && h.snapshot.axes.length === 4 && h.snapshot.staff.length === 7));
  noRaw(assert, ls.mem[HKEY], '저장 데이터');
  // 누가 저장소에 원문을 넣어 두어도 읽을 때 다시 가림
  const bad = JSON.parse(ls.mem[HKEY]);
  bad[0].snapshot.input.text = '원문 ' + PII.mobile;
  bad[0].snapshot.details.push({ label: 'x', value: PII.account });
  noRaw(assert, JSON.stringify(T.parseHistory(JSON.stringify(bad))), '다시 읽은 기록');
});

test('T4 기록 다시 보기 중 fetch 0회(스냅샷·예시·옛 기록 모두), 모드가 실제여도', async () => {
  const v1 = fixture('v1_verify_tampered.response.json');
  const { Hk, conn, f } = setup(() => ({ status: 200, body: v1 }));
  conn.setMode('api');
  const ans = await conn.check(JSON.stringify({ proof_id: 'prf_demo_001', amount_minor: 1 }));
  const before = f.calls.length;
  const T = Hk.text;
  const saved = T.parseHistory(JSON.stringify(T.addHistory([], entry(Hk, 1, ans))))[0];
  const back = await conn.restore(saved);
  assert.equal(back.verification_status, 'TAMPERED');
  assert.equal(back.conclusion.text, ans.conclusion.text);
  assert.deepEqual(j(back.staff.map(s => s.staff)), j(ans.staff.map(s => s.staff)));     // 도착 순서 그대로
  assert.equal(JSON.stringify(back.axes[1].compare), JSON.stringify(ans.axes[1].compare));
  await conn.restore({ sampleId: 'tamper' });
  await conn.restore({ text: '옛 기록 글 https://verify.example/p/prf_1b2c3d4e5f60718293a4b5c6d7e8f901' });
  assert.equal(f.calls.length, before, '기록 다시 보기 중 서버를 부름');
  // 5안: web-2안 app.js 기록 열기 정적 확인은 뺌(5안에는 그 화면이 없음)
});

test('T4 개별 삭제·전체 삭제 뒤 저장소 상태', () => {
  const { Hk, ls } = setup();
  const T = Hk.text;
  let list = [];
  for (let i = 1; i <= 3; i++) list = T.addHistory(list, { id: 'h' + i, date: '2026-10-19', title: 't' + i, text: '글 ' + i });
  T.storageSet(ls, HKEY, JSON.stringify(list));
  list = T.removeHistory(T.parseHistory(ls.mem[HKEY]), 'h2');            // app.js deleteHistory
  T.storageSet(ls, HKEY, JSON.stringify(list));
  assert.deepEqual(j(T.parseHistory(ls.mem[HKEY]).map(h => h.id)), ['h3', 'h1']);
  T.storageSet(ls, HKEY, JSON.stringify([]));                             // app.js clearHistory
  assert.equal(ls.mem[HKEY], '[]');
  assert.deepEqual(j(T.parseHistory(ls.mem[HKEY])), []);
  // 5안: web-2안 app.js 저장 정적 확인은 뺌(5안에는 그 화면이 없음)
});
