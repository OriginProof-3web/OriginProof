// T2 프록시 시험: 소켓을 열지 않음. 가짜 업스트림 함수 + 가짜 req/res 로 처리기만 부름(설치 없음).
//   node --test 시험/op5_proxy.test.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { Readable } from 'node:stream';
import { createHandler, parsePort, parseUpstream, rewriteSetCookie, API_METHODS } from '../개발/op5-proxy.mjs';

const PORT = 8790;
const SELF = `http://127.0.0.1:${PORT}`;

function fakeReq(method, url, headers = {}, body) {
  const r = Readable.from(body == null ? [] : [Buffer.from(body)]);
  r.method = method; r.url = url;
  r.headers = { host: `127.0.0.1:${PORT}`, ...Object.fromEntries(Object.entries(headers).map(([k, v]) => [k.toLowerCase(), v])) };
  return r;
}
function fakeRes() {
  return { status: 0, headers: {}, body: Buffer.alloc(0), ended: false,
    writeHead(s, h) { this.status = s; this.headers = Object.fromEntries(Object.entries(h || {}).map(([k, v]) => [k.toLowerCase(), v])); },
    end(b) { this.ended = true; if (b) this.body = Buffer.from(b); } };
}
function fakeUpstream(reply) {
  const calls = [];
  const fn = async (r) => { calls.push(r); return typeof reply === 'function' ? reply(r) : reply; };
  fn.calls = calls;
  return fn;
}
async function run(h, ...a) { const res = fakeRes(); await h(fakeReq(...a), res); assert.ok(res.ended, '응답이 끝나야 함'); return res; }
const ok = (body, headers = {}) => ({ status: 200, headers: { 'content-type': 'application/json', ...headers }, body: Buffer.from(JSON.stringify(body)) });

test('v3 GET: /api 를 떼고 쿼리째 전달, 상태·Content-Type·X-Request-ID 그대로', async () => {
  const up = fakeUpstream(ok({ items: [] }, { 'x-request-id': 'req_up1' }));
  const res = await run(createHandler({ port: PORT, forward: up }), 'GET', '/api/v3/analyses?limit=20', { cookie: 'originproof_session=abc', 'x-request-id': 'req_b1', accept: 'application/json' });
  assert.equal(up.calls.length, 1);
  assert.equal(up.calls[0].method, 'GET');
  assert.equal(up.calls[0].path, '/v3/analyses?limit=20');
  assert.equal(up.calls[0].headers.cookie, 'originproof_session=abc');
  assert.equal(up.calls[0].headers['x-request-id'], 'req_b1');
  assert.equal(up.calls[0].headers['content-length'], undefined);
  assert.equal(res.status, 200);
  assert.equal(res.headers['content-type'], 'application/json');
  assert.equal(res.headers['x-request-id'], 'req_up1');
  assert.deepEqual(JSON.parse(res.body), { items: [] });
});

test('v3 POST: 본문·Content-Type·X-CSRF-Token 전달, Origin·Sec-Fetch-Site 는 빼고 보냄', async () => {
  const up = fakeUpstream({ status: 202, headers: { 'content-type': 'application/json' }, body: Buffer.from('{"analysis_id":"ana_1","status":"QUEUED"}') });
  const body = JSON.stringify({ request_id: 'req_x', input_ref: 'inp_1' });
  const res = await run(createHandler({ port: PORT, forward: up }), 'POST', '/api/v3/analyses',
    { 'content-type': 'application/json', 'x-csrf-token': 'tok-123', cookie: 'originproof_session=abc', origin: SELF, 'sec-fetch-site': 'same-origin', referer: SELF + '/business.html' }, body);
  const c = up.calls[0];
  assert.equal(c.method, 'POST');
  assert.equal(c.path, '/v3/analyses');
  assert.equal(c.body.toString(), body);
  assert.equal(c.headers['content-type'], 'application/json');
  assert.equal(c.headers['content-length'], String(Buffer.byteLength(body)));
  assert.equal(c.headers['x-csrf-token'], 'tok-123');
  assert.equal(c.headers.origin, undefined);
  assert.equal(c.headers['sec-fetch-site'], undefined);
  assert.equal(c.headers.referer, undefined);
  assert.equal(res.status, 202);
});

test('v3 DELETE: 업스트림으로 DELETE 전달, 204 그대로', async () => {
  assert.ok(API_METHODS.includes('DELETE'));
  const up = fakeUpstream({ status: 204, headers: { 'x-request-id': 'req_d' }, body: Buffer.alloc(0) });
  const res = await run(createHandler({ port: PORT, forward: up }), 'DELETE', '/api/v3/analyses/ana_1', { 'x-csrf-token': 'tok-1', cookie: 's=1', origin: SELF });
  assert.equal(up.calls[0].method, 'DELETE');
  assert.equal(up.calls[0].path, '/v3/analyses/ana_1');
  assert.equal(up.calls[0].headers['x-csrf-token'], 'tok-1');
  assert.equal(up.calls[0].headers['content-length'], undefined);
  assert.equal(res.status, 204);
  assert.equal(res.body.length, 0);
});

test('v1·v2·health 도 GET·POST·DELETE 전달(경로 앞 /api 만 뗌)', async () => {
  const up = fakeUpstream(ok({}));
  const h = createHandler({ port: PORT, forward: up });
  for (const p of ['/api/v1/auth/me', '/api/v2/issuer/proofs', '/api/health/ready', '/api/v3/operations/op_1'])
    for (const m of ['GET', 'POST', 'DELETE']) {
      const res = await run(h, m, p, { origin: SELF, 'content-type': 'application/json' }, m === 'POST' ? '{}' : undefined);
      assert.equal(res.status, 200, `${m} ${p}`);
      const c = up.calls.at(-1);
      assert.equal(c.method, m); assert.equal(c.path, p.slice(4));
    }
  assert.equal(up.calls.length, 12);
});

test('쿠키 왕복: 로그인 Set-Cookie(Domain 뺌, 여러 줄 유지) → 다음 요청 Cookie 전달', async () => {
  const up = fakeUpstream((r) => r.path === '/v1/auth/login'
    ? ok({ csrf_token: 'c1' }, { 'set-cookie': ['originproof_session=SID1; Domain=127.0.0.1; HttpOnly; Max-Age=28800; Path=/; SameSite=lax', 'other=1; Path=/; Secure'] })
    : ok({ username: 'u' }));
  const h = createHandler({ port: PORT, forward: up });
  const login = await run(h, 'POST', '/api/v1/auth/login', { origin: SELF, 'content-type': 'application/json' }, '{"username":"u","password":"x"}');
  assert.deepEqual(login.headers['set-cookie'], ['originproof_session=SID1; HttpOnly; Max-Age=28800; Path=/; SameSite=lax', 'other=1; Path=/; Secure']);
  const cookie = login.headers['set-cookie'].map((c) => c.split(';')[0]).join('; ');
  await run(h, 'GET', '/api/v1/auth/me', { cookie });
  assert.equal(up.calls[1].headers.cookie, 'originproof_session=SID1; other=1');
  assert.deepEqual(rewriteSetCookie('a=1; domain=x.test; Path=/'), ['a=1; Path=/']);
});

test('CSRF 전달: X-CSRF-Token 그대로, 없으면 만들어 넣지 않음', async () => {
  const up = fakeUpstream(ok({}));
  const h = createHandler({ port: PORT, forward: up });
  await run(h, 'POST', '/api/v1/auth/logout', { origin: SELF, 'x-csrf-token': 'abc.DEF-123' }, '');
  await run(h, 'POST', '/api/v1/auth/logout', { origin: SELF }, '');
  assert.equal(up.calls[0].headers['x-csrf-token'], 'abc.DEF-123');
  assert.equal('x-csrf-token' in up.calls[1].headers, false);
});

test('429 Retry-After·X-Request-ID·본문 그대로 전달', async () => {
  const up = fakeUpstream({ status: 429, headers: { 'content-type': 'application/json', 'retry-after': '37', 'x-request-id': 'req_rl' }, body: Buffer.from('{"detail":"RATE_LIMITED"}') });
  const res = await run(createHandler({ port: PORT, forward: up }), 'POST', '/api/v3/inputs', { origin: SELF, 'content-type': 'application/json' }, '{}');
  assert.equal(res.status, 429);
  assert.equal(res.headers['retry-after'], '37');
  assert.equal(res.headers['x-request-id'], 'req_rl');
  assert.deepEqual(JSON.parse(res.body), { detail: 'RATE_LIMITED' });
});

test('정적: business.html 200(HTML), "/" 도 business.html, js 200', async () => {
  const up = fakeUpstream(ok({}));
  const h = createHandler({ port: PORT, forward: up });
  const a = await run(h, 'GET', '/business.html?theme=light');
  assert.equal(a.status, 200);
  assert.match(a.headers['content-type'], /^text\/html/);
  assert.match(a.body.toString(), /<html/i);
  const b = await run(h, 'GET', '/');
  assert.equal(b.status, 200);
  assert.equal(b.body.length, a.body.length);
  const c = await run(h, 'GET', '/js/op5_connect.js');
  assert.equal(c.status, 200);
  assert.match(c.headers['content-type'], /javascript/);
  assert.equal(up.calls.length, 0, '정적은 업스트림을 부르지 않음');
});

test('허용 경로 밖은 404, 업스트림 안 부름', async () => {
  const up = fakeUpstream(ok({}));
  const h = createHandler({ port: PORT, forward: up });
  for (const p of ['/api/v4/x', '/api/admin', '/api', '/api/', '/api/v3/../admin', '/api/v3/%2e%2e/admin', '/api/health', '/없는파일.html', '/../개발/op5-proxy.mjs', '/%2e%2e/개발/op5-proxy.mjs', '/.DS_Store', '/js/..%2f..%2f개발%2fop5-proxy.mjs'])
    assert.equal((await run(h, 'GET', p)).status, 404, p);
  assert.equal(up.calls.length, 0);
});

test('Origin 검사(security.py:58-63 과 같은 규칙): 다른 출처·cross-site 쓰기는 403, GET 은 통과', async () => {
  const up = fakeUpstream(ok({}));
  const h = createHandler({ port: PORT, forward: up });
  const bad = await run(h, 'POST', '/api/v3/inputs', { origin: 'http://evil.test' }, '{}');
  assert.equal(bad.status, 403);
  assert.deepEqual(JSON.parse(bad.body), { detail: 'ORIGIN_FORBIDDEN' });
  const bad1 = await run(h, 'DELETE', '/api/v1/x', { origin: 'http://127.0.0.1:8768' });
  assert.deepEqual(JSON.parse(bad1.body), { error: 'ORIGIN_FORBIDDEN' });
  assert.equal((await run(h, 'POST', '/api/v3/inputs', { 'sec-fetch-site': 'cross-site' }, '{}')).status, 403);
  assert.equal(up.calls.length, 0);
  assert.equal((await run(h, 'POST', '/api/v3/inputs', { origin: `http://localhost:${PORT}` }, '{}')).status, 200);
  assert.equal((await run(h, 'GET', '/api/v3/analyses', { origin: 'http://evil.test' })).status, 200);
});

test('Host 가 프록시 주소가 아니면 421(DNS rebinding 막기), 허용 안 된 메서드 405, 업스트림 꺼짐 502·시간 초과 504', async () => {
  const h = createHandler({ port: PORT, forward: fakeUpstream(ok({})) });
  const req = fakeReq('GET', '/business.html'); req.headers.host = 'evil.test:8790';
  const res = fakeRes(); await h(req, res); assert.equal(res.status, 421);
  assert.equal((await run(h, 'PUT', '/api/v3/x', { origin: SELF }, '{}')).status, 405);
  const down = createHandler({ port: PORT, forward: async () => { throw Object.assign(new Error('x'), { code: 'ECONNREFUSED' }); } });
  assert.deepEqual(JSON.parse((await run(down, 'GET', '/api/v3/analyses')).body), { detail: 'UPSTREAM_UNREACHABLE' });
  const slow = createHandler({ port: PORT, forward: async () => { throw Object.assign(new Error('x'), { code: 'ETIMEDOUT' }); } });
  assert.equal((await run(slow, 'GET', '/api/v1/auth/me')).status, 504);
});

test('설정 검증: 포트·업스트림', () => {
  assert.deepEqual(parsePort(undefined), { ok: true, value: 8790 });
  for (const p of ['8768', '8770', '8780', '8000', '3000', '8001', '80', '99999', 'abc', '8790; rm']) assert.equal(parsePort(p).ok, false, p);
  assert.equal(parseUpstream(undefined).value, 'http://127.0.0.1:8000');
  assert.equal(parseUpstream('http://localhost:8000/').value, 'http://localhost:8000');
  for (const u of ['https://127.0.0.1:8000', 'http://example.com:8000', 'http://127.0.0.1', 'http://127.0.0.1:8000/v3', 'http://127.0.0.1.evil.test:80']) assert.equal(parseUpstream(u).ok, false, u);
});
