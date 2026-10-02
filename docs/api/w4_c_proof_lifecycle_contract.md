# W4-C2/C3 — Proof 등록·폐기·현재 상태·1회 사용 연결

- 담당 C / `@Jordi2801K`, 실제 작업일 2026-10-02.
- 작업 branch: `feat/w4-c-proof-lifecycle`, C 코드·검사 SHA `596f3130e9291f620932161c818389c63e1b53b3`.
- 선행 C W4-C1 `85e152c`, B W3 `92e0e94` / W4 `58e819e`를 준비 branch에서 연결했습니다.
- C 구현·자체 검사·실제 PostgreSQL/Anvil 연결 확인 완료. 공유 phase 병합·A 화면·D 독립 QA·작성자 외 리뷰는 별도 대기입니다.
- B Contract/Adapter/배포/projection 원본은 변경하지 않았습니다. [B 인계](../blockchain/w4_proof_status_handoff.md)와 [ADR](../adr/0001-finals-contracts.md)을 소비합니다.

## HTTP 계약과 화면 연결

| 경로 | 권한·입력 | 응답·동작 |
| --- | --- | --- |
| POST `/v2/issuer/proofs` | 기존 issuer + CSRF, IssueInput | 기존 ProofView + `registration_status`, `registration_operation_id`; 서명·DB 저장 후 등록 Operation 실행 |
| POST `/v2/issuer/proofs/{id}/register` | 자기 발행기관 issuer + CSRF, `{"request_id":"req_register_001"}` | OperationView; 기존 W3 envelope를 재서명하지 않고 등록, 미확정은 동일 tx 복구 |
| POST `/v2/issuer/proofs/{id}/revoke` | 자기 발행기관 issuer + CSRF, `{"request_id":"req_revoke_001","reason":"합성 폐기"}` | OperationView; 체인 폐기, 반복 폐기는 추가 tx/event 없이 현재 상태 관찰 |
| POST `/v2/proofs/{id}/consume` | 자기 발행기관 또는 지정 수신자 세션 + CSRF, `{"request_id":"req_use_001"}` | OperationView; 기관/수신자 주체는 서버에서 계산, trusted gateway로 제출 |
| POST `/v2/proofs/{id}/verify` | 기존 공개/제한 비교 권한 | FinalsVerificationResult; 서명·내용 검사와 현재 lifecycle을 분리; 읽기는 consume하지 않음 |
| GET `/v2/proofs/{id}` · GET `/v2/issuer/proofs` | 기존 공개/기관 권한 | ProofView에 등록 Operation 상태·opaque ID 추가; payload/token/salt/복구 참조 제외 |
| GET `/v1/operations/{id}` · POST `/v1/operations/{id}/recover` | 기존 Operation 권한·복구 CSRF | 등록/폐기/consume도 기존 조회·복구 사용 |

`registration_status`는 DB에 기록한 Operation 상태입니다. 현재 사용 가능 표시에는 verify의
실제 체인 lifecycle을 사용합니다. 등록 Operation이 없으면 `NOT_REGISTERED`입니다.
조회 응답에 상태가 CONFIRMED여도 현재 폐기·만료·소비 상태가 ACTIVE라는 뜻은 아닙니다.
미확정 발행은 같은 IssueInput·request_id로 재시도하거나 registration_operation_id를 복구합니다.
입력 fingerprint가 다르면 409입니다. 발행 DB commit 전에 등록 tx를 보내지 않습니다.
DB 저장 뒤 체인 준비 오류이면 HTTP 503이 될 수 있지만 같은 발행 ID로 원래 Proof/Operation을 찾습니다.

등록의 새 요청 ID도 원래 등록 tx를 공유하는 별도 reservation에 원자적으로 기록합니다.
동일 요청 ID를 다른 Proof에 재사용하면 409이고, alias 저장 실패가 새 nonce를 만드는 상태를 남기지 않습니다.
원래 등록이 확실히 FAILED인 경우에만 새 등록 요청 ID로 다시 시도할 수 있습니다.
SUBMITTED/UNKNOWN의 새 등록 요청은 동일 복구 참조를 사용합니다.

## 신뢰 상태와 실패

W3-B1의 `get_issuer_key_snapshot`을 발행·검증에 연결했습니다. 발행 직전 기관/키/소속/signer와
현재 키 기간을 같은 블록에서 확인합니다. 과거 Proof는 발행 당시 키 기간을 사용합니다.
Proof Reader 결과와 기관/키 snapshot의 배포·chain ID·block/hash가 일치해야 현재 상태를 판정합니다.
조회 사이에 head가 바뀌거나 reorg/RPC/ABI/배포 오류가 있으면 판정을 보류하며 클라이언트가 다시 조회합니다.

체인 commitment의 Proof/기관/키 ID hash, signing digest, subject binding, issued/expires, single_use를
서버 envelope와 모두 대조합니다. 신규 등록·사용 전에 실제 서명과 서버의 recipient token/salt binding을 확인합니다.
등록 실패·미등록을 ACTIVE로 간주하거나 원본을 소급 재서명하지 않습니다.

| 상황 | verify 또는 변경 API 결과 |
| --- | --- |
| 서명·근거·등록 확정·현재 정상 | VERIFIED + ACTIVE; 비교 범위는 PROOF_ONLY/FULL_COMPARISON/PARTIAL_COMPARISON으로 별도 표시 |
| 체인에 미등록 | NOT_REGISTERED + null lifecycle, PROOF_NOT_FOUND; 변경은 거부 |
| 체인에 존재하지만 등록 Operation 미확정 | INCONCLUSIVE + null lifecycle, REGISTRATION_PENDING |
| commitment 불일치 | INCONCLUSIVE + null lifecycle, CHAIN_COMMITMENT_MISMATCH; 변경 거부 |
| 현재 체인 조회 실패 | INCONCLUSIVE + null lifecycle, DEPENDENCY_UNAVAILABLE; 변경은 503 |
| 정상 서명 + 폐기/소비/만료/기관 중지/키 유출 폐기 | VERIFIED + 해당 lifecycle; 현재 사용 차단, 확인된 원인 모두 보존 |
| 같은 요청 ID 재시도 | 원래 Operation/tx 결과·복구; 새로운 consume 성공으로 세지 않음 |
| 새 ID로 이미 사용한 Proof | 409 REPLAY_DETECTED |
| 다른 consume Operation이 미확정 | 409 PROOF_OPERATION_PENDING; 기존 Operation 복구 후 재조회 |
| 문서형 consume | 409 PROOF_NOT_SINGLE_USE |
| 타 기관/다른 수신자/일반 운영자 | 404 PROOF_NOT_FOUND; 수신자·운영자 폐기 요청은 403 |
| 클라이언트 actor_kind/actor_binding 지정 | 422; 입력 모델 extra=forbid |
| DB reservation 저장 실패 | 외부 제출 없음; 제출 뒤 최종 DB commit 실패는 기존 복구 참조로 확인 |
| 실패 receipt | Operation FAILED; tx hash를 성공으로 표시하지 않음 |

기관/수신자 consume은 같은 PostgreSQL advisory lock과 B의 체인 원자성을 함께 사용합니다.
최종 consume 권위는 체인이며, gateway는 서버의 서명·세션 검증을 신뢰하는 P0 대행 경계입니다.
공개 계정 ID·token·salt는 온체인/공개 응답에 저장하지 않습니다.
CONSUMED 뒤 적법한 폐기는 허용하고 consumedAt과 REPLAY_DETECTED 원인을 보존합니다.
정상 키 교체/기간 종료만으로 과거 서명을 무효화하지 않습니다.

## 실행 증거와 재현

검사 코드 SHA는 위 C 커밋입니다. macOS, Python 3.13, PostgreSQL 16 Alpine,
Anvil/Forge 1.4.4, 별도 임시 합성 DB/chain·서명기만 사용했습니다. 기존 데모 볼륨은 변경하지 않았습니다.

- `PYTHONPATH=apps/api/src:packages/python:services/analyzer/src:services/indexer/src uv run pytest apps/api/tests packages/python/tests services/analyzer/tests services/indexer/tests`: **268 passed / opt-in 5 skipped**.
- `test_proof_lifecycle.py`: **4 passed**, 실제 HTTP/SQLite 저장·합성 Adapter. 권한/경쟁/재시도/미등록/commitment 불일치/기존 W3 등록/수신자 binding/UNKNOWN/실패/DB 예약 실패를 확인했습니다.
- `test_live_finals.py`: **1 passed**, 실제 PostgreSQL + B Reader/Writer + 임시 Anvil. 두 유형 등록·정상/변조 비교·키 교체·유출 폐기·기관 중지/복귀·Proof 폐기·만료·실제 RPC 연결 실패를 확인했습니다.
- 실제 consume: 발행기관/수신자 경쟁 중 한 건만 상태 전이. status=0 실패 tx는 소비하지 않음. 성공 receipt를 UNKNOWN으로 보류한 뒤 같은 tx/hash로 복구. 실제 로그는 해당 Proof의 register/revoke/consume 각각 1개, 문서 consume 0개. 반복 폐기 tx 없음, consume 이력 보존.
- 실제 등록 UNKNOWN: chain commitment가 존재해도 등록 확정 전 ACTIVE 표시 없음; 동일 Operation 복구 뒤 ACTIVE 확인.
- `forge test --root packages/contracts --summary`: **22 passed**, B 기존 Contract·서명/기간/권한/경쟁 검사 재실행.
- Ruff 전체, 변경 Python format, 생성 TypeScript `tsc --noEmit`, 저장소 구조 검사, compileall·diff 검사 통과.
- 임시 DB에 migration 0001→0005 적용 및 `alembic check` 통과. 기존 Operation/Proof 테이블을 재사용하여 추가 migration은 없습니다.

재현 전 폐기 가능한 DB와 새 Anvil을 준비하고 B deploy_local.py로 세 계약 manifest를 생성합니다.
`API_DATABASE_URL`로 해당 DB에 `alembic -c apps/api/alembic.ini upgrade head`를 실행합니다.
live 검사는 `TEST_DATABASE_URL`, `TEST_CHAIN_RPC_URL`, `TEST_CHAIN_MANIFEST`를 지정한 뒤
`pytest apps/api/tests/test_live_finals.py`로 실행합니다. live 검사는 합성 계정·키·tx를 생성하고
임시 체인 시각을 진행하므로 보존 DB/운영 체인에 실행하지 않습니다.
생성 계약은 `scripts/generate_schemas.py`, `scripts/generate_api_contracts.py`가 원본입니다.

## 다음 담당자와 병합

- A: 생성 `ProofMutation`/ProofView로 등록 대기·복구·폐기·1회 사용 화면을 연결하고 verify의 lifecycle/reason/scope를 표시합니다. 조회 버튼에서 consume하지 않습니다.
- B: 본인 W3/W4 원본의 단계 PR·리뷰와 C의 실제 Adapter 소비 경계를 확인합니다.
- D: 새 세션·브라우저·다른 환경에서 독립 재현 및 실패/경쟁 사례를 확인합니다.
- C: W4 단계 생성/선행 병합 뒤 준비 PR을 phase/W4로 옮겨 재검증합니다. 후속 W5/W6 보안 branch에도 병합된 W4 결과를 반영해야 합니다.

실제 브라우저·D 독립 QA·외부 리뷰·공유 phase/integration 승격은 이번 검사에 포함하지 않습니다.
