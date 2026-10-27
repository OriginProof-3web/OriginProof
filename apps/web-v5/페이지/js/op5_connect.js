/* 5안 화면 연결 (business.html 에 이미 있는 칸·단추에 기능만 붙임).
   - 디자인 변경 없음: 새 CSS 클래스·카드·패널·단추 자리 없음. 결과는 기존 말풍선(.msg-user/.msg-ai .bubble) 모양,
     AI 말풍선 안 단추는 기존 '＋ 파일 추가' 단추 모양(.add-btn), 모드 칩은 기존 '연결 전' 칩 모양(.tag-offline),
     직원 칩은 기존 .st 상태(대기·확인 중·확인됨·연결 전 + 같은 모양 '문제 찾음').
   - 첫 화면은 그대로: 이 파일은 불러올 때 DOM·문구를 바꾸지 않고 이벤트만 붙임(서버도 부르지 않음).
     ?demo=장면 이 있을 때만 캡처용 장면을 재현함(js/op5_scenes.js, 가짜 응답·저장소에 안 남김).
   - 왼쪽 사이드바(business.bundle.js)는 고치지 않음: 메뉴는 그 번들이 보내는 'originproof-action' 이벤트,
     도움말·검색칸은 바깥에서 이벤트로 받음.
   - 입력칸·보내기: business.html 안쪽 스크립트의 '연결 전' 답 대신 이 파일이 답하도록, 같은 이벤트를 먼저(capture) 받아 처리. */
(function () {
  'use strict';
  var Hk = window.Hk;
  if (!Hk || !Hk.op5 || !Hk.text || !Hk.createConnection) return;
  var T = Hk.text, O = Hk.op5;
  var $ = function (id) { return document.getElementById(id); };
  var thread = $('chatThread'), scroll = $('chatScroll'), input = $('chatInput'), form = $('composer'), hint = $('composerHint');
  if (!thread || !input || !form) return;

  var Q = new URLSearchParams(location.search);
  var S = Hk.op5scenes;
  var scene = S && S.valid(Q.get('demo')) ? Q.get('demo') : '';
  var fileMode = location.protocol === 'file:' && !scene;

  /* ---------------- 저장소(장면이면 메모리만) ---------------- */
  function memStore() { var m = {}; return { getItem: function (k) { return k in m ? m[k] : null; }, setItem: function (k, v) { m[k] = String(v); }, removeItem: function (k) { delete m[k]; } }; }
  function safe(name) { try { var s = window[name]; s.getItem('op5'); return s; } catch (e) { return memStore(); } }
  var LS = scene ? memStore() : safe('localStorage');
  var SS = scene ? memStore() : safe('sessionStorage');
  var store = Hk.createSettingsStore(LS);
  var BASE_KEY = 'op5.apiBase', RETAIN_KEY = 'op5.retain';
  function getBase() { var v = T.storageGet(LS, BASE_KEY); var p = v ? O.parseBase(v) : null; return p && p.ok ? p.value : '/api'; }
  var retain = (function () { try { var r = JSON.parse(T.storageGet(LS, RETAIN_KEY) || '{}'); return { report: r.report === true, original: r.original === true }; } catch (e) { return { report: false, original: false }; } })();
  function saveRetain() { T.storageSet(LS, RETAIN_KEY, JSON.stringify(retain)); }
  if (scene) { store.get().mode = S.mode(scene); store.save(); }
  else if (Q.get('mode') === 'api' || Q.get('mode') === 'sample') { store.get().mode = Q.get('mode'); store.save(); }

  var fetchFn = scene ? S.fetchFor(scene) : function (u, i) { return window.fetch(u, i); };
  var ethFn = scene ? function () { return S.ethereum(scene); } : function () { return window.ethereum; };
  var client, wallet, conn;
  function rebuild() {
    client = O.createClient({ fetch: fetchFn, base: getBase(), opStore: SS, fileMode: fileMode, timeoutMs: 25000 });
    wallet = O.createWallet({ client: client, ethereum: ethFn });
    conn = Hk.createConnection({
      store: store, fetch: fetchFn,
      createApi: function (o) {
        var a = Hk.createApiAdapter({
          fetch: fetchFn, base: getBase(), csrf: client.csrf, retain: function () { return retain; }, isDeleted: client.isDeleted,
          loginWhy: '분석은 로그인이 필요해요. 왼쪽 메뉴 기관 상태에서 로그인 화면을 열어 주세요.',
          timeoutMs: 25000, pollMs: scene ? 30 : 2000
        });
        a.serverUrl = o.serverUrl;
        return a;
      },
      checkConnection: function () { return client.health(); }
    });
  }
  rebuild();
  function isApi() { return conn.mode() === 'api'; }

  /* ---------------- 말풍선 (기존 모양 그대로) ---------------- */
  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function toBottom() { scroll.scrollTop = scroll.scrollHeight; }
  function clearEmpty() { var e = $('chatEmpty'); if (e) e.remove(); }
  function userMsg(text) {
    clearEmpty();
    var m = el('div', 'msg msg-user');
    m.append(el('div', 'bubble', text));
    thread.append(m); toBottom();
  }
  function modeTag() { return scene ? '장면 재현 · 가짜 응답' : isApi() ? '실서버 모드' : '예시 모드'; }
  /* AI 말풍선: para(제목, 줄들) 로 글 묶음, btn(글, 할 일) 로 기존 모양 단추 */
  function aiMsg(tag) {
    clearEmpty();
    var m = el('div', 'msg msg-ai');
    var w = el('div', 'who');
    w.append(el('i', null, '✓'), el('span', null, 'OriginProof AI'), el('span', 'tag-offline', tag || modeTag()));
    var b = el('div', 'bubble');
    m.append(w, b); thread.append(m); toBottom();
    var api = {
      box: b,
      para: function (title, lines) {
        var p = el('p');
        api.set(p, title, lines);
        b.append(p); toBottom();
        return p;
      },
      set: function (p, title, lines) {
        p.replaceChildren();
        if (title) { p.append(el('b', null, title)); if (lines && lines.length) p.append(el('br')); }
        (lines || []).forEach(function (l, i) { if (i) p.append(el('br')); p.append(document.createTextNode(String(l))); });
        toBottom();
      },
      line: function (p, text) { if (p.childNodes.length) p.append(el('br')); p.append(document.createTextNode(String(text))); toBottom(); },
      btn: function (label, fn) {
        var x = el('button', 'add-btn', label);
        x.type = 'button';
        x.addEventListener('click', function () {
          if (x.disabled) return;
          x.disabled = true;
          Promise.resolve().then(function () { return fn(x); }).catch(function () { say('처리 중 오류가 났어요. 다시 해 주세요.'); }).then(function () { if (!x.dataset.done) x.disabled = false; });
        });
        b.append(x); toBottom();
        return x;
      }
    };
    return api;
  }
  function say(text, title) { var r = aiMsg(); r.para(title || null, [text]); return r; }
  function codeLine(e) { return e && e.code ? '코드: ' + e.code + (e.status ? ' · HTTP ' + e.status : '') + (e.retryAfter != null ? ' · Retry-After ' + e.retryAfter + '초' : '') : ''; }
  function errLines(res) { var e = client.say(res); return [e.text, codeLine(e)].filter(Boolean); }

  /* ---------------- 오른쪽 직원 7칩 (기존 .st 모양) ---------------- */
  var IDS = ['intake', 'ledger', 'signature', 'original', 'status', 'ai', 'report'];
  var LABEL = { wait: '대기', run: '확인 중', ok: '확인됨', off: '연결 전', bad: '문제 찾음' };
  var CLS = { wait: 'st st-wait', run: 'st st-run', ok: 'st st-ok', off: 'st st-off', bad: 'st st-run' };
  var firstWhere = null, finished = {};
  function rows() { return Array.prototype.slice.call(document.querySelectorAll('#staffList li.staff')); }
  function chip(id, state, where, final) {
    var li = rows()[IDS.indexOf(id)];
    if (!li) return;
    var st = li.querySelector('.st'), w = li.querySelector('.staff-where');
    if (!st) return;
    st.className = CLS[state]; st.textContent = LABEL[state];
    if (where != null && w) w.textContent = where;
    if (final || state === 'ok' || state === 'off' || state === 'bad') finished[id] = 1; else delete finished[id];
    var c = $('staffCount'); if (c) c.textContent = Object.keys(finished).length + '/7';
  }
  function resetStaff(note) {
    if (!firstWhere) firstWhere = rows().map(function (li) { var w = li.querySelector('.staff-where'); return w ? w.textContent : ''; });
    finished = {};
    IDS.forEach(function (id, i) { chip(id, 'run', firstWhere[i] || ''); });
    var n = $('staffNote'); if (n && note) n.textContent = note;
  }
  // 응답 모양 → 기존 칩 5가지. '보류'·'해당 없음' 칩은 화면에 없어(자리 없음) 대기 칩 + 아래 줄 사유 글로 보여 줌
  function stateOf(tone) { return tone === 'ok' || tone === 'info' ? 'ok' : tone === 'fail' || tone === 'caution' ? 'bad' : tone === 'offline' ? 'off' : 'wait'; }
  function chipObs(o) { if (o && IDS.indexOf(o.staff) >= 0) chip(o.staff, stateOf(o.tone), o.line1 || '', true); }
  function animateStaff(list, done) {
    var reduce = matchMedia('(prefers-reduced-motion: reduce)').matches || !!scene;
    var i = 0;
    (function next() {
      if (i >= list.length) { if (done) done(); return; }
      chipObs(list[i++]);
      if (reduce) next(); else setTimeout(next, 220);
    })();
  }

  /* ---------------- 첨부: 업로드 경로가 없어 '연결 전' 유지 ---------------- */
  function attachedNames() { return Array.prototype.slice.call(document.querySelectorAll('#fileList .file .fname')).map(function (x) { return x.textContent; }); }

  /* ---------------- 결과 그리기: 블록체인 결정 / AI 설명 두 구역 ---------------- */
  /* 4축 보고서(3회차 멘토링 C-4 4): 왼쪽 '블록체인 결정(사실)' / 오른쪽 'AI 위험 설명(맥락)'.
     값은 응답(axes·ai_report) 그대로이고, 없는 값(수법 ID 등)은 지어내지 않고 '연결 전'으로 둔다. */
  function opRow(x) {
    var row = el('div', 'op-row');
    row.append(el('b', null, x.name), el('span', 'op-chip t-' + (x.tone || 'none'), x.status), el('span', 'op-body', x.body));
    return row;
  }
  /* 근거 위치(형광펜): 예시(ai_report.evidence, role)·실서버(계약 AnalysisReport.evidence, source RULE/LLM) 모두
     Hk.api.evidenceSpans 로 계산 — 코드포인트 위치를 UTF-16 으로 바꾸고, 범위 밖·역순·quote 불일치·겹침은 칠하지 않음.
     보고서가 없는 예전 모양이면 AI 칸 문구의 따옴표 안 문장을 글에서 (한 번만 나올 때) 찾음. */
  var NO_SPANS = { spans: [], skipped: [] };
  function isRisky(a, ai) {
    var rep = a.ai_report;
    return rep ? (rep.risk_level === 'HIGH' || rep.risk_level === 'CAUTION') : !!ai && (ai.tone === 'fail' || ai.tone === 'caution');
  }
  function riskSpans(a, ai, text) {
    var calc = Hk.api && Hk.api.evidenceSpans;
    if (!calc || !text || !isRisky(a, ai)) return NO_SPANS;
    var rep = a.ai_report;
    if (rep && Array.isArray(rep.evidence) && rep.evidence.length) {
      return calc(text, rep.evidence.map(function (e) { return e && e.role === 'request' ? null : e; }));   // 예시 자료의 '요청' 문장은 안 칠함
    }
    var qs = [], m = ai && ai.body ? String(ai.body).match(/["“]([^"”]{2,200})["”]/g) : null;
    (m || []).forEach(function (q) { qs.push({ quote: q.slice(1, -1) }); });
    return calc(text, qs);
  }
  var SRC = { RULE: ['규칙 검사', 'info'], LLM: ['AI 모델', 'none'] };     // 기존 칩 모양(.op-chip.t-info / .t-none) 재사용
  function srcOf(s) { return SRC[s] || ['출처 미상', 'none']; }
  function markedText(text, spans) {
    var box = el('div', 'op-quote'), at = 0;
    spans.forEach(function (sp) {
      if (sp.start > at) box.append(document.createTextNode(text.slice(at, sp.start)));
      var mk = el('mark', null, text.slice(sp.start, sp.end));
      if (sp.source === 'RULE' || sp.source === 'LLM') mk.setAttribute('title', '근거 ' + (sp.index + 1) + ' · ' + srcOf(sp.source)[0]);
      box.append(mk); at = sp.end;
    });
    box.append(document.createTextNode(text.slice(at)));
    return box;
  }
  // 근거 한 줄씩(계약 모양만, 예시 자료는 그리지 않음): 근거 n · [규칙 검사|AI 모델] · "문장" · 규칙 번호 · 위치 못 칠한 사유
  function evidenceRows(zone, a, res) {
    var rep = a.ai_report, ev = rep && !a.sample && Array.isArray(rep.evidence) ? rep.evidence : [];
    var why = {}, W = (Hk.api && Hk.api.SPAN_WHY) || {};
    res.skipped.forEach(function (s) { why[s.index] = s.reason; });
    ev.forEach(function (e, i) {
      if (!e || typeof e.quote !== 'string') return;
      var s = srcOf(e.source);
      zone.append(opRow({ name: '근거 ' + (i + 1), status: s[0], tone: s[1],
        body: '“' + T.maskPersonal(e.quote).slice(0, 120) + '”' + (e.rule_id ? ' · 규칙 번호 ' + e.rule_id : '') + (why[i] ? ' · 위치 표시 안 함(' + (W[why[i]] || why[i]) + ')' : '') }));
    });
    if (rep && rep.dropped) zone.append(el('p', 'op-tech', '모양이 틀린 근거 ' + rep.dropped + '건은 그리지 않았어요.'));
  }
  function chainButton(zone, a) {
    var out = el('p', 'op-foot');
    var b = el('button', 'add-btn', '내 브라우저에서 체인 직접 대조하기');
    b.type = 'button';
    b.title = 'OriginProof 서버를 거치지 않고 블록체인 RPC 에 직접 물어 서버 응답과 같은지 비교해요';
    b.addEventListener('click', function () {
      if (!Hk.chain) { out.textContent = '체인 확인 도구를 불러오지 못했어요.'; return; }
      b.disabled = true; out.textContent = '체인에 직접 묻는 중…';
      Hk.chain.verify({ answer: a, settings: Hk.chain.createStore(LS).get(), fetch: function (u, i) { return window.fetch(u, i); } }).then(function (res) {
        out.replaceChildren(el('b', null, '[' + res.shape + '] ' + res.headline), el('br'), document.createTextNode(res.body));
        (res.rows || []).forEach(function (x) { out.append(el('br'), document.createTextNode('· ' + x.label + (x.server != null ? ': 서버 ' + x.server + ' / 체인 ' + x.chain : ''))); });
        (res.links || []).forEach(function (l) { var k = el('a', null, l.label); k.href = l.href; k.target = '_blank'; k.rel = 'noopener noreferrer'; out.append(el('br'), k); });
      }).then(function () { b.disabled = false; toBottom(); });
    });
    zone.append(b, out);
  }
  function renderReport(r, a) {
    var c = a.conclusion || { badge: { text: '', tone: 'none' }, text: '' };
    var axes = Array.isArray(a.axes) ? a.axes : [];
    var ai = axes.filter(function (x) { return x.axis === 'ai'; })[0];
    var wrap = el('div', 'op-report');

    var fact = el('section', 'op-zone op-fact');
    fact.setAttribute('aria-label', '블록체인 결정');
    fact.append(el('span', 'op-zone-tag', 'Blockchain & Crypto Core'), el('h4', null, '블록체인 결정 · 사실'));
    // 종합 결론(사실+맥락)은 두 구역 위에 한 줄로
    var concl = el('p', 'op-concl');
    concl.append(el('b', null, '종합 '), el('span', 'op-chip t-' + (c.badge.tone || 'none'), c.badge.text || '-'), document.createTextNode(' ' + (c.text || '')));
    r.box.append(concl);
    axes.filter(function (x) { return x.axis !== 'ai'; }).forEach(function (x) { fact.append(opRow(x)); });
    fact.append(el('p', 'op-foot', '이 영역은 AI 없이 기관 서명과 블록체인 기록만으로 판정해요. ①공식 발행 ②원본 일치 ③현재 상태'));
    chainButton(fact, a);

    var aiz = el('section', 'op-zone op-ai');
    aiz.setAttribute('aria-label', 'AI 위험 설명');
    aiz.append(el('span', 'op-zone-tag', '규칙·AI 위험 분석 · 서버 분석기·RAG 연결 전'), el('h4', null, 'AI 위험 설명 · 맥락'));
    if (ai) aiz.append(opRow(ai));
    var text = a.input && typeof a.input.text === 'string' ? a.input.text : '';
    var sp = riskSpans(a, ai, text);
    evidenceRows(aiz, a, sp);
    if (text) aiz.append(el('p', 'op-tech', sp.spans.length ? '받은 글에서 위험 요구 문장을 칠했어요' : '받은 글'), markedText(text, sp.spans));
    var ids = a.ai_report && Array.isArray(a.ai_report.matched_technique_ids) ? a.ai_report.matched_technique_ids : null;
    if (sp.spans.length || sp.skipped.some(function (s) { return s.reason !== 'NO_QUOTE'; })) aiz.append(el('p', 'op-tech', ids && ids.length ? '일치한 공개 피싱 수법: ' + ids.join(', ') : '공개 피싱 수법 ID: 수법 지식베이스(RAG) 연결 전'));
    aiz.append(el('p', 'op-foot', (ai && ai.note ? ai.note + ' ' : '') + '이 영역은 규칙과 AI가 메시지가 요구하는 행동의 위험을 설명만 해요. 진위 판정과 분리돼요. 확률 숫자는 쓰지 않아요.'));

    wrap.append(fact, aiz);
    r.box.append(wrap); toBottom();
  }

  function renderAnswer(a) {
    var r = aiMsg();
    renderReport(r, a);
    if (a.next_action && a.next_action.text) r.para('다음 행동', [a.next_action.text]);
    if (a.sample) r.para(null, ['예시 응답이에요. ' + (a.assumption || '')]);
    var files = attachedNames();
    if (files.length) r.para(null, ['첨부 ' + files.length + '개는 서버로 보내지 않았어요. 첨부 업로드는 아직 연결 전이에요(서버 계약에 업로드 경로 없음).']);
    if (a.analysis_id && !a.analysis_deleted) {
      r.para('보관', ['분석 번호 ' + a.analysis_id + ' · 상태 ' + (a.analysis_status || '-'), '보고서 ' + (retain.report ? '7일 보관' : '끝난 뒤 10분만 보관') + ' · 원본 ' + (retain.original ? '7일 보관' : '처리 직후 삭제')]);
      if (a.analysis_status === 'COMPLETED') r.btn('보고서 받기', function () { return downloadReport(a.analysis_id); });
      if (retain.original && a.analysis_status === 'COMPLETED') r.btn('원본 받기', function () { return downloadOriginal(a.analysis_id); });
      r.btn('이 분석 지우기', function (x) { return removeAnalysis(a.analysis_id, x); });
    }
    r.btn('자세히 보기', function (x) {
      x.dataset.done = '1';
      var d = aiMsg();
      d.para('자세히', (a.details || []).map(function (row) { return row.label + ': ' + row.value; }));
    });
  }

  /* ---------------- 입력 → 결과 ---------------- */
  var running = {};       // 같은 모드·같은 글이 진행 중이면 다시 보내지 않음
  var awaiting = null;    // 말풍선이 입력을 기다리는 중(초안·거래 해시·철회·주소)
  function check(text) {
    var key = conn.mode() + '|' + text;
    if (running[key]) { say('같은 내용을 이미 확인하고 있어요. 결과가 나오면 여기에 보여 드려요.'); return running[key]; }
    if (hint) hint.textContent = 'Enter 보내기 · Shift+Enter 줄바꿈 · ' + (isApi() ? '실서버 모드(' + getBase() + ')' : '예시 모드(예시 응답)');
    resetStaff(isApi() ? '직원 7명이 실제 응답이 온 순서대로 표시해요.' : '예시 모드: 예시 응답을 직원 순서대로 보여 줘요.');
    var api = isApi();
    var p = conn.check(text, { onStaff: api ? chipObs : null }).then(function (a) {
      return new Promise(function (resolve) {
        animateStaff(Array.isArray(a.staff) ? a.staff : [], function () {
          var n = $('staffNote');
          if (n) n.textContent = api ? '실제 응답이 온 순서대로 갱신했어요. 판정은 서버 값 그대로예요.' : '예시 응답이에요. 서버에 보내지 않았어요.';
          renderAnswer(a); resolve(a);
        });
      });
    }, function (e) {
      IDS.forEach(function (id) { chip(id, 'wait'); });
      say(e && e.userMessage ? e.userMessage : '입력을 확인하지 못했어요.');
    }).then(function (x) { delete running[key]; return x; }, function (x) { delete running[key]; throw x; });
    running[key] = p;
    return p;
  }
  function submit() {
    var v = Hk.validateInput(input.value);
    if (!v.ok) { if (input.value.trim()) say(v.message); return null; }
    input.value = '';
    input.dispatchEvent(new Event('input'));     // 안쪽 스크립트의 높이·보내기 단추 상태 갱신
    var w = awaiting;
    if (w) { awaiting = null; userMsg(w.mask ? w.mask(v.text) : T.maskPersonal(v.text)); return w.handle(v.text); }
    userMsg(T.maskPersonal(v.text));
    return check(v.text);
  }
  function ask(kind, prompt, handle, mask) {
    awaiting = { kind: kind, handle: handle, mask: mask };
    var r = aiMsg();
    r.para(null, [prompt, '취소하려면 아래 단추를 누르세요.']);
    r.btn('입력 취소', function (x) { x.dataset.done = '1'; if (awaiting && awaiting.kind === kind) { awaiting = null; say('입력을 취소했어요.'); } });
    input.focus();
    return r;
  }

  // 안쪽 스크립트보다 먼저 받기(capture): Enter·보내기 단추·한글 조합 끝
  var composeSend = false;
  window.addEventListener('keydown', function (e) {
    if (e.target !== input || e.key !== 'Enter' || e.shiftKey) return;
    e.stopImmediatePropagation();
    if (e.isComposing || e.keyCode === 229) { composeSend = true; return; }
    e.preventDefault(); submit();
  }, true);
  window.addEventListener('compositionend', function (e) {
    if (e.target !== input || !composeSend) return;
    e.stopImmediatePropagation(); composeSend = false; setTimeout(submit, 0);
  }, true);
  window.addEventListener('submit', function (e) {
    if (e.target !== form) return;
    e.preventDefault(); e.stopImmediatePropagation(); submit();
  }, true);

  /* ---------------- 보관/삭제 ---------------- */
  function save(name, text, type) {
    try {
      var url = URL.createObjectURL(new Blob([text], { type: type }));
      var a = document.createElement('a'); a.href = url; a.download = name; a.hidden = true;
      document.body.append(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 2000);
      return true;
    } catch (e) { return false; }
  }
  function downloadReport(id) {
    return client.report(id).then(function (res) {
      if (res.ignored) return say('지운 분석이라 늦게 온 응답은 버렸어요.');
      if (res.status !== 200) return aiMsg().para('보고서 받기', errLines(res));
      save(id + '-report.json', JSON.stringify(res.data, null, 2), 'application/json');
      say('보고서를 내려받았어요(' + id + '-report.json).');
    });
  }
  function downloadOriginal(id) {
    return client.original(id).then(function (res) {
      if (res.ignored) return say('지운 분석이라 늦게 온 응답은 버렸어요.');
      if (res.status !== 200) return aiMsg().para('원본 받기', errLines(res));
      save(id + '.txt', res.text || '', 'text/plain;charset=utf-8');
      say('원본을 내려받았어요(' + id + '.txt).');
    });
  }
  function removeAnalysis(id, btn) {
    if (btn && btn.dataset.confirm !== '1') { btn.dataset.confirm = '1'; btn.textContent = '정말 지울까요? 한 번 더 누르기'; return; }
    if (btn) btn.dataset.done = '1';
    return client.removeAnalysis(id).then(function (res) {
      if (res.status === 204) return say('분석 ' + id + ' 를 지웠어요. 이 분석에 늦게 오는 응답은 쓰지 않고 버려요.');
      aiMsg().para('지우기', errLines(res).concat(['이 화면에서는 지운 것으로 보고 늦은 응답을 버려요.']));
    });
  }
  function retainButtons(r) {
    var p = r.para('보관 선택(다음 분석부터)', [retainText()]);
    r.btn('보고서 보관 켜기/끄기', function () { retain.report = !retain.report; saveRetain(); r.set(p, '보관 선택(다음 분석부터)', [retainText()]); });
    r.btn('원본 보관 켜기/끄기', function () { retain.original = !retain.original; saveRetain(); r.set(p, '보관 선택(다음 분석부터)', [retainText()]); });
  }
  function retainText() { return 'retain_report ' + (retain.report ? '켬(7일)' : '끔(끝난 뒤 10분)') + ' · retain_original ' + (retain.original ? '켬(7일)' : '끔(처리 직후 삭제)'); }
  function showAnalyses() {
    if (!isApi()) return exampleOnly('내 확인 기록(보관한 분석)');
    var r = aiMsg();
    var p = r.para('내 확인 기록(GET /v3/analyses)', ['불러오는 중…']);
    return client.listAnalyses().then(function (res) {
      if (res.status !== 200 || !res.data || !Array.isArray(res.data.items)) return r.set(p, '내 확인 기록', errLines(res));
      var items = res.data.items.filter(function (x) { return x && O.RE.ana.test(String(x.analysis_id)) && !client.isDeleted(x.analysis_id); });
      if (!items.length) return r.set(p, '내 확인 기록', ['보관 중인 분석이 없어요. 보관을 켜고 분석하면 여기에 남아요(보고서 7일).']);
      r.set(p, '내 확인 기록', items.slice(0, 5).map(function (x) {
        return x.analysis_id + ' · ' + x.status + ' · 보고서 ' + (x.retain_report ? '보관' : '-') + ' · 원본 ' + (x.retain_original ? '보관' : '-') + (x.result_expires_at ? ' · 보고서 기한 ' + when(x.result_expires_at) : '');
      }).concat(items.length > 5 ? ['… 외 ' + (items.length - 5) + '건'] : []));
      items.slice(0, 5).forEach(function (x) {
        if (x.retain_report) r.btn('보고서 받기 ' + x.analysis_id, function () { return downloadReport(x.analysis_id); });
        if (x.retain_original) r.btn('원본 받기 ' + x.analysis_id, function () { return downloadOriginal(x.analysis_id); });
        r.btn('지우기 ' + x.analysis_id, function (b) { return removeAnalysis(x.analysis_id, b); });
      });
    });
  }
  function when(sec) { try { return new Date(sec * 1000).toLocaleString('ko-KR'); } catch (e) { return String(sec); } }

  /* ---------------- 왼쪽 메뉴 → 말풍선 대화 ---------------- */
  function modeButtons(r) {
    r.btn(isApi() ? '예시 모드로 바꾸기' : '실서버 모드로 바꾸기', function (x) {
      x.dataset.done = '1';
      conn.setMode(isApi() ? 'sample' : 'api');
      say(isApi() ? '실서버 모드로 바꿨어요. 연결 주소 ' + getBase() + ' 로 보내요.' : '예시 모드로 바꿨어요. 서버에 보내지 않고 예시 응답만 보여요.');
    });
  }
  function exampleOnly(what) {
    var r = aiMsg();
    r.para(what, ['지금은 예시 모드라 서버에 보내지 않아요. 실서버 모드에서 실제 서버로 보내요.']);
    modeButtons(r);
    return r;
  }
  /* 기관 화면 보강(3회차 멘토링 C-1 4)·C-2 3)②): 승인 주체 역할 이름, 가스비 배지(지금은 기관 지갑 부담, 서버 중계는 향후 확장), 참여 효과 숫자 카드.
     실제 승인 현황·통계 API 가 아직 없어서 예시 모드에서만 진행 상태·숫자를 '예시'로 표시하고, 실서버 모드에서는 지어내지 않음. */
  var APPROVERS = [
    { n: '승인 노드 #1', who: '공공·도메인 검증원 (KISA 모델)', what: '도메인(.go.kr)과 발송 자격 확인' },
    { n: '승인 노드 #2', who: '금융·산업 자율규제원 (금융보안원 모델)', what: '법인 실체와 담당자 공문 확인' },
    { n: '승인 노드 #3', who: '통신·인프라 보안 컨소시엄', what: '기관 공개키 보유 증명과 발신번호 확인' }
  ];
  function govPanel(r) {
    var ex = !isApi();
    var box = el('div', 'op-gov');
    box.append(el('b', null, '기관 활성화 · 2-of-3 공동승인' + (ex ? ' (예시 진행)' : '')));
    APPROVERS.forEach(function (a, i) {
      var row = el('div', 'op-gov-row');
      var st = ex ? (i === 0 ? ['서명 완료 1/3', 't-ok'] : i === 1 ? ['서명 완료 2/3 → 기관 활성화', 't-ok'] : ['대기 (정족수 달성으로 불필요)', 't-none']) : ['승인 현황 연결 전', 't-offline'];
      row.append(el('span', 'op-gov-n', a.n), el('span', 'op-gov-who', a.who), el('span', 'op-chip ' + st[1], st[0]), el('span', 'op-body', a.what));
      box.append(row);
    });
    box.append(el('p', 'op-foot', '서로 다른 3곳 중 2곳이 각자 지갑으로 서명해야 기관이 활성화돼요. 긴급 정지는 1곳 단독, 재활성화·키 교체는 2-of-3이에요.' + (ex ? ' 기관 이름은 역할 모델이며 실제 기관이 참여한 것은 아니에요.' : ' 실제 승인 현황(/v3/proposals) 화면은 아직 연결 전이에요.')));
    r.box.append(box); toBottom();
  }
  function roiPanel(r) {
    var box = el('div', 'op-roi');
    [['이번 달 공식 발행 증명', '1,240건'], ['사칭·변조 방어', '87건'], ['추정 콜센터 문의 절감', '약 4,350,000원']].forEach(function (c) {
      var card = el('div', 'op-roi-card'); card.append(el('span', null, c[0]), el('b', null, c[1])); box.append(card);
    });
    var wrap = el('div'); wrap.append(el('b', null, '참여 효과'), box, el('p', 'op-foot', '예시 수치예요(실제 통계 아님). 절감액은 문의 1건당 3,500원 기준으로 계산해요. 통계 API 가 생기면 실제 값으로 바뀌어요.'));
    r.box.append(wrap); toBottom();
  }
  function gasBadges(r) {
    var row = el('div', 'op-badges');
    row.append(el('span', 'op-badge', 'EIP-712 기관 서명'), el('span', 'op-badge', '가스비: 지금은 기관 지갑이 부담 · 중계자 대납(Relayer)은 향후 확장'), el('span', 'op-badge', '기대 효과(설명): 비대면 금융사고 자율배상·면책 판단 때 증빙 자료로 활용'));
    r.box.append(row);
    r.para(null, ['기관 지갑이 서명한 뒤 그 지갑에서 거래를 직접 보내고 가스비도 내요. 서버 중계자(Relayer)가 대신 보내고 가스비를 내는 방식은 지금 꺼져 있어요(향후 확장).']);
  }

  function showStatus() {
    var r = aiMsg();
    r.para('연결 설정', ['지금 모드: ' + (isApi() ? '실서버 모드' : '예시 모드'), '연결 주소: ' + getBase() + (getBase() === '/api' ? ' (같은 출처 프록시)' : ''), retainText()]);
    var h = r.para('서버 상태(/health/live · /health/ready)', ['확인 중…']);
    var who = r.para('로그인', ['확인 중…']);
    modeButtons(r);
    r.btn('연결 다시 확인', function () { return showStatus(); });
    r.btn('연결 주소 바꾸기', function () {
      ask('base', '새 연결 주소를 입력칸에 넣고 보내 주세요. 같은 출처 경로(예: /api) 또는 이 컴퓨터 주소(예: http://127.0.0.1:8000)만 받아요.', function (t) {
        var b = O.parseBase(t);
        if (!b.ok) return say(b.message);
        T.storageSet(LS, BASE_KEY, b.value); rebuild();
        say('연결 주소를 ' + b.value + ' 로 바꿨어요.' + (/^https?:/.test(b.value) ? ' 다른 주소는 서버가 이 화면 주소를 허용(CORS·Origin)해야 해요.' : ''));
      });
    });
    r.btn('보관 선택 바꾸기', function () { retainButtons(aiMsg()); });
    govPanel(r);
    roiPanel(r);
    var pending = [client.health().then(function (x) {
      r.set(h, '서버 상태(/health/live · /health/ready)', ['live: ' + x.live.text + ' (' + x.live.code + ')', 'ready: ' + x.ready.text + ' (' + x.ready.code + ')']);
    })];
    pending.push(client.me().then(function (res) {
      if (res.status !== 200 || !res.data) {
        r.set(who, '로그인', errLines(res).concat(['로그인은 로그인 화면(login.html)에서 해요. 비밀번호는 이 대화에 쓰지 마세요.']));
        r.btn('로그인 화면 열기', function (x) { x.dataset.done = '1'; location.href = 'login.html?next=business.html'; });
        return;
      }
      var me = res.data;
      r.set(who, '로그인', [String(me.username) + ' · 역할 ' + String(me.role) + (me.issuer_id ? ' · 기관 ' + String(me.issuer_id) : '')]);
      r.btn('로그아웃', function (x) { x.dataset.done = '1'; return client.logout().then(function (o) { say(o.status === 200 ? '로그아웃했어요.' : errLines(o).join(' ')); }); });
      if (me.role !== 'issuer') return;
      var iss = r.para('기관 상태(/v1/issuer/status · 신청)', ['확인 중…']);
      return Promise.all([client.get('/v1/issuer/status'), client.get('/v1/issuer-applications/mine')]).then(function (z) {
        var lines = [];
        if (z[0].status === 200 && z[0].data) lines.push('기관 ' + z[0].data.issuer_id + ' · 상태 ' + z[0].data.status + ' · 체인 ' + z[0].data.chain_id);
        else lines = lines.concat(errLines(z[0]));
        if (z[1].status === 200 && z[1].data) lines.push('신청 ' + z[1].data.application_id + ' · ' + z[1].data.issuer_name + ' · ' + z[1].data.status);
        else if (z[1].status === 200) lines.push('기관 신청 기록이 없어요.');
        else lines = lines.concat(errLines(z[1]));
        r.set(iss, '기관 상태(/v1/issuer/status · 신청)', lines);
      });
    }));
    return Promise.all(pending);
  }
  function stepLine(r, p) { return function (s) { r.line(p, (s.ok ? '✓ ' : '✕ ') + s.text + (s.ok ? '' : (s.code ? ' (코드: ' + s.code + (s.data && s.data.status ? ' · HTTP ' + s.data.status : '') + ')' : ''))); }; }
  function needWallet(r) { var w = ethFn(); if (!w || typeof w.request !== 'function') { r.para('지갑 필요', ['이 브라우저에는 지갑(window.ethereum)이 없어요. 서명은 기관 지갑에서만 하고, 서버에는 개인키를 보내지 않아요.']); return true; } return false; }
  function txButton(r, sr, kind) {
    r.btn('지갑에서 보낸 거래 해시 알리기', function (x) {
      x.dataset.done = '1';
      ask('tx', '지갑에서 보낸 거래 해시(0x + 64자리)를 입력칸에 넣고 보내 주세요. 같은 서명 요청 ' + sr.signing_request_id + ' 에 붙여요.', function (t) {
        var rr = aiMsg(); var p = rr.para('거래 해시 알림(signing-requests/{id}/transactions)', []);
        return wallet.submitTx(sr.signing_request_id, t, kind).then(function (res) { stepLine(rr, p)(res); if (res.ok) opButtons(rr, res.data.op); });
      });
    });
  }
  function opButtons(r, op) {
    if (!op || !O.RE.op.test(String(op.operation_id))) return;
    r.btn('작업 상태 조회 ' + op.operation_id, function () { return showOperation(op.operation_id); });
    if (op.status === 'UNKNOWN' || op.status === 'SUBMITTED' || op.next_action === 'RECONCILE') r.btn('복구 조회(reconcile) ' + op.operation_id, function () { return reconcileOp(op.operation_id); });
  }
  function showOperation(id) {
    return client.operation(id).then(function (res) {
      var r = aiMsg();
      if (res.status !== 200 || !res.data) return r.para('작업 ' + id, errLines(res));
      var op = res.data; client.track(op, 'lookup');
      r.para('작업 ' + id, ['상태 ' + op.status + ' · 다음 ' + op.next_action + (op.error_code ? ' · 코드 ' + op.error_code : '') + (op.tx_hash ? ' · 거래 ' + op.tx_hash.slice(0, 12) + '…' : ''),
        op.status === 'UNKNOWN' ? '결과가 불명확해요. 다시 보내지 말고 복구 조회(reconcile)로 기존 거래부터 확인해요.' : op.next_action === 'RESIGN' ? '서명 기한이 지나 새로 서명해야 해요.' : '']);
      opButtons(r, op);
    });
  }
  function reconcileOp(id) {
    return client.reconcile(id).then(function (res) {
      var r = aiMsg();
      if (res.status < 200 || res.status >= 300 || !res.data) return r.para('복구 조회 ' + id, errLines(res));
      client.track(res.data, 'reconcile');
      r.para('복구 조회 ' + id, ['상태 ' + res.data.status + ' · 다음 ' + res.data.next_action + (res.data.error_code ? ' · 코드 ' + res.data.error_code : '')]);
    });
  }
  var SAMPLE_DRAFT = function () {
    var now = Math.floor(Date.now() / 1000);
    return JSON.stringify({ doc_key: '0x' + '0'.repeat(63) + '1', expected_version: 1, expires_at: now + 30 * 86400,
      content: { notice_type: 'OFFICIAL_DOCUMENT', institution_code: '기관 코드', document_type: '안내문', document_number: 'DOC-0001', title: '합성 시험 안내', summary: '합성 시험용 안내문입니다.' } }, null, 2);
  };
  function startIssue() {
    var r = aiMsg();
    r.para('새 Proof 발행(기관 지갑)', ['1. 발행 초안 보내기(document-drafts)', '2. 지갑에서 Publish 서명(EIP-712)', '3. 서명 제출(publications) → 작업 번호', '4. 지갑에서 보낸 거래 해시 알리기(signing-requests/{id}/transactions)', '5. 작업 확인 — UNKNOWN 이면 다시 보내지 않고 복구 조회(reconcile)']);
    gasBadges(r);
    if (!isApi()) { r.para(null, ['예시 모드라 서버에 보내지 않아요.']); modeButtons(r); return; }
    if (needWallet(r)) return;
    r.btn('예시 초안을 입력칸에 넣기', function () { input.value = SAMPLE_DRAFT(); input.dispatchEvent(new Event('input')); input.focus(); });
    r.btn('초안 보내기 시작', function (x) {
      ask('draft', '발행 초안 JSON({doc_key, expected_version, expires_at, content})을 입력칸에 넣고 보내 주세요. request_id 는 화면이 붙여요.', function (t) {
        var d = O.parseDraft(t, Math.floor(Date.now() / 1000));
        if (!d.ok) return say(d.message);
        var rr = aiMsg(); var p = rr.para('발행 진행', []);
        return wallet.publish(d.body, stepLine(rr, p)).then(function (res) {
          if (res.ok && res.sr) { opButtons(rr, res.data.op); txButton(rr, res.sr, 'publish'); }
        });
      }, function (t) { return T.maskPersonal(t); });
    });
  }
  function showKeys() {
    var r = aiMsg();
    var p = r.para('공개키 관리(GET /v1/issuer/keys)', [isApi() ? '불러오는 중…' : '예시 모드라 서버에 보내지 않아요.']);
    if (!isApi()) { modeButtons(r); return; }
    var start = function () {
      if (needWallet(r)) return;
      r.btn('지갑 키 증명 시작(key-challenges → key-proofs)', function (x) {
        x.dataset.done = '1';
        var rr = aiMsg(); var q = rr.para('지갑 키 증명', []);
        return wallet.keyProof(stepLine(rr, q));
      });
    };
    return client.get('/v1/issuer/keys').then(function (res) {
      if (res.status !== 200 || !Array.isArray(res.data)) r.set(p, '공개키 관리', errLines(res));
      else r.set(p, '공개키 관리', res.data.length ? res.data.slice(0, 8).map(function (k) { return String(k.key_id).slice(0, 14) + '… · ' + k.status + (k.selected ? ' · 사용 중' : '') + ' · ' + String(k.signer).slice(0, 10) + '…'; }) : ['등록된 키가 없어요.']);
      start();
    });
  }
  function showProofs(proofId) {
    var r = aiMsg();
    if (!isApi()) { r.para('발행 목록', ['예시 모드라 서버에 보내지 않아요.']); modeButtons(r); return; }
    if (proofId) {
      if (!O.RE.prf.test(String(proofId))) return r.para('발행 기록', ['Proof ID 형식이 맞지 않아요.']);
      var q = r.para('발행 기록 ' + proofId, ['불러오는 중…']);
      return client.get('/v2/proofs/' + proofId).then(function (res) {
        r.set(q, '발행 기록 ' + proofId, res.status === 200 && res.data ? [JSON.stringify(res.data).slice(0, 400)] : errLines(res));
      });
    }
    var p = r.para('발행 목록(GET /v2/issuer/proofs)', ['불러오는 중…']);
    return client.get('/v2/issuer/proofs').then(function (res) {
      if (res.status !== 200 || !Array.isArray(res.data)) r.set(p, '발행 목록', errLines(res));
      else r.set(p, '발행 목록', res.data.length ? res.data.slice(0, 8).map(function (x) { return x.proof_id + ' · ' + x.proof_type + ' · 등록 ' + x.registration_status + ' · 만료 ' + x.expires_at; }) : ['발행한 Proof 가 없어요.']);
      r.para(null, ['v3 지갑 발행 문서는 목록 경로가 없어 문서 ID로 찾아요(왼쪽 발행 기록 검색칸에 0x… 입력).']);
      if (needWallet(r)) return;
      r.btn('철회 시작(revoke-drafts → revocations)', function () {
        ask('revoke', '철회할 문서 ID(0x + 64자리)와 버전을 "0x… 2" 처럼 입력칸에 넣고 보내 주세요.', function (t) {
          var d = O.parseRevoke(t);
          if (!d.ok) return say(d.message);
          var rr = aiMsg(); var pp = rr.para('철회 진행', []);
          return wallet.revoke(d.body, stepLine(rr, pp)).then(function (res) { if (res.ok && res.sr) { opButtons(rr, res.data.op); txButton(rr, res.sr, 'revoke'); } });
        });
      });
    });
  }
  function showOps() {
    var r = aiMsg();
    var ops = client.readOps();
    r.para('이 탭에서 만든 지갑 작업(v3)', ops.length ? ops.slice(0, 5).map(function (o) { return o.operation_id + ' · ' + o.kind + ' · ' + o.status + ' · 다음 ' + o.next_action; }) : ['아직 없어요.']);
    ops.slice(0, 3).forEach(function (o) { opButtons(r, o); });
    r.btn('내 확인 기록(보관한 분석) 보기', function () { return showAnalyses(); });
    r.btn('보관 선택 바꾸기', function () { retainButtons(aiMsg()); });
    if (!isApi()) { r.para(null, ['예시 모드라 서버 작업 목록은 부르지 않아요.']); modeButtons(r); return; }
    var p = r.para('서버 작업 이력(GET /v1/operations)', ['불러오는 중…']);
    return client.get('/v1/operations?limit=5').then(function (res) {
      if (res.status !== 200 || !Array.isArray(res.data)) return r.set(p, '서버 작업 이력', errLines(res));
      r.set(p, '서버 작업 이력(v1)', res.data.length ? res.data.map(function (o) { return o.operation_id + ' · ' + o.action + ' · ' + o.status + ' · 다음 ' + o.next_action; }) : ['작업이 없어요.']);
    });
  }
  function showHelp() {
    var r = aiMsg();
    r.para('도움말', [
      '· 입력칸: 받은 문자·검증 링크·Proof ID 를 붙여 넣고 Enter. 문서 ID 는 {"document_id":"0x…","version":1} 처럼 넣어요.',
      '· 기관 상태: 연결 모드·주소, 서버 상태, 로그인, 기관 상태',
      '· 새 Proof 발행 / 발행 목록(철회) / 공개키 관리(키 증명): 기관 지갑 단계를 대화로 진행',
      '· 작업 이력: 지갑 작업 상태·복구 조회, 내 확인 기록(보관·내려받기·지우기)',
      '· 발행 기록 검색칸: 0x…(문서 ID)·prf_…·ana_…·op_… 를 넣고 Enter',
      '· 첨부: 이 브라우저 안에만 있어요. 서버 업로드는 아직 연결 전이에요.',
      '자기 기관 상태, 공개키 관리, Proof 발행·목록과 작업 이력을 확인할 수 있습니다.'
    ]);
    r.btn('예시 문자를 입력칸에 넣기', function () {
      var list = Hk.sampleAdapter.list();
      if (list[0]) { input.value = list[0].input.text; input.dispatchEvent(new Event('input')); input.focus(); }
    });
    modeButtons(r);
  }
  function search(q) {
    var s = String(q || '').trim().slice(0, 140);
    if (!s) return;
    userMsg('발행 기록 검색: ' + T.maskPersonal(s));
    if (!isApi()) return exampleOnly('발행 기록 검색');
    var r = aiMsg(), path = null, title = '발행 기록 검색';
    if (/^0x[0-9a-fA-F]{64}$/.test(s)) { path = '/v3/documents/' + s.toLowerCase(); title = '문서 ' + s.slice(0, 10) + '…'; }
    else if (O.RE.prf.test(s)) path = '/v2/proofs/' + s;
    else if (O.RE.ana.test(s)) path = '/v3/analyses/' + s;
    else if (O.RE.op.test(s)) return showOperation(s);
    if (!path) return r.para(title, ['찾을 수 있는 것: 문서 ID(0x + 64자리)·Proof ID(prf_…)·분석 번호(ana_…)·작업 번호(op_…)']);
    if (O.RE.ana.test(s) && client.isDeleted(s)) return r.para(title, ['지운 분석이에요.']);
    var p = r.para(title, ['찾는 중…']);
    return client.get(path).then(function (res) {
      if (res.status !== 200 || !res.data) return r.set(p, title, errLines(res));
      var d = res.data;
      if (d.document_id && d.state) r.set(p, title, ['상태 ' + d.state + ' · 버전 ' + d.version + '/' + d.latest_version + (d.warnings && d.warnings.length ? ' · 경고 ' + d.warnings.join(', ') : '') + ' · 원본 ' + (d.original_available ? '있음' : '없음')]);
      else if (d.analysis_id) r.set(p, title, [d.analysis_id + ' · ' + d.status + (d.error_code ? ' · 코드 ' + d.error_code : '')]);
      else r.set(p, title, [JSON.stringify(d).slice(0, 400)]);
    });
  }

  var MENU = { issue: startIssue, status: showStatus, keys: showKeys, proofs: showProofs, operations: showOps };
  window.addEventListener('originproof-action', function (e) {
    var d = e && e.detail ? e.detail : {};
    var fn = MENU[d.key];
    if (!fn) return;
    if (d.key === 'proofs' && d.proofId) return showProofs(d.proofId);
    fn();
  });
  // 도움말: 번들의 알림창 대신 말풍선(바깥에서 먼저 받음, 번들 파일은 그대로)
  document.addEventListener('click', function (e) {
    var b = e.target && e.target.closest ? e.target.closest('#sidebar-root button') : null;
    if (!b || b.textContent.trim() !== '도움말') return;
    e.preventDefault(); e.stopPropagation();
    showHelp();
  }, true);
  // 발행 기록 검색칸: Enter 로 찾기(번들은 Escape 만 다룸)
  document.addEventListener('keydown', function (e) {
    var t = e.target;
    if (e.key !== 'Enter' || e.isComposing || !t || !t.matches || !t.matches('#sidebar-root input[aria-label="최근 확인 검색"]')) return;
    e.preventDefault();
    search(t.value);
  });

  // 장면 재현(캡처용)에서만 쓰는 손잡이
  var ui = { submitText: function (t) { input.value = t; return submit(); }, menu: function (k) { return MENU[k](); }, showAnalyses: showAnalyses, removeAnalysis: removeAnalysis, client: function () { return client; } };
  if (scene) setTimeout(function () { S.run(scene, ui); }, 0);
})();
