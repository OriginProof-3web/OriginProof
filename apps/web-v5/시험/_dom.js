// 시험 도우미: 브라우저 없이 business.html 안쪽 스크립트와 5안 연결 스크립트를 돌려 볼 작은 가짜 DOM.
// 설치 없음. 필요한 기능만(요소 만들기·붙이기·글자·클래스·간단한 선택자·이벤트 capture/bubble).
'use strict';
let muted = true, mutations = 0;
const mut = () => { if (!muted) mutations++; };

class Ev {
  constructor(type, init) { this.type = type; this.bubbles = true; this.defaultPrevented = false; this._stop = false; this._now = false; Object.assign(this, init || {}); }
  preventDefault() { this.defaultPrevented = true; }
  stopPropagation() { this._stop = true; }
  stopImmediatePropagation() { this._stop = true; this._now = true; }
}
class Target {
  constructor() { this._l = []; }
  addEventListener(type, fn, cap) { this._l.push({ type, fn, cap: cap === true || (cap && cap.capture === true) }); }
  removeEventListener(type, fn) { this._l = this._l.filter(x => !(x.type === type && x.fn === fn)); }
  _fire(e, phase) {
    for (const x of this._l.slice()) {
      if (x.type !== e.type) continue;
      if (phase === 'cap' && !x.cap) continue;
      if (phase === 'bub' && x.cap) continue;
      e.currentTarget = this; x.fn.call(this, e);
      if (e._now) return;
    }
  }
}
class TextNode { constructor(t) { this.nodeType = 3; this.data = String(t); this.parent = null; } get textContent() { return this.data; } }
function parseSel(sel) { return sel.trim().match(/(?:[^\s\[]+|\[[^\]]*\])+/g).map(p => { const m = /^([a-z0-9-]*)((?:[#.][\w-]+)*)(?:\[([\w-]+)="([^"]*)"\])?$/i.exec(p); const o = { tag: m[1] || '', id: '', cls: [], attr: m[3] ? [m[3], m[4]] : null }; (m[2].match(/[#.][\w-]+/g) || []).forEach(t => t[0] === '#' ? (o.id = t.slice(1)) : o.cls.push(t.slice(1))); return o; }); }
function one(n, o) {
  if (!n || n.nodeType !== 1) return false;
  if (o.tag && n.tagName !== o.tag.toUpperCase()) return false;
  if (o.id && n.id !== o.id) return false;
  for (const c of o.cls) if (!n.className.split(/\s+/).includes(c)) return false;
  if (o.attr && n.getAttribute(o.attr[0]) !== o.attr[1]) return false;
  return true;
}
function matchSel(n, sel) {
  return sel.split(',').some(s => {
    const parts = parseSel(s);
    if (!one(n, parts[parts.length - 1])) return false;
    let i = parts.length - 2, p = n.parent;
    while (i >= 0 && p) { if (one(p, parts[i])) i--; p = p.parent; }
    return i < 0;
  });
}
class El extends Target {
  constructor(tag, doc) {
    super(); this.nodeType = 1; this.tagName = tag.toUpperCase(); this.children = []; this.parent = null; this._cls = ''; this._attrs = {}; this.dataset = {}; this.style = {};
    this.disabled = false; this._hidden = false; this.value = ''; this.type = ''; this.scrollTop = 0; this.scrollHeight = 0; this.ownerDocument = doc; this.files = [];
    const self = this;
    this.classList = { toggle(c, on) { const s = new Set(self._cls.split(/\s+/).filter(Boolean)); const want = on === undefined ? !s.has(c) : !!on; want ? s.add(c) : s.delete(c); self.className = [...s].join(' '); return want; }, add(c) { this.toggle(c, true); }, remove(c) { this.toggle(c, false); }, contains(c) { return self._cls.split(/\s+/).includes(c); } };
  }
  get className() { return this._cls; } set className(v) { if (v !== this._cls) { this._cls = String(v); mut(); } }
  get id() { return this._attrs.id || ''; } set id(v) { this._attrs.id = v; }
  get hidden() { return this._hidden; } set hidden(v) { if (!!v !== this._hidden) { this._hidden = !!v; mut(); } }
  setAttribute(k, v) { if (this._attrs[k] !== String(v)) { this._attrs[k] = String(v); mut(); } }
  getAttribute(k) { return k in this._attrs ? this._attrs[k] : null; }
  get childNodes() { return this.children; }
  get textContent() { return this.children.map(c => c.textContent).join(''); }
  set textContent(v) { this.children.forEach(c => (c.parent = null)); this.children = []; if (v !== '' && v != null) { const t = new TextNode(v); t.parent = this; this.children.push(t); } mut(); }
  append(...ns) { for (let n of ns) { if (typeof n === 'string') n = new TextNode(n); if (n.parent) n.parent.children = n.parent.children.filter(c => c !== n); n.parent = this; this.children.push(n); mut(); } }
  prepend(...ns) { for (let n of ns.reverse()) { n.parent = this; this.children.unshift(n); mut(); } }
  remove() { if (this.parent) { this.parent.children = this.parent.children.filter(c => c !== this); this.parent = null; mut(); } }
  replaceChildren(...ns) { this.children.forEach(c => (c.parent = null)); this.children = []; mut(); this.append(...ns); }
  all() { const out = []; const walk = n => n.children.forEach(c => { if (c.nodeType === 1) { out.push(c); walk(c); } }); walk(this); return out; }
  querySelectorAll(sel) { return this.all().filter(n => matchSel(n, sel)); }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
  matches(sel) { return matchSel(this, sel); }
  closest(sel) { let n = this; while (n && n.nodeType === 1) { if (matchSel(n, sel)) return n; n = n.parent; } return null; }
  focus() {} click() { this.dispatchEvent(new Ev('click')); }
  dispatchEvent(e) { return this.ownerDocument._dispatch(this, e); }
}
function makeDom(search) {
  const win = new Target();
  const doc = new Target();
  doc.documentElement = new El('html', doc); doc.documentElement.dataset = {};
  doc.body = new El('body', doc); doc.documentElement.append(doc.body);
  doc.createElement = t => new El(t, doc);
  doc.createTextNode = t => new TextNode(t);
  doc.getElementById = id => doc.documentElement.all().find(n => n.id === id) || null;
  doc.querySelectorAll = s => doc.documentElement.querySelectorAll(s);
  doc.querySelector = s => doc.documentElement.querySelector(s);
  doc._dispatch = (target, e) => {
    e.target = target;
    const path = []; for (let n = target; n; n = n.parent) path.push(n);
    const chain = [win, doc, ...path.slice().reverse()];
    for (const n of chain) { if (n === target) break; n._fire(e, 'cap'); if (e._stop) return !e.defaultPrevented; }
    target._fire(e, 'cap'); if (e._stop) return !e.defaultPrevented;
    target._fire(e, 'bub'); if (e._stop) return !e.defaultPrevented;
    for (const n of [...path.slice(1), doc, win]) { n._fire(e, 'bub'); if (e._stop) break; }
    return !e.defaultPrevented;
  };
  const store = () => { const m = {}; return { getItem: k => (k in m ? m[k] : null), setItem: (k, v) => { m[k] = String(v); }, removeItem: k => { delete m[k]; }, m }; };
  Object.assign(win, {
    document: doc, location: { search: search || '', protocol: 'http:', href: 'http://127.0.0.1/business.html' },
    localStorage: store(), sessionStorage: store(), matchMedia: () => ({ matches: false, addEventListener() {} }),
    Event: Ev, CustomEvent: class extends Ev { constructor(t, i) { super(t, i); } }, URLSearchParams, URL: { createObjectURL: () => 'blob:x', revokeObjectURL() {} }, Blob: class {},
    setTimeout, clearTimeout, console, Promise, AbortController, AbortSignal, TextEncoder, crypto: globalThis.crypto, JSON, Math, Date
  });
  win.window = win; win.self = win;
  win.dispatchEvent = e => { e.target = win; win._fire(e, 'cap'); if (!e._stop) win._fire(e, 'bub'); return true; };
  return { win, doc, El, Ev, arm() { muted = false; mutations = 0; }, disarm() { muted = true; }, mutations: () => mutations };
}
// 화면을 글로 펼침(첫 화면 비교용)
function snapshot(n) {
  if (n.nodeType === 3) return n.data;
  return '<' + n.tagName + ' ' + JSON.stringify(n._attrs) + ' c=' + n.className + (n.hidden ? ' hidden' : '') + (n.disabled ? ' disabled' : '') + '>' + n.children.map(snapshot).join('') + '</' + n.tagName + '>';
}
module.exports = { makeDom, snapshot, Ev };
