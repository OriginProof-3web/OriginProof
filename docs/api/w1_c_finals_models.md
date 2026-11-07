# W1-C3 — v2 모델과 생성 계약

기준: phase/W1 322416e. 정책: ADR 0001. 상태: 독립 구현·검사, B/A/D 소비 리뷰 대기.

- `originproof_core.finals`: PaymentRequest, OfficialDocument, FinalsSignedProofEnvelope,
  FinalsVerificationResult, VerificationScope, CheckState, FinalsReasonCode.
- v1 모델/endpoint/Golden은 그대로 보존합니다. v2는 2.0.0 / originproof.finals입니다.
- 모든 v2 envelope 필드는 metadata_hash 외 필수이며 시간은 timezone·정수 초,
  금액/개정 번호는 양의 정수, nonce는 128~256비트 lowercase hex입니다.
- 서버가 recipient_binding/beneficiary_binding/target_binding을 계산합니다.
  token·salt는 공개 응답이나 서명 envelope에 포함하지 않습니다.
- `evaluate_finals`는 순수 함수이며 호출자가 제한 필드 비교 권한과 RPC 조회를 책임집니다.
  W3 중간 결과에서 proof_states=None이면 proof_status=NOT_RUN, lifecycle=null입니다.
  실제 RPC 실패를 이 중간 결과로 치환하면 안 됩니다. W4 상태 조회는 별도 연결 대상입니다.
- 새 모델/평가 함수는 아직 API에 연결하지 않았습니다. 새 발행/검증 API는 W3입니다.
- 대표 lifecycle 우선순위와 모든 확인 원인을 분리하며 서명 실패 시 lifecycle=null입니다.
- 생성: `PYTHONPATH=packages/python python scripts/generate_schemas.py`,
  `PYTHONPATH=packages/python python scripts/generate_finals_golden.py`.
- 공개 합성 서명 벡터의 고정 scalar는 테스트 전용입니다. 운영 서명기에서 사용하지 않습니다.
- Golden의 signing digest·identifier hash·binding hash를 B가 검토하고 생성 타입을 A/D가 소비합니다.
