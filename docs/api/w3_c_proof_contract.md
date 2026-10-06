# W3-C1~C3 — 두 유형 발행·조회·검증 인계

- 담당 C / @Jordi2801K. 기준 `phase/W2@1f8ed63`, PR #32/#33의 실제 모델·키/Operation 구현 재사용.
- C 구현·합성 HTTP/DB 검사 및 실제 PostgreSQL/Anvil 검사 완료. A 화면 연결, B의 W3-B1/B2 소비자·서명 교차 리뷰, D 독립 재현은 대기입니다.
- 기존 v1 저장·서명·endpoint는 유지하며 v2는 `finals_proofs`에 따로 저장합니다. migration 0005 필요.

## HTTP 계약

| 경로 | 권한 | 결과 |
| --- | --- | --- |
| GET /v2/issuer/recipients | issuer | 준비된 수신자 opaque ID/합성 표시 이름; token 없음 |
| POST /v2/issuer/proofs | issuer + CSRF | ProofView: 서버가 만든 ID·기관·키·유형·시각·공개 조회 경로 |
| GET /v2/issuer/proofs | 자기 기관 issuer | 최신 100개 ProofView; 타 기관 관리 목록 제외 |
| GET /v2/proofs/{id} | 공개 | ProofView만; payload·대상 참조·계정·salt/token 없음 |
| GET /v2/proofs/{id}/content | 자기 기관 issuer 또는 binding이 맞는 지정 recipient | signed envelope와 합성 target_ref; 타 기관/수신자는 404 |
| POST /v2/proofs/{id}/verify | ID 검사 공개, candidate 비교는 위 content 권한 필요 | FinalsVerificationResult; 읽기 전용이며 consume 없음 |

발행 예시:
```json
{"request_id":"req_issue_001","recipient_id":"acct_recipient_demo","expires_at":"2026-12-01T00:00:00Z","content":{"proof_type":"PAYMENT_REQUEST","amount_minor":10000,"currency":"KRW","target_ref":"SYNTHETIC-INVOICE-001"}}
```
문서는 content를 `proof_type=OFFICIAL_DOCUMENT`, `institution_code=ORIGIN_MOCK_OFFICE`,
`document_type`, `document_number`, 양의 정수 `version`으로 바꿉니다.
`API_FINALS_PAYMENT_ISSUER_ID` 기본 `iss_origin_mock_bank`,
`API_FINALS_DOCUMENT_ISSUER_ID` 기본 `iss_origin_mock_office`,
`API_FINALS_DOCUMENT_INSTITUTION_CODE` 기본 `ORIGIN_MOCK_OFFICE`가 서버 허용 대응입니다.
합성 테스트의 동적 기관 ID만 테스트 settings에서 대응을 지정합니다.
클라이언트 issuer/key/proof ID·발행 시각·nonce·binding·signature 지정은 금지합니다.

비교 요청은 `{"request_id":"req_compare_001","candidate":{"amount_minor":10000,"currency":"KRW","target_ref":"SYNTHETIC-INVOICE-001"}}`입니다.
문서는 institution_code/document_type/document_number/version을 비교합니다.
`candidate` 생략은 PROOF_ONLY, 일부 누락은 PARTIAL_COMPARISON/INCONCLUSIVE,
실제 불일치는 TAMPERED가 우선입니다. 임의 target_hash 대신 권한 있는 원문 target_ref를
서버에서 동일 hash로 계산합니다. ID만 조회해 받은 자료까지 일치한다고 표시하지 않습니다.

## 저장·서명·실패 경계

기관·현재 선택 키·배포·키 소속/signer·발행 당시 기간·보호된 signer challenge를 재검사합니다.
W2의 PostgreSQL transaction advisory lock을 공유해 발행과 키 교체/폐기 API를 직렬화합니다.
발행·수신자별 비공개 token·Proof별 32-byte salt·binding·감사 이력을 하나의 DB transaction으로 저장합니다.
각 발행의 ID/salt/nonce는 새 무작위 값입니다. token/salt는 API와 envelope에서 제외합니다.
동일 (account_id, request_id)·입력은 기존 결과, 변경 입력/기관은 409입니다.
서명·저장 실패는 성공 응답을 반환하지 않습니다. 이미 저장된 동일 요청은 키 교체 후에도 원래 Proof를 반환합니다.

Proof는 발행 당시 deployment_id를 저장합니다. 재배포 mismatch 또는 RPC 오류는
INCONCLUSIVE/DEPENDENCY_UNAVAILABLE이며 과거 DB 기록을 현재 체인 성공 근거로 쓰지 않습니다.
기관/유형·문서 코드·수신자·CSRF·엄격 정수·시간 입력을 검사합니다.

## W3 최초 산출물과 W4 후속 경계

W3는 실제 기관/키 조회·서명·내용 비교를 제공합니다. ProofStatusRegistry는 아직 없으므로
`proof_status=NOT_RUN`, `lifecycle_status=null`입니다. VERIFIED만으로 현재 사용 가능을 주장하지 않습니다.
키 폐기·기관 중지·만료의 확인된 원인은 reason_codes로 남기며 전체 lifecycle 성공은 만들지 않습니다.
W4-C1은 신규 키 확정 후 새 발행 전환·과거 서명 보존을 연결합니다.
Proof 폐기·consume·원자적 경쟁은 W4-B1/B2/B3와 W4-C2/C3에서 별도 구현합니다.

## 검사·인계

- 합성 HTTP/SQLite/실제 서명: 5개 검사, 두 유형·경쟁 동일 ID·권한·누락/변조·저장 rollback·RPC·재배포·signer/기간/입력 거부.
- 전체 Python 236 passed / opt-in 5 skipped; Ruff 통과.
- 별도 실제 PostgreSQL/Anvil: `apps/api/tests/test_live_finals.py` 1 passed, 두 유형 새 발행/서명·경쟁 재시도·지정 사용자 비교·변조/공개성 검사.
- migration 0001→0005 및 alembic check 통과. 기존 데모 DB/chain은 변경하지 않았습니다.
- 생성 원본: finals_proofs.py; `make generate`로 OpenAPI·types/api.ts 생성. 생성 파일을 손으로 수정하지 않습니다.
- A: 위 경로/생성 타입으로 W3 발행·목록·공개 조회·권한 있는 비교 화면 연결.
- B: 기존 Reader 소비 경계와 v2 Golden digest/domain 교차 확인, W3-B3 Proof 상태 계약 제공.
- D: 독립 새 세션/브라우저·별도 환경·실패 주입 검증. 이번 검사는 실제 브라우저 성공 증거가 아닙니다.


## W4 후속 변경

`feat/w4-c-proof-lifecycle` / C `596f313`에서는 B W3-B1의 동일 블록 기관/키 snapshot과
W4-B의 실제 ProofStatusRegistry를 연결했습니다. 위 NOT_RUN/null은 최초 W3 branch의 범위입니다.
후속 branch는 등록 Operation·현재 lifecycle·폐기/consume을 제공하며 Registry/RPC가 없으면
W3 성공으로 우회하지 않습니다. ProofView의 등록 상태·Operation ID와 신규 API/오류는
[W4 lifecycle 인계](w4_c_proof_lifecycle_contract.md) 및 재생성 OpenAPI/타입을 사용합니다.
