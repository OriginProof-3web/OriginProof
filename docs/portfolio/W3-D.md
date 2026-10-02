# W3 / D / 여인준 — 개인 개발 기록

- GitHub: `@yijun0330`, 작업일 2026-10-02. W3는 개발 단계입니다.
- 작업: W3-D1 합성 사례, W3-D2 코어 경계 및 연결 검사 준비, W3-D3 재현 계획.
- 상태: **독립 fixture·모델/코어 검사 통과; 실제 발행 API·브라우저 연결 대기**.
- branch: `test/w3-d-proof-qa`, 시작 `phase/W3@1f8ed632ea9c74091abaf2fe2ec32882038f731f`.
- 검사 코드 SHA: `cbe8aaeea59e18bd4e8529bf59b618683f3e3964`. 후속 기록 commit은 검사 소스를 바꾸지 않습니다.

## 목표·실제 기여

| 담당 | 수행·재사용 | 근거 |
| --- | --- | --- |
| D | 두 유형 64개 합성 사례, 기대값·변조 분리·기간 경계, 65개 자동 검사, 실제 실행·인계 기록 | fixtures/finals/build_w3_cases.py, w3_cases.json, services/analyzer/tests/test_w3_proof_qa.py |
| C | 기존 v2 원본 모델·evaluate_finals·서명 Golden/생성기 재사용 | packages/python/originproof_core, fixtures/golden, scripts/generate_finals_golden.py |
| A/B/C | 후보 W3 구현·계약을 읽고 실제 연결 조건만 정리 | PR #44/#40/#35. 병합·소유자 승인·D 실행으로 취급하지 않음 |

기존 Golden·v1·W1 fixture·애플리케이션 소스를 보존했습니다. D의 AI 안전성 PR #43은
별도로 유지하며 P0 두 유형 발행·검증을 AI에 의존시키지 않습니다.

## 판단·검증·한계

- C의 공개 서명 벡터와 승인 ADR을 재사용해 새 모델/키/서명기/의존성을 만들지 않았습니다.
- 정상과 단일 변조는 같은 서명 자료를 유지하고 관찰 입력만 바꿉니다. 코어/모델과
  실제 API/DB/체인의 검사 계층을 분리하고 W3 lifecycle null/Proof 상태 NOT_RUN을 고정했습니다.
- 신규 65 passed, `make test` 236 passed/3 opt-in skipped, Analyzer 195 passed.
  구조·환경·Ruff·웹 ESLint/tsc·compileall 통과. 중복 사례 수를 합산하지 않습니다.
- 최초 Ruff는 루프 내부 helper의 변수 바인딩 B023을 지적했습니다. profile을 함수 기본
  인수에 고정했고 fixture 내용이 바뀌지 않는 재현 검사와 Ruff 통과를 확인했습니다.
- 정적 모델 거부는 실제 HTTP 422 검사나 발행 권한 거부 증거가 아닙니다. trust record는
  합성이며 실제 ECDSA 검증만 수행했습니다. 성능·추출 정확도·기여 비율은 측정하지 않았습니다.
- 자세한 입력/기대값/명령·환경·선행 SHA·D2/D3 다음 검사: [QA 보고](../qa/w3-d-acceptance.md),
  [환경](../qa/w3-d-environment.json).

Codex가 fixture·테스트·기록을 작성하고 실행했습니다. 사용자님이 D 담당 W3 시작을
지시하셨으며, 다른 담당자의 기능 구현이나 단계 전체 완료로 범위를 넓히지 않았습니다.
작성자 외 C 리뷰 및 본인 기여 사실 확인은 대기입니다. A/B/C 후보 코드 승인을 만들어내지 않습니다.

## 다음 작업

C/B 선행 반영 후 D2 실제 발행 권한·동시성·서명/저장/RPC 실패·제한 조회 검사,
A 연결 후 D3 새 발행→익명 ID/링크 조회→지정 수신자 정상/변조 비교를 진행합니다.
전체 단계 리뷰·A~D 기록·최종 phase SHA와 integration 승격은 별도입니다.
