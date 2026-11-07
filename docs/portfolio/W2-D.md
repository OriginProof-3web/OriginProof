# V5-W2-D — 기관 승인 실패 검사

- 담당: D 여인준님 `@yijun0330`. 작업일 2026-10-16 한국시간. Wn은 개발 단계입니다.
- 상태: 독립 합성 QA 실행 완료 / 실제 연결·사람 리뷰·단계 완료 대기.
- 작업 기준: 계획서 5.1 / 병합 공유 계약 v5-shared-0.1, `V5-F01/02/05/12`.
- 현재 작업 브랜치: `codex/v5-w2-d-governance-qa`, [PR #72](https://github.com/OriginProof-3web/OriginProof/pull/72). 최초 단계 PR head는 `17774fb89d5c0efa70f548f697a320ad152ff632`입니다.
- 2026-10-18 수정 기준: `origin/integration@54705588d660aceea71ff1cb03eefb5aefe37aa4`를 merge로 반영했습니다. 원래 수집 브랜치 `codex/v5-d-independent-qa@65ad8db90db46ff072b15408579f1ff5a65a1567`와 구분합니다.
- 최초 실행 소스: `40ab4da11c71d75d26b6b94145e53ee03e3d54a6`. 이후 보고 문서 커밋과 구분합니다.
- 소비한 C 고정 후보: `eaa0d166269833cf7ee49675cfa777b0208c3725` (#62, 미병합 v5-shared-0.2). 다른 담당자 브랜치를 병합하거나 제품 코드를 바꾸지 않았습니다.
- 단계별 PR·원격 push: 수행. #72는 리뷰 수정 중이며 단계 완료·작성자 외 최종 승인은 대기입니다.

## 개인 작업과 재사용

D가 [명시 실행 검사](../../fixtures/finals/v5_d_w2_governance_qa.py)의 요청·변조·실패 단언을 작성했습니다. 자기/타 기관 승인·메일 도메인/코드 오류, 제안 만료/nonce/기관/메타데이터 변경, 승인 수/중복 소비와 receipt만 확정된 UNKNOWN을 검사했습니다.

C의 `apps/api/tests/test_wallet_runtime.py`에 있는 ASGI/SQLite fixture와 onboarding·서명·publication/revocation 준비 helper를 고정 SHA에서 재사용했습니다. 공통 모델·API·Registry 포트·기존 helper의 구현은 C/기존 작성자의 기여이며 D 신규 구현으로 기록하지 않습니다.

## 검증·실패와 한계

해당 파일 **12 PASS / 0 FAIL / 0 SKIP**. 실제 SQLAlchemy 저장과 HTTP·ECDSA 계산을 수행하지만 Registry 스냅샷·상태 전이는 합성이며 실제 EVM/브라우저 검사가 아닙니다. 호출 소켓과 실제 모델 요청은 차단했습니다.

최초 W2는 11 PASS / 1 FAIL이었습니다. 중복 승인 오염을 유효 포트 객체 뒤에 주입하도록 D 준비 데이터를 수정한 뒤 12 PASS가 되었습니다. 보안 기대 결과·C 제품 코드를 바꾸거나 skip/xfail을 추가하지 않았습니다.

2026-10-18 리뷰 수정에서는 오염된 중복 승인 스냅샷의 503 응답에 `WALLET_REGISTRY_UNAVAILABLE` 사유를 단언합니다. 실제 중복 승인 제출의 409와 혼동하지 않습니다. 고정 C 소스를 별도 checkout하는 [전용 CI·재현 명령](../qa/v5-d-review-fixes.md)을 추가했습니다. CI 결과와 최초 로컬 실행을 구분합니다.

A/B/C 동일 신규 후보의 실제 기관 신청·2-of-3 승인·중복/만료·단독 정지/공동 복구 브라우저/체인 검사가 남습니다. 작성자 외 라벨/코드 리뷰를 받거나 단계 전체를 완료한 것으로 표시하지 않습니다.

[전체 명령·결과·환경](https://github.com/OriginProof-3web/OriginProof/blob/52c80b8d974d0a0542680d687447bce7cba413f8/docs/qa/v5-d-readiness.md), [구조화 실행 근거](https://github.com/OriginProof-3web/OriginProof/blob/52c80b8d974d0a0542680d687447bce7cba413f8/docs/qa/v5-d-readiness-results.json).

## AI 활용과 사실 확인

Codex가 D 사례·검사·실행·기록을 작성했고 기존 Graphify 지도와 실제 소스/계약을 대조했습니다. 사용자는 D 담당과 독립 작업 착수를 지시했습니다. 사람의 기여 비율·코드 승인·타인의 확인은 추정하지 않았습니다.

- 본인 사실 확인: 대기.
- 작성자 외 리뷰: #72의 변경 요청을 반영 중이며 재리뷰/승인은 대기입니다.


## 2026-10-21 AI 검사 증거 보완

Codex가 #72 JUnit 정확 수·summary·skip 보호와 indexer/lockfile trigger, 동일 HEAD 재현 안내를 보완했습니다. 로컬 guard 16 / W2 12 / consumer 31 PASS(각 skip 0), [환경·한계](../qa/v5-d-same-head-w2-20261021.md). 사람의 대행 변경 확인·리뷰·단계 완료는 대기입니다.
