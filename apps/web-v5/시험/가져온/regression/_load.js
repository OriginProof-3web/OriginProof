// 시험 도우미: 직원 웹 스크립트를 브라우저 없이 node vm 에 싣고, 가짜 fetch·가짜 저장소를 만든다.
// 설치 없음(node 기본 모듈만). tools/*.test.js 가 씀.
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const WEB = path.resolve(__dirname, '../../../페이지');   // 5안: 가져온 스크립트는 페이지/js
const FIX = path.join(__dirname, '../../fixtures', 'originproof');   // 5안: 시험/fixtures 로 복사
const FILES = ['data/sample_data.js', 'js/text_tools.js', 'js/adapter.js', 'js/op5_staff.js', 'js/api_adapter.js', 'js/connection.js'];

function loadWeb() {
  const sandbox = { console, setTimeout, clearTimeout, AbortController, crypto: globalThis.crypto, Promise };
  sandbox.window = sandbox;
  sandbox.self = sandbox;
  vm.createContext(sandbox);
  for (const f of FILES) vm.runInContext(fs.readFileSync(path.join(WEB, f), 'utf8'), sandbox, { filename: f });
  return sandbox.Hk;
}

function fixture(name) {
  const d = JSON.parse(fs.readFileSync(path.join(FIX, name), 'utf8'));
  delete d._source;
  return d;
}

/* 가짜 fetch. route(url, init, n) 이 돌려주는 것:
   { status, body, headers, delay }  → 그 답
   { reject: 'TypeError' , delay }    → fetch 가 실패(서버 꺼짐·CORS 차단처럼)
   { hang: true }                     → 끝까지 답 없음(시간 초과 시험)
   calls 에 [url, init] 을 모두 남김 */
function fakeFetch(route) {
  const calls = [];
  const fn = (url, init) => {
    calls.push({ url, init: init || {}, body: init && init.body ? String(init.body) : '' });
    const r = route(url, init || {}, calls.length) || { status: 404, body: { detail: 'Not Found' } };
    return new Promise((resolve, reject) => {
      if (r.hang) return;
      setTimeout(() => {
        if (r.reject) return reject(new TypeError(r.reject));
        const headers = Object.assign({}, r.headers || {});
        const text = r.raw != null ? r.raw : JSON.stringify(r.body == null ? null : r.body);
        resolve({ status: r.status, headers: { get: h => { for (const k of Object.keys(headers)) if (k.toLowerCase() === h.toLowerCase()) return headers[k]; return null; } }, text: () => Promise.resolve(text) });
      }, r.delay || 0);
    });
  };
  fn.calls = calls;
  return fn;
}

function memStorage() {
  const mem = {};
  return { mem, getItem: k => (k in mem ? mem[k] : null), setItem: (k, v) => { mem[k] = String(v); }, removeItem: k => { delete mem[k]; } };
}

// 시험용 개인정보(모두 지어낸 값)
const PII = { mobile: '010-1234-5678', account: '110-123-456789', rrn: '900101-1234567' };
function noRaw(assert, s, where) {
  for (const v of Object.values(PII)) assert.ok(!String(s).includes(v), where + ' 에 원문 개인정보가 남음: ' + v);
}

const CODE_RE = /\b[A-Z][A-Z0-9_]{2,}\b/;
const BANNED = ['안' + '전', '사' + '기'];
// 화면에 바로 보이는 글(자세히·말풍선 2줄 빼고)
function visibleTexts(a) {
  const out = [a.conclusion.text, a.conclusion.badge.text, a.next_action.text];
  a.axes.forEach(ax => {
    out.push(ax.name, ax.status, ax.body, ax.note || '');
    (ax.compare || []).forEach(c => out.push(c.label, c.value));
  });
  a.staff.forEach(st => out.push(st.line1, st.line3 || '', st.shape));
  return out;
}

module.exports = { loadWeb, fixture, fakeFetch, memStorage, PII, noRaw, CODE_RE, BANNED, visibleTexts, WEB, FIX };
