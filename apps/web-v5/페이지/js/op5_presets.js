/* 시연 프리셋 버튼 (3회차 멘토링 D 전략·W6 과제 '5대 공격 시나리오 프리셋 버튼화').
   - 예시 문자(data/sample_data.js)를 입력칸에 넣고 바로 보냄. 결과는 예시 응답이며 칩에 '예시 모드'가 붙음.
   - 실서버 모드에서는 서버에 보내지 않고 예시 결과를 '예시 자료 · 서버에 보내지 않음' 표시로 보여 줌(미등록 사칭만 실제로 보냄).
   - 예시 자료로 재현할 수 있는 것만 바로 실행. 서버·체인이 있어야 재현되는 공격(DB 조작·권한 도용·서명 재사용·키 유출 정지)은
     지어낸 결과를 보여 주지 않고, 무엇을 보여 주는 장면인지와 '실서버 연결 뒤 재현'만 알려 줌. */
(function () {
  'use strict';
  var bar = document.getElementById('presetBar');
  var input = document.getElementById('chatInput'), form = document.getElementById('composer');
  if (!bar || !input || !form) return;
  var DATA = Array.isArray(window.SAMPLE_DATA) ? window.SAMPLE_DATA : [];
  function textOf(id) { var s = DATA.filter(function (x) { return x.id === id; })[0]; return s && s.input ? s.input.text : ''; }

  var LIVE = [
    { label: '정상 안내문', id: 'normal', tip: '기관이 발행한 원본 그대로 → 기록 일치' },
    { label: '금액 1원 변조', id: 'tamper', tip: '문구는 그대로, 금액만 85,000원 → 85,001원 → 원본과 다름' },
    { label: '사진 고지서 변조', id: 'tamper_image', tip: '고지서 사진의 금액을 바꾼 경우 → 원본과 다름' },
    { label: '구버전 재사용', id: 'superseded', tip: '정정 전 v1 안내문을 다시 보냄 → 새 버전 있음' },
    { label: '철회된 안내', id: 'revoked', tip: '기관이 철회한 안내문 → 철회됨' },
    { label: '미등록 기관 사칭', id: 'unregistered', tip: '체인에 없는 기관 + 원격 앱 설치 유도 → 기록 없음 + AI 위험 신호' }
  ];
  var SERVER = [
    { label: 'DB 직접 조작', why: '해커가 서버 DB의 금액·공개키를 몰래 바꿔도, 체인 기록과 대조해 TAMPERED로 잡아내는 장면이에요.' },
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
  }

  bar.append(el('span', 'preset-title', '시연'));
  LIVE.forEach(function (p) {
    var t = textOf(p.id);
    if (!t) return;
    var b = el('button', 'preset', p.label);
    b.type = 'button'; b.title = p.tip;
    b.addEventListener('click', function () {
      // 예시 자료의 ID는 실서버에 없어 '기록 없음'으로 잘못 나온다. 실서버 모드에서는 서버에 보내지 않고 예시 결과를 '예시 자료'로 보여 줌.
      // 미등록 사칭만 실서버에서도 그 결과가 맞아 실제로 보냄(실제 AI 위험 분석까지).
      if (live() && p.id !== 'unregistered') {
        if (window.Hk && window.Hk.op5sampleCheck) { window.Hk.op5sampleCheck(t); return; }
        bubble('예시 자료', '시연 · ' + p.label, ['이 버튼은 예시 자료라 실서버 기록과 맞지 않아 보내지 않았어요. 예시 모드에서 볼 수 있어요.', '실서버로 확인하려면 기관이 발행한 문자를 입력칸에 붙여 넣어 주세요.']);
        return;
      }
      send(t);
    });
    bar.append(b);
  });
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
    bar.append(b);
  });
})();
