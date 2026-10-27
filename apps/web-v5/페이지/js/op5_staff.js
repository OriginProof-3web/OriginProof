/* 5안 직원 7명 이름표(순수 자료, 화면을 만지지 않음).
   api_adapter.js 의 nameOf 가 Hk.STAFF 로 직원 이름을 붙임. 이름·순서는 business.html 오른쪽 패널 STAFF 와 같음.
   web-2안 staff.js(그림 패널)는 5안 디자인이 아니라 가져오지 않고, 이름표만 둔다. */
(function () {
  'use strict';
  var Hk = (window.Hk = window.Hk || {});
  Hk.STAFF = [
    { id: 'intake', no: 1, name: '접수 직원' },
    { id: 'ledger', no: 2, name: '블록체인 기록관' },
    { id: 'signature', no: 3, name: '서명 감정사' },
    { id: 'original', no: 4, name: '원본 대조관' },
    { id: 'status', no: 5, name: '상태 확인관' },
    { id: 'ai', no: 6, name: 'AI 분석가' },
    { id: 'report', no: 7, name: '보고서 담당' }
  ];
})();
