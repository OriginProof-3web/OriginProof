'use strict';
// 교차 검수에서 나온 회귀 시험의 공통 도구(가짜 DOM·fetch, 브라우저 아님).
const path = require('node:path'), fs = require('node:fs'), vm = require('node:vm');
const ROOT = path.join(__dirname, '..');
const WEB = path.join(ROOT, '페이지');
const { fakeFetch } = require(path.join(ROOT, '시험/가져온/regression/_load.js'));
const { makeDom, Ev } = require(path.join(ROOT, '시험/_dom.js'));
const FILES = ['data/sample_data.js', 'js/text_tools.js', 'js/op5_staff.js', 'js/adapter.js', 'js/chain_check.js', 'js/api_adapter.js', 'js/session.js', 'js/connection.js', 'js/op5_client.js'];
function load() {
  const sb = { console, setTimeout, clearTimeout, AbortController, AbortSignal, TextEncoder, URL, crypto: globalThis.crypto, Promise };
  sb.window = sb; sb.self = sb; vm.createContext(sb);
  for (const f of FILES) vm.runInContext(fs.readFileSync(path.join(WEB, f), 'utf8'), sb, { filename: f });
  return sb.Hk;
}
const REAL = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures_review/lookup_matched_real.json'), 'utf8'));   // test_r1a_lookup_contract.py 가 실제 ASGI 에서 받은 응답
function adapter(Hk, route) {
  const f = fakeFetch(route);
  const c = Hk.op5.createClient({ fetch: f, base: '/api', timeoutMs: 300 });
  return { f, a: Hk.createApiAdapter({ fetch: f, base: '/api', csrf: c.csrf, isDeleted: c.isDeleted, retain: () => ({}), loginWhy: '분석은 로그인이 필요해요.', timeoutMs: 300, pollMs: 5, pollLimitMs: 200 }) };
}
/* 실제 화면 스크립트 + 가짜 DOM(ai_analysis.test.js 의 page() 와 같은 조립). 브라우저 미검증 */
const HTML = fs.readFileSync(path.join(WEB, 'business.html'), 'utf8');
const SCRIPTS = [...HTML.matchAll(/<script src="((?:data|js)\/[^"]+)"><\/script>/g)].map(m => m[1]);
const INLINE = (() => { const i = HTML.indexOf('function selectAction'); return HTML.slice(HTML.lastIndexOf('<script>', i) + 8, HTML.indexOf('</script>', i)); })();
function page(route, extra) {
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
  win.fetch = fakeFetch(route);
  Object.assign(win, extra || {});
  for (const k of ['addEventListener', 'removeEventListener']) win[k] = win[k].bind(win);
  vm.createContext(win);
  vm.runInContext(INLINE, win);
  for (const f of SCRIPTS) vm.runInContext(fs.readFileSync(path.join(WEB, f), 'utf8'), win, { filename: f });
  return d;
}
const sleep = ms => new Promise(r => setTimeout(r, ms));
module.exports = { ROOT, WEB, load, adapter, page, sleep, fakeFetch, REAL, Ev };
