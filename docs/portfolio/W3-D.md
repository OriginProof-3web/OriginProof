# V5-W3-D — 내용·DB 변조 실패 검사

- 담당: D 여인준님 `@yijun0330`. 작업일 2026-10-16 한국시간. Wn은 개발 단계입니다.
- 상태: 독립 합성 QA 실행 완료 / 실제 연결·사람 리뷰·단계 완료 대기.
- 작업 기준: 계획서 5.1 / 병합 공유 계약 v5-shared-0.1, `V5-F07/10/11`.
- 현재 작업 브랜치: `codex/v5-w3-d-content-qa`, [PR #73](https://github.com/OriginProof-3web/OriginProof/pull/73). 최초 단계 PR head는 `4b6f73bec57aa10f28b29901f86e74852dfd2ff6`입니다.
- 2026-10-18 수정 기준: D W2를 이력 보존 merge하여 최신 `integration@54705588d660aceea71ff1cb03eefb5aefe37aa4`(#80 포함)를 반영했습니다. 원래 수집 브랜치 `codex/v5-d-independent-qa@65ad8db90db46ff072b15408579f1ff5a65a1567`와 구분합니다.
- 최초 실행 소스: `40ab4da11c71d75d26b6b94145e53ee03e3d54a6`. 이후 보고 문서 커밋과 구분합니다.
- 소비한 C 고정 후보: `eaa0d166269833cf7ee49675cfa777b0208c3725` (#62, 미병합 v5-shared-0.2). 다른 담당자 브랜치를 병합하거나 제품 코드를 바꾸지 않았습니다.
- 단계별 PR·원격 push: 수행. #73은 리뷰 수정 중이며 단계 완료·작성자 외 최종 승인은 대기입니다.

## 개인 작업과 재사용

D가 [명시 실행 검사](../../fixtures/finals/v5_d_w3_content_qa.py)의 요청·변조·실패 단언을 작성했습니다. 격리된 합성 Bank/Office와 두 템플릿에서 단일 금액/계좌/URL/제목 변조, ID/부분 비교, DB 원본/내용/메타데이터/이름/버전 변조와 원본 부재를 검사했습니다.

C의 `apps/api/tests/test_wallet_runtime.py`에 있는 ASGI/SQLite fixture와 onboarding·서명·publication/revocation 준비 helper를 고정 SHA에서 재사용했습니다. 공통 모델·API·Registry 포트·기존 helper의 구현은 C/기존 작성자의 기여이며 D 신규 구현으로 기록하지 않습니다.

## 검증·실패와 한계

해당 파일 **13 PASS / 0 FAIL / 0 SKIP**. 실제 SQLAlchemy 저장과 HTTP·ECDSA 계산을 수행하지만 Registry 스냅샷·상태 전이는 합성이며 실제 EVM/브라우저 검사가 아닙니다. 호출 소켓과 실제 모델 요청은 차단했습니다.

최초 W3는 11 PASS / 2 FAIL이었습니다. 공식 템플릿의 합성 기관 코드를 C fixture와 맞춘 뒤 13 PASS가 되었습니다. 보안 기대 결과·C 제품 코드를 바꾸거나 skip/xfail을 추가하지 않았습니다.

2026-10-18 리뷰 수정에서는 DB 원본/내용/메타데이터/이름/버전의 5개 변조마다 예상 `reason_codes`와 FAILED check 이름을 함께 단언합니다. 단순 TAMPERED만으로 다른 거부 원인이 통과하지 않게 했습니다. [고정 C 전용 CI·재현 명령](../qa/v5-d-review-fixes.md)은 stage 25개(W2 12 + W3 13)와 consumer 결과를 분리합니다.

실제 두 기관 동시 운영·기관 격리·새 Registry/DB·브라우저 QR와 전달 메시지·원본 bytes 비교 및 기존 v1/v2 실제 회귀가 남습니다. 작성자 외 라벨/코드 리뷰를 받거나 단계 전체를 완료한 것으로 표시하지 않습니다.

[전체 명령·결과·환경](https://github.com/OriginProof-3web/OriginProof/blob/52c80b8d974d0a0542680d687447bce7cba413f8/docs/qa/v5-d-readiness.md), [구조화 실행 근거](https://github.com/OriginProof-3web/OriginProof/blob/52c80b8d974d0a0542680d687447bce7cba413f8/docs/qa/v5-d-readiness-results.json).

## AI 활용과 사실 확인

Codex가 D 사례·검사·실행·기록을 작성했고 기존 Graphify 지도와 실제 소스/계약을 대조했습니다. 사용자는 D 담당과 독립 작업 착수를 지시했습니다. 사람의 기여 비율·코드 승인·타인의 확인은 추정하지 않았습니다.

- 본인 사실 확인: 대기.
- 작성자 외 리뷰: #73의 변경 요청을 반영 중이며 재리뷰/승인은 대기입니다.

## 이전 계획의 개발 기록 보존

아래는 C의 재사용 기준에 포함된 이전 개발 기록입니다. 당시 검사·연결·리뷰 상태를 보존하며, 위 V5 작업의 완료 근거로 합산하지 않습니다.

### W3 / D / 여인준 — 개인 개발 기록

- GitHub: `@yijun0330`, 작업일 2026-10-02. W3는 개발 단계입니다.
- 작업: W3-D1 합성 사례, W3-D2 코어 경계 및 연결 검사 준비, W3-D3 재현 계획.
- 상태: **독립 fixture·모델/코어 검사 통과; 실제 발행 API·브라우저 연결 대기**.
- branch: `test/w3-d-proof-qa`, 시작 `phase/W3@1f8ed632ea9c74091abaf2fe2ec32882038f731f`.
- 작업 PR: [#46](https://github.com/OriginProof-3web/OriginProof/pull/46), `phase/W3` 대상 초안. C 리뷰 요청 완료.
- 검사 코드 SHA: `cbe8aaeea59e18bd4e8529bf59b618683f3e3964`. 후속 기록 commit은 검사 소스를 바꾸지 않습니다.

#### 목표·실제 기여

| 담당 | 수행·재사용 | 근거 |
| --- | --- | --- |
| D | 두 유형 64개 합성 사례, 기대값·변조 분리·기간 경계, 65개 자동 검사, 실제 실행·인계 기록 | fixtures/finals/build_w3_cases.py, w3_cases.json, services/analyzer/tests/test_w3_proof_qa.py |
| C | 기존 v2 원본 모델·evaluate_finals·서명 Golden/생성기 재사용 | packages/python/originproof_core, fixtures/golden, scripts/generate_finals_golden.py |
| A/B/C | 후보 W3 구현·계약을 읽고 실제 연결 조건만 정리 | PR #44/#40/#35. 병합·소유자 승인·D 실행으로 취급하지 않음 |

기존 Golden·v1·W1 fixture·애플리케이션 소스를 보존했습니다. D의 AI 안전성 PR #43은
별도로 유지하며 P0 두 유형 발행·검증을 AI에 의존시키지 않습니다.

#### 판단·검증·한계

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

#### 다음 작업

C/B 선행 반영 후 D2 실제 발행 권한·동시성·서명/저장/RPC 실패·제한 조회 검사,
A 연결 후 D3 새 발행→익명 ID/링크 조회→지정 수신자 정상/변조 비교를 진행합니다.
전체 단계 리뷰·A~D 기록·최종 phase SHA와 integration 승격은 별도입니다.


## 2026-10-21 AI 동일 HEAD 검사 보완

Codex가 앞 D PR의 정확한 JUnit 검사/trigger/재현 안내를 전파했습니다. guard 16 / stage 25 / consumer 31 PASS(각 skip 0). [환경·범위·미완료](../qa/v5-d-same-head-w3-20261021.md). 기존 기록은 보존하고 사람 확인·외부 리뷰·실제 연결 수용은 대기합니다.
