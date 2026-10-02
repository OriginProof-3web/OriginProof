# W1 / C / Jordi — 개인 개발 기록

- 계정: @Jordi2801K
- 작업 기간: 2026-09-30 ~ 2026-10-01
- 상태: 독립 구현·검사 완료, 소비자 리뷰와 단계 완료 대기
- 작업: W1-C1~C4, 기준 phase/W1 322416e

## 실제 결과와 기여

C 인증·세션·권한·기관 신청은 PR #23으로 병합됐습니다. 후속 W1-C3는 ADR 0001의
두 유형 v2 모델·binding·서명/검증 경계와 생성 Schema/TypeScript/Golden을 구현했습니다.
기존 canonicalization/signature 알고리즘을 재사용하고 v1 모델과 fixture를 보존했습니다.
B Registry 명세는 입력으로 참고했으며 B 코드 수정이나 B/A/D 리뷰를 대신하지 않았습니다.

## 검증

Python core 검사 19개 통과: v1 Golden/기존 판정, 두 v2 서명 복구·binding·기간·타입,
실패 검사 순서·내용 누락/불일치·상태 우선순위·정상 키 기간 종료 이후 과거 서명.
실제 API/DB/EVM 새 v2 발행은 W3 범위로 미실행입니다. 코드 SHA는 작업 PR에 기록합니다.

## 판단·AI 활용·잔여

별도 v2 모델로 기존 v1 계약을 보존하고 현재 상태 미실행을 null/NOT_RUN으로 표시합니다.
Codex가 구현·검사·문서 작성을 보조했습니다. 정책은 사용자 승인 ADR을 따랐습니다.
B의 체인 경계 검토, A/D 생성물 소비, 단계 독립 확인은 아직 없습니다.

## 2026-10-02 D 검토·연결 확인

원 기록 이후 D/Codex가 공식 `phase/W1@0308cb24`의 C API 및 모델을 검사했습니다. 실제 PostgreSQL·Chromium에서 로그인/권한/신청/승인·반려/세션 경계가 확인됐고, 생성 Schema/TypeScript/Golden 재생성 및 Foundry hash 교차 검사가 통과했습니다. [검증 보고](../qa/w1-final-verification.md)를 참조합니다.

PR #23과 #32에는 `yijun0330` 계정의 Codex 수행 사후 승인 리뷰를 기록했습니다. 이는 C 작성자 외 D 기술 검토이며 B/A 소유자 본인의 확인이나 과거 병합 전 승인으로 소급하지 않습니다. [리뷰 현황](../qa/w1-scope-and-reviews.md)을 참조합니다. 정책 승인과 구현 리뷰, 실제 연결, 단계 승격은 계속 구분합니다.

이번 후보의 제품 변경은 D가 발견한 A 승인 화면 접근성 수정이며 C API·모델·Golden은 바꾸지 않았습니다. 단계 승격은 [PR #39](https://github.com/OriginProof-3web/OriginProof/pull/39)의 최종 SHA·외부 리뷰 뒤 진행해야 합니다. C 본인의 새 기록 확인은 미확인입니다.
