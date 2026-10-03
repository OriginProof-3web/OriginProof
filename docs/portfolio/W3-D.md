# W3 / D / 여인준 — 개인 개발 기록

> 2026-10-03 최신 기록은 아래 **실제 연결 검사 추가** 절을 확인합니다.
> 기존 독립 준비 기록은 당시 범위와 결과를 보존합니다.

- GitHub: `@yijun0330`, 작업일 2026-10-02. W3는 개발 단계입니다.
- 작업: W3-D1 합성 사례, W3-D2 코어 경계 및 연결 검사 준비, W3-D3 재현 계획.
- 상태: **독립 fixture·모델/코어 검사 통과; 실제 발행 API·브라우저 연결 대기**.
- branch: `test/w3-d-proof-qa`, 시작 `phase/W3@1f8ed632ea9c74091abaf2fe2ec32882038f731f`.
- 작업 PR: [#46](https://github.com/OriginProof-3web/OriginProof/pull/46), `phase/W3` 대상 초안. C 리뷰 요청 완료.
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

## 2026-10-03 실제 연결 검사 추가

- 담당 D / 여인준님 `@yijun0330`; 사용자님의 W3 즉시 가능 작업 진행 요청으로 수행.
- 시작 제품 SHA: `phase/W3@121e1cade40f9ac3b001dc7aa24256d9033f0214`.
- 새 작업 branch: `test/w3-d-live-qa`, 검증 QA 코드 SHA
  `53da535ae36ca4c9616c04ad4f179bec74aac539`.
- #35/#40/#44/#46 병합 후 D 실제 HTTP·PG·Anvil 실패 검사와 실제 브라우저 연결을 진행.
  기존 #46의 코어 검사 결과와 이번 실제 연결 결과를 구분합니다.

| 작업 | 실제 D 기여 | 기존 구현·협업 재사용 | 상태 |
| --- | --- | --- | --- |
| W3-D2 | 실제 권한·주입·동시 발행·누락/변조·signer/commit/RPC 실패·응답 소실 재시도 검사 | C API·DB·서명기/모델, B official Foundry/Reader/Writer, 기존 C live 검사 | 통과. DB/signer/Anvil 실패 주입은 새 owned 환경만 사용 |
| W3-D3 | 두 유형 UI 새 발행→새 익명/수신자 세션→정상/변조/누락·로그아웃/기관 분리 독립 검사 | A 공식 화면·production 설정·기존 Playwright | D 2개 및 기존 전체11개 통과. PC 공개 링크 범위 |
| 재현 | 고정 QA commit의 새 archive에서 새 DB/chain/API 준비 및 D 실제 API/브라우저 재실행 | lockfile에 고정된 첫 clone 의존성과 동일 제품의 production 웹 build 재사용 | 통과. 다른 컴퓨터 재현은 미실행 |

기본 Python 241 passed/4 opt-in skipped, actual HTTP D API 1 passed, 기존 actual
PG/Reader C 검사 1 passed, D actual 브라우저2 passed, 기존 웹 E2E11 passed/skip0,
컴포넌트15 passed, 공식 Foundry12 passed와 실제 HTTP 카드 정상/변조 회귀 통과.
중복 사례 수를 합산하거나 mock·실제 API·브라우저 결과를 같은 검사로 세지 않습니다.

원래 로컬 미추적 작업·개인 설정·MVP fixture·Golden·A/B/C 제품 소스·lockfile을 보존했습니다.
개인 Node 기본값은 유지하고 검사는 Node22.18.0으로 진행했습니다. Bank 중복 활성화,
npm cache 권한, cached symlink 자동 설치 오류를 QA 준비/명령에서 해결했습니다.
Codex 하위 에이전트의 코드 검토로 owned DB/환경/기존 파일 보호·실패 로그를 보완했으며
이를 C 또는 A/B의 사람 리뷰 승인으로 기록하지 않습니다.

상세 결과·재현·잔여 범위: [실제 연결 QA](../qa/w3-d-live-acceptance.md),
[새 환경 fingerprint](../qa/w3-d-live-environment.json).
QR/휴대폰 LAN, 타 컴퓨터 재현, C의 동일 블록 snapshot 소비 확인과 기존 dependency 보안
안내 후속은 남아 있습니다. W4 Proof 상태/consume·AI 유료 호출은 이번 범위가 아닙니다.
새 PR의 C 리뷰·CI 및 전체 A~D 기록/최종 phase 판정 후 단계 승격은 C가 조율합니다.
이번 기록은 사용자님의 작업 지시에 따라 Codex가 작성·실행한 사실이며 별도 본인 확인이나
다른 담당자의 승인·단계 완료를 만들어내지 않습니다.
