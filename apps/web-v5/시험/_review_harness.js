// 교차 검수 회귀 시험 하네스: 페이지를 가짜 DOM 에서 돌린다. 브라우저 아님.
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const ROOT = path.join(__dirname, '..');
const { makeDom, Ev } = require(path.join(ROOT, '시험/_dom.js'));
const { fakeFetch } = require(path.join(ROOT, '시험/가져온/regression/_load.js'));
const WEB = path.join(ROOT, '페이지');
const read = f => fs.readFileSync(path.join(WEB, f), 'utf8');
const HTML = read('business.html');
const SCRIPTS = [...HTML.matchAll(/<script src="((?:data|js)\/[^"]+)"><\/script>/g)].map(m => m[1]);
const INLINE = (() => { const i = HTML.indexOf('function selectAction'); return HTML.slice(HTML.lastIndexOf('<script>', i) + 8, HTML.indexOf('</script>', i)); })();
const sleep = ms => new Promise(r => setTimeout(r, ms));

function build(search, fetchFn, pre) {
  const d = makeDom(search);
  const { win, doc, El } = d;
  const e = (tag, attrs, parent, text) => { const n = new El(tag, doc); Object.entries(attrs || {}).forEach(([k, v]) => (k === 'class' ? (n.className = v) : n.setAttribute(k, v))); if (text) n.textContent = text; if (parent) parent.append(n); return n; };
  const app = e('div', { class: 'app', id: 'app' }, doc.body);
  const side = e('div', { id: 'sidebar-root', class: 'dark' }, app);
  e('button', { type: 'button' }, side, '도움말');
  e('input', { 'aria-label': '최근 확인 검색' }, side);
  const main = e('main', { class: 'main chat-main' }, app);
  e('button', { class: 'theme-btn', id: 'themeBtn' }, main);
  e('div', { class: 'preset-bar', id: 'presetBar' }, main);
  const sc = e('section', { class: 'chat-scroll', id: 'chatScroll' }, main);
  const th = e('div', { class: 'chat-thread', id: 'chatThread' }, sc);
  e('div', { class: 'chat-empty', id: 'chatEmpty' }, th);
  const wrap = e('div', { class: 'composer-wrap' }, main);
  const form = e('form', { class: 'composer', id: 'composer' }, wrap);
  e('textarea', { id: 'chatInput' }, form);
  const bar = e('div', { class: 'composer-bar' }, form);
  e('button', { class: 'composer-icon', id: 'attachBtn' }, bar, '＋');
  e('span', { class: 'composer-note', id: 'attachNote' }, bar);
  e('button', { class: 'composer-send', id: 'sendBtn' }, bar, '↑');
  e('p', { class: 'composer-hint', id: 'composerHint' }, wrap, 'hint');
  const aside = e('aside', { class: 'side', id: 'sidePanel' }, app);
  e('button', { class: 'side-close', id: 'sideClose' }, aside);
  e('ol', { class: 'staff-list', id: 'staffList' }, aside);
  e('span', { class: 'pcard-count', id: 'staffCount' }, aside, '0/7');
  e('p', { class: 'pcard-note', id: 'staffNote' }, aside, 'n');
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
  if (pre) pre(win);
  vm.createContext(win);
  vm.runInContext(INLINE, win, { filename: 'business.html(inline)' });
  for (const f of SCRIPTS) vm.runInContext(read(f), win, { filename: f });
  return d;
}
const threadText = d => d.doc.getElementById('chatThread').textContent;
const enter = (d, text) => { const i = d.doc.getElementById('chatInput'); i.value = text; d.doc._dispatch(i, new Ev('keydown', { key: 'Enter' })); };
const menu = (d, k) => vm.runInContext('selectAction(' + JSON.stringify(k) + ')', d.win);
const buttons = d => d.doc.querySelectorAll('#chatThread button');
const find = (d, label) => buttons(d).filter(b => (label instanceof RegExp ? label.test(b.textContent) : b.textContent === label)).pop();
async function press(d, label, ms = 25) { const b = typeof label === 'object' && !(label instanceof RegExp) ? label : find(d, label); assert.ok(b, '단추 없음: ' + label); d.doc._dispatch(b, new Ev('click')); await sleep(ms); }
const toSample = async d => { if (!find(d, '예시 모드로 바꾸기') || find(d, '예시 모드로 바꾸기').disabled) { menu(d, 'status'); await sleep(40); } await press(d, '예시 모드로 바꾸기'); };

const APP = 'app_1', PID = '0x' + 'ab'.repeat(32), ISS = '0x' + 'cd'.repeat(32), TX = '0x' + 'ef'.repeat(32), TX2 = '0x' + '12'.repeat(32);
/* identifier_hash 와 같은 규칙: keccak256(utf8(값)) (packages/python/originproof_core/wallet_signatures.py:69-74).
   SHA3-256 이 아니라 Keccak 패딩(0x01)이라 node:crypto 의 sha3-256 을 쓸 수 없고, 설치 금지라 순수 JS 로 계산한다.
   결과는 저장소 .venv 의 진짜 identifier_hash 와 logs/t8_asgi_suspension.json 으로 대조했다(t8_parity.js). */
const KECCAK_RC = ['0x0000000000000001', '0x0000000000008082', '0x800000000000808a', '0x8000000080008000', '0x000000000000808b', '0x0000000080000001', '0x8000000080008081', '0x8000000000008009', '0x000000000000008a', '0x0000000000000088', '0x0000000080008009', '0x000000008000000a', '0x000000008000808b', '0x800000000000008b', '0x8000000000008089', '0x8000000000008003', '0x8000000000008002', '0x8000000000000080', '0x000000000000800a', '0x800000008000000a', '0x8000000080008081', '0x8000000000008080', '0x0000000080000001', '0x8000000080008008'].map(BigInt);
const KECCAK_ROT = [1, 3, 6, 10, 15, 21, 28, 36, 45, 55, 2, 14, 27, 41, 56, 8, 25, 43, 62, 18, 39, 61, 20, 44];
const KECCAK_PIL = [10, 7, 11, 17, 18, 3, 5, 16, 8, 21, 24, 4, 15, 23, 19, 13, 12, 2, 20, 14, 22, 9, 6, 1];
function identifierHash(text) {
  const M = (1n << 64n) - 1n, rotl = (x, n) => ((x << BigInt(n)) | (x >> BigInt(64 - n))) & M;
  const RATE = 136, input = Buffer.from(String(text), 'utf8'), s = new Array(25).fill(0n);
  const p = Buffer.alloc((Math.floor(input.length / RATE) + 1) * RATE);
  input.copy(p);
  p[input.length] ^= 0x01;
  p[p.length - 1] ^= 0x80;
  for (let off = 0; off < p.length; off += RATE) {
    for (let i = 0; i < RATE / 8; i++) s[i] ^= p.readBigUInt64LE(off + 8 * i);
    for (const rc of KECCAK_RC) {
      const c = [0, 1, 2, 3, 4].map(x => s[x] ^ s[x + 5] ^ s[x + 10] ^ s[x + 15] ^ s[x + 20]);
      for (let x = 0; x < 5; x++) { const d = c[(x + 4) % 5] ^ rotl(c[(x + 1) % 5], 1); for (let y = 0; y < 25; y += 5) s[x + y] ^= d; }
      let t = s[1];
      KECCAK_PIL.forEach((j, i) => { const b = s[j]; s[j] = rotl(t, KECCAK_ROT[i]); t = b; });
      for (let y = 0; y < 25; y += 5) { const r = s.slice(y, y + 5); for (let x = 0; x < 5; x++) s[y + x] = r[x] ^ (~r[(x + 1) % 5] & M & r[(x + 2) % 5]); }
      s[0] ^= rc;
    }
  }
  const out = Buffer.alloc(32);
  for (let i = 0; i < 4; i++) out.writeBigUInt64LE(s[i], 8 * i);
  return '0x' + out.toString('hex');
}
const HEX32 = /^0x[0-9a-f]{64}$/;   // wallet_contract.py:27
/* 지갑 쓰기 요청: authorize(mutation=True) 가 역할 검사보다 먼저 CSRF 를 본다(wallet_runtime.py:85-93, accounts.py:99-102) */
const WALLET_WRITE = /^\/v3\/(issuer-applications\/|proposals|inputs$|analyses$|operations\/[^/]+\/reconcile$)/;
/* 서버 규칙을 그대로 따르는 대역(wallet_runtime.py:85-110, wallet_onboarding.py:56-67·98-238, wallet_governance.py:247-255·352-361·424-438).
   persona: { role, account_id, issuer_id } / 설정: applicant(신청 계정), approver(지정 승인자), operatorAddress(승인 지갑 등록·is_approver 를 한 값으로),
   issuerOnChain(false 면 rpc("issuer") 가 None), applicationIssuer(신청의 기관, 다른 기관이면 404), over(요청별 덮어쓰기) */
function serverDouble(o) {
  const persona = Object.assign({ account_id: 'acct_me', username: 'u', role: 'issuer', issuer_id: 'iss_origin_mock_bank', csrf_token: 'c' }, o.persona || {});
  const applicant = o.applicant === undefined ? 'acct_me' : o.applicant;
  const approver = o.approver || 'acct_designated';
  const hasAddress = o.operatorAddress !== false;
  const issuerOnChain = o.issuerOnChain !== false;
  const applicationIssuer = o.applicationIssuer === undefined ? persona.issuer_id : o.applicationIssuer;
  const isIssuer = persona.role === 'issuer' && !!persona.issuer_id;   // role="issuer" 면 issuer_id 도 있어야 함(wallet_runtime.py:91-92, chain_management.py:530·587, finals_proofs.py:351)
  const csrfOk = init => !!init.headers && init.headers['X-CSRF-Token'] === persona.csrf_token;
  const V = { application_id: APP, roster_matched: true, demo_only: true, email_verified: true, internally_approved: false, metadata: {}, metadata_hash: '0x' + '00'.repeat(32) };
  const OP = { operation_id: 'op_1', request_id: 'req_x', status: 'SUBMITTED', recovery_required: false, next_action: 'WAIT' };
  const deny = (s, c) => ({ status: s, body: { detail: c } });
  const f = fakeFetch((url, init, n) => {
    const m = init.method || 'GET';
    const u = url.replace(/^\/api/, '');
    if (o.over) { const r = o.over(u, m, init, n); if (r) return r; }
    if (u === '/v1/auth/me') return { status: 200, body: persona };
    if (u.startsWith('/health/')) return { status: 200, body: { status: u.endsWith('live') ? 'live' : 'ready' } };
    if (u === '/v1/chain/network') return { status: 200, body: { chain_target: 'anvil', chain_id: 31337, rpc_fallback_configured: false, approver_nodes: [] } };
    if (u === '/v1/issuer/status') return isIssuer ? { status: 200, body: { issuer_id: persona.issuer_id, status: 'ACTIVE', chain_id: 31337 } } : deny(403, 'FORBIDDEN');
    if (u === '/v1/issuer-applications/mine') return persona.role === 'issuer' ? { status: 200, body: { application_id: APP, issuer_id: persona.issuer_id, issuer_name: 'Origin Mock Bank', applicant_account_id: applicant, status: 'APPROVED', decision_reason: null, decided_by_account_id: null, created_at: 'x' } } : deny(403, 'FORBIDDEN');
    /* suspensions:시작 wallet_governance.py:424-438, wallet_runtime.py:85-110. 형식(422)은 FastAPI 가 함수 실행 전에 거른다(main.py:190-203) */
    const suspend = m === 'POST' && u.match(/^\/v3\/issuers\/([^/]+)\/suspensions$/);
    if (suspend) {
      let b = null;
      try { b = JSON.parse(init.body); } catch { b = null; }
      const shape = !!b && typeof b === 'object' && Object.keys(b).sort().join() === 'request_id,tx_hash' && /^req_[A-Za-z0-9_-]{1,124}$/.test(b.request_id) && HEX32.test(b.tx_hash);
      if (!HEX32.test(suspend[1]) || !shape) return deny(422, 'MALFORMED_INPUT');
      if (!csrfOk(init)) return deny(403, 'CSRF_REQUIRED');
      if (persona.role === 'operator') return hasAddress ? { status: 202, body: OP } : deny(403, 'APPROVER_REQUIRED');
      if (isIssuer && identifierHash(persona.issuer_id) === suspend[1]) return issuerOnChain ? { status: 202, body: OP } : deny(404, 'ISSUER_NOT_FOUND');
      return deny(403, 'FORBIDDEN');
    }
    /* suspensions:끝 */
    if (m !== 'GET' && WALLET_WRITE.test(u) && !csrfOk(init)) return deny(403, 'CSRF_REQUIRED');
    if (u.startsWith('/v3/issuer-applications/')) {
      if (!isIssuer) return deny(403, 'FORBIDDEN');
      if (applicationIssuer !== persona.issuer_id) return deny(404, 'APPLICATION_NOT_FOUND');
      if (u.endsWith('/internal-approvals')) {
        if (applicant === persona.account_id) return deny(403, 'SELF_APPROVAL_FORBIDDEN');
        if (approver !== persona.account_id) return deny(403, 'INTERNAL_APPROVER_REQUIRED');
        return { status: 200, body: V };
      }
      if (applicant !== persona.account_id) return deny(404, 'APPLICATION_NOT_FOUND');
      if (u.endsWith('/demo-inbox')) return { status: 200, body: { code: '654321', expires_at: 1 } };
      if (u.endsWith('/email-codes')) return { status: 201, body: V };
      if (u.endsWith('/email-verifications')) return JSON.parse(init.body).code === '654321' ? { status: 200, body: V } : deny(422, 'EMAIL_CODE_INVALID');
      return { status: 200, body: V };
    }
    if (u.startsWith('/v3/proposals')) {
      if (persona.role !== 'operator') return deny(403, 'FORBIDDEN');
      if (!hasAddress) return deny(403, 'APPROVER_REQUIRED');
      if (m === 'GET') return { status: 200, body: { proposal_id: PID, proposal: {}, status: 'PENDING', approvals: [], threshold: 2 } };
      if (u === '/v3/proposals') return { status: 201, body: { proposal_id: PID, proposal: {}, status: 'PREPARED', approvals: [], threshold: 2 } };
      return { status: 202, body: OP };
    }
    if (u === '/v3/operations/op_1') return { status: 200, body: Object.assign({}, OP, { status: 'UNKNOWN', next_action: 'RECONCILE' }) };
    if (u === '/v3/operations/op_1/reconcile') return { status: 202, body: Object.assign({}, OP, { status: 'CONFIRMED', next_action: 'NONE' }) };
    if (u === '/v3/inputs') return { status: 201, body: { input_ref: 'inp_' + n, expires_at: 1 } };
    if (u === '/v3/analyses' && m === 'POST') return { status: 202, body: { analysis_id: 'ana_' + n, status: 'COMPLETED', input_kind: 'TEXT', retain_report: false, retain_original: false } };
    if (u.startsWith('/v3/analyses?')) return { status: 200, body: { items: [{ analysis_id: 'ana_k', status: 'COMPLETED', retain_report: true, retain_original: true }] } };
    if (u.startsWith('/v3/analyses/')) return { status: 200, body: {} };
    if (u.startsWith('/v1/issuer/keys')) return isIssuer ? { status: 200, body: [] } : deny(403, 'FORBIDDEN');
    if (u.startsWith('/v2/issuer/proofs')) return isIssuer ? { status: 200, body: [] } : deny(403, 'FORBIDDEN');
    if (u.startsWith('/v1/operations')) return { status: 200, body: [] };
    if (u.startsWith('/v3/documents/')) return { status: 200, body: { document_id: PID, state: 'ACTIVE', version: 1, latest_version: 1, warnings: [] } };
    return { status: 404, body: { detail: 'Not Found' } };
  });
  return f;
}
const posted = (f, re) => f.calls.filter(c => (c.init.method === 'POST') && re.test(c.url));
const reqs = f => f.calls.map(c => (c.init.method || 'GET') + ' ' + c.url);
const eth = () => ({ request: async ({ method }) => method === 'eth_requestAccounts' ? ['0x' + '11'.repeat(20)] : '0x' + 'aa'.repeat(65) });
module.exports = { ROOT, WEB, build, threadText, enter, menu, buttons, find, press, toSample, sleep, serverDouble, identifierHash, posted, reqs, eth, APP, PID, ISS, TX, TX2, Ev, fakeFetch, vm };
