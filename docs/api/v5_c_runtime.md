# 5.1 C 독립 DB/API 인계

V5-W1~W5-C의 독립 구현입니다. 재사용 원본·브랜치는 [구현 기록](../handoffs/v5_c_implementation.md), 모델은 [공유 계약](../shared_contract_v5.md)을 따릅니다. B의 새 Registry/Adapter, A 지갑 화면, D 실제 분석기는 연결 전입니다. 이 문서의 합성 검사 통과가 해당 팀원의 구현·리뷰·단계 완료를 뜻하지 않습니다.

## 계약과 기동

- 현재 HTTP 정의: [실제 앱 OpenAPI](../../packages/schemas/generated/openapi.json). `create_app().openapi()`에서 생성합니다.
- 신규 타입: [wallet-contract.ts](../../packages/schemas/generated/types/wallet-contract.ts). 기존 api.ts의 v1/v2 `OperationView`와 이름이 같으므로 모듈을 구분합니다.
- [예정 OpenAPI](../../packages/schemas/generated/openapi/wallet-contract.openapi.json)는 최초 22개 경로의 검토 기준을 보존합니다. 실제 추가 경로·응답은 앱 OpenAPI를 사용합니다.
- 계약 개정은 `v5-shared-0.2`입니다. 분석의 선택 `verification_session_id`, 작업 `error_code`, 근거 개수/길이 제한과 독립 API 구현을 반영했습니다. EIP-712/domain 버전·내용 schema·서명 digest·Registry ABI는 바뀌지 않았습니다. 빈 quote는 이제 거부합니다.

```sh
PYTHONPATH=apps/api/src:packages/python:services/indexer/src uv run --all-packages --all-groups alembic -c apps/api/alembic.ini upgrade head
PYTHONPATH=apps/api/src:packages/python:services/indexer/src uv run --all-packages --all-groups python scripts/generate_api_contracts.py
```

기존 `API_DATABASE_URL`을 확인하고 백업·대상을 검토한 뒤 적용합니다. 실제 검사는 사용자 DB 대신 폐기 가능한 PostgreSQL 16.4에서 수행했습니다. 신규 migration은 `0007`(기관 확인/서명/제안/문서/입력/분석), `0008`(요청 충돌/검증 세션), `0009`(분석 검증 사본/세션 소유권)입니다. 기존 v1/v2 행을 변환하지 않습니다. `0009 → 0008 → 0009` 왕복과 schema check를 확인했습니다. downgrade는 새 열/테이블의 자료를 지우므로 운영 rollback 명령으로 그대로 사용하지 않습니다. DB rollback으로 확정 체인 거래를 되돌릴 수 없습니다.

`create_app(wallet_chain=adapter, analysis_processor=processor)`에 실제 구현을 주입합니다. 주소 설정만으로 Adapter가 생기지 않습니다. 미주입 Registry는 503, 분석기는 `FAILED / ANALYZER_UNAVAILABLE`입니다. 기본값에 성공 mock이나 기관 업무 개인키를 넣지 않았습니다.

| 설정 | 기본값과 의미 |
| --- | --- |
| `API_WALLET_REGISTRY_ADDRESS` | 없음. B의 새 배포 주소와 기존 `API_BLOCKCHAIN_CHAIN_ID`가 서명 domain입니다. Golden 주소를 운영 값으로 복사하지 않습니다. |
| `API_WALLET_OPERATOR_ADDRESSES` | `{}`. 서버 계정→승인 지갑 주소 JSON. operator 역할과 실제 `is_approver`를 모두 검사합니다. |
| `API_WALLET_INTERNAL_APPROVERS` | `{}`. 내부 issuer ID→같은 기관의 별도 승인 계정 ID JSON. 자기 승인은 거부합니다. |
| `API_WALLET_DEMO_EMAIL_ENABLED` | false. 두 합성 명부의 `.example.invalid` 데모 전달만 허용합니다. |
| `API_WALLET_TEXT_INPUT_ENABLED` | false. V5-Q01 선정 전 합성 텍스트 검사만 opt-in하며 이미지/PDF/STT는 활성화하지 않습니다. |
| `API_WALLET_RELAY_ENABLED` | false. 직접 기관 거래가 기본입니다. true이면 같은 port의 submit을 호출하며 불명확한 제출은 재전송하지 않습니다. |

readiness는 migration head·세 역할·설정된 두 기관 계정·Registry 조회·활성 projection/worker 상태를 검사합니다. 신규 지갑 모드에서 서버 기관키 디렉터리를 요구하지 않습니다. 기존 projection은 구 Registry용이므로 실제 새 projection 연결을 별도로 확인합니다. 기존 DB·기존 기동 명령은 그대로 유지합니다. 새 모드의 두 계정 기관 ID는 명부의 iss_origin_mock_bank/iss_origin_mock_office와 맞춰 준비하며, 개인 .env의 기존 finals 기관 ID/projection 설정을 검토합니다.

## 의존성 상향 승인

| 패키지 | integration `1d9b349` | `phase/W5` |
| --- | --- | --- |
| fastapi | 0.115.14 | 0.142.2 |
| starlette (uv 제약) | 0.46.2 | 1.7.0 |
| pytest | 8.4.2 | 9.1.1 |
| pytest-asyncio | 0.25.3 | 1.4.0 |

출처는 미병합 종료된 #38 계열의 `28a3e00`(2026-10-03, "patch shared security dependencies")이며 C W1 재사용 기준(#57)으로 들어왔습니다. httpx·pydantic·uvicorn은 바뀌지 않았습니다. 2026-10-19 C(사용자님 `@Jordi2801K`)가 lockfile 조율 담당(AGENTS 4절)으로서 위 버전을 승인했습니다. 근거는 `phase/W5` `15c5588`의 Quality Gate SUCCESS와 같은 소스의 전체 Python 601 PASS / 9 SKIP입니다. 실행 이미지·웹 등 다른 소비자 영향은 각 담당 리뷰에서 확인합니다. eth-abi의 API 실행 의존성 이동은 B #64 범위로 따로 다룹니다.

## A: 화면에서 사용할 순서

기존 `/v1/auth/login` 세션 cookie와 상태 변경의 `X-CSRF-Token`을 재사용합니다. 실제 계정 ID·기관은 세션에서 결정합니다. 비공개 객체의 타인 접근은 404입니다. v3 오류는 `detail`·선택 `field_paths`와 `Retry-After`를 읽으며 제출값 전체를 오류에 넣지 않습니다.

1. 기존 기관 신청 후 `/v3/issuer-applications/{id}` 아래 `email-codes`, 소유자 전용 `demo-inbox`, `email-verifications`, 별도 지정 계정의 `internal-approvals`를 사용합니다. 명부/메일/내부 승인만으로 체인 기관이 활성화되지 않습니다.
2. 신청자의 `key-challenges` → 지갑 KeyProof 서명 → `key-proofs` 후 operator가 `proposals`를 준비합니다. 생성 시 승인 수는 0입니다. 실제 propose/approve 거래를 `/proposals/{id}/transactions` 또는 `/approvals`로 접수합니다. 서로 다른 두 승인자가 체인에서 실행해야 활성화됩니다.
3. `document-drafts`에 `request_id`, `doc_key`, 정확한 다음 `expected_version`, `expires_at`, `content`를 보냅니다. 응답의 불변 원본 bytes·보호 hash·domain/message를 재계산해 지갑에 표시합니다. `publications`에는 `request_id`, `signing_request_id`, `signature`만 제출합니다.
4. 접수된 원본/서명/Operation이 저장된 뒤 지갑의 실제 publish txHash를 `/signing-requests/{id}/transactions`에 같은 `signing_request_id`와 새 `request_id`로 전달합니다. `202/PENDING_SUBMISSION`은 확정이 아닙니다. `UNKNOWN/SUBMITTED`는 `/operations/{id}/reconcile`로 기존 거래부터 조회합니다. 기한 경과·현재 nonce/미발행 확인 후에만 `FAILED/SIGNATURE_EXPIRED/RESIGN`을 안내합니다.
5. `revoke-drafts` → 별도 Revoke 서명 → `revocations`도 같은 흐름입니다. 정지 중 현재 비사고 키의 철회는 허용합니다. 최신 버전 철회로 과거 버전을 복구하지 않습니다.
6. 공개 `/documents/{id}`는 version 생략 시 최신을 명시합니다. `/verification-material`은 기관 원본·서명과 체인 식별을 제공합니다. 만료/미보관은 410입니다. `/verifications`에는 `request_id`가 필수입니다. ID 단독은 INCONCLUSIVE이며 전체 필드/원본 비교와 구분합니다. 원본이 없어도 확인 가능한 정지/사고 경고를 유지합니다.

같은 request ID의 본문 변경은 409입니다. 잘못된 직접 txHash는 올바른 서명 요청을 영구 무효화하지 않습니다. nonce는 가스 nonce와 별개이며 같은 배포(chainId·Registry 주소)에서 같은 기관의 미확정 업무 nonce가 있으면 409입니다. 이전 배포의 미해결 작업은 삭제하지 않고 보존하되 현재 배포의 예약으로 보지 않습니다. 구 `/v1/operations/{id}/recover`로 신규 작업을 복구하지 않고 v3 reconcile을 사용합니다.

정상·거부 요청의 실행 가능한 예시는 [HTTP 검사](../../apps/api/tests/test_wallet_runtime.py)와 [분석 검사](../../apps/api/tests/test_wallet_analyses.py)에 있습니다. 기존 v1/v2 binding·consume은 그대로 보존하며 새 공개 문서에 consume을 추가하지 않습니다.

## B: 실제 Adapter 경계

[WalletRegistry](../../packages/python/originproof_core/wallet_ports.py)를 구현합니다. `issuer/key/document/proposal`은 같은 canonical block의 chain/contract·blockNumber/hash와 키 등록/정상 교체/사고 이력을 제공합니다. API는 domain과 모델 제약을 다시 검사합니다. 검증 결과의 서로 다른 조회 block은 INCONCLUSIVE입니다.

`transaction/find_transaction`의 arguments는 실제 calldata를 ABI로 해독한 값입니다. 요청 intent를 그대로 돌려주는 구현은 허용되지 않습니다. 실제 배포, canonical receipt, 필요한 이벤트·현재 상태·발신자를 검증해야 CONFIRMED입니다. publish/revoke는 message+signature, propose는 proposal+proof+signature, approve는 proposalId를 정확히 대조합니다. REACTIVATE의 실제 proof는 전 필드 0, signature는 `0x`이며 API의 선택 key_proof=null을 calldata null로 해석하지 않습니다. 철회 확정에는 REVOKED 상태가 필요합니다.

`find_transaction`은 기존 intent/nonce를 검색하고 거래를 새로 보내지 않습니다. 저장된 원본/기관 서명은 제출 전에 commit됩니다. 서버는 기관 키를 만들거나 수집하지 않으며 가스 중계와 기관 업무 권한을 분리합니다. 새 배포 manifest/실제 Adapter·체인 원자성/G07 혼합 환경은 아직 검증하지 않았습니다.

## D: 분석·검증 집계와 보관

async processor는 텍스트를 받아 공통 `AnalysisReport` 또는 해당 dict를 반환합니다. API가 실제 quote·Unicode 코드 포인트 위치를 대조하며 빈/모호한 인용·틀린 범위·텍스트에 대한 page/time 위치를 거부합니다. `verification`을 provider가 정하면 `ANALYZER_AUTHORITY_VIOLATION`입니다. 모델의 발행 진위 추론을 체인 결과로 저장하지 않습니다.

선택 `verification_session_id`는 C가 생성한 24시간 검증 세션입니다. 소유자 세션은 본인만, 공개 세션은 공개 범위에서 연결하며 기존 소유권 불명 LEGACY 세션은 거부합니다. 해당 결과는 분석 요청 때의 사본과 checked_at으로 보관합니다. 분석 입력과 검증 비교 범위는 각각 표시하며 보고서의 과거 검증을 현재 사용 가능 판정으로 재사용하지 않습니다. 위험 수준과 발행 검증은 독립입니다.

`POST /v3/inputs` → `POST /v3/analyses` → 작업 GET/이력 GET/보고서·원본 다운로드/DELETE를 사용합니다. 계정당 실행 1건·10분당 5건·작업 전체 180초이며 동일 요청/입력의 중복 실행을 방지합니다. 삭제는 CANCELLED를 먼저 저장해 늦은 응답의 재저장을 막습니다. 재시작 시 RUNNING은 실패 처리하고 유효 QUEUED만 재개합니다.

| 자료 | 보관/접근 경계 |
| --- | --- |
| 미선택 원본 | 처리 직후 삭제, 실패 잔여물은 수락 후 최대 1시간 |
| 미선택 보고서 | 종료 후 10분 |
| 선택 보고서 | 종료 후 7일 |
| 별도 선택 원본 | 입력 수락 후 7일 |
| 기관 발행 원본/서명 | 해당 버전 expiresAt 이후 30일; 사용자 분석 삭제와 독립 |
| 검증 세션 | 24시간 |
| 신규 Operation/감사 | 해결 후 30일, 미해결 작업·해결 시각 없는 기존 작업은 보수적으로 보존 |

접근은 만료 시각부터 거부하고 물리 정리는 기동/접수/5분 주기 maintenance에서 수행합니다. 두 보관 옵션의 네 조합을 검사했습니다. worker는 현 P0의 단일 API 프로세스 내부 task입니다. 여러 API worker에서의 재시작 판정·분산 작업 실행은 기존 queue로 옮기고 검증해야 합니다. 현재는 단일 worker로 실행합니다. processor의 안전한 code(REFUSAL/TIMEOUT/RATE_LIMIT/INCOMPLETE_OUTPUT 등)는 구분하고 예외 메시지·원시 응답은 복제하지 않습니다. 실제 D 모델 연결·유료 평가·처리 성능은 미검증입니다.

## 재현한 검사

```sh
PYTHONPATH=apps/api/src:packages/python:services/indexer/src:services/analyzer/src uv run --all-packages --all-groups --frozen pytest -q apps/api/tests packages/python/tests services/analyzer/tests services/indexer/tests scripts/ci
forge test --root packages/contracts --offline
node scripts/ci/check_wallet_browser_hashes.mjs
```

PostgreSQL 동시성은 `V5_C_TEST_DATABASE_URL`이 있는 경우에만 [별도 검사](../../apps/api/tests/test_wallet_postgres.py)를 실행합니다. 주소는 127.0.0.1, DB명은 `originproof_v5_c_test_` 접두사이고 새 migration head·빈 계정 테이블이 필요합니다. 합성 DB를 스스로 삭제하지 않습니다. 결과/환경은 구현 기록을 확인합니다. Registry 증거와 분석기는 합성이며 실제 EVM/브라우저 E2E·작성자 외 리뷰를 대신하지 않습니다.
