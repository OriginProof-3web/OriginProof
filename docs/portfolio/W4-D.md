# W4 / D / 여인준 — 개인 개발 기록

- GitHub `@yijun0330`, 실제 작업일 2026-10-03. W4는 개발 단계입니다.
- 작업 W4-D1/D2 독립 상태·1회 사용 QA, W4-D3은 A 실제 화면 연결 대기.
- 시작 `phase/W4@8011f7fe3da033c9253894a9de0fd98aa7bbcc16`.
- branch `test/w4-d-lifecycle-qa`, PR 대상 `phase/W4`.
- 작업 PR [#49](https://github.com/OriginProof-3web/OriginProof/pull/49), C 리뷰 요청. 단계 승격 PR은 아닙니다.
- 검사 코드 `0bb5da42d64b9ce298cb2de2951b327da6bc4fc7`; 이후 기록 커밋은 제품을 변경하지 않습니다.

## 목표·기여·재사용

| 작업 | 실제 D 기여 | 기존 소유자 구현 재사용 | 상태 |
| --- | --- | --- | --- |
| W4-D1 | 두 유형의 합성 lifecycle 기대값, 만료 초 경계·과거 키 기간·교체/유출 폐기·기관 중지 독립 검사 | C Golden/코어/API/DB/서명기, B Registry/Reader/Writer | 위 실제 실행 범위 통과 |
| W4-D2 | ASGI API + 실제 PG/Anvil의 권한/직접 호출/동시·같은 ID 사용/재사용/읽기/반복 폐기/RPC 장애 검사 | C Operation/인증/binding·복구, B 실제 receipt/event·배포 | 새 자원 2회 재현 통과 |
| W4-D3 | 현재 화면 연결 조건과 다음 브라우저 시나리오를 기록 | A W4 화면 소비 필요 | 실제 브라우저 미실행 |

## 결정·실패 해결

- C의 공개 Golden을 읽고 기존 v3.0/ADR 기대값을 검사합니다. Golden·제품·정책을 바꾸지 않습니다.
- 새 이름의 tmpfs DB/Anvil만 생성하고 caller DB/RPC를 받지 않아 보존 환경 변경을 피합니다.
- 만료 시각은 API 신뢰 시각과 실제 EVM 블록 시각을 함께 통제합니다. 실제 상태/서명기를 mock하지 않습니다.
- Anvil 임의 호스트 포트가 재시작 때 바뀌는 실패를 독립 probe로 확인해 새 자원 포트를 명시했습니다.
  원래 실패를 숨기지 않고 최종 검사와 새 archive 재현으로 확인했습니다.

## 검증 근거

상세 실행·명령·한계: [W4 D QA](../qa/w4-d-acceptance.md), [환경 fingerprint](../qa/w4-d-environment.json).
코어 20 + 실제 PG/Anvil 순차 API 1 = 21 passed, fresh archive도 21 passed.
기본 Python 248 passed/4 skipped, indexer 86 passed/1 skipped, Foundry container 22 passed.
구조·lint·typecheck·fingerprint와 fixture Ruff/문서/diff를 확인했습니다.
ASGI 요청·실제 DB/체인과 socket/브라우저 미실행을 구분하고 반복 건수를 합산하지 않습니다.

## AI·사실 확인·후속

사용자님의 D W4 착수 지시에 따라 Codex가 읽기·QA 작성·실행·원인 분석·기록을 수행했습니다.
하위 에이전트는 사용하지 않았습니다. 사람의 검토·본인 사실 확인을 에이전트가 대신하지 않습니다.
작성자 외 리뷰·본인 기여 사실 확인은 대기입니다. 정책 승인과 구현 리뷰를 구분합니다.
A W4 연결 후 D3 전체 브라우저 검사와 최종 phase SHA 확인이 필요하며 단계 완료로 기록하지 않습니다.
