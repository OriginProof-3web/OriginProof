/* 시연 프리셋 버튼 (3회차 멘토링 D 전략·W6 과제 '5대 공격 시나리오 프리셋 버튼화').
   - 예시 문자(data/sample_data.js)를 입력칸에 넣고 바로 보냄. 결과는 예시 응답이며 칩에 '예시 모드'가 붙음.
   - 실서버 모드에서는 RC 시연 데이터와 맞는 버튼(정상·위험 요구·변조·구버전·미등록 사칭)만 실제로 보내고,
     나머지는 서버에 보내지 않고 예시 결과를 '예시 자료 · 서버에 보내지 않음' 표시로 보여 줌.
   - DB 직접 조작: 시연 계정(서버 API_DEMO_ATTACK_USERNAMES)이 누르면 서버 DB의 은행 #10 금액을 바꾸고(시연용 공격 재현), 원래 받은 안내문으로 검증해 변조로 잡힘.
     말풍선의 'DB 되돌리기'로 되돌림. 시연 계정이 아니면 DB는 그대로 두고 검증만 함(터미널 scripts/rc_local.sh db-tamper 로도 바꿀 수 있음).
   - 예시 자료로 재현할 수 있는 것만 바로 실행. 서버·체인이 있어야 재현되는 공격(권한 도용·서명 재사용·키 유출 정지)은
     지어낸 결과를 보여 주지 않고, 무엇을 보여 주는 장면인지와 '실서버 연결 뒤 재현'만 알려 줌. */
(function () {
  'use strict';
  var bar = document.getElementById('presetBar');
  var input = document.getElementById('chatInput'), form = document.getElementById('composer');
  if (!bar || !input || !form) return;
  var DATA = Array.isArray(window.SAMPLE_DATA) ? window.SAMPLE_DATA : [];
  function textOf(id) { var s = DATA.filter(function (x) { return x.id === id; })[0]; return s && s.input ? s.input.text : ''; }

  // 실서버 모드에서는 예시 자료 대신 rc_local.sh 시연 데이터와 맞는 입력을 보냄.
  // 문자는 어느 RC에서나 같은 값(기관·금액·계좌)이라 고정(api_adapter.js DEMO_TEXTS, AI 지연 대체 응답과 같은 글),
  // 문서 JSON(ID·기한)은 RC마다 달라 rc_local.sh 가 data/rc_presets.json 으로 만든다.
  var DT = (window.Hk && window.Hk.api && window.Hk.api.DEMO_TEXTS) || {};
  // 실서버 시연 버튼은 누를 때마다 은행 → 카드사 → 통신사 → 병원 순서로 다음 기관 장면을 보냄(버튼마다 따로 셈, 새로고침하면 은행부터).
  // 문자는 DEMO_TEXTS(rc_normal_card…), 문서 JSON은 rc_presets.json 의 scenes[i](rc_local.sh 가 만듦)
  var ROT = [{ k: '', name: '은행' }, { k: '_card', name: '카드사' }, { k: '_telecom', name: '통신사' }, { k: '_clinic', name: '병원' }];
  var UNREG_NAMES = ['환급센터', '카드사', '통신사', '병원'];   // 미등록 사칭은 등록 기관이 아니라 이 이름들을 사칭함
  var turn = {};
  var SERVER_INPUT = {
    normal: { text: function (i) { return DT['rc_normal' + ROT[i].k]; } },
    risky: { text: function (i) { return DT['rc_risky' + ROT[i].k]; } },
    tamper: { file: 'tamper', vs: '발행 원본' },
    superseded: { file: 'superseded', vs: '최신판' },
    db: { file: 'db_target' }
  };
  function unregText(i) { return i ? DT['unreg' + ROT[i].k] : textOf('unregistered'); }
  // 문서 JSON을 읽을 수 있는 안내문으로 보여 주고, 기준 문서(rc_presets.json 의 genuine)와 다른 항목엔 기준 값을 붙인다.
  var FIELDS = [['payment_purpose', '납부 목적'], ['amount_minor', '납부 금액'], ['payee_bank_name', '입금 은행'],
    ['payee_account_number', '입금 계좌'], ['payee_account_holder', '예금주'], ['due_at', '납부 기한']];
  function fmt(k, v) {
    if (k === 'amount_minor') return Number(v).toLocaleString('ko-KR') + '원';
    if (k === 'due_at') return new Date((Number(v) + 9 * 3600) * 1000).toISOString().slice(0, 10);   // 한국 날짜
    return window.Hk.text ? window.Hk.text.maskPersonal(String(v)) : String(v);
  }
  function describe(label, doc, base, vs) {
    var f = doc.protected_fields || {}, b = (base && base.protected_fields) || {}, changed = [];
    var rows = FIELDS.filter(function (x) { return f[x[0]] != null; }).map(function (x) {
      var line = '· ' + x[1] + ': ' + fmt(x[0], f[x[0]]);
      if (base && b[x[0]] !== f[x[0]]) { changed.push(x[1]); line += '   ⟵ ' + vs + (base.version !== doc.version ? '(v' + base.version + ')' : '') + ' ' + fmt(x[0], b[x[0]]); }
      return line;
    });
    var head = [label + ' 안내문 · 문서 v' + doc.version];
    if (base) head.push(changed.length ? '⚠ ' + vs + '과 다른 항목: ' + changed.join(', ') : vs + '과 같은 내용');
    return head.concat(rows).join('\n');
  }

  var LIVE = [
    { label: '정상 안내문', id: 'normal', tip: '기관이 발행한 원본 그대로 → 기록 일치' },
    { label: '진짜 안내 + 위험 요구', id: 'risky', tip: '발행 기록과 맞는 안내 + 단어 규칙에 없는 위험 요구(수사관 사칭·상품권 핀번호·결제 대행 앱·가족에게 숨기기) → 발행 확인됨 + AI 위험 신호(실서버 전용)' },
    { label: '금액 1원 변조', id: 'tamper', tip: '문구는 그대로, 금액만 1원 바꿈 → 원본과 다름' },
    { label: '사진 고지서 변조', id: 'tamper_image', tip: '고지서 사진의 금액을 바꾼 경우 → 원본과 다름' },
    { label: '구버전 재사용', id: 'superseded', tip: '정정 전 v1 안내문을 다시 보냄 → 새 버전 있음' },
    { label: 'DB 직접 조작', id: 'db', tip: '해커가 서버 DB의 금액을 몰래 바꿔도 기관 서명·블록체인 기록과 대조해 변조로 잡아요(시연 계정 전용 공격 재현)' },
    { label: '철회된 안내', id: 'revoked', tip: '기관이 철회한 안내문 → 철회됨' },
    { label: '미등록 기관 사칭', id: 'unregistered', tip: '체인에 없는 기관 + 원격 앱 설치 유도 → 기록 없음 + AI 위험 신호' }
  ];
  var SERVER = [
    { label: '타 기관 권한 도용', why: 'A 기관 계정으로 B 기관 안내문을 발행하려 하면 거부되는 장면이에요.' },
    { label: '서명 재사용', why: '이미 쓴 EIP-712 서명을 다시 제출하면 nonce 때문에 거부되는 장면이에요.' },
    { label: '키 유출 긴급 정지', why: '승인자 1명이 단독으로 기관을 즉시 정지하고, 2-of-3 승인으로 키를 바꿔 복구하는 장면이에요.' }
  ];

  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function send(text) {
    input.value = text;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    if (form.requestSubmit) form.requestSubmit(); else form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
  }

  function live() { return !!(window.Hk && window.Hk.op5live && window.Hk.op5live()); }
  function member() { return !!(window.Hk && window.Hk.auth && window.Hk.auth.state.member); }
  function bubble(tag, title, lines) {
    var thread = document.getElementById('chatThread'), empty = document.getElementById('chatEmpty');
    if (empty) empty.remove();
    var m = el('div', 'msg msg-ai'), w = el('div', 'who'), bub = el('div', 'bubble');
    w.append(el('i', null, ''), el('span', null, 'OriginProof AI'), el('span', 'tag-offline', tag));
    var para = el('p');
    para.append(el('b', null, title));
    lines.forEach(function (t) { para.append(el('br'), document.createTextNode(t)); });
    bub.append(para); m.append(w, bub); thread.append(m);
    var sc = document.getElementById('chatScroll'); if (sc) sc.scrollTop = sc.scrollHeight;
    return bub;
  }
  function won(n) { return Number(n).toLocaleString('ko-KR') + '원'; }
  // DB 직접 조작 장면: 시연용 공격 재현으로 그 기관 대상 안내문의 서버 DB 금액을 바꾸고(시연 계정만) 원래 받은 안내문으로 검증한 뒤, 결과가 나오면 바로 되돌림.
  // 브라우저를 닫는 등으로 되돌리지 못해도 rc_local.sh up 이 켤 때 되돌림
  function dbScene(go, name, account) {
    var hk = window.Hk && window.Hk.op5demoAttack;
    var attack = hk && function (action) { return hk(action, account); };
    return (attack ? attack('db-tamper') : Promise.resolve(null)).then(function (res) {
      var d = res && res.status === 200 && res.data;
      if (!d) {
        bubble('시연용 공격 재현', 'DB를 바꾸지 않았어요', ['이 계정은 시연 계정이 아니거나 서버에서 시연 기능이 꺼져 있어요. 원래 안내문으로 확인만 해요.']);
        return go();
      }
      bubble('시연용 공격 재현 · 실서비스에는 없는 기능', '해커가 서버 DB를 몰래 바꿨어요', ['서버 DB에 저장된 ' + name + ' 안내문의 금액을 ' + won(d.original_amount) + ' → ' + won(d.amount_after) + '으로 바꿨어요. 기관 서명과 블록체인 기록은 그대로예요.', '이제 원래 받은 안내문으로 확인해요.']);
      var restore = function () {
        return attack('db-restore').then(function (r) {
          if (r && r.status === 200 && r.data) bubble('시연용 공격 재현', '시연을 마쳐 DB를 원래대로 되돌렸어요', ['서버 DB의 금액을 다시 ' + won(r.data.amount_after) + '으로 돌려 놓았어요.']);
          else bubble('시연용 공격 재현', 'DB를 되돌리지 못했어요', ['터미널에서 scripts/rc_local.sh db-restore 로 되돌려 주세요. 서버를 다시 켜면(up) 자동으로 되돌아가요.']);
        });
      };
      return Promise.resolve(go()).then(restore, restore);
    });
  }

  function canLive(p) { return !!SERVER_INPUT[p.id] || p.id === 'unregistered'; }
  function addLive(p) {
    var t = textOf(p.id), s = SERVER_INPUT[p.id];
    if (!t && !s) return;
    var b = el('button', canLive(p) ? 'preset' : 'preset preset-sample', p.label);
    b.type = 'button'; b.title = p.tip;
    // 실서버 모드에서는 다음에 보낼 기관을 버튼 안에 작게 보여 줌
    var badge = el('span', 'preset-turn');
    function mark() { var i = turn[p.id] || 0; badge.textContent = live() && canLive(p) ? ' · ' + (p.id === 'unregistered' ? UNREG_NAMES[i] : ROT[i].name) : ''; }
    function advance() { var i = turn[p.id] || 0; turn[p.id] = (i + 1) % ROT.length; mark(); return i; }
    b.append(badge); mark();
    b.addEventListener('click', function () {
      if (live() && s && s.text) { send(s.text(advance())); return; }
      if (live() && s && s.file) {
        var i = advance();
        // 검증 결과가 다 그려질 때 끝나는 약속을 돌려줌(DB 조작 장면이 그 뒤에 되돌림)
        window.fetch('data/rc_presets.json', { cache: 'no-store' })
          .then(function (r) { return r.ok ? r.json() : null; })
          .catch(function () { return null; })
          .then(function (all) {
            if (!all) return bubble('시연 데이터 없음', '시연 · ' + p.label, ['이 컴퓨터의 시연 데이터 파일(data/rc_presets.json)이 없어 보내지 않았어요.', 'scripts/rc_local.sh up 으로 시연 데이터를 만든 뒤 새로고침해 주세요.']);
            var sc = Array.isArray(all.scenes) ? all.scenes[i] : (i ? null : all);   // scenes 가 없는 옛 파일은 은행만
            var doc = sc && sc[s.file];
            if (!doc) return bubble('시연 데이터 없음', '시연 · ' + p.label + ' · ' + ROT[i].name, [ROT[i].name + ' 장면이 시연 데이터에 없어 보내지 않았어요.', '기관이 추가되기 전에 만든 시연 데이터예요. scripts/rc_local.sh purge 뒤 up 으로 새로 만든 다음 새로고침해 주세요.']);
            var go = function () {
              if (window.Hk.op5send) return window.Hk.op5send(JSON.stringify(doc), describe(p.label + ' · ' + ROT[i].name, doc, s.vs ? sc.genuine : null, s.vs));
              return send(JSON.stringify(doc));
            };
            return p.id === 'db' ? dbScene(go, ROT[i].name, (doc.protected_fields || {}).payee_account_number) : go();
          });
        return;
      }
      // 예시 자료의 ID는 실서버에 없어 '기록 없음'으로 잘못 나온다. 실서버 모드에서는 서버에 보내지 않고 예시 결과를 '예시 자료'로 보여 줌.
      // 미등록 사칭만 실서버에서도 그 결과가 맞아 실제로 보냄(실제 AI 위험 분석까지).
      if (live() && p.id !== 'unregistered') {
        if (window.Hk && window.Hk.op5sampleCheck) { window.Hk.op5sampleCheck(t); return; }
        bubble('예시 자료', '시연 · ' + p.label, ['이 버튼은 예시 자료라 실서버 기록과 맞지 않아 보내지 않았어요. 예시 모드에서 볼 수 있어요.', '실서버로 확인하려면 기관이 발행한 문자를 입력칸에 붙여 넣어 주세요.']);
        return;
      }
      if (!t) { bubble('실서버 전용', '시연 · ' + p.label, ['이 버튼은 실서버 시연 데이터와 맞춰 둔 장면이라 실서버 모드에서만 보내요.']); return; }
      send(live() && p.id === 'unregistered' ? unregText(advance()) : t);
    });
    track.append(b);
  }
  // 버튼은 가운데 줄(track)에만 두고 양 끝 화살표로 옮김. 화살표는 늘 보이고, 더 갈 곳이 없으면 흐리게(스크롤바는 숨김)
  var track = el('div', 'preset-track');
  function nav(dir) {
    var b = el('button', 'preset-nav preset-nav-' + dir, dir === 'l' ? '‹' : '›');
    b.type = 'button'; b.setAttribute('aria-label', dir === 'l' ? '시연 버튼 왼쪽으로' : '시연 버튼 오른쪽으로');
    b.addEventListener('click', function () { if (track.scrollBy) track.scrollBy({ left: (dir === 'l' ? -0.7 : 0.7) * track.clientWidth, behavior: 'smooth' }); });
    return b;
  }
  var navL = nav('l'), navR = nav('r');
  function navUpdate() {
    navL.disabled = !(track.scrollLeft > 0);
    navR.disabled = !(track.scrollWidth - track.clientWidth - track.scrollLeft > 1);
  }
  bar.append(navL, track, navR);
  track.append(el('span', 'preset-title', '실서버 시연'));
  LIVE.filter(canLive).forEach(addLive);
  track.append(el('span', 'preset-title', '예시 결과'));
  LIVE.filter(function (p) { return !canLive(p); }).forEach(addLive);
  track.append(el('span', 'preset-title', '설명만'));
  SERVER.forEach(function (p) {
    var b = el('button', 'preset preset-server', p.label);
    b.type = 'button'; b.title = '실서버·체인 연결 뒤 재현';
    b.addEventListener('click', function () {
      if (live() && member()) {
        bubble('설명', '공격 시나리오 · ' + p.label, [p.why, '이 장면은 DB·계정·지갑을 직접 건드려야 해서 이 버튼으로 실행하지 않아요. 예시 결과를 지어내지 않았어요.']);
        return;
      }
      bubble('실서버 필요', '공격 시나리오 · ' + p.label, [p.why, '이 장면은 서버와 체인(Anvil 또는 Sepolia)을 켜고 로그인한 뒤 실제 응답으로만 보여 드려요. 예시 결과를 지어내지 않았어요.']);
    });
    track.append(b);
  });
  track.addEventListener('scroll', navUpdate);
  window.addEventListener('resize', navUpdate);
  navUpdate();
})();
