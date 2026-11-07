# W1-D1/D2 — 착수 및 독립 QA

- 담당: D / 여인준님 (@yijun0330). 제안 리뷰어: C (@Jordi2801K); 아직 리뷰 미수행.
- 작업: W1-D1 수용 사례표·카드 회귀, W1-D2 합성 입력·실패 재현 준비.
- 기준: 개발 계획서 v3.0 §15.2·§16, ADR 0001.
- 작업 branch: `codex/w1-d-qa`. PR 대상: `phase/W1`.
- 단계 기준: `ae8c8e2335ace5f241b3a1ad3b548426364c218e`.
- 최신 integration 반영: `3295a71c10a1a99c523d3cfefde91b5737b737ac` (phase 기준의 후손, 개인 branch만 fast-forward).
- 원래 로컬 `mvp/ai`는 커밋 전 미추적 작업이므로 별도 worktree에서 진행한다.
- 수정 경로: fixtures/finals, services/analyzer/tests, D의 QA·기여 문서.
- 선행 계약: C1/C3의 구현·생성물은 현재 phase에 병합된 것으로 간주하지 않는다.
- 독립 범위: ADR 기반 합성 사례, 자료 무결성 검사, 기존 카드 mock/core 회귀.
- 실제 연결 대기: C2/C4 세션·신청 API, C3 v2 모델/생성물, A 브라우저, B 실제 Registry.
- 수락 기준: F01~F15의 역할·입력·기대 결과·계층·미실행 구분, 합성 두 기관/두 유형 및 변조·기간·권한 경계, 기존 v1 회귀 증거.
- 검증: Makefile의 bootstrap-check/env-check/env-fingerprint, test-api/test-analyzer/test, 관련 fixture lint. 기존 MVP의 합성 로컬 E2E는 `make mvp-e2e`로 DB migration·seed·Anvil 배포를 수행해 통과했다. W1 신규 기능 E2E는 실제 연결 후 실행한다.
- 새 정책 없음. OCR/PDF·유료 모델 호출·공유 모델/ABI/Golden 생성기 변경은 범위 밖이다.

확정 정책을 사용한 QA 입력은 실제 HTTP 요청/서명된 v2 Golden/구현 완료 증거가 아니다.
다음 원격 확인은 선행 PR 병합 통지 또는 이 작업 PR 제출 전이다.
