# ADR 0001 — 본선 두 유형·상태·키·수신자·체인 처리

> **2026-10-13 적용 안내:** 이 문서 본문은 당시 결정 기록입니다. 신규 개발은 [ADR 0004](0004-v5-governance-wallet-versioning.md)와 [최신 개발 계획서](../development_plan.md)을 따릅니다. 공동승인·기관 지갑 서명·문서 버전·입력 미정 정책은 새 결정으로 대체되며, 기존 v1/v2 자료의 서명·권한·상태·consume과 명시적으로 유지한 기본값은 보존합니다.

- 상태: **과거 정책 승인 / ADR 0002·0004로 부분 대체 / 기존 버전 계약 보존 / 구현·연결 완료와 별개**
- 결정일: 2026-09-30
- 근거: 사용자님이 지침 정리 계획의 기술 결정 권장 방향 전체를 승인하고 개발 계획서 v3.0 반영을 요청하셨습니다.
- 담당: C(모델·API·인증·서명기), B(Contract·Adapter·체인 권한), A(입력·결과 화면), D(합성 사례·독립 확인).
- 관련 작업: W1-B1/B2/C1/C3, W2-B1/B2/C1~C3, W3 전체, W4 전체, W5~W7 통합·재현.
- 범위: 합성 기관·준비된 테스트 계정·로컬 EVM의 P0 시제품. 실제 기관 신원 확인이나 외부 지갑 기반 수신자 인증을 구현했다고 주장하지 않습니다.

## 배경과 기존 구현

2026-10-08 추가: [ADR 0002](0002-v4-hybrid-verification.md)가 기관 인증·납부 보호 필드 확장·AI 분석·저장/보관·공개 체인/별도 검증 목표를 변경합니다. 아래는 v3.0 결정과 당시 구현 기록이며, 기존 schema 2.0.0의 서명·권한·상태 규칙은 해당 버전의 계약으로 유지합니다. 새 목표를 기존 코드가 지원한다고 간주하거나 기존 서명을 소급 변경하지 않습니다.

개발 계획에는 기능·주요 필드·권한이 정해져 있지만 키 교체 후 과거 Proof, 만료 결과 조합, binding 저장과 consume 권한 전달 방식이 남아 있었습니다. 이 결정으로 해당 정책을 확정하고 구현자는 계약 원본·생성물·테스트를 맞춥니다. 담당자 리뷰는 정책 재승인이 아니라 구현·ABI·보안 경계의 적합성 확인입니다.

기존 카드 v1은 `CARD_PAYMENT_NOTICE`, `schema_version=1.0.0`, `originproof.mvp` domain의 seed/Golden Fixture, 현재 서명 알고리즘을 사용합니다. 만료 시 서명을 검사하기 전에 `INCONCLUSIVE + EXPIRED`를 반환합니다. 해당 기존 endpoint와 fixture는 회귀로 보존합니다. 현재 Reader에는 기관·키 조회만 있고 ProofStatusRegistry는 추가 구현이 필요합니다.

W1 계정/신청과 W2 Operation 준비 코드는 `feat/w1-c-independent@167e0a9`, `feat/w2-c-operations-prep@89bb658`에 있습니다. 이는 재사용 후보의 위치이며 integration 병합·본선 완료 증거가 아닙니다. 연결 시 실제 최신 SHA와 검사를 확인합니다.

## 1. 두 유형과 서명 버전

P0는 `Origin Mock Bank`의 `PAYMENT_REQUEST`, `Origin Mock Office`의 `OFFICIAL_DOCUMENT`로 고정합니다. 둘 다 실제 기관과 무관한 합성 발행자입니다. 새 두 유형의 schema version은 `2.0.0`, app domain은 `originproof.finals`로 구분합니다. signature scheme은 `ECDSA_SECP256K1_KECCAK256_V1`을 유지합니다. chain ID는 배포 manifest와 일치해야 합니다.

[기존 서명 명세](../signing_spec.md)의 envelope 필드·Keccak-256·recoverable secp256k1·NFC/trim·정렬 JSON·UTC 직렬화를 재사용합니다. null 포함 방식도 기존과 동일합니다. 새 payload는 유형별 모델로 추가하고 알 수 없는 필드를 거부합니다. 새 유형에 v1 판정을 적용하거나 기존 v1 Proof를 v2로 재서명하지 않습니다.

| 유형 | 필드 | 필수·검증·비교 규칙 |
| --- | --- | --- |
| PAYMENT_REQUEST | `amount_minor`, `currency` | 필수. 양의 최소 화폐 단위 정수와 대문자 3자리 통화 코드. 금액 비교는 부동소수점을 사용하지 않습니다. |
| PAYMENT_REQUEST | `payer_binding` | 필수. envelope의 subject_binding_hash와 동일하며 서버가 수신자 계정에서 생성합니다. |
| PAYMENT_REQUEST | `beneficiary_binding` | 필수. 발행기관 ID·domain·chain ID를 결합한 canonical hash. 서버가 생성하며 실제 계좌번호를 넣지 않습니다. |
| PAYMENT_REQUEST | `target_hash` | 필수. 합성 요청 대상 참조 문자열의 canonical hash. 원문 참조는 서버에 두고 비교 권한이 있는 사용자에게만 공개합니다. |
| OFFICIAL_DOCUMENT | `institution_code` | 필수. 준비된 합성 기관 코드와 발행기관의 대응을 서버에서 검사합니다. |
| OFFICIAL_DOCUMENT | `document_type`, `document_number` | 필수. 정규화 후 빈 문자열을 거부하고 받은 문서와 비교합니다. |
| OFFICIAL_DOCUMENT | `subject_token` | 필수. 계정 ID 대신 이 Proof의 subject_binding_hash 값을 사용합니다. 클라이언트가 임의 지정하지 않습니다. |
| OFFICIAL_DOCUMENT | `version` | 필수. 양의 정수인 문서 개정 번호입니다. schema_version과 별개이며 수정본은 새 Proof ID로 발행합니다. |

Envelope의 proof/issuer/key ID, 두 유형, schema/signature version, chain ID, domain, payload hash, subject binding, issued_at, expires_at, nonce, single_use는 필수입니다. `metadata_hash`만 선택(null 가능)입니다. 신규 ID·nonce는 서버가 생성하고 nonce는 최소 128비트 무작위 값을 사용합니다. v2 시각은 timezone을 포함하며 초 단위로 검증해 체인 정수 초와 일치시킵니다. `issued_at < expires_at`, 유효 구간은 `[issued_at, expires_at)`로 고정합니다. 발행 시각은 서버 현재 시각이고 사용자가 소급 지정할 수 없습니다.

PAYMENT_REQUEST는 `single_use=true`, OFFICIAL_DOCUMENT는 `single_use=false`입니다. 두 유형 모두 수신자를 지정하고 만료 시각을 입력합니다. 문서형 consume은 거부합니다. 정규화와 payload/domain 서명 변경은 version과 별도 fixture로 식별합니다. `beneficiary_binding`은 기존 payload_hash 함수에 `{binding_domain: "originproof.beneficiary.v1", app_domain, chain_id, issuer_id}`를 전달한 값이고 `target_hash`는 `{target_domain: "originproof.target.v1", target_ref: <합성 참조>}`의 hash입니다. 필드명은 문자열 JSON key이며 값은 envelope/서버 참조에서 가져옵니다. 문자열 길이·API route 등 일반 구현 상세는 C가 모델·OpenAPI로 작성하고 소비자가 검토합니다.

## 2. 로그인·수신자 binding·보호된 저장

준비된 operator/issuer/recipient 계정을 사용합니다. 계정 role·issuer_id는 서버에서 공급하며 요청자가 바꿀 수 없습니다. 현재 독립 구현의 서버 세션 방식을 채택합니다: 8시간 고정 만료, 무작위 session token의 hash만 DB 저장, logout 시 폐기, host-only HttpOnly/SameSite=Lax cookie, 인증 후 변경 요청의 CSRF 확인. HTTPS에서는 Secure cookie를 사용하고 로컬 HTTP에서만 해제합니다. 기존 salt가 있는 PBKDF2-HMAC-SHA256 비밀번호 저장을 재사용합니다. 로그인 Origin 검사/요청 제한 등 누락 보호는 후속 구현 검사 대상입니다.

수신자 계정마다 무작위 비공개 recipient token을 서버에서 생성합니다. Proof마다 32바이트 무작위 salt를 생성하고 다음 canonical JSON의 Keccak-256을 binding으로 사용합니다. 문자열은 기존 canonicalization을 따르고 salt는 64자리 소문자 hex로 표현합니다.

```text
{ "binding_domain": "originproof.recipient.v1",
  "app_domain": <envelope domain>, "chain_id": <chain ID>,
  "proof_id": <Proof ID>, "recipient_token": <server token>, "salt": <salt hex> }
```

수신자 계정·recipient token·salt 대응은 서버 전용 저장에 두고 Proof와 원자적으로 저장합니다. salt/token은 공개 envelope·QR·온체인·로그에 넣지 않습니다. 같은 사람의 서로 다른 Proof를 공개 binding으로 연결하지 못하도록 salt를 재사용하지 않습니다. salt/token을 잃으면 binding을 임의로 재생성해 사용 권한을 복구하지 않습니다.

발행자는 준비된 합성 수신자 선택 목록의 opaque ID를 지정할 수 있지만 서버가 계정 존재·역할을 확인하고 binding을 계산합니다. consume 시 인증 계정의 token과 저장된 salt로 다시 계산해 서명된 binding과 비교합니다. body의 계정 ID·role·binding을 인증 근거로 사용하지 않습니다. 발행자 경로는 인증 계정의 기관과 Proof 발행기관 일치를 검사하며 타 기관은 거부합니다.

기관별 발행 개인키는 제한된 영속 secret 파일/볼륨(디렉터리 0700, 파일 0600 또는 동등 접근 통제)에 저장합니다. DB에는 key ID·공개 signer·보관 참조만 저장합니다. 재시작 시 challenge 서명으로 대응을 확인하고 키가 없거나 다르면 발행을 막습니다. recipient token/salt는 서버 전용 DB 권한·보호된 볼륨으로 보관하고 API/로그에서 제외합니다. 실제 KMS·외부 지갑은 P1입니다.

## 3. 정상 교체·키 만료·유출 폐기

정상 교체는 새 서명기 생성 → challenge 검증 → 체인 등록 확정·재조회 → DB의 발행 키 선택 전환 순서입니다. 실패 시 전환 전 상태를 유지합니다. 이전 키를 자동 revoke하지 않으며 더 이상 신규 발행에 선택하지 않습니다. 진행 중 발행과 교체는 일관된 키 선택을 사용하고 기관·키 상태를 발행 직전에 재검사합니다.

과거 Proof는 **발행 당시 키의 유효 구간**과 서명을 검사합니다. 정상 교체나 키 기간 종료만으로 이전 정상 Proof를 무효화하지 않습니다. 현재 키가 REVOKED이면 과거 서명이 수학적으로 맞더라도 lifecycle은 ISSUER_KEY_REVOKED로 사용 불가입니다. Proof 자체 만료·폐기·기관 중지는 각각 따로 반영합니다. 발행 당시 키 기간 밖의 Proof는 신뢰 검사를 통과시키지 않습니다.

유출 폐기는 즉시 신규 발행을 차단하고 키를 되살리지 않습니다. 해당 키의 모든 과거 Proof에 현재 사용 불가를 반영하는 보수적 정책이며 유출 시점을 추정해 일부를 살리지 않습니다. 정상 교체와 유출 폐기는 화면·감사 이력에서 다른 동작으로 표시합니다.

## 4. 검증 상태·현재 상태·검사 범위

v2의 verification_status는 발행 근거·서명·hash 및 요청한 비교 범위의 검사 결과이고 lifecycle_status는 현재 상태입니다. `VERIFIED` 하나만으로 현재 사용 가능을 뜻하지 않습니다. ID 조회의 scope는 `PROOF_ONLY`, 전체 필수 비교 성공은 `FULL_COMPARISON`, 비교할 자료가 일부 부족하면 `PARTIAL_COMPARISON`으로 구분합니다.

| 상황 | v2 결과 | 표시·처리 |
| --- | --- | --- |
| ID 조회의 발행 근거·서명·hash·현재 상태 확인 성공(최종 RC) | VERIFIED + 해당 lifecycle, PROOF_ONLY | 발행 기록만 확인; 받은 자료 내용 일치 주장은 금지 |
| 필수 비교 필드 전체 일치·정상 상태 | VERIFIED + ACTIVE, FULL_COMPARISON | 입력 자료의 보호 필드 일치 |
| 유효 서명/발행 근거, 만료·폐기·소비·중지 | VERIFIED + EXPIRED/PROOF_REVOKED/CONSUMED/ISSUER_SUSPENDED/ISSUER_KEY_REVOKED | 서명 근거는 일치해도 현재 사용 불가 |
| 서명/hash/비교 필드 불일치 | TAMPERED + 확인 가능한 lifecycle | 불일치 필드·사유, 서명 실패 뒤 신뢰할 수 없는 envelope 상태는 사용하지 않음 |
| Proof 또는 발행기관 미등록 | NOT_REGISTERED | 위조로 단정하지 않음 |
| 비교 필드 부족, 미지원 schema, domain/network 불일치, 키 미등록 또는 발행 당시 키 기간 불일치 | INCONCLUSIVE | 해당 실패/미실행 이유; ACTIVE 사용 가능 표시 금지 |
| RPC 등 신뢰 상태 조회 불가 | INCONCLUSIVE + null lifecycle | DEPENDENCY_UNAVAILABLE, 현재 유효 판정 보류 |
| 입력 형식·인증·권한 거부 | HTTP 422/401/403 또는 객체 존재를 숨기는 404 | 검증 성공 결과를 만들지 않음 |
| 내부 예외 | ERROR, 또는 처리 불가능한 요청은 HTTP 5xx | 민감 상세 없이 오류 표시, 성공으로 치환 금지 |

검사 순서는 입력/권한 → Proof 조회 → type/version/domain/network → canonical hash → Registry의 발행기관·키 소속/공개 signer 및 발행 시각 유효 구간 → 서명 → 현재 lifecycle → 권한 있는 필드 비교입니다. 현재 revoked/suspended 상태 때문에 서명 검사를 건너뛰고 VERIFIED를 만들지 않습니다. 신뢰 근거를 읽지 못하면 보류하고, 형식/domain/서명 등 필수 검사가 실패하면 의존 검사는 NOT_RUN으로 표시합니다.

내용 비교 시 하나라도 실제 불일치하면 TAMPERED가 우선이고, 불일치가 없으나 필수 비교 항목이 부족하면 INCONCLUSIVE입니다. 지급 요청의 필수 비교는 amount_minor·currency·target_hash, 문서는 institution_code·document_type·document_number·version입니다. binding은 인증 계정에서 별도로 검사하며 caller가 제출한 hash의 일치로 대체하지 않습니다.

여러 lifecycle 조건이 동시에 있으면 `PROOF_REVOKED → ISSUER_KEY_REVOKED → ISSUER_SUSPENDED → CONSUMED → EXPIRED → ACTIVE` 순서로 대표 상태를 선택하고 모든 확인된 원인은 checks/reason_codes에 남깁니다. RPC 실패로 필수 현재 상태를 알 수 없으면 대표 lifecycle은 null입니다. 키 만료는 신규 발행을 차단하지만 정상 발행된 과거 Proof의 lifecycle을 키 폐기로 바꾸지 않습니다. 기관 REVOKED도 현재 사용 불가로 처리하며 대표 lifecycle은 ISSUER_SUSPENDED, 상세 checks에 REVOKED를 남깁니다.

현재 사용 가능 판정은 신뢰 검사 성공, lifecycle ACTIVE, 요청 동작의 권한·기간·single_use 조건을 모두 요구합니다. 실제 consume은 API 조회 결과 이후에도 체인 트랜잭션 안에서 다시 검사합니다. domain/network 오류는 기존 서명의 다른 환경 재사용을 허용하지 않습니다.

사유 코드는 기존 AMOUNT_MISMATCH/FIELD_MISMATCH/INVALID_SIGNATURE/PAYLOAD_HASH_MISMATCH/PROOF_EXPIRED/PROOF_NOT_FOUND/ISSUER_NOT_FOUND/SCHEMA_UNSUPPORTED/DEPENDENCY_UNAVAILABLE/REPLAY_DETECTED를 재사용합니다. v2에 필요한 DOMAIN_MISMATCH, NETWORK_MISMATCH, KEY_NOT_FOUND, KEY_TIME_INVALID, INPUT_INCOMPLETE, SUBJECT_BINDING_MISMATCH와 lifecycle별 PROOF_REVOKED/ISSUER_KEY_REVOKED/ISSUER_SUSPENDED를 C 모델에서 추가·생성합니다. 웹이 임의 enum을 만들지 않습니다. 원문 기대값은 오류 응답에 넣지 않습니다.

## 5. 공개 조회와 제한 비교

공개 ID/QR 조회는 로그인 없이 Proof ID·합성 발행기관 이름/ID·유형·발행/만료 시각·verification/lifecycle·checks·검사 범위·확인 시각만 제공합니다. 공개 링크에는 Proof ID만 넣습니다. 원문 payload·수신자 계정·token/salt·binding·개인키·인증 token은 포함하지 않습니다.

전체 payload, 금액·대상·문서번호 등 제한 필드의 조회/비교는 발행기관 담당자 또는 지정 수신자의 인증 뒤 제공합니다. 익명 비교 API를 이용해 숨긴 값을 추측할 수 없도록 권한 검사 전에 제한 필드 비교 결과를 반환하지 않습니다. 운영자는 운영 이력·기관 관리 권한만으로 제한 payload나 발행 서명권한을 얻지 않습니다. A의 화면은 공개 ID 조회에서 제한 자료 비교를 요청할 때 로그인으로 연결합니다.

## 6. Proof 상태 등록과 consume 신뢰 경계

최종 원자성 권위는 로컬 EVM의 ProofStatusRegistry입니다. API DB lock만으로 1회 사용을 보장했다고 하지 않습니다. 테스트 계정에는 외부 지갑을 요구하지 않고, **서버가 인증한 주체를 체인에 대행 전달하는 trusted gateway**를 사용합니다. gateway 권한은 기관 발행 서명키·Registry 관리자 권한과 별도로 둡니다.

C는 원본 envelope의 domain/hash/서명/기관·키/기간과 인증 주체를 확인합니다. B는 권한 있는 등록 경로에서 Proof ID hash에 다음 불변 commitment를 저장합니다: issuer/key ID hash, envelope signing digest, subject_binding_hash, issued_at/expires_at, single_use. 저장 시 해당 기관 권한·현재 등록 키·기간을 검사하며 이후 다른 digest·기관·수신자로 덮어쓸 수 없습니다. 원문 payload·계정 ID·salt는 저장하지 않습니다.

체인은 등록 호출자가 해당 기관 운영자이거나 명시적으로 위임된 gateway인지 검사합니다. P0에서 gateway가 C의 서명 검증을 완료했다는 사실을 신뢰하며, JSON envelope 전체를 Solidity에서 다시 직렬화해 검증하는 방식은 채택하지 않습니다. gateway 침해에 대한 독립 신원 보증은 제공하지 않습니다. 검증 없이 임의 digest를 등록하는 공개 경로는 금지합니다.

consume은 권한 있는 gateway만 제출하고, 인증 결과를 `발행기관 주체` 또는 `수신자 주체`로 전달합니다. Contract는 등록 commitment 기준으로 issuer 일치 또는 subject binding 일치, 기관 활성·키 미폐기·발행 당시 키 기간, Proof 기간·single_use·폐기/소비 여부를 트랜잭션 안에서 검사합니다. gateway 외 호출, 타 기관/다른 binding, 만료·폐기·이미 소비된 Proof는 거부합니다. 같은 Proof의 경쟁 요청 중 한 번만 상태를 바꾸고 event를 남깁니다.

수신자의 웹 로그인 자체는 체인이 확인하지 않습니다. actor 정보는 서버가 세션에서 도출하고 chain은 허가된 gateway의 주장과 불변 commitment가 맞는지 검사합니다. 이 신뢰 모델을 API 권한 검사·Contract 우회 호출 테스트·발표 설명에 명시합니다. 별도 지갑 서명이나 무신뢰 수신자 증명은 P0에 추가하지 않습니다.

Proof 폐기는 자기 발행기관 주체만 수행하며 수신자·일반 운영자 계정의 폐기 요청은 거부합니다. API는 같은 요청 ID 재시도에 기존 결과를 반환하고 이미 폐기된 동일 Proof의 새 적법한 폐기 요청도 현재 상태를 반환하여 새 트랜잭션을 만들지 않습니다. Contract는 반복 상태 전이에 새 event를 만들지 않는 idempotent 폐기를 구현합니다. CONSUMED 뒤 폐기는 허용하되 소비 이력을 지우지 않습니다.

W3는 실제 서명·DB 저장·기존 Issuer/Key Reader 기반 발행/검증을 완료할 수 있으며 W4 Registry를 선행 요구하지 않습니다. W3 결과는 수행한 발행 근거·서명/내용 검사 성공을 VERIFIED로 반환할 수 있지만 Proof 상태 조회는 NOT_RUN, lifecycle은 null로 두어 전체 현재 유효성을 주장하지 않습니다. 비교 범위는 별도로 표시하고 consume/Proof 폐기는 제공하지 않습니다. 이는 W3 중간 산출물의 명시적 기능 범위이며 W4 이후 RPC 장애를 이 방식으로 우회하지 않습니다. W4 연결 뒤에는 등록·receipt·재조회가 끝난 Proof만 상태 기능에 준비된 것으로 취급하며 미등록을 ACTIVE로 간주하지 않습니다. 기존 W3 Proof 등록은 저장된 검증된 envelope로 수행하고 소급 재서명하지 않습니다. 새 발행은 DB 저장 후 등록 Operation을 거치며 미확정 상태는 대기로 반환합니다. W3의 제한된 성공은 W4/최종 RC 수용 증거가 아닙니다.

## 7. Operation·확정·복구

요청 ID의 유일 범위는 `(account_id, action, request_id)`입니다. 같은 ID에서 입력 hash 또는 기관이 달라지면 409 REQUEST_ID_CONFLICT로 거부하고, 동일 입력이면 진행/완료 상태를 포함한 기존 결과를 반환합니다. 동일 request_id 재조회 성공을 두 번째 consume 상태 전이 성공으로 세지 않습니다. 새로운 ID로 이미 소비된 Proof를 사용하면 REPLAY_DETECTED로 거부합니다.

상태는 `PENDING_SUBMISSION → SUBMITTED → CONFIRMED`, 확실한 실패는 `FAILED`, 제출 여부/receipt가 불명확하면 `UNKNOWN`입니다. 외부 전송 전 Operation과 signer·nonce·계산된 tx hash 등 복구 참조를 영속 저장합니다. 전송 전 crash를 포함해 모호한 경우 상태 확인 없이 새 nonce로 재전송하지 않습니다. 복구에는 동일 트랜잭션의 재전파를 허용하되 새로운 동작 제출과 구분합니다.

로컬 EVM은 canonical block에 포함된 성공 receipt(1 confirmation)와 해당 변경의 상태 재조회까지 확인해야 CONFIRMED입니다. tx hash·status=0 receipt·RPC timeout은 성공이 아닙니다. DB 마지막 기록이 실패했으면 재시작 후 같은 tx와 체인 상태를 확인해 복구합니다. receipt 뒤 조회 실패는 확정 성공으로 응답하지 않습니다. 이후 폐기/소비가 진행됐더라도 해당 tx의 성공 이력과 현재 상태는 따로 반환합니다.

manifest에는 무작위 deployment_id·chain ID·contract 주소·source SHA·배포 block/hash를 기록하고 DB Operation/projection도 배포 구분을 참조합니다. 같은 chain ID의 로컬 재배포도 새 배포로 취급합니다. checkpoint의 block hash가 맞지 않으면 해당 projection을 재구축하고, 이전 배포의 pending 작업·Proof를 새 배포에서 성공으로 복구하지 않습니다. demo reset은 DB·chain·manifest·합성 signer/seed의 대응을 다시 만들며 보존 환경에서 자동 실행하지 않습니다.

## 8. 대안·호환성·검증·되돌림

매번 팀원 코드를 기다리는 방식 대신 확정 정책과 공유 계약으로 자기 구현·검사를 진행하고 실제 연결을 나중에 검증합니다. 정상 교체 시 일괄 revoke는 과거 문서의 불필요한 무효화를 일으켜 채택하지 않습니다. DB만의 consume은 체인 직접 호출 경쟁을 보장하지 않아 채택하지 않습니다. 외부 지갑/KMS는 테스트 계정·로컬 시제품 범위를 늘리므로 P1로 남깁니다.

| 영역 | 후속 구현·리뷰 | 필요한 증거 |
| --- | --- | --- |
| 모델·상태·서명 | W1-C3, B 교차 확인, A/D 소비 검토 | v1 Golden/판정 불변, v2 생성 Schema·타입·Golden, domain/network 실패, 상태 우선순위 |
| 인증·키·작업 | W1-C1/C2, W2-C1~C3, B 연결 | CSRF/기관 권한, 동일 ID 충돌/경쟁, 서명기 재시작, 부분 실패·receipt 복구 |
| 두 유형 API·공개성 | W3-C1~C3, A 연결, D 확인 | 새 발행·제한 조회/비교·변조·누락·저장 실패, W3 상태 기능 미실행 표시 |
| lifecycle·consume | W3-B3, W4-B1~B3/C1~C3 | gateway 무권한/주체 교체 거부, 경쟁 상태 전이 1개, 키 교체/만료/유출, 조회 불변 |
| 전체 시연 | W4-D1~D3, W5~W7 | 실제 DB·체인·새 브라우저 세션·다른 환경 재현, F01~F15 |

이번 변경은 문서 정책입니다. 실제 Python 모델·Schema·OpenAPI·ABI·migration 변경은 위 작업에서 관련 소유자가 구현·리뷰하고 버전을 함께 공유합니다. 새 두 유형 API의 정확한 URL과 생성 타입은 C가 확정 정책으로 작성하여 전달하며, 기존 v1 endpoint의 응답 계약은 보존합니다.

되돌림은 구현 전에는 이 ADR을 대체하는 결정과 계획 개정으로, 구현 후에는 v2 신규 발행/상태 변경을 중단하고 해당 migration·배포 절차에 따라 수행합니다. 서명된 Proof·키/Proof 폐기·소비 이력을 덮어쓰거나 v1으로 재해석하지 않습니다. 검증 기록과 이전 schema/ABI·manifest를 보존합니다.
