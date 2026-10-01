# W2-C1~C3 — 실제 기관·키 API 인계

- 기준: phase/W2 e40191f, 승인 정책 ADR 0001, B Adapter PR #26의 최신 741b8f8.
- W1-C3 PR #32의 모델을 작업 브랜치에 포함했습니다. W1/W2 공통 브랜치 병합은 별도입니다.
- 상태: C 구현 및 실제 PostgreSQL·B Adapter·Anvil 연결 검사 완료. A 화면 연결·D 독립 검증·작성자 외 리뷰 대기.

## A가 연결할 경로

변경 요청은 세션 cookie와 `X-CSRF-Token`을 요구합니다. request_id는 req_ 접두사,
reason은 비어 있지 않은 문자열입니다. 모든 키 생성/보관/challenge는 서버에서 수행합니다.

| HTTP 경로 | 권한·입력 | 결과 |
| --- | --- | --- |
| POST /v1/operator/issuer-applications/{application_id}/decision | operator, 기존 APPROVE/REJECT·reason | 기존 ApplicationView; APPROVE는 APPROVED_PENDING_CHAIN |
| POST /v1/operator/issuer-applications/{application_id}/activate | operator, request_id·reason | OperationView; 실제 체인 등록·확인 후 신청 ACTIVE |
| POST /v1/operator/issuers/{issuer_id}/suspend | operator, request_id·reason | OperationView |
| POST /v1/operator/issuers/{issuer_id}/reactivate | operator, request_id·reason | OperationView |
| POST /v1/operator/issuers/{issuer_id}/revoke | operator, request_id·reason | OperationView; 기관 영구 폐기 |
| GET /v1/issuer/status | 자기 기관 issuer | issuer_id·현재 체인 status·deployment_id·chain_id |
| POST /v1/issuer/keys | 활성 기관 issuer, request_id·reason·valid_from·valid_until | OperationView; target_id가 생성 key_id |
| GET /v1/issuer/keys | 자기 기관 issuer | KeyView[] |
| GET /v1/issuer/keys/{key_id} | 자기 기관 issuer | KeyView; 타 기관은 404 |
| POST /v1/issuer/keys/{key_id}/revoke | 자기 기관 issuer, request_id·reason | OperationView |
| GET /v1/operations/{operation_id} | 요청자·동일 기관·operator | OperationView |
| POST /v1/operations/{operation_id}/recover | 요청자·operator, CSRF | 기존 제출의 receipt/상태 복구; 새 tx 제출 없음 |
| GET /v1/audit-events | 자기 기관·operator | AuditView[]; 자기 기관 범위 제한 |

승인 화면은 기존 decision 후 activate를 호출해야 합니다. 기존 W1 응답 계약을 보존하기 위해
검토 결정만으로 자동 체인 등록하지 않습니다. 등록/폐기 뒤 Operation이 CONFIRMED인지 확인하고
기관/키를 다시 조회합니다. FAILED/UNKNOWN을 성공 표시하지 않습니다.

키 등록 예시:
```json
{"request_id":"req_demo_key_001","reason":"합성 발행 키 등록","valid_from":"2026-10-01T00:00:00Z","valid_until":"2026-11-01T00:00:00Z"}
```
시각은 timezone을 포함한 초 단위이며 valid_from < valid_until입니다. 서버가 256비트 무작위
서명기와 key ID를 만들고 challenge로 공개 signer 대응을 확인합니다. 공개 응답은 key ID,
issuer ID, signer, 정수 초 기간, status, selected, deployment ID만 포함합니다.
정상 교체는 새 등록 확정 뒤 selected를 전환하며 이전 키를 자동 폐기하지 않습니다.

## Operation 저장과 실패 경계

- 유일 범위: (account_id, action, request_id). 본문/기관 충돌은 409 REQUEST_ID_CONFLICT.
- action: register_issuer, suspend_issuer, reactivate_issuer, revoke_issuer, register_key, revoke_key.
- 상태: PENDING_SUBMISSION → SUBMITTED → CONFIRMED. 확실한 실패는 FAILED, 불명은 UNKNOWN.
- 전송 전 B prepared recovery_reference(action/deployment/chain/sender/contract/data/nonce/scan)을
  DB에 commit합니다. tx hash 수신 직후 별도 commit하며 마지막 DB 반영 실패도 동일 tx로 복구합니다.
- fixed nonce와 deployment를 복원하고 B recover_prepared로 기존 블록·pending/receipt를 확인합니다.
  준비만 저장되고 전송 여부가 불명확한 경우에도 자동 재전송하지 않습니다. 작업은 UNKNOWN으로
  남길 수 있으며 새 nonce로 성공을 만들어 내지 않습니다.
- P0 체인 변경은 PostgreSQL advisory lock으로 프로세스 사이에 직렬화합니다. 재시작 시 DB의
  미확정 nonce 예약도 반영해 다른 작업이 동일 nonce를 재사용하지 않습니다.
- CONFIRMED는 B의 canonical 성공 receipt·1 confirmation·상태 재조회 결과입니다.
- 공개 chain_evidence는 tx/receipt/confirmation/재조회 정보이며 복구 calldata·secret 참조는 제외합니다.
- 같은 요청의 재시도는 기존 Operation을 반환합니다. 새 ID로 이미 폐기된 키를 다시 폐기하면
  현 Contract가 거절하므로 FAILED/CHAIN_REVERTED입니다. 미구현 idempotent Contract로 가정하지 않습니다.
- chain 오류는 503, 미승인/중지 기관 키 등록은 409, role/CSRF는 403, 미인증은 401입니다.

## 보호·재시작·migration

- API_SIGNER_DIRECTORY 기본값 build/secrets/issuer-signers. 디렉터리 0700·파일 0600·소유자 확인,
  symlink 거부, 독점 생성·fsync, 재시작 challenge 검증. 없어지거나 달라진 키를 자동 재생성하지 않습니다.
- Compose API의 issuer-signers named volume이 /app/build/secrets를 영속 보관합니다.
  demo-reset의 volume 삭제는 해당 합성 서명기도 삭제합니다. 보존 환경에서 임의 실행하지 않습니다.
- 키 폐기 요청은 확정 전에도 신규 발행 선택을 차단합니다. RPC/기간/폐기/다른 배포/secret 오류를
  ACTIVE 선택으로 표시하지 않습니다. 실제 발행 직전 기관/키/서명기 재검사는 W3에서 연결합니다.
- P0는 manifest의 unlocked 합성 issuer_account를 체인 호출자로 사용하고 기관별 발행 서명기는
  별도로 만듭니다. 브라우저 계정과 EVM 계정은 동일 신원이 아니며 API 세션이 기관 권한 경계입니다.
- 0003 Operation 준비 migration과 0004 복구·키 테이블을 적용합니다. 0004는 기존 nullable
  created_at을 backfill 시각으로 채우고 NOT NULL을 맞춥니다. 원래 사건 발생 시각을 복원했다고 주장하지 않습니다.
- 0004 downgrade는 신규 키·복구 데이터를 제거하므로 보존 DB에서 실행하기 전 별도 확인이 필요합니다.
- API Schema/TypeScript: packages/schemas/generated/openapi.json, generated/types/api.ts.
  `make generate`로 원본에서 재생성합니다. 생성물은 손으로 고치지 않습니다.

## 실제 검사와 다음 담당자

- 전체 Python 171 passed, live opt-in 2 skipped; Indexer 60 passed / live opt-in 1 skipped.
- 별도 실제 PostgreSQL+Anvil: live W1/W2 2 passed. DB migration upgrade/downgrade/upgrade와
  alembic check 통과. 기존 실행 중인 데모 DB·체인은 변경하지 않았습니다.
- 동시 같은 ID, 변경 입력 충돌, 권한/CSRF, 실제 응답 유실 후 재시작 복구, 키 교체/폐기,
  실패 receipt, final DB 실패/prepare 저장 실패를 검사했습니다.
- Ruff·TypeScript 생성 타입 검사·byte-for-byte 재생성 통과. v1 Golden 변경 없음.
- A: 위 경로/타입으로 기관 상태와 실제 키 화면 연결.
- B: persistence callback·복구·nonce/체인 권한 경계 소비자 리뷰.
- D: 실제 브라우저·별도 환경·RPC 실패 주입과 독립 단계 검증.
- C: 리뷰 수정·주차별 PR 반영·개인 기록·단계 통합 조율. W3 발행과 W4 consume은 이번 구현 범위 밖입니다.
