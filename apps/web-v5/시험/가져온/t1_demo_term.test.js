// 감사 T1 재작업 시험: 엔진 NOT_REGISTERED ↔ 시연 표기 UNVERIFIED 대응(js/api_adapter.js DEMO_TERM).
// node 기본 모듈만(설치 없음), 브라우저를 띄우지 않음.
//   node --test web-prototype/tools/t1_demo_term.test.js
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { loadWeb, fixture, fakeFetch, CODE_RE, visibleTexts } = require('./regression/_load.js');

const ROOT = path.resolve(__dirname, '../../페이지');   // 5안 위치
const read = f => fs.readFileSync(path.join(ROOT, f), 'utf8');
const j = x => JSON.parse(JSON.stringify(x));
const ENGINE = ['VERIFIED', 'NOT_REGISTERED', 'TAMPERED', 'INCONCLUSIVE', 'ERROR'];   // 웹_설계.md 1.8

test('대응표: NOT_REGISTERED 하나만 UNVERIFIED 로 잇고, 엔진 값에는 UNVERIFIED 가 없다', () => {
  const Hk = loadWeb();
  assert.deepEqual(j(Hk.DEMO_TERM), { NOT_REGISTERED: 'UNVERIFIED' });
  assert.ok(!ENGINE.includes('UNVERIFIED'));
  const rows = j(Hk.demoTermRows('NOT_REGISTERED'));
  assert.deepEqual(rows, [{ label: '시연 표기', value: 'UNVERIFIED (검증 엔진 값 NOT_REGISTERED와 같은 뜻)' }]);
  for (const vs of ENGINE.filter(v => v !== 'NOT_REGISTERED')) assert.deepEqual(j(Hk.demoTermRows(vs)), [], vs);
  // 이상한 입력 검증: 값 없음·다른 형식·이미 시연 표기인 값·객체 기본 속성 이름은 행을 만들지 않음
  for (const vs of [null, undefined, '', 42, {}, 'UNVERIFIED', 'not_registered', '__proto__', 'toString', 'constructor']) {
    assert.deepEqual(j(Hk.demoTermRows(vs)), [], String(vs));
  }
});

test('대응표는 api_adapter.js 한 곳에만 있고 다른 화면 소스에 UNVERIFIED 를 직접 쓰지 않는다', () => {
  assert.equal((read('js/api_adapter.js').match(/var DEMO_TERM = /g) || []).length, 1);
  for (const d of ['js']) {   // 5안: 페이지/css 폴더 없음, 가져온 js 만
    for (const f of fs.readdirSync(path.join(ROOT, d))) {
      if (f === 'api_adapter.js') continue;
      assert.ok(!read(d + '/' + f).includes('UNVERIFIED'), d + '/' + f + ' 에 UNVERIFIED 직접 사용');
    }
  }
  assert.ok(!read('business.html').includes('UNVERIFIED'));   // 5안 화면
});

test('프리셋 ③: 엔진 값 NOT_REGISTERED 유지, 대응표로 UNVERIFIED, 바로 보이는 글은 한국어 그대로', () => {
  const Hk = loadWeb();
  const un = Hk.sampleAdapter.get('unregistered');
  assert.ok(un, '프리셋 ③ 없음');
  assert.equal(un.verification_status, 'NOT_REGISTERED');
  assert.ok(un.details.some(d => d.label === 'reason_codes' && d.value === 'ISSUER_NOT_FOUND'));
  assert.equal(Hk.demoTermRows(un.verification_status)[0].value.split(' ')[0], 'UNVERIFIED');
  assert.equal(un.conclusion.badge.text, '기록 없음');
  for (const t of visibleTexts(un)) {
    assert.ok(!t.includes('UNVERIFIED'), '바로 보이는 글에 UNVERIFIED: ' + t);
    assert.ok(!CODE_RE.test(t), '바로 보이는 글에 영문 코드: ' + t);
  }
  // 예시 8개 중 엔진 값으로 UNVERIFIED 를 쓰는 것은 없음
  assert.ok(!Hk.sampleAdapter.list().some(s => s.verification_status === 'UNVERIFIED'));
});

test('화면: 시연 표기 행은 자세히(extra)로만 들어가고, 자세히 칸을 그리기 전에 넣는다', {skip:'5안 미사용: web-2안 화면 전용 파일(app.js·index.html·staff.js) 정적 확인'}, () => {
  const app = read('js/app.js');
  const push = app.indexOf('Hk.demoTermRows(a.verification_status).forEach(function (d) { extra.push(d); });');
  const decl = app.indexOf('var extra = [];');
  const det = app.indexOf("var det = el('details', 'more');");
  const draw = app.indexOf('extra.forEach(function (d) { row(d.label, d.value); });');
  assert.ok(decl >= 0 && push > decl && det > push && draw > det, '순서: extra 선언 → 시연 표기 push → details → extra 그리기');
  assert.equal(app.split('demoTermRows').length - 1, 2, 'app.js 에서 demoTermRows 는 확인 1번·호출 1번만');
});

test('실서버 경로(v1 가짜 응답): NOT_REGISTERED 를 그대로 두고 대응표로 UNVERIFIED', async () => {
  const Hk = loadWeb();
  const input = fixture('v1_card_notice_amount_tampered.input.json');
  const resp = fixture('v1_verify_tampered.response.json');
  resp.verification_status = 'NOT_REGISTERED';
  resp.reason_codes = ['ISSUER_NOT_FOUND'];
  const f = fakeFetch(url => url.endsWith('/v1/mvp/card-notices/verify') ? { status: 200, body: resp } : null);
  const a = Hk.createApiAdapter({ fetch: f, serverUrl: 'http://127.0.0.1:8000', pollMs: 1, timeoutMs: 200 });
  const ans = await a.check(JSON.stringify(input));
  assert.equal(ans.verification_status, 'NOT_REGISTERED');
  assert.equal(ans.conclusion.badge.text, '기록 없음');
  assert.ok(ans.details.some(d => d.label === '검증 엔진 결과' && d.value.startsWith('NOT_REGISTERED')));
  assert.deepEqual(j(Hk.demoTermRows(ans.verification_status)).map(r => r.value.split(' ')[0]), ['UNVERIFIED']);
  for (const t of visibleTexts(ans)) assert.ok(!t.includes('UNVERIFIED'), '바로 보이는 글에 UNVERIFIED: ' + t);
});
