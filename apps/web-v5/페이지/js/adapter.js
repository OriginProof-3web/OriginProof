/* 데이터 어댑터.
   지금: SampleAdapter 가 data/sample_data.js(window.SAMPLE_DATA)의 예시 응답만 돌려줌.
   실제 연결 때: 같은 모양(check(input) -> Promise<Answer>)을 돌려주는 ApiAdapter 로 바꾸면
   app.js 는 고치지 않아도 됨. 응답 형식 -> bubble_key 변환은 웹_설계.md 4.3 어댑터 계층 규칙을 따름
   (판정을 다시 계산하지 않고 응답 값을 4.1 표의 문구 키로 옮기기만 함). */
(function () {
  'use strict';
  var Hk = (window.Hk = window.Hk || {});

  // 입력 상한은 이 숫자 하나만 씀. 입력창 maxlength 는 app.js 가 MAX_PASTE 로 넣음
  // (상한보다 크게 두어야 넘친 글자가 조용히 잘리지 않고 오류 줄이 나옴 — 재디자인_설계.md 6장 #6)
  var MAX_INPUT = 2000;
  var MAX_PASTE = MAX_INPUT * 2;
  var TONES = ['ok', 'fail', 'caution', 'info', 'pending', 'none', 'offline'];

  /* 원칙: AI 칸·AI 말풍선에는 초록(tone.ok)을 쓰지 않음(웹_설계.md 1.1-4).
     데이터가 잘못 와도 화면에서 막고, 회청색 정보색으로 바꿈. 모르는 값은 "해당 없음" 색. */
  function guardTone(axisOrStaff, tone) {
    if (TONES.indexOf(tone) < 0) return 'none';
    if (axisOrStaff === 'ai' && tone === 'ok') return 'info';
    return tone;
  }

  function samples() {
    return Array.isArray(window.SAMPLE_DATA) ? window.SAMPLE_DATA : [];
  }

  function getSample(id) {
    var list = samples();
    for (var i = 0; i < list.length; i++) if (list[i].id === id) return list[i];
    return null;
  }

  function normalize(t) {
    return String(t).replace(/\s+/g, ' ').trim();
  }

  /* 사용자 입력 검증. 통과하면 { ok:true, text }, 아니면 { ok:false, message } */
  function validate(raw) {
    if (typeof raw !== 'string') return { ok: false, message: '받은 문자나 링크를 붙여 넣어 주세요.' };
    // 제어 문자 제거(줄바꿈·탭은 남김)
    var text = raw.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, '').trim();
    if (!text) return { ok: false, message: '받은 문자나 링크를 붙여 넣어 주세요.' };
    if (text.length > MAX_INPUT) {
      return { ok: false, message: '너무 길어요. ' + MAX_INPUT.toLocaleString('ko-KR') + '자 이하로 붙여 넣어 주세요. (지금 ' + text.length.toLocaleString('ko-KR') + '자)' };
    }
    return { ok: true, text: text };
  }

  function T() { return Hk.text; }

  /* 입력에서 찾은 것: 검증 링크·Proof ID 를 나온 차례대로. 첫 번째를 쓰고 나머지는 '자세히'에 적음.
     실제 확인은 하지 않음(서버 연결은 A3 ApiAdapter). */
  function inspect(text) {
    var refs = T().findRefs(text);
    var first = refs[0] || null;
    var kind = '문자';
    if (first && refs.length === 1 && normalize(text) === first.value) kind = first.type === 'proof' ? 'Proof ID' : '검증 링크';
    return { kind: kind, refs: refs, first: first };
  }

  function staffLines(fn) {
    return Hk.STAFF.map(function (s) { var o = fn(s.id); o.staff = s.id; o.name = s.name; return o; });
  }
  var OFFLINE_LINE = { bubble_key: 'common.not_connected', line1: '연결 전', line2: '', shape: '연결 전', tone: 'offline' };
  function offline() { var o = {}; for (var k in OFFLINE_LINE) o[k] = OFFLINE_LINE[k]; return o; }

  // '자세히'에 넣는 찾은 값(가린 뒤). 첫 번째는 "확인에 쓸 것", 나머지는 "더 찾은 것"
  function refDetails(found) {
    var out = [];
    found.refs.forEach(function (r, i) {
      var what = r.type === 'proof' ? 'Proof ID' : '링크';
      var label = i === 0 ? '확인에 쓸 ' + what : '더 찾은 ' + what + ' ' + i + ' (쓰지 않음)';
      out.push({ label: label, value: T().maskPersonal(r.value) });
      if (r.type === 'link' && r.proofId) out.push({ label: (i === 0 ? '링크 안 Proof ID' : '└ 링크 안 Proof ID'), value: r.proofId });
    });
    return out;
  }

  /* 연결 전 응답: 검증 링크·Proof ID 는 찾았지만 이 시안은 서버를 부르지 않음.
     4.1 common.not_connected("연결 전")와 1.8 "연결 전" 칸 문구만 씀. */
  function notConnected(text, found) {
    var axis = function (key, name, ids) {
      return { axis: key, name: name, status: '연결 전', tone: 'offline', icon: 'plug', body: '이 확인 기능은 아직 연결 전이에요.', staff: ids };
    };
    var details = [
      { label: '입력 종류', value: found.kind },
      { label: '입력 길이', value: text.length + '자' }
    ].concat(refDetails(found));
    details.push({ label: '연결 상태', value: 'common.not_connected · 이 시안은 검증 서버를 부르지 않음' });
    return {
      id: 'not_connected',
      label: '시안',
      sample: true,
      assumption: '이 시안은 예시 ' + samples().length + '개만 답합니다. 다른 입력은 서버에 보내지 않고 "연결 전"으로 보여 줍니다.',
      verification_status: null,
      input: { kind: 'message', text: T().maskPersonal(text) },
      ref: found.first,
      conclusion: { badge: { tone: 'offline', icon: 'plug', text: '연결 전' }, text: '이 시안은 예시 ' + samples().length + '개만 답해요. 검증 엔진을 연결하면 실제로 확인해요.' },
      axes: [
        axis('official', '공식 발행', ['ledger', 'signature']),
        axis('original', '원본 일치', ['original']),
        axis('status', '현재 상태', ['status']),
        axis('ai', 'AI 위험', ['ai'])
      ],
      next_action: { text: '결과가 없으니, 돈을 보내기 전에 기관의 공식 전화번호로 직접 확인하세요. ‘새 확인’을 누르면 예시 ' + samples().length + '개를 다시 볼 수 있어요.' },
      details: details,
      staff: staffLines(function () { return offline(); })
    };
  }

  /* 검증 링크·Proof ID 가 없는 문자: 공식 기록 세 칸은 "확인할 수 없음", AI 칸만 남음.
     이 시안(서버 없음)에서는 AI 칸도 "연결 전". A3 ApiAdapter 가 AI 분석 결과로 이 칸만 채우면 됨.
     말풍선: 서명·원본·상태는 4.1 *.no_source("확인할 원본 없음"), 기록관은 4.1 ledger.not_run,
     접수 직원 문구는 4.1 표에 없어 새로 씀(출처 미확인). */
  function noReference(text, found) {
    var none = function (key, name, ids) {
      return { axis: key, name: name, status: '확인할 수 없음', tone: 'none', icon: 'dash', body: '검증 링크가 없어 공식 기록과 맞춰 볼 수 없어요.', staff: ids };
    };
    var lines = {
      intake: { bubble_key: 'intake.no_reference', line1: '검증 링크를 못 찾았어요', line2: '', shape: '해당 없음', tone: 'none', '출처': '미확인', '메모': '4.1 표에 없는 새 문구(피터 A2)' },
      ledger: { bubble_key: 'ledger.not_run', line1: '앞 단계에서 멈춰 확인 안 함', line2: '', shape: '해당 없음', tone: 'none' },
      signature: { bubble_key: 'signature.no_source', line1: '확인할 원본 없음', line2: '', shape: '해당 없음', tone: 'none' },
      original: { bubble_key: 'original.no_source', line1: '확인할 원본 없음', line2: '', shape: '해당 없음', tone: 'none' },
      status: { bubble_key: 'status.no_source', line1: '확인할 원본 없음', line2: '', shape: '해당 없음', tone: 'none' },
      ai: offline(),
      report: { bubble_key: 'report.ready', line1: '네 축 보고서를 정리했어요', line2: '', shape: '확인됨', tone: 'ok' }
    };
    return {
      id: 'no_reference',
      label: '시안',
      sample: true,
      assumption: '붙여 넣은 글에 검증 링크도 Proof ID 도 없어 공식 기록과 맞춰 보지 않았습니다. AI 분석은 검증 엔진을 연결하면 합니다.',
      verification_status: null,
      input: { kind: 'message', text: T().maskPersonal(text) },
      ref: null,
      conclusion: { badge: { tone: 'none', icon: 'dash', text: '확인할 수 없음' }, text: '공식 기록으로 확인할 수 없는 문자예요.' },
      axes: [
        none('official', '공식 발행', ['ledger', 'signature']),
        none('original', '원본 일치', ['original']),
        none('status', '현재 상태', ['status']),
        { axis: 'ai', name: 'AI 위험', status: '연결 전', tone: 'offline', icon: 'plug', body: 'AI 분석은 검증 엔진을 연결하면 해요.', staff: ['ai'] }
      ],
      next_action: { text: '링크를 누르거나 돈을 보내기 전에, 기관의 공식 전화번호로 직접 확인하세요.' },
      details: [
        { label: '입력 종류', value: '문자' },
        { label: '입력 길이', value: text.length + '자' },
        { label: '찾은 검증 링크·Proof ID', value: '없음' },
        { label: '공식 기록 칸', value: '확인할 수 없음 · 검증 링크가 없음' },
        { label: 'AI 칸', value: 'common.not_connected · 이 시안은 분석 서버를 부르지 않음' }
      ],
      staff: staffLines(function (id) { return lines[id]; })
    };
  }

  /* SampleAdapter.check: 입력이 예시 문자와 같으면 그 예시,
     아니면 검증 링크·Proof ID 가 있으면 "연결 전", 없으면 "공식 기록으로 확인할 수 없음" 응답 */
  var SampleAdapter = {
    mode: 'sample',
    list: samples,
    get: getSample,
    check: function (text) {
      var n = normalize(text);
      var list = samples();
      for (var i = 0; i < list.length; i++) {
        if (normalize(list[i].input.text) === n) return Promise.resolve(list[i]);
      }
      var found = inspect(text);
      return Promise.resolve(found.first ? notConnected(text, found) : noReference(text, found));
    }
  };

  /* 실제 연결: js/api_adapter.js 의 Hk.createApiAdapter(같은 check 모양). 설정의 "실제 서버 연결" 스위치로 바꿈
     (js/connection.js 가 모드·서버 주소를 보고 어느 어댑터를 쓸지 정함). */

  Hk.guardTone = guardTone;
  Hk.validateInput = validate;
  Hk.adapter = SampleAdapter;
  Hk.sampleAdapter = SampleAdapter;
  Hk.MAX_INPUT = MAX_INPUT;
  Hk.MAX_PASTE = MAX_PASTE;
  Hk.inspectInput = inspect;
  Hk.refDetails = refDetails;
})();
