/* 글자 도구 (순수 함수만, 화면·저장소를 직접 만지지 않음).
   - 브라우저: window.Hk.text 로 씀
   - node: require('../js/text_tools.js') 로 시험(tools/text_tools.test.js, node --test)
   들어 있는 것: 개인정보 가림, 검증 링크·Proof ID 찾기, 결과 복사 글, 지난 기록 목록, 설정 정리. */
(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else { root.Hk = root.Hk || {}; root.Hk.text = api; }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  /* ------------------------------ 개인정보 가림 ------------------------------
     화면 기록(대화 말풍선)·보관(localStorage)·복사 글에 넣기 전에 씀.
     순서: 주민번호 -> 전화번호 -> 계좌번호(긴 숫자). 앞뒤가 영문·숫자·붙임표면 건드리지 않음
     (Proof ID 의 16진수, 링크 안 영문 섞인 값, 날짜 2026-10-19, 금액 85,000원은 그대로). */
  var MASK = {
    rrn: '(주민번호 가림)',
    phone: '(전화번호 가림)',
    account: '(계좌번호 가림)'
  };
  // 주민번호: 앞 6자리(생년월일 꼴) + 붙임표 + 뒤 7자리(첫 자리 1~8)
  var RRN_RE = /(?<![\w-])\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\s?[-–]?\s?[1-8]\d{6}(?![\w-])/g;
  // 전화번호: 휴대폰 01x, 지역번호 02·031~064, 070. +82 꼴도. 구분은 붙임표·점·빈칸·괄호 하나까지
  var PHONE_RE = /(?<![\w-])(?:\+82[-.\s]?|0)(?:1[016789]|2|[3-6][1-5]|70)\)?[-.\s]?\d{3,4}[-.\s]?\d{4}(?![\w-])/g;
  // 계좌·카드번호: 붙임표로 나뉜 숫자 묶음(합 10~16자리), 빈칸으로 나뉜 카드번호 4-4-4-4, 붙어 있는 10~16자리
  var ACCOUNT_GROUP_RE = /(?<![\w-])\d{2,6}(?:-\d{2,7}){1,4}(?![\w-])/g;
  var CARD_SPACE_RE = /(?<![\w-])\d{4}(?: \d{4}){3}(?![\w-])/g;
  var ACCOUNT_PLAIN_RE = /(?<![\w-])\d{10,16}(?![\w-])/g;

  function digitCount(s) { return (s.match(/\d/g) || []).length; }

  function maskPersonal(text) {
    if (typeof text !== 'string' || !text) return '';
    var out = text.replace(RRN_RE, MASK.rrn);
    out = out.replace(PHONE_RE, MASK.phone);
    out = out.replace(ACCOUNT_GROUP_RE, function (m) {
      var n = digitCount(m);      // 날짜 2026-10-19(8자리)·대표번호 1588-1234(8자리)는 그대로
      return n >= 10 && n <= 16 ? MASK.account : m;
    });
    out = out.replace(CARD_SPACE_RE, MASK.account);
    out = out.replace(ACCOUNT_PLAIN_RE, MASK.account);
    return out;
  }

  // 가림 뒤에도 남은 개인정보 꼴이 있는지(시험·방어용)
  function hasPersonal(text) {
    return maskPersonal(text) !== text;
  }

  /* ------------------------------ 검증 링크·Proof ID 찾기 ------------------------------ */
  var URL_RE = /\bhttps?:\/\/[^\s<>"'　]{1,300}/gi;
  /* Proof ID 형식은 OriginProof 스키마 그대로 `^prf_[A-Za-z0-9_-]+$` (대소문자 구별, 바꾸지 않음).
     근거: origin/integration·origin/phase/W5 packages/python/originproof_core/models.py:88·124,
     packages/schemas/generated/json/verification-request.schema.json:136, 예 prf_demo_001(fixtures/mvp/card_notice_valid.json:3).
     길이 상한 124자(스키마에는 없음, 화면 방어용). 더 길면 잘라 쓰지 않고 버림. */
  var PROOF_SRC = 'prf_[A-Za-z0-9_-]{1,124}(?![A-Za-z0-9_-])';
  var PROOF_RE = new RegExp('\\b' + PROOF_SRC, 'g');
  var PROOF_IN_URL_RE = new RegExp('(?:^|[^A-Za-z0-9_-])(' + PROOF_SRC + ')');
  var TRAIL_RE = /[.,;:!?)\]}>'"’”」』〉》]+$/;

  /* 붙여 넣은 원문에서 나온 차례대로 찾음. 링크 안에 Proof ID 가 있으면 링크 하나로 셈.
     돌려줌: [{ type:'link'|'proof', value, proofId, index }] */
  function findRefs(text) {
    if (typeof text !== 'string') return [];
    var refs = [];
    var spans = [];
    var m;
    URL_RE.lastIndex = 0;
    while ((m = URL_RE.exec(text))) {
      var url = m[0].replace(TRAIL_RE, '');
      if (!/^https?:\/\/[^/?#\s]+/i.test(url)) continue;     // 호스트가 없는 링크는 버림
      var p = PROOF_IN_URL_RE.exec(url);
      refs.push({ type: 'link', value: url, proofId: p ? p[1] : '', index: m.index });
      spans.push([m.index, m.index + url.length]);
    }
    PROOF_RE.lastIndex = 0;
    while ((m = PROOF_RE.exec(text))) {
      var at = m.index;
      var inside = spans.some(function (s) { return at >= s[0] && at < s[1]; });
      if (!inside) refs.push({ type: 'proof', value: m[0], proofId: m[0], index: at });
    }
    refs.sort(function (a, b) { return a.index - b.index; });
    // 같은 값이 여러 번 나오면 한 번만
    var seen = {};
    return refs.filter(function (r) {
      var k = r.type + ':' + r.value;
      if (seen[k]) return false;
      seen[k] = true;
      return true;
    });
  }

  /* ------------------------------ AI 근거 형광펜 (T2) ------------------------------
     화면 말풍선은 가린 글(maskPersonal)이라 원문 오프셋이 밀릴 수 있음.
     ① 원문[start:end] 가 quote 와 같고 가린 글의 같은 자리도 quote 면 그 자리,
     ② 아니면 가린 글에서 quote 를 찾음(처음 나온 곳), ③ 못 찾으면 칠하지 않음(지어내지 않음).
     돌려줌: [{ text, mark:boolean, role }] — 이어 붙이면 가린 글과 똑같음. */
  function highlightSegments(original, evidence) {
    var masked = maskPersonal(original);
    if (!masked) return [];
    var spans = [];
    (Array.isArray(evidence) ? evidence : []).forEach(function (ev) {
      if (!ev || typeof ev.quote !== 'string' || !ev.quote) return;
      var q = ev.quote;
      var a = ev.start_offset, b = ev.end_offset;
      var at = -1;
      if (typeof a === 'number' && typeof b === 'number' && original.slice(a, b) === q && masked.slice(a, b) === q) at = a;
      else at = masked.indexOf(q);
      if (at < 0) return;
      spans.push({ start: at, end: at + q.length, role: ev.role === 'risk' ? 'risk' : 'request' });
    });
    spans.sort(function (x, y) { return x.start - y.start; });
    var out = [];
    var pos = 0;
    spans.forEach(function (sp) {
      if (sp.start < pos) return;               // 겹치면 앞의 것만
      if (sp.start > pos) out.push({ text: masked.slice(pos, sp.start), mark: false });
      out.push({ text: masked.slice(sp.start, sp.end), mark: true, role: sp.role });
      pos = sp.end;
    });
    if (pos < masked.length) out.push({ text: masked.slice(pos), mark: false });
    return out;
  }

  /* ------------------------------ 결과 복사 글 ------------------------------
     결론·네 칸·다음 행동만. 원문(input.text)·AI 인용(AI 칸 본문)은 넣지 않고, 마지막에 한 번 더 가림. */
  function buildCopyText(answer) {
    if (!answer || !answer.conclusion) return '';
    var lines = [];
    lines.push('찐품명품 확인 결과' + (answer.sample ? ' (시안 · 예시 응답)' : ''));
    lines.push('');
    lines.push('결론: [' + answer.conclusion.badge.text + '] ' + answer.conclusion.text);
    lines.push('');
    (answer.axes || []).forEach(function (ax) {
      var line = '- ' + ax.name + ': ' + ax.status;
      // AI 칸 본문에는 받은 문자에서 따온 문장이 들어 있어 넣지 않음
      if (ax.axis !== 'ai' && ax.body) line += ' — ' + ax.body;
      lines.push(line);
    });
    lines.push('');
    if (answer.next_action && answer.next_action.text) lines.push('다음 행동: ' + answer.next_action.text);
    lines.push('');
    lines.push('받은 문자 원문은 넣지 않았어요. AI는 설명만 하고 발행 여부를 판정하지 않아요.');
    return maskPersonal(lines.join('\n'));
  }

  /* ------------------------------ 지난 기록 목록 ------------------------------
     항목: { id, date, title, tone, icon, label, text(가린 원문), sampleId(예시면 그 id, 아니면 '') }
     최신이 앞. 최대 max 개, 넘치면 가장 오래된 것(맨 뒤)부터 버림. */
  var HISTORY_MAX = 20;
  var TONES = ['ok', 'fail', 'caution', 'info', 'pending', 'none', 'offline'];
  var ICONS = ['check', 'warn', 'caution', 'info', 'question', 'dash', 'plug'];
  var DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

  /* 결과 스냅샷: 기록을 다시 볼 때 서버를 다시 부르지 않으려고 화면에 그린 답을 가린 채 보관.
     정해진 칸만 옮기고(모르는 키는 버림), 글자는 모두 maskPersonal 을 거치고 길이를 자름.
     tone·icon 은 허용 목록 밖이면 'none'·'dash'. 저장소에서 읽을 때도 이 함수를 다시 거침. */
  function s(v, max) { return typeof v === 'string' ? maskPersonal(v).slice(0, max || 600) : ''; }
  function arr(v, max) { return Array.isArray(v) ? v.slice(0, max || 40) : []; }
  function toneOf(t) { return TONES.indexOf(t) >= 0 ? t : 'none'; }
  function iconOf(i) { return ICONS.indexOf(i) >= 0 ? i : 'dash'; }
  function cleanSnapshot(a) {
    if (!a || typeof a !== 'object' || !a.conclusion || !Array.isArray(a.axes) || !Array.isArray(a.staff)) return null;
    var badge = a.conclusion.badge || {};
    var ref = a.ref && typeof a.ref === 'object' ? { type: a.ref.type === 'proof' ? 'proof' : 'link', value: s(a.ref.value, 300), proofId: s(a.ref.proofId, 140) } : null;
    return {
      id: s(a.id, 60), label: s(a.label, 40), sample: a.sample === true,
      assumption: s(a.assumption, 400),
      verification_status: typeof a.verification_status === 'string' ? s(a.verification_status, 40) : null,
      input: { kind: 'message', text: s(a.input && a.input.text, 4000) },
      ref: ref,
      conclusion: { badge: { tone: toneOf(badge.tone), icon: iconOf(badge.icon), text: s(badge.text, 40) }, text: s(a.conclusion.text, 400) },
      axes: arr(a.axes, 4).map(function (x) {
        var o = { axis: s(x && x.axis, 20), name: s(x && x.name, 40), status: s(x && x.status, 40), tone: toneOf(x && x.tone), icon: iconOf(x && x.icon), body: s(x && x.body, 600), staff: arr(x && x.staff, 7).map(function (v) { return s(v, 20); }) };
        if (x && x.note) o.note = s(x.note, 300);
        if (x && Array.isArray(x.compare)) o.compare = arr(x.compare, 4).map(function (c) { var r = { label: s(c && c.label, 40), value: s(c && c.value, 80) }; if (c && c.changed === true) r.changed = true; return r; });
        return o;
      }),
      next_action: { text: s(a.next_action && a.next_action.text, 400) },
      details: arr(a.details, 60).map(function (d) { return { label: s(d && d.label, 80), value: s(d && d.value, 600) }; }),
      staff: arr(a.staff, 7).map(function (o) {
        var r = { staff: s(o && o.staff, 20), name: s(o && o.name, 20), bubble_key: s(o && o.bubble_key, 60), line1: s(o && o.line1, 120), line2: s(o && o.line2, 300), shape: s(o && o.shape, 20), tone: toneOf(o && o.tone) };
        if (o && o.line3) r.line3 = s(o.line3, 120);
        return r;
      })
    };
  }

  function cleanEntry(e) {
    if (!e || typeof e !== 'object') return null;
    var text = typeof e.text === 'string' ? maskPersonal(e.text).slice(0, 4000) : '';
    var sampleId = typeof e.sampleId === 'string' && /^[a-z_]{1,40}$/.test(e.sampleId) ? e.sampleId : '';
    var snapshot = e.snapshot ? cleanSnapshot(e.snapshot) : null;
    if (!text && !sampleId && !snapshot) return null;
    var out = {
      id: typeof e.id === 'string' && /^[\w-]{1,40}$/.test(e.id) ? e.id : 'h' + Math.random().toString(36).slice(2, 10),
      date: typeof e.date === 'string' && DATE_RE.test(e.date) ? e.date : '',
      title: maskPersonal(String(e.title || '직접 붙여 넣은 내용')).slice(0, 60),
      tone: TONES.indexOf(e.tone) >= 0 ? e.tone : 'none',
      icon: ICONS.indexOf(e.icon) >= 0 ? e.icon : 'dash',
      label: String(e.label || '').slice(0, 20),
      text: text,
      sampleId: sampleId
    };
    if (snapshot) out.snapshot = snapshot;
    return out;
  }

  function addHistory(list, entry, max) {
    max = max || HISTORY_MAX;
    var e = cleanEntry(entry);
    var out = (Array.isArray(list) ? list : []).slice();
    if (!e) return out;
    out.unshift(e);
    while (out.length > max) out.pop();
    return out;
  }

  function removeHistory(list, id) {
    return (Array.isArray(list) ? list : []).filter(function (h) { return h.id !== id; });
  }

  // 저장소에서 읽은 값(문자열)을 믿지 않고 다시 정리함
  function parseHistory(raw, max) {
    max = max || HISTORY_MAX;
    var data;
    try { data = JSON.parse(raw); } catch (e) { return null; }
    if (!Array.isArray(data)) return null;
    return data.map(cleanEntry).filter(Boolean).slice(0, max);
  }

  // 기록 제목: 가린 원문 앞부분
  function titleFrom(maskedText) {
    var t = String(maskedText || '').replace(/\s+/g, ' ').trim();
    if (!t) return '직접 붙여 넣은 내용';
    return t.length > 24 ? t.slice(0, 24) + '…' : t;
  }

  /* ------------------------------ 설정 ------------------------------
     theme·reduce 가 null 이면 시스템 설정을 따름. panel 이 null 이면 화면 폭 기본값.
     serverUrl·mode 는 설정 화면의 서버 주소·"실제 서버 연결" 스위치(A3)가 씀. */
  var DEFAULT_SERVER = 'http://127.0.0.1:8000';
  var DEFAULT_SETTINGS = { large: false, reduce: null, theme: null, present: false, panel: null, serverUrl: DEFAULT_SERVER, mode: 'sample' };
  var MODES = ['sample', 'api'];   // sample: 예시로 보기, api: 실제 서버 연결(A3)

  // http(s) 주소만, 경로·쿼리·계정 정보 없이 "프로토콜://호스트[:포트]" 로 정리. 틀리면 ''
  function normalizeServerUrl(v) {
    if (typeof v !== 'string') return '';
    var s = v.trim();
    var m = s.match(/^(https?):\/\/([a-z0-9.-]{1,253}|\[[0-9a-f:]{2,39}\])(?::(\d{1,5}))?\/?$/i);
    if (!m) return '';
    if (m[3] && (+m[3] < 1 || +m[3] > 65535)) return '';
    return m[1].toLowerCase() + '://' + m[2].toLowerCase() + (m[3] ? ':' + (+m[3]) : '');
  }

  function normalizeSettings(raw) {
    var s = {};
    var src = raw && typeof raw === 'object' ? raw : {};
    s.large = src.large === true;
    s.present = src.present === true;
    s.reduce = src.reduce === true || src.reduce === false ? src.reduce : null;
    s.theme = src.theme === 'dark' || src.theme === 'light' ? src.theme : null;
    s.panel = src.panel === 'full' || src.panel === 'strip' ? src.panel : null;
    s.serverUrl = normalizeServerUrl(src.serverUrl) || DEFAULT_SERVER;
    s.mode = MODES.indexOf(src.mode) >= 0 ? src.mode : 'sample';
    return s;
  }

  function parseSettings(raw) {
    var data = null;
    try { data = JSON.parse(raw); } catch (e) { data = null; }
    return normalizeSettings(data);
  }

  /* ------------------------------ 저장소 (try/catch) ------------------------------
     storage 를 받아서 씀(브라우저는 localStorage, 시험은 가짜 객체). 실패하면 null/false. */
  var KEYS = { settings: 'jjin.settings.v1', history: 'jjin.history.v1' };

  function storageGet(storage, key) {
    try { return storage ? storage.getItem(key) : null; } catch (e) { return null; }
  }
  function storageSet(storage, key, value) {
    try { if (!storage) return false; storage.setItem(key, value); return true; } catch (e) { return false; }
  }

  return {
    MASK: MASK,
    maskPersonal: maskPersonal,
    hasPersonal: hasPersonal,
    findRefs: findRefs,
    highlightSegments: highlightSegments,
    buildCopyText: buildCopyText,
    HISTORY_MAX: HISTORY_MAX,
    addHistory: addHistory,
    removeHistory: removeHistory,
    parseHistory: parseHistory,
    cleanEntry: cleanEntry,
    cleanSnapshot: cleanSnapshot,
    titleFrom: titleFrom,
    DEFAULT_SERVER: DEFAULT_SERVER,
    DEFAULT_SETTINGS: DEFAULT_SETTINGS,
    normalizeServerUrl: normalizeServerUrl,
    normalizeSettings: normalizeSettings,
    parseSettings: parseSettings,
    KEYS: KEYS,
    storageGet: storageGet,
    storageSet: storageSet
  };
});
