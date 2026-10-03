# W3 / A / 김형준 — 웹 연결 작업 기록

- 역할 담당: 김형준님 / @kimhyounjun.
- 기록 기간: 2026-10-02; Codex가 사용자 요청에 따라 로컬 구현·검사를 진행했습니다.
- 상태: W3 웹 부분 구현. QR·D 독립 실제 재현은 후속 작업입니다.
- 작업: W3-A1/A2/A3; branch `codex/w3-a-official-web`, [PR #44](https://github.com/OriginProof-3web/OriginProof/pull/44), 대상 phase/W3.
- 시작 SHA·검사 fingerprint·명령·환경: [웹 검사 기록](../../apps/web/W3_VALIDATION.md).

## 실제 결과·기여

| 작업 | 이번 웹 작업 | 재사용·협업 원본 | 상태 |
| --- | --- | --- | --- |
| A1 | 두 유형 입력 검증·422 필드 연결·중복 차단·동일 요청 재시도·실제 ID 표시 | C #35 API·생성 타입, 사용자 제공 BusinessWorkspace | 구현·검사 완료 / 계약 리뷰 대기 |
| A2 | 기관별 목록·상세·ID/공개 링크 복사, 기관 간 접근 거부 실제 확인 | C의 서버 기관 권한·저장·제한 content | 링크 구현·검사 완료 / QR 미완료 |
| A3 | 익명 조회·권한 있는 비교 구분, null lifecycle·NOT_RUN·이유 표시 | C의 실제 서명·결정론적 비교, 사용자 제공 UserWorkspace | 구현·연결 검사 완료 / D 독립 재현 대기 |

## 결정·실패·근거

- 사용자님이 제공한 메인/SidebarNav 스타일을 유지하기 위해 기존 HTML·React source를
  `apps/web/official`에 보존하고 Next public assets로 빌드합니다. 기존 MVP 회귀 화면은 `/mvp`로 옮겼습니다.
- backend/contract를 구현한 것으로 주장하지 않습니다. 생성 snapshot은 C #35 고정 SHA에서
  byte 그대로 복사했고, 실제 연결 검사 API는 C #36입니다.
- React 중복 로딩·접근성 label 오류·브라우저 timeout과 수정·한계는 웹 검사 기록에 남겼습니다.
- 기능 코드·검사는 Codex가 작성했습니다. 사용자님이 선택·제공하신 디자인과 역할 범위,
  C/B의 API·계약 기여를 재사용했습니다. 기여 비율은 측정하지 않았습니다.

## 남은 작업·확인

- QR 라이브러리 추가는 AGENTS 12절 사용자 확인 요청 후 대기 중입니다.
- C API 계약/생성물 소비 리뷰, D 새 환경·새 세션 독립 재현, CI·작성자 외 리뷰가 필요합니다.
- 본인 확인·작성자 외 리뷰: 아직 받지 않았습니다. W3 팀 전체 완료 판정은 하지 않습니다.
- 실행·인계: [W3 웹 안내](../../apps/web/W3_OFFICIAL_WEB.md).

## 협업 코드 추가 검사

사용자 요청에 따라 C #42/#37/#38, D #41/W2 QA, B W6 고정 SHA를 별도 archive에서 검사했습니다. 실제 DB·체인과 현재 웹 결과, 실패한 의존성 감사, 팀원별 후속 작업은 [추가 검사 보고서](../../apps/web/ADDITIONAL_TEST_RESULTS.md)에 연결합니다. 다른 팀원의 구현이나 작성자 외 승인으로 집계하지 않습니다.

## 2026-10-03 CI 보완·병합 준비

사용자님 요청으로 C 계정의 Codex가 최신 W3(#35/#40/#46)를 반영하고 CI E2E의 서버를
production build로 맞췄습니다. 기능 검사에는 기존 live QA와 같은 reduced motion을 적용하고,
390px 바로가기 메뉴의 키보드 열기·Escape 닫기/포커스 복귀·실제 링크 이동 검사를 추가했습니다.
원본 디자인·WebGL·발행/조회/비교 제품 코드는 변경하지 않았습니다.

웹 lint/typecheck/build 통과, component 15 passed, production E2E 9 passed/2 live skipped,
Python 318 passed/5 opt-in skipped입니다. 과거 실제 브라우저 10 passed와 합산하지 않습니다.
생성 타입 snapshot 두 파일은 병합된 C 생성 원본과 byte 일치를 확인했습니다.
QR/LAN·현재 통합 SHA의 실제 API 브라우저 재현·D 독립 검증·W4 화면은 완료로 기록하지 않습니다.
앞 절의 리뷰/CI 대기는 최초 제출 당시 기록이며 최신 결과는 웹 검사 기록과 PR에 남깁니다.

## 2026-10-03 QR 후속 구현·검사

사용자님이 qrcode와 타입 추가를 승인하신 뒤, #44 병합 phase/W3@121e1ca에서
`codex/w3-a-qr-followup`을 시작했습니다. W3-A2의 QR 보기·PNG 저장·공개 ID 링크 전달을
추가했고 메인/Sidebar/WebGL 디자인은 보존했습니다. 기능 코드와 검사는 Codex가 작성했고,
사용자님이 의존성 추가와 디자인 유지 판단을 하셨습니다. 기존 API/서명/권한은 C/B 구현을 재사용했습니다.

component 18 passed, production browser 12 passed/0 skipped입니다. 기존 C #36 실제 API에서
두 유형의 새 발행 QR을 macOS Vision으로 해독하고 익명 조회·수신자 비교·변조 거부를 확인했습니다.
최신 phase backend/휴대폰 스캔/새 변경의 작성자 외 리뷰·CI는 완료로 기록하지 않습니다.
[QR 후속 검사·환경·실패·한계](../../apps/web/W3_QR_VALIDATION.md)에 근거를 남겼습니다.
앞의 QR 미완료·승인 대기는 당시 기록이며 이 절이 최신 QR 상태입니다.
