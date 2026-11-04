'use strict';
// 5안 새 기능: Track B 원본 찾기(/v3/document-lookups), 문서 사진 입력(DOCUMENT_IMAGE)
const test = require('node:test'); const assert = require('node:assert');
const fs = require('node:fs'); const path = require('node:path'); const vm = require('node:vm');
const { fakeFetch } = require('./가져온/regression/_load.js');
const WEB = path.join(__dirname, '..', '페이지');
const FILES = ['data/sample_data.js', 'js/text_tools.js', 'js/op5_staff.js', 'js/adapter.js', 'js/chain_check.js', 'js/api_adapter.js', 'js/session.js', 'js/connection.js', 'js/op5_client.js'];
const ME = { account_id: 'a', username: 'u', role: 'recipient', issuer_id: null, csrf_token: 'c' };
function load() { const sb = { console, setTimeout, clearTimeout, AbortController, AbortSignal, TextEncoder, URL, crypto: globalThis.crypto, Promise }; sb.window = sb; sb.self = sb; vm.createContext(sb); for (const f of FILES) vm.runInContext(fs.readFileSync(path.join(WEB, f), 'utf8'), sb, { filename: f }); return sb.Hk; }
function api(Hk, f) { const client = Hk.op5.createClient({ fetch: f, base: '/api', timeoutMs: 500 }); return Hk.createApiAdapter({ fetch: f, base: '/api', csrf: client.csrf, isDeleted: client.isDeleted, retain: () => ({}), timeoutMs: 500, pollMs: 5, pollLimitMs: 500 }); }
const MSG = '[Origin Mock Bank] 카드대금 1,250,000원을 입금계좌 110-123-456789 로 보내주세요';

test('Track B 키: 기관·금액·계좌 / 공문 번호, 못 읽으면 null', () => {
  const k = load().api.lookupKey;
  assert.deepEqual(JSON.parse(JSON.stringify(k(MSG))), { issuer_id: '0x9d6e623a821f35508c0c970540013aa75041537806d71a2e318ac7ca5358a217', key: { notice_type: 'PAYMENT_REQUEST', amount_minor: 1250000, currency: 'KRW', payee_account_number: '110123456789' } });
  assert.equal(k('Origin Mock Office 공문 번호: OMO-17').key.document_number, 'OMO-17');
  assert.equal(k('안녕하세요 1000원 계좌 1234567'), null);
  assert.equal(k('Origin Mock Bank Origin Mock Office 1000원 계좌 1234567'), null);
});

test('Track B MATCHED → 검증 결과 그대로, UNVERIFIED → 가짜라 하지 않고 확인할 수 없음', async () => {
  const Hk = load();
  const V = { session_id: 'vs_1', verification_status: 'INCONCLUSIVE', reason_codes: ['PARTIAL_COMPARISON'] };
  for (const [st, body] of [['MATCHED', { lookup_status: 'MATCHED', match_count: 1, document_ids: ['0x' + 'ab'.repeat(32)], reason_codes: [], verification: V }], ['UNVERIFIED', { lookup_status: 'UNVERIFIED', match_count: 0, document_ids: [], reason_codes: [] }]]) {
    const f = fakeFetch((url) => url === '/api/v3/document-lookups' ? { status: 200, body } : url === '/api/v1/auth/me' ? { status: 200, body: ME } : { status: 409, body: { detail: 'INPUT_SUPPORT_UNDECIDED' } });
    const a = await api(Hk, f).check(MSG, {});
    const sent = f.calls.find(c => c.url === '/api/v3/document-lookups');
    assert.ok(sent && /^req_/.test(JSON.parse(sent.body).request_id));
    if (st === 'MATCHED') assert.equal(a.verification_status, 'INCONCLUSIVE');
    else { assert.equal(a.verification_status, null); assert.match(a.conclusion.text, /가짜 의심/); }
  }
});

test('코드 없는 일반 문자는 원본 찾기를 보내지 않음, 경로 404 면 기존처럼', async () => {
  const Hk = load();
  const f = fakeFetch(() => ({ status: 404, body: { detail: 'Not Found' } }));
  await api(Hk, f).check('그냥 안부 문자예요', {});
  assert.equal(f.calls.filter(c => c.url === '/api/v3/document-lookups').length, 0);
});

test('문서 사진: /v3/inputs 에 DOCUMENT_IMAGE, 글은 보내지 않음, 검증·원본 찾기 없음', async () => {
  const Hk = load();
  const f = fakeFetch((url) => url === '/api/v1/auth/me' ? { status: 200, body: ME } : url === '/api/v3/inputs' ? { status: 409, body: { detail: 'INPUT_SUPPORT_UNDECIDED' } } : null);
  const a = await api(Hk, f).check('[문서 사진] a.png', { image: { media_type: 'image/png', base64: 'iVBORw0KGgo=' } });
  const inp = f.calls.filter(c => c.url === '/api/v3/inputs').map(c => JSON.parse(c.body));
  // 사진 접수가 거절되면(409) 글자 읽기도 AI 분석도 없음: 사진은 한 번만 보냄
  assert.deepEqual(inp, [{ kind: 'DOCUMENT_IMAGE', image_media_type: 'image/png', image_base64: 'iVBORw0KGgo=' }]);
  assert.equal(f.calls.filter(c => /verifications|document-lookups|card-notices/.test(c.url)).length, 0);
  assert.equal(a.details.find(d => d.label === '입력 종류').value, '문서 사진');
  // 사진만으로는 원본 대조를 안 하므로 가짜 의심이라 하지 않음(진짜 안내문 사진을 가짜로 몰지 않게)
  assert.equal(a.conclusion.badge.text, '확인 못 함');
  assert.doesNotMatch(a.conclusion.text, /가짜 의심/);
});

test('문서 사진: 서버가 글자를 읽어 주면 그 글로 원본 찾기·AI(TEXT) 확인, 사진은 한 번만 접수', async () => {
  const Hk = load();
  const READ = '[Web발신]\n[오리진 목 은행] 카드 대금 85,000원 청구 안내입니다. 납부 계좌 001-234-500003 으로 11/10까지 입금 바랍니다.';
  let n = 0;
  const f = fakeFetch((url, init) => {
    if (url === '/api/v1/auth/me') return { status: 200, body: ME };
    if (url === '/api/v3/inputs') return { status: 201, body: { input_ref: 'inp_' + (++n), expires_at: 1 } };
    if (url === '/api/v3/inputs/inp_1/text') return { status: 200, body: { text: READ, complete: true } };
    if (url === '/api/v3/document-lookups') return { status: 200, body: { lookup_status: 'UNVERIFIED', match_count: 0, document_ids: [], reason_codes: ['NO_MATCHING_RETAINED_RECORD'] } };
    return { status: 409, body: { detail: 'INPUT_SUPPORT_UNDECIDED' } };
  });
  const a = await api(Hk, f).check('[문서 사진] a.png', { image: { media_type: 'image/png', base64: 'iVBORw0KGgo=' } });
  const inp = f.calls.filter(c => c.url === '/api/v3/inputs').map(c => JSON.parse(c.body).kind);
  assert.deepEqual(inp, ['DOCUMENT_IMAGE', 'TEXT'], '사진 1번(글자 읽기용) + 읽은 글 1번(AI)');
  const look = f.calls.find(c => c.url === '/api/v3/document-lookups');
  assert.ok(look, '읽은 글로 원본 찾기');
  assert.deepEqual(JSON.parse(look.body).key, { notice_type: 'PAYMENT_REQUEST', amount_minor: 85000, currency: 'KRW', payee_account_number: '001234500003' });
  assert.equal(a.from_image, true);
  assert.match(a.details[0].value, /사진 글자를 읽어/);
  assert.notEqual(a.conclusion.badge.text, '확인 못 함');
});

test('문서 사진: 사진 읽기가 기관 이름을 비슷하게 잘못 읽으면(오렌지 몰 은행) 등록 기관으로 맞춰 원본 찾기, 먼 이름은 그대로', async () => {
  for (const [read, want] of [
    ['[Web발신]\n[오렌지 몰 은행] 카드 대금 85,000원 청구 안내입니다. 납부 계좌\n001-234-500003 으로 11/10까지 입금 바랍니다.', true],
    ['[국민 행복 은행] 카드 대금 85,000원 청구 안내입니다. 납부 계좌 001-234-500003', false]
  ]) {
    const Hk = load();
    let n = 0;
    const f = fakeFetch(url => {
      if (url === '/api/v1/auth/me') return { status: 200, body: ME };
      if (url === '/api/v3/inputs') return { status: 201, body: { input_ref: 'inp_' + (++n), expires_at: 1 } };
      if (url === '/api/v3/inputs/inp_1/text') return { status: 200, body: { text: read, complete: true } };
      if (url === '/api/v3/document-lookups') return { status: 200, body: { lookup_status: 'UNVERIFIED', match_count: 0, document_ids: [], reason_codes: [] } };
      return { status: 409, body: { detail: 'INPUT_SUPPORT_UNDECIDED' } };
    });
    const a = await api(Hk, f).check('[문서 사진] a.png', { image: { media_type: 'image/png', base64: 'iVBORw0KGgo=' } });
    const look = f.calls.find(c => c.url === '/api/v3/document-lookups');
    assert.equal(!!look, want, read);
    if (want) {
      assert.equal(JSON.parse(look.body).issuer_id, Hk.api.lookupKey('[오리진 목 은행] 1000원 계좌 001-234-500003').issuer_id);
      assert.match(a.details.find(d => d.label === '사진 속 기관 이름').value, /오렌지 몰 은행.*오리진 목 은행/);
    } else assert.equal(a.details.find(d => d.label === '사진 속 기관 이름'), undefined);
  }
});

test('첨부 함수: 문서 사진을 base64 로, 다른 형식·5MB 초과는 보내지 않음', async () => {
  class FR { readAsDataURL(f) { this.result = 'data:' + f.type + ';base64,QUJD'; this.onload(); } }
  const sb = { console, setTimeout, clearTimeout, AbortController, AbortSignal, TextEncoder, URL, crypto: globalThis.crypto, Promise, FileReader: FR }; sb.window = sb; sb.self = sb; vm.createContext(sb);
  for (const f of FILES) vm.runInContext(fs.readFileSync(path.join(WEB, f), 'utf8'), sb, { filename: f });
  const up = sb.Hk.op5.uploadAttachment;
  const ok = await up({ name: 'a.png', type: 'image/png', size: 10 });
  assert.equal(ok.ok, true); assert.equal(ok.image.media_type, 'image/png'); assert.equal(ok.image.base64, 'QUJD');
  assert.equal((await up({ name: 'a.pdf', type: 'application/pdf', size: 10 })).ok, false);
  assert.equal((await up({ name: 'b.png', type: 'image/png', size: 6 * 1024 * 1024 })).ok, false);
});

test('금액 입력: 쉼표·원은 정수로, 숫자가 아니면 null(P2: 85,001 이 NaN 이 되어 비교에서 빠지던 결함)', async () => {
  const { parseWholeNumber: n } = await import('../개발/components/user/candidate-number.mjs');
  assert.equal(n('85,001'), 85001);
  assert.equal(n(' 85,001원 '), 85001);
  assert.equal(n('120000'), 120000);
  for (const bad of ['85.5', '-1', 'abc', '', '１２', '99999999999999999999']) assert.equal(n(bad), null, bad);
});

test('가입 화면: 기관 가입은 서버로 보내지 않고 개인만 보냄', () => {
  const join = fs.readFileSync(path.join(WEB, 'join.html'), 'utf8');
  assert.match(join, /kind:"personal",email,username:user,password:pw,terms_accepted:true/);
  assert.doesNotMatch(join, /kind:biz|issuer_id:/);
  assert.match(join, /if\(biz\)\{[^}]*운영자가 발급/);
  // 연결 실패에도 비밀번호 칸을 비움
  assert.match(join, /catch\(_\)\{\$\("password"\)\.value="";\$\("password2"\)\.value="";show\("err","서버에 연결하지/);
});

test('가입 화면: AI 키 입력 없음(AI는 서버 키로 분석), 예전에 남은 키는 지움', () => {
  const join = fs.readFileSync(path.join(WEB, 'join.html'), 'utf8');
  assert.doesNotMatch(join, /id="apiKey"|name="provider"|op5_keyvault|OP5KeyVault|Anthropic|sk-ant/);
  assert.match(join, /localStorage\.removeItem\("op5\.aikey"\)/);
  assert.equal(fs.existsSync(path.join(WEB, 'js', 'op5_keyvault.js')), false);
});

test('가입 성공 → 로그인 화면 이동, 아이디는 주소가 아닌 sessionStorage 로 넘기고 로그인 화면이 한 번 쓰고 지움', () => {
  const join = fs.readFileSync(path.join(WEB, 'join.html'), 'utf8');
  const login = fs.readFileSync(path.join(WEB, 'login.html'), 'utf8');
  assert.match(join, /sessionStorage\.setItem\("op5\.joinId",user\)[\s\S]*location\.href="login\.html\?next=business\.html"/);
  assert.doesNotMatch(join, /login\.html\?[^"]*(email|user)/);
  assert.match(login, /sessionStorage\.removeItem\("op5\.joinId"\);\$\("username"\)\.value=j/);
});
