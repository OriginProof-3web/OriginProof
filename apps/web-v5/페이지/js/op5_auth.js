/* 5안 로그인/로그아웃 단추와 비회원·회원 구분.
   - 비회원: 예시 확인(예시 8개)·첨부 사전 검사·화면 기능은 그대로 쓴다.
   - 회원(로그인): 정확한 확인(실제 서버의 기관 기록 대조)과 AI 분석을 쓴다. 서버도 로그인 없이는 401로 막는다(계약 그대로).
   세션은 GET /api/v1/auth/me 로만 판단하고, 비밀번호는 이 화면에서 받지 않는다(로그인 화면 user-login.html 에서 입력). */
(function (root) {
  'use strict';
  var Hk = (root.Hk = root.Hk || {});
  var state = { member: false, me: null, checked: false };
  var LOGIN = 'login.html?next=business.html', SIGNUP = 'join.html';
  var GUEST_KEY = 'op5.guestSample', ORG_ONLY = ['새 Proof 발행', '공개키 관리', '발행 목록'];
  var authBtn = null;
  function guestMark(v) { try { if (v) root.localStorage.setItem(GUEST_KEY, '1'); else if (root.localStorage.getItem(GUEST_KEY)) { root.localStorage.removeItem(GUEST_KEY); return true; } } catch (e) {} return false; }
  var demo = !!(Hk.op5scenes && Hk.op5scenes.valid(new URLSearchParams(location.search).get('demo')));
  var served = /^https?:$/.test(location.protocol) && !demo;

  function me() {
    if (!served) return Promise.resolve(null);  // 파일로 연 화면은 서버가 없으니 비회원
    return fetch('/api/v1/auth/me', { credentials: 'same-origin', headers: { Accept: 'application/json' } })
      .then(function (r) { return r.ok ? r.json() : null; }, function () { return null; });
  }

  // 로그인 확인은 한 번만 하고, 모드 판단은 이 결과가 나온 뒤에 한다(확인 전에 회원을 예시 모드로 되돌리지 않음)
  var checked = me().then(function (u) {
    state.checked = true; state.member = !!(u && u.username); state.me = u; return u;
  });

  // 정확한 확인(실서버 모드)은 회원만: 연결 모드 바꾸기를 가로채 비회원이면 막고 안내한다
  var origCreate = Hk.createConnection;
  if (!demo && typeof origCreate === 'function') {
    Hk.createConnection = function (opts) {
      var c = origCreate(opts), set = c.setMode;
      if (typeof set === 'function') c.setMode = function (m) {
        if (m === 'api' && state.checked && !state.member) { notice('정확한 확인(기관 기록과 실제로 대조)은 로그인 뒤에 쓸 수 있어요.'); return c.mode ? c.mode() : 'sample'; }
        return set.apply(c, arguments);
      };
      // 확인이 끝났는데 비회원이면(확인 중에 바꾼 경우 포함) 예시 모드로 되돌린다
      // 비회원 때 머문 예시 모드는 로그인 뒤 실서버로 되돌린다. 회원이 직접 고른 예시 모드와 ?mode=sample 은 그대로 둔다.
      checked.then(function () {
        if (!set || !c.mode) return;
        if (!state.member) { guestMark(true); if (c.mode() === 'api') set.call(c, 'sample'); return; }
        if (guestMark(false) && c.mode() !== 'api' && new URLSearchParams(location.search).get('mode') !== 'sample') set.call(c, 'api');
      });
      return c;
    };
  }

  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  var noticed = false;
  function notice(text) {
    var thread = document.getElementById('chatThread'); if (!thread) return;
    var empty = document.getElementById('chatEmpty'); if (empty) empty.remove();
    var m = el('div', 'msg msg-ai'), w = el('div', 'who');
    w.append(el('i', null, '✓'), el('span', null, 'OriginProof AI'), el('span', 'tag-offline', '비회원'));
    var b = el('div', 'bubble');
    b.append(el('p', 'auth-p', text), el('p', 'auth-p', '회원가입 없이도 예시 확인과 첨부 파일 검사는 그대로 쓸 수 있어요.'));
    var row = el('div', 'auth-row'), a1 = el('a', 'auth-link auth-link-main', '로그인'), a2 = el('a', 'auth-link', '회원가입');
    a1.href = LOGIN; a2.href = SIGNUP; row.append(a1, a2); b.append(row);
    m.append(w, b); thread.append(m);
    var sc = document.getElementById('chatScroll'); if (sc) sc.scrollTop = sc.scrollHeight;
  }

  function paint(btn) {
    btn.textContent = state.member ? '로그아웃' : '로그인';
    btn.title = state.member ? (state.me && state.me.username ? state.me.username + ' 로그아웃' : '로그아웃') : '로그인 화면으로';
    btn.setAttribute('aria-label', btn.title);
    btn.dataset.member = state.member ? '1' : '0';
  }

  // 세션이 끊기면 다시 불러오기 전에도 단추를 로그인으로 바꾼다
  function expired() {
    if (!state.member) return;
    state.member = false; state.me = null; guestMark(true);
    if (authBtn) paint(authBtn);
  }

  // 기관이 아닌 계정(개인·운영자)에는 기관 전용 메뉴를 숨긴다(권한은 서버가 따로 막음). 메뉴가 다시 그려져도 유지.
  // 맨 위 '새 Proof 발행' 자리는 숨기지 않고 '새 대화'(빈 확인 화면)로 바꿔 씀 — 번들 디자인 그대로
  var NEW_PAGE = '새 대화';
  function relabel(node, from, to) {
    for (var i = 0; i < node.childNodes.length; i++) {
      var c = node.childNodes[i];
      if (c.nodeType === 3 && c.nodeValue.trim() === from) { c.nodeValue = to; return true; }
      if (c.nodeType === 1 && relabel(c, from, to)) return true;
    }
    return false;
  }
  function hideOrgMenu() {
    var side = document.getElementById('sidebar-root'); if (!side) return;
    function apply() {
      side.querySelectorAll('button').forEach(function (b) {
        var t = b.textContent.trim();
        if (t === ORG_ONLY[0]) { relabel(b, t, NEW_PAGE); b.setAttribute('aria-label', NEW_PAGE); return; }
        if (ORG_ONLY.indexOf(t) >= 0 && b.style.display !== 'none') b.style.display = 'none';
      });
    }
    apply();
    if (root.MutationObserver) new MutationObserver(apply).observe(side, { childList: true, subtree: true });
  }

  // 사이드바 아래(모든 역할 공통, 대표 지시 2026-11-04): 워크스페이스 메뉴의 '워크스페이스 설정'·'로그아웃'을 밖으로 꺼내
  // 도움말 위에 한 줄씩, 도움말에도 아이콘. 워크스페이스 메뉴의 '새 워크스페이스'·'팀원 초대'는 뺀다. 번들 클래스만 씀.
  var ICONS = {   // lucide 아이콘 경로(번들과 같은 모양)
    settings: ['M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z', 'circle:12,12,3'],
    logout: ['m16 17 5-5-5-5', 'M21 12H9', 'M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4'],
    login: ['m10 17 5-5-5-5', 'M15 12H3', 'M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4'],
    help: ['circle:12,12,10', 'M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3', 'M12 17h.01']
  };
  function icon(name, size) {
    var NS = 'http://www.w3.org/2000/svg', svg = document.createElementNS(NS, 'svg');
    [['width', size], ['height', size], ['viewBox', '0 0 24 24'], ['fill', 'none'], ['stroke', 'currentColor'], ['stroke-width', '2'], ['stroke-linecap', 'round'], ['stroke-linejoin', 'round'], ['aria-hidden', 'true']].forEach(function (kv) { svg.setAttribute(kv[0], String(kv[1])); });
    ICONS[name].forEach(function (d) {
      var n;
      if (d.indexOf('circle:') === 0) { var c = d.slice(7).split(','); n = document.createElementNS(NS, 'circle'); n.setAttribute('cx', c[0]); n.setAttribute('cy', c[1]); n.setAttribute('r', c[2]); }
      else { n = document.createElementNS(NS, 'path'); n.setAttribute('d', d); }
      svg.appendChild(n);
    });
    return svg;
  }
  var ROW = 'sidebar-row relative flex h-8 w-full items-center rounded-[8px] px-2 text-left transition-[background-color,transform] duration-150 hover:bg-hover-2 active:scale-[0.98]';
  function row(key, label, ic, onClick) {
    var b = el('button', ROW); b.type = 'button'; b.dataset.op5Foot = key; b.setAttribute('aria-label', label);
    var i = el('span', 'flex size-5 shrink-0 items-center justify-center text-ink-2'); i.appendChild(icon(ic, 18));
    b.append(i, el('span', 'sidebar-copy ml-1.5 min-w-0 flex-1 truncate text-[14px] font-medium text-ink-2', label));
    b.addEventListener('click', onClick);
    return b;
  }
  function logout(btn) {
    if (!state.member) { location.href = LOGIN; return; }
    if (btn) btn.disabled = true;
    fetch('/api/v1/auth/logout', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': (state.me && state.me.csrf_token) || '' }, body: '{}' })
      .then(function () { location.reload(); }, function () { if (btn) btn.disabled = false; notice('로그아웃하지 못했어요. 잠시 뒤 다시 눌러 주세요.'); });
  }
  var WS_DROP = ['새 워크스페이스', '워크스페이스 설정', '팀원 초대', '로그아웃'];
  function sideFooter() {
    var side = document.getElementById('sidebar-root'); if (!side) return;
    function apply() {
      var help = null;
      side.querySelectorAll('button').forEach(function (b) { if (!b.dataset.op5Foot && b.textContent.trim() === '도움말') help = b; });
      if (!help || !help.parentNode) return;
      if (!help.dataset.op5Icon) { help.dataset.op5Icon = '1'; help.insertBefore(icon('help', 15), help.firstChild); }
      var box = help.parentNode;
      if (!box.querySelector('[data-op5-foot]')) {
        box.insertBefore(row('settings', '워크스페이스 설정', 'settings', function () { if (root.selectAction) root.selectAction('settings'); }), help);
        box.insertBefore(row('auth', '로그아웃', 'logout', function (e) { logout(e.currentTarget); }), help);
        help.classList.add('mt-1');
      }
      var a = box.querySelector('[data-op5-foot="auth"]');
      if (a && a.dataset.member !== (state.member ? '1' : '0')) {   // 비로그인은 같은 자리에 '로그인'
        var label = state.member ? '로그아웃' : '로그인';
        a.dataset.member = state.member ? '1' : '0'; a.setAttribute('aria-label', label);
        a.firstChild.replaceChildren(icon(state.member ? 'logout' : 'login', 18)); a.lastChild.textContent = label;
      }
    }
    // 워크스페이스 메뉴(번들이 body 에 붙임): 빼거나 밖으로 옮긴 줄과 구분선 숨김
    function trimMenu() {
      document.querySelectorAll('[data-workspace-menu]').forEach(function (m) {
        m.querySelectorAll('button').forEach(function (b) { if (WS_DROP.indexOf(b.textContent.trim()) >= 0) b.hidden = true; });
        m.querySelectorAll('div.h-px').forEach(function (d) { d.hidden = true; });
      });
    }
    apply();
    if (root.MutationObserver) {
      new MutationObserver(apply).observe(side, { childList: true, subtree: true });
      new MutationObserver(trimMenu).observe(document.body, { childList: true });
    }
    return apply;
  }

  // 휴대폰 폭에서는 메뉴를 처음부터 접는다(접기 단추는 번들 것을 그대로 씀)
  function foldNarrow(left) {
    if (!root.matchMedia || !root.matchMedia('(max-width:760px)').matches) return;
    var c = document.querySelector('#sidebar-root .sidebar-collapse-control');
    if (c) c.click(); else if (left > 0) setTimeout(function () { foldNarrow(left - 1); }, 100);
  }

  function start() {
    foldNarrow(20);
    var btn = authBtn = document.getElementById('authBtn'); if (!btn) return;
    paint(btn);
    var foot = null;
    try { foot = sideFooter(); } catch (e) { foot = null; }   // 사이드바 꾸미기가 실패해도 로그인 처리는 계속
    // 비로그인도 개인 화면과 같은 메뉴(기관 전용 메뉴 숨김). ?demo= 시연 화면만 예전 그대로
    checked.then(function () { paint(btn); if (foot) { try { foot(); } catch (e) {} } if (!demo && !(state.me && state.me.role === 'issuer')) hideOrgMenu(); });
    btn.addEventListener('click', function () { logout(btn); });
    // 비회원이 처음 확인을 보내면(대화에 내 말풍선이 생기면) 결과 뒤에 한 번만 회원 기능을 알려 준다
    var thread = document.getElementById('chatThread');
    if (thread && root.MutationObserver) {
      var ob = new MutationObserver(function (list) {
        if (state.member || noticed) return;
        for (var i = 0; i < list.length; i++) for (var j = 0; j < list[i].addedNodes.length; j++) {
          var n = list[i].addedNodes[j];
          if (n.nodeType === 1 && n.classList.contains('msg-user')) {
            noticed = true; ob.disconnect();
            setTimeout(function () { if (!state.member) notice('지금은 비회원이라 예시로만 확인했어요. 정확한 확인(기관 기록 대조)과 AI 분석은 로그인하면 쓸 수 있어요.'); }, 2600);
            return;
          }
        }
      });
      ob.observe(thread, { childList: true });
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
  Hk.auth = { state: state, notice: notice, checked: checked, expired: expired, demo: demo };
})(window);
