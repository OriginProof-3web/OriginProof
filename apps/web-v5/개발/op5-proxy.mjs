// 5안 같은 출처 프록시 (감사팀 재작업 T2). Node 표준 모듈만 씀(설치 없음).
//   - 정적: ../페이지/ 를 그대로 내보냄(GET·HEAD). "/" 는 business.html.
//   - API: /api/v1/ · /api/v2/ · /api/v3/ · /api/health/ 의 GET·HEAD·POST·DELETE 를 "/api" 를 떼고 업스트림(d0111d8 API)으로 넘김.
//   - 듣는 곳: 127.0.0.1 만. 포트 기본 8790(8768·8770·8780·8000·3000·8001 은 쓰지 않음).
//   - 환경변수: OP5_PROXY_PORT(기본 8790), OP5_UPSTREAM(기본 http://127.0.0.1:8000, 이 컴퓨터 http 주소만).
//   - Origin: 쓰기 요청은 이 프록시가 d0111d8 security.py:59-63 과 같은 규칙으로 먼저 검사(자기 출처만 허용)한 뒤,
//     Origin·Sec-Fetch-* 를 빼고 넘김 → 업스트림에서는 origin None + sec-fetch-site 없음이라 통과(자세한 근거는 docs/T2_T5_개발메모.md).
//   - 로그에는 메서드·경로·상태만 남김(쿠키·토큰·본문은 남기지 않음).
// 실행: node 개발/op5-proxy.mjs   (또는 개발/'5안 d0111d8 프록시 시작.command')
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const DEFAULT_PORT = 8790;
export const DEFAULT_UPSTREAM = 'http://127.0.0.1:8000';
export const RESERVED_PORTS = [8768, 8770, 8780, 8000, 3000, 8001];
export const API_PREFIXES = ['/api/v1/', '/api/v2/', '/api/v3/', '/api/health/'];
export const API_METHODS = ['GET', 'HEAD', 'POST', 'DELETE']; // DELETE: /v3/analyses/{id} 지우기(op5_client.js)
const WRITE_METHODS = ['POST', 'DELETE'];
const REQ_HEADERS = ['cookie', 'x-csrf-token', 'x-request-id', 'content-type', 'accept'];
const RES_HEADERS = ['content-type', 'set-cookie', 'retry-after', 'x-request-id', 'cache-control', 'x-content-type-options', 'content-disposition'];
const BODY_MAX = 1024 * 1024;          // d0111d8 settings.py request_body_max_bytes 상한(le=1048576)
const RES_MAX = 16 * 1024 * 1024;
const UPSTREAM_TIMEOUT_MS = 30000;
const ROOT = fileURLToPath(new URL('../페이지/', import.meta.url));
const TYPES = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.mjs': 'text/javascript; charset=utf-8', '.json': 'application/json; charset=utf-8', '.png': 'image/png', '.svg': 'image/svg+xml', '.ico': 'image/x-icon', '.woff2': 'font/woff2', '.txt': 'text/plain; charset=utf-8' };

/* ---------- 설정 검증 ---------- */
export function parsePort(v) {
  if (v == null || v === '') return { ok: true, value: DEFAULT_PORT };
  if (!/^\d{1,5}$/.test(String(v))) return { ok: false, why: '포트는 숫자만 받아요' };
  const n = Number(v);
  if (n < 1024 || n > 65535) return { ok: false, why: '포트는 1024~65535 만 받아요' };
  if (RESERVED_PORTS.includes(n)) return { ok: false, why: `포트 ${n} 은 다른 서버가 써서 받지 않아요(${RESERVED_PORTS.join('·')})` };
  return { ok: true, value: n };
}
export function parseUpstream(v) {
  const s = v == null || v === '' ? DEFAULT_UPSTREAM : String(v).replace(/\/+$/, '');
  const m = /^http:\/\/(127\.0\.0\.1|localhost|\[::1\]):(\d{1,5})$/.exec(s);
  if (!m || Number(m[2]) < 1 || Number(m[2]) > 65535) return { ok: false, why: '업스트림은 이 컴퓨터 http 주소만 받아요(예: http://127.0.0.1:8000)' };
  return { ok: true, value: s };
}

/* ---------- 업스트림 호출(기본: node:http). 시험에서는 같은 모양의 가짜 함수를 넣음 ---------- */
// forward({ method, path, headers, body }) → Promise<{ status, headers(소문자 키, set-cookie 는 배열), body: Buffer }>
export function httpForward(upstream) {
  const u = new URL(upstream);
  return ({ method, path: p, headers, body }) => new Promise((resolve, reject) => {
    const r = http.request({ host: u.hostname.replace(/^\[|\]$/g, ''), port: u.port, method, path: p, headers: { ...headers, host: u.host }, timeout: UPSTREAM_TIMEOUT_MS }, (up) => {
      const chunks = []; let size = 0;
      up.on('data', (c) => { size += c.length; if (size > RES_MAX) { up.destroy(); reject(Object.assign(new Error('too large'), { code: 'RES_TOO_LARGE' })); } else chunks.push(c); });
      up.on('end', () => resolve({ status: up.statusCode, headers: up.headers, body: Buffer.concat(chunks) }));
      up.on('error', reject);
    });
    r.on('timeout', () => r.destroy(Object.assign(new Error('timeout'), { code: 'ETIMEDOUT' })));
    r.on('error', reject);
    r.end(body && body.length ? body : undefined);
  });
}

/* ---------- 도우미 ---------- */
function send(res, status, headers, body) {
  res.writeHead(status, { 'cache-control': 'no-store', 'x-content-type-options': 'nosniff', ...headers });
  res.end(body);
}
function errKey(apiPath) { return apiPath.startsWith('/v3/') ? 'detail' : 'error'; } // security.py:47 과 같은 칸 이름
function json(res, status, apiPath, code) {
  send(res, status, { 'content-type': 'application/json' }, JSON.stringify({ [errKey(apiPath)]: code }));
}
// 경로 안의 . / .. / 빈 칸 / 역슬래시 / NUL 은 받지 않음(인코딩된 것 포함)
function cleanPath(p) {
  let d;
  try { d = decodeURIComponent(p); } catch { return null; }
  if (/[\\\0]/.test(d)) return null;
  const segs = d.split('/').slice(1);
  if (segs.slice(0, -1).some((s) => s === '' || s === '.' || s === '..') || segs[segs.length - 1] === '.' || segs[segs.length - 1] === '..') return null;
  return d;
}
// Set-Cookie: Domain 속성만 뺌(프록시 주소에 붙게). Secure·HttpOnly·SameSite·Path·Max-Age 는 그대로.
export function rewriteSetCookie(v) {
  const list = v == null ? [] : Array.isArray(v) ? v : [v];
  return list.map((c) => String(c).split(';').filter((part, i) => i === 0 || !/^\s*domain\s*=/i.test(part)).join(';'));
}
function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = []; let size = 0;
    req.on('data', (c) => { size += c.length; if (size > BODY_MAX) { reject(Object.assign(new Error('too large'), { code: 'BODY_TOO_LARGE' })); req.destroy?.(); } else chunks.push(c); });
    req.on('end', () => resolve(Buffer.concat(chunks)));
    req.on('error', reject);
  });
}

/* ---------- 요청 처리기 ---------- */
// opts: { port, upstream, forward, root, log }
export function createHandler(opts = {}) {
  const port = opts.port ?? DEFAULT_PORT;
  const forward = opts.forward ?? httpForward(opts.upstream ?? DEFAULT_UPSTREAM);
  const root = path.resolve(opts.root ?? ROOT);
  const log = opts.log ?? (() => {});
  const hosts = [`127.0.0.1:${port}`, `localhost:${port}`];
  const origins = hosts.map((h) => 'http://' + h);

  return async function handle(req, res) {
    const method = String(req.method || 'GET').toUpperCase();
    const raw = String(req.url || '/');
    const qi = raw.indexOf('?');
    const pathname = qi < 0 ? raw : raw.slice(0, qi);
    const search = qi < 0 ? '' : raw.slice(qi);
    const done = (s) => log(`${method} ${pathname} ${s}`);
    // DNS rebinding 막기: Host 는 이 프록시 주소만
    if (!hosts.includes(String(req.headers.host || '').toLowerCase())) { done(421); return send(res, 421, { 'content-type': 'text/plain; charset=utf-8' }, 'host not allowed'); }
    const clean = cleanPath(pathname);

    /* ----- API ----- */
    if (pathname === '/api' || pathname.startsWith('/api/')) {
      const apiPath = pathname.slice(4);
      if (!clean || !API_PREFIXES.some((p) => pathname.startsWith(p))) { done(404); return json(res, 404, apiPath, 'NOT_FOUND'); }
      if (!API_METHODS.includes(method)) { done(405); return send(res, 405, { allow: API_METHODS.join(', '), 'content-type': 'application/json' }, JSON.stringify({ [errKey(apiPath)]: 'METHOD_NOT_ALLOWED' })); }
      if (WRITE_METHODS.includes(method)) {
        // d0111d8 security.py:58-63 과 같은 규칙을 이 프록시 출처 기준으로 먼저 적용
        const origin = req.headers.origin;
        const site = req.headers['sec-fetch-site'];
        if ((origin != null && !origins.includes(origin)) || (origin == null && site === 'cross-site')) { done(403); return json(res, 403, apiPath, 'ORIGIN_FORBIDDEN'); }
      }
      let body;
      try { body = WRITE_METHODS.includes(method) ? await readBody(req) : Buffer.alloc(0); } catch { done(413); return json(res, 413, apiPath, 'REQUEST_TOO_LARGE'); }
      const headers = {};
      for (const h of REQ_HEADERS) if (req.headers[h] != null) headers[h] = req.headers[h];
      if (method === 'POST' || body.length) headers['content-length'] = String(body.length);
      let up;
      try {
        up = await forward({ method, path: apiPath + search, headers, body });
      } catch (e) {
        const timeout = e && e.code === 'ETIMEDOUT';
        done(timeout ? 504 : 502);
        return json(res, timeout ? 504 : 502, apiPath, timeout ? 'UPSTREAM_TIMEOUT' : 'UPSTREAM_UNREACHABLE');
      }
      const out = {};
      for (const h of RES_HEADERS) {
        const v = up.headers?.[h];
        if (v == null) continue;
        out[h] = h === 'set-cookie' ? rewriteSetCookie(v) : v;
      }
      done(up.status);
      res.writeHead(up.status, out);
      return res.end(method === 'HEAD' ? undefined : up.body);
    }

    /* ----- 정적(../페이지) ----- */
    if (method !== 'GET' && method !== 'HEAD') { done(405); return send(res, 405, { allow: 'GET, HEAD', 'content-type': 'text/plain; charset=utf-8' }, 'method not allowed'); }
    if (!clean || clean.split('/').some((s) => s.startsWith('.') && s !== '')) { done(404); return send(res, 404, { 'content-type': 'text/plain; charset=utf-8' }, 'not found'); }
    const rel = clean === '/' ? 'business.html' : clean.slice(1);
    const file = path.resolve(root, rel);
    if (!file.startsWith(root + path.sep)) { done(404); return send(res, 404, { 'content-type': 'text/plain; charset=utf-8' }, 'not found'); }
    let data;
    try {
      const st = fs.statSync(file);
      if (!st.isFile()) throw new Error('not file');
      data = fs.readFileSync(file);
    } catch { done(404); return send(res, 404, { 'content-type': 'text/plain; charset=utf-8' }, 'not found'); }
    done(200);
    return send(res, 200, { 'content-type': TYPES[path.extname(file).toLowerCase()] || 'application/octet-stream', 'content-length': String(data.length) }, method === 'HEAD' ? undefined : data);
  };
}

/* ---------- 직접 실행할 때만 listen ---------- */
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const p = parsePort(process.env.OP5_PROXY_PORT);
  const u = parseUpstream(process.env.OP5_UPSTREAM);
  if (!p.ok || !u.ok) { console.error('설정 오류: ' + (p.ok ? '' : p.why + ' ') + (u.ok ? '' : u.why)); process.exit(2); }
  const handler = createHandler({ port: p.value, upstream: u.value, log: (s) => console.log(new Date().toISOString().slice(11, 19), s) });
  const server = http.createServer((req, res) => { handler(req, res).catch(() => { try { send(res, 500, { 'content-type': 'text/plain; charset=utf-8' }, 'proxy error'); } catch {} }); });
  server.listen(p.value, '127.0.0.1', () => {
    console.log(`5안 프록시: http://127.0.0.1:${p.value}/business.html?mode=api  →  ${u.value} (/api 를 떼고 전달)`);
    console.log('끄기: Ctrl+C');
  });
}
