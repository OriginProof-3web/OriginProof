# V5-W4-D — 버전·키 상태 실패 검사

- 담당: D 여인준님 `@yijun0330`. 작업일 2026-10-16 한국시간. Wn은 개발 단계입니다.
- 상태: 독립 합성 QA 실행 완료 / 실제 연결·사람 리뷰·단계 완료 대기.
- 작업 기준: 계획서 5.1 / 병합 공유 계약 v5-shared-0.1, `V5-F03/05/08/09/11`.
- 현재 작업 브랜치: `codex/v5-w4-d-lifecycle-qa`, [PR #74](https://github.com/OriginProof-3web/OriginProof/pull/74). 최초 단계 PR head는 `a6b8f04930e809cec8136e99a782c8fbdc8b1d7e`입니다.
- 2026-10-18 수정 기준: D W3를 이력 보존 merge하여 최신 `integration@54705588d660aceea71ff1cb03eefb5aefe37aa4`(#80 포함)를 반영했습니다. 원래 수집 브랜치 `codex/v5-d-independent-qa@65ad8db90db46ff072b15408579f1ff5a65a1567`와 구분합니다.
- 최초 실행 소스: `40ab4da11c71d75d26b6b94145e53ee03e3d54a6`. 이후 보고 문서 커밋과 구분합니다.
- 소비한 C 고정 후보: `eaa0d166269833cf7ee49675cfa777b0208c3725` (#62, 미병합 v5-shared-0.2). 다른 담당자 브랜치를 병합하거나 제품 코드를 바꾸지 않았습니다.
- 단계별 PR·원격 push: 수행. #74는 리뷰 수정 중이며 단계 완료·작성자 외 최종 승인은 대기입니다.

## 개인 작업과 재사용

D가 [명시 실행 검사](../../fixtures/finals/v5_d_w4_lifecycle_qa.py)의 요청·변조·실패 단언을 작성했습니다. 최신 철회 뒤 구버전 자동 활성화 금지, 순차 경쟁 draft 예약, 정지 중 발행 거부/철회 허용, 키 교체의 과거 서명 보존/구키 거부/유출 경고, deadline 경계를 검사했습니다.

C의 `apps/api/tests/test_wallet_runtime.py`에 있는 ASGI/SQLite fixture와 onboarding·서명·publication/revocation 준비 helper를 고정 SHA에서 재사용했습니다. 공통 모델·API·Registry 포트·기존 helper의 구현은 C/기존 작성자의 기여이며 D 신규 구현으로 기록하지 않습니다.

## 검증·실패와 한계

해당 파일 **5 PASS / 0 FAIL / 0 SKIP**. 실제 SQLAlchemy 저장과 HTTP·ECDSA 계산을 수행하지만 Registry 스냅샷·상태 전이는 합성이며 실제 EVM/브라우저 검사가 아닙니다. 호출 소켓과 실제 모델 요청은 차단했습니다.

최초 W4는 4 PASS / 1 FAIL이었습니다. 교체 키의 등록/관측 블록 조건을 C fixture와 맞춘 뒤 5 PASS가 되었습니다. 보안 기대 결과·C 제품 코드를 바꾸거나 skip/xfail을 추가하지 않았습니다.

2026-10-18 리뷰 수정에서는 구키의 신규 발행 거부를 `422 INVALID_SIGNATURE`로 단언하고, 거부 요청 전후 전송 목록이 같은지 확인합니다. 준비 과정의 기존 전송을 새 거부 요청의 전송으로 오인하지 않습니다. [고정 C 전용 CI·재현 명령](../qa/v5-d-review-fixes.md)은 stage 30개(W2 12 + W3 13 + W4 5)와 consumer 결과를 분리합니다.

실제 동시 제출 원자성·다른 chain/contract·nonce 재전송·키 사고 공동 복구·기존 consume·브라우저 회귀가 남습니다. G07은 B/C 원인/수정 인계 전 미해결입니다. 작성자 외 라벨/코드 리뷰를 받거나 단계 전체를 완료한 것으로 표시하지 않습니다.

[전체 명령·결과·환경](https://github.com/OriginProof-3web/OriginProof/blob/52c80b8d974d0a0542680d687447bce7cba413f8/docs/qa/v5-d-readiness.md), [구조화 실행 근거](https://github.com/OriginProof-3web/OriginProof/blob/52c80b8d974d0a0542680d687447bce7cba413f8/docs/qa/v5-d-readiness-results.json).

## AI 활용과 사실 확인

Codex가 D 사례·검사·실행·기록을 작성했고 기존 Graphify 지도와 실제 소스/계약을 대조했습니다. 사용자는 D 담당과 독립 작업 착수를 지시했습니다. 사람의 기여 비율·코드 승인·타인의 확인은 추정하지 않았습니다.

- 본인 사실 확인: 대기.
- 작성자 외 리뷰: #74의 변경 요청을 반영 중이며 재리뷰/승인은 대기입니다.
