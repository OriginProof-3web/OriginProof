# 5.0 공유 계약 — v5-shared-0.1

- 작성일: 2026-10-14 · 작업: V5-W1-C / V5-W1-B 경계 준비
- 상태: **공통 명세·모델·생성물·독립 서명 검사 준비 완료 / B 계약 검토·A/D 소비 검토·실제 서비스 구현은 후속**
- 기준: [개발 계획서 5.0](development_plan.md), [ADR 0004](adr/0004-v5-governance-wallet-versioning.md).
- 목적: 팀원별로 필드·서명·상태를 따로 정의하지 않고 아래 원본과 예시를 함께 사용합니다. 검토 의견은 이 명세와 원본에 반영하고 다시 생성합니다. 검토 완료 여부는 10절에 실제 근거로 기록합니다.

## 1. 공통 원본과 사용 순서

| 자료 | 원본·생성물 | 사용 담당 |
| --- | --- | --- |
| 데이터·요청·응답 모델 | [wallet_contract.py](../packages/python/originproof_core/wallet_contract.py) | C 원본 관리, A/D 소비 |
| hash·EIP-712·복구 서명자 | [wallet_signatures.py](../packages/python/originproof_core/wallet_signatures.py) | C/B, A 원본 대조 |
| JSON Schema | [wallet-contract.schema.json](../packages/schemas/generated/json/wallet-contract.schema.json) | 각 `$defs/모델명`을 선택해 검사 |
| TypeScript 타입·서명 필드 순서 | [wallet-contract.ts](../packages/schemas/generated/types/wallet-contract.ts) | A/B/D가 별도 모듈로 import |
| 예정 API 정의 | [wallet-contract.openapi.json](../packages/schemas/generated/openapi/wallet-contract.openapi.json) | C 구현, A/D 소비; 현재 서버 OpenAPI와 구분 |
| Registry 인터페이스·컴파일 ABI | [IOriginProofWalletRegistry.sol](../packages/contracts/src/IOriginProofWalletRegistry.sol), [ABI](../packages/contracts/abi/IOriginProofWalletRegistry.json) | B 구현·검토, C Adapter 연결 |
| 서명 Golden | [wallet_contract_v1.json](../fixtures/golden/wallet_contract_v1.json) | 합성 납부·공식 안내·철회·키 보유 증명 4개와 제안 ID |
| API/실패 예시 | [shared_contract_cases_v1.json](../fixtures/synthetic/shared_contract_cases_v1.json) | 정상 서명 요청·제출, UNKNOWN·409 예시, SG01~16 후속 검사 |

`originproof_core.wallet_contract`를 명시적으로 import합니다. 기존 `originproof_core`의 v1/v2 이름을 덮어쓰지 않습니다. 신규 인터페이스에는 실행 가능한 Registry 구현·배포 주소가 없고 `/v3` 예정 경로도 서버에 등록하지 않았습니다. `v5-shared-0.1`, API 경로 `/v3`, EIP-712 도메인 버전 `1`, 내용 schema 이름과 문서 개정 번호는 서로 다른 값입니다.

## 2. 공통 표현과 원본 생성

| 항목 | 고정 규격 |
| --- | --- |
| ID/hash | `0x` + 소문자 hex 64자리. issuerId/keyId는 서버가 기존 ASCII 내부 ID의 UTF-8 Keccak-256 대응을 관리; 브라우저의 기관 ID를 권한 근거로 믿지 않음 |
| docKey | 기관 안에서 사용하는 개인정보 없는 32바이트 난수. 최초 발행 화면이 생성 후 재시도에 같은 값을 사용; API는 세션 기관·소유권·중복을 검사 |
| documentId | `keccak256(abi.encode(bytes32 issuerId, bytes32 docKey))`. Golden에 인코딩 결과 포함; 구 proof_id와 별도 namespace |
| 주소 | 20바이트 hex, 비교/저장 시 소문자; 지갑 표시에는 checksum 주소 사용 가능. 서명 도메인·발행키는 0 주소 거부 |
| 시각/버전/금액 | JSON 정수, bool/float 거부, 최대 `2^53-1`. 시각은 UTC Unix **초**, 버전은 1부터 시작. Solidity 시각·버전은 uint64 |
| chainId/nonce/blockNumber | JSON의 선행 0 없는 **10진 문자열**, Solidity uint256; chainId는 양수, nonce는 0부터 시작. JavaScript Number로 변환하지 않음 |
| 문자열 | 발행 보호 필드는 NFC·양끝 공백 제거. 내부 공백·대소문자는 보존. 계좌는 ASCII 공백/하이픈만 제거하고 6~32자리 ASCII 숫자·선행 0 보존 |
| null | 선택 필드는 null을 포함해 canonical JSON 생성; 필드 생략과 null의 임의 혼용 금지 |
| 요청 멱등 키 | `req_` + 영숫자/`_`/`-` 1~124자리. 계정·action·request_id를 묶고 같은 키의 다른 본문은 409 |

납부 내용은 금액·통화·은행·계좌·예금주·목적·납부 기한·선택 공식 링크를 보호합니다. 공식 안내는 기관 코드·문서 유형/번호·제목·요약·선택 공식 링크를 보호합니다. 링크는 인증정보 없는 HTTPS이며 자동 방문하지 않습니다. `issuedAt < due_at <= expiresAt`를 검사합니다. 배포/모델은 공개 합성 안내 전용이며 실제 개인 청구서로 확장하지 않습니다.

보호 필드 bytes는 기존 `canonical_json_bytes(content)`의 UTF-8·NFC·정렬 키·compact JSON입니다. `protectedHash = SHA-256(보호 필드 bytes)`이고 hash algorithm 코드 **1=SHA-256**입니다. 기존 v1/v2의 Keccak payload hash는 바꾸지 않습니다.

신규 기관 발행 원본의 준비 규격은 `originproof.original.v1` canonical UTF-8 JSON입니다. `format`, `issuer_id`, `doc_key`, `document_id`, `version`, `issued_at`, `expires_at`, `content`를 포함하는 bytes를 서버가 생성합니다. `originalHash = SHA-256(원본 bytes)`입니다. 원본 전체와 보호 필드 hash가 각각 다른 범위를 보호합니다. PDF 등 사용자 입력 형식 선정과 별개이며, 나중에 발행 원본 형식을 바꾸면 새 format/schema와 Golden을 정의합니다. QR을 붙인 렌더링 사본은 이 hash 대상이 아닙니다.

원본 bytes는 base64로 서명 요청에 제공하고 기관 브라우저가 Web Crypto SHA-256으로 재계산합니다. 표시 필드와 원본을 대조한 다음 지갑에 서명을 요청합니다. 서버가 제공한 hash만 그대로 서명하지 않습니다. `SigningRequest` 모델도 원본·보호 내용·문서 ID의 일치를 검사합니다.

브라우저에서 보호 필드 hash를 계산할 때는 API가 정규화한 flat content의 키를 ASCII 순서로 정렬하고 JSON.stringify·UTF-8을 사용합니다. 값에 다시 trim/정규화를 적용하지 않습니다. 원본 JSON의 content와 같은지도 확인합니다. [Node Web Crypto 교차 검사](../scripts/ci/check_wallet_browser_hashes.mjs)가 두 템플릿의 원본/보호 hash·필드 일치를 독립 확인합니다. 실제 브라우저 지갑 서명 검사는 별도입니다.

## 3. EIP-712 업무 서명

도메인은 `name=OriginProof`, `version=1`, 실제 `chainId`, 신규 `verifyingContract`입니다. 사용 중인 브라우저 지갑 네트워크·주소가 바뀌면 기존 서명 요청을 재검사합니다. 최종 신규 주소는 B 배포 manifest에서 가져오며 Golden의 `0x1212…1212`는 배포 주소가 아닙니다.

정확한 필드 순서·타입은 `wallet_signatures.py`의 `EIP712_TYPES`가 원본이고 생성 TypeScript의 `WALLET_EIP712_TYPES`로 전달됩니다.

| 타입/action | 필드 순서 |
| --- | --- |
| Publish / 1 | action, issuerId, docKey, documentId, version, keyId, originalHash, protectedHash, contentSchema, signatureSchema, originalHashAlgorithm, protectedHashAlgorithm, issuedAt, expiresAt, nonce, deadline |
| Revoke / 2 | action, issuerId, docKey, documentId, version, keyId, nonce, deadline |
| KeyProof / 3 | action, applicationId, issuerId, signer, challengeNonce, deadline |

bytes32의 signatureSchema는 `keccak256(utf8("originproof.wallet.v1"))`입니다. contentSchema는 납부 `originproof.content.payment.v1`, 공식 안내 `originproof.content.official.v1` 문자열의 Keccak-256입니다. 해시 알고리즘 코드 둘 다 1을 서명하고 Registry가 지원 schema/알고리즘을 검사합니다. unsigned client 옵션으로 해석하지 않습니다.

`issuedAt < deadline <= expiresAt`; **현재 시각 >= deadline이면 제출 거부**입니다. expiresAt은 문서 유효기간, deadline은 서명 제출 기한입니다. API가 작성하는 발행/철회 서명 요청의 준비 기본 수명은 300초, 발행은 문서 만료보다 늦게 설정하지 않습니다. RPC 장애로 deadline이 지나면 기존 작업을 먼저 재조회하고 새 서명을 받습니다.

업무 nonce는 기관별 `nextNonce`, 등록 직후 0이며 publish/revoke 성공 시 하나씩 원자적으로 소비합니다. 같은 nonce의 다른 동시 요청 중 하나만 성공합니다. 가스 트랜잭션 nonce와 별개입니다. 철회는 정지 중에도 해당 문서 소유 기관의 **현재 활성 키**로 허용하고, 이전 발행키를 다시 활성화하지 않습니다.

서명은 65바이트 r/s/v hex, v=27/28, low-s를 사용합니다. 서버에는 기관 개인키를 제출하지 않습니다. 중계자의 msg.sender는 가스 제출자이고, 업무 권한은 복구된 기관 서명자로 판단합니다. Signature/EIP-712 검사 성공과 기관·키·소유권·버전의 현재 권한 검사를 구분합니다.

브라우저는 응답의 `primary_type`으로 `Publish`/`Revoke`/`KeyProof` 한 타입과 `EIP712Domain`만 선택해 `eth_signTypedData_v4`에 전달합니다. API의 message/domain은 이미 camelCase alias를 사용합니다. API 본문·응답의 나머지 업무 필드는 snake_case입니다. 값이나 순서를 별도로 재정의하지 않습니다.

근거: [EIP-712](https://eips.ethereum.org/EIPS/eip-712), [Solidity ABI](https://docs.soliditylang.org/en/latest/abi-spec.html). 문서·예시로 replay 방지가 자동 제공되지는 않으며 위 nonce/deadline 검사가 필요합니다.

## 4. 키 보유 증명과 공동승인

KeyProof의 applicationId는 서버가 현재 신청 ID의 UTF-8 Keccak-256으로 만들고 신청자 세션·명부 기관·새 signer에 묶습니다. challengeNonce는 서버 32바이트 난수, 수명 300초, 한 번만 소비합니다. 웹 역할은 세션에서 확인합니다. 키 보유 증명은 기관 심사·내부 승인·공동승인을 대신하지 않습니다.

GovernanceProposal의 ABI 순서는 `uint8 action, bytes32 issuerId, bytes32 keyId, address signer, bytes32 metadataHash, uint256 nonce, uint64 deadline`입니다. action **1=REGISTER, 2=ROTATE_KEY, 3=REACTIVATE**이고 EIP 업무 action과 별도 enum입니다. `proposalId = keccak256(abi.encode(uint256 chainId, address verifyingContract, GovernanceProposal proposal))`입니다. 서명 Golden에 별도 제안 ID 예시를 제공합니다.

- 제안은 승인 지갑이 `propose` 트랜잭션으로 체인에 등록합니다. 생성은 승인으로 세지 않고 승인 수 0부터 시작합니다. REGISTER/ROTATE에는 해당 기관·새 signer와 묶인 KeyProof와 서명을 전달하고, 제안 만료는 proof 만료보다 늦을 수 없습니다.
- API의 `PREPARED`는 DB 준비 상태이고, 체인 등록 후 `PENDING`, 두 번째 서로 다른 승인자의 트랜잭션에서 `EXECUTED`가 됩니다. 승인자가 보낸 txHash만으로 실행 성공을 표시하지 않습니다.
- 승인 지갑 3개는 배포 시 고정합니다. 세션의 operator 역할과 체인의 approver 권한을 각각 검사합니다. API/서버가 승인키를 대신 보관하거나 단독 승인하지 않습니다.
- `governanceNonce(issuerId)`는 업무 nonce와 별도이고 0부터 시작합니다. 실행 시 소비하여 같은 nonce의 다른 제안을 STALE로 만듭니다. 정지 전 제안으로 바로 재활성화하지 못하도록 최초 긴급 정지 전이도 이 nonce를 증가시킵니다.
- REACTIVATE는 현재 키·메타데이터를 그대로 지정합니다. 신규 KeyProof 없이 proof는 0값, signature는 빈 bytes로 전달하고 Registry가 action별 조건을 검사합니다. 키 교체는 새 keyId/주소로 별도 ROTATE 제안을 실행합니다.
- 키 ID는 기관/주소 이력과 고정 연결하며 재사용·소유 기관 변경을 거부합니다. 새 키의 보유 증명은 등록 또는 교체 제안 생성 시 소비합니다. 같은 서명을 다른 제안에 재사용하지 않습니다.
- `suspendIssuer`는 승인자 1명 또는 해당 기관의 활성 키가 직접 호출합니다. 원문 없이 reasonCode hash를 기록하고 발행을 차단합니다. reasonCode는 `KEY_COMPROMISE`, `ABUSE_REPORT`, `OTHER` ASCII 문자열의 Keccak-256이며 그 외 값을 거부합니다. KEY_COMPROMISE는 현재 키의 compromiseBlock을 기록하고 과거 안내에도 경고를 남깁니다. 사고 키를 그대로 지정한 REACTIVATE는 거부하고 공동 키 교체를 먼저 수행합니다. 이미 정지한 상태의 재조회는 성공으로 읽되 불필요한 nonce 증가로 복구 제안을 무효화하지 않습니다.

제안 기본 수명은 KeyProof가 필요한 등록/교체 300초, 재활성화 86,400초의 준비 값입니다. 실제 3개 지갑 운영 방식·공개 네트워크는 V5-Q02/Q04 결정 후 검토합니다. 긴급 정지→공동 키 교체→필요한 문서 철회→공동 재활성화 순서를 지킵니다. 키 교체만으로 정지 상태를 해제하지 않습니다.

## 5. 문서와 현재 상태

최초 version=1, 이후 정확히 latest+1입니다. 등록·최신 포인터 변경·이전 최신의 SUPERSEDED 전이는 같은 트랜잭션입니다. 동시에 같은 다음 버전을 요청하면 하나만 성공하고 나머지는 VERSION_CONFLICT로 현재 최신을 다시 확인합니다.

체인 저장 state **1=ACTIVE, 2=REVOKED, 3=SUPERSEDED**이며 state 1의 기간 만료는 조회 시 EXPIRED로 계산합니다. REVOKED/SUPERSEDED를 만료나 기관 정지로 덮어쓰지 않습니다. 최신 버전 철회로 과거 버전을 자동 복구하지 않습니다. getDocument의 미존재는 별도 not-found이며 state 0을 ACTIVE로 해석하지 않습니다.

기관 상태는 0=미등록, 1=ACTIVE, 2=SUSPENDED입니다. `DocumentView.state`, `warnings`, 검사 결과를 각각 읽습니다. 정상 교체로 종료된 과거 발행키의 정상 서명은 유지하고, 사고 키의 과거 안내에는 KEY_COMPROMISED 경고를 표시합니다. getKey의 등록/교체/사고 block과 getDocument의 실제 publishedAt/publishedBlock을 대조합니다. 자기 선언 issuedAt만으로 발행 당시 권한을 소급 만들지 않으며 새 발행은 현재 활성 키로만 허용합니다. getIssuer만으로 과거 키 검사가 완료되지 않습니다.

검증 결과는 ID_ONLY / FULL_COMPARISON / PARTIAL_COMPARISON / NONE을 구분합니다. ID 조회는 내용 일치를 주장하지 않고 INCONCLUSIVE로 표시합니다. 실제 내용 불일치는 TAMPERED, 미등록은 NOT_REGISTERED, RPC/원본 부재·부분 비교는 INCONCLUSIVE입니다. VERIFIED는 전체 요청 범위의 내용·서명·현재 체인 검사가 모두 통과한 결과입니다. 사용 가능 여부는 문서 상태·기간·기관/키 경고를 추가로 확인합니다. AI 위험 수준과 섞지 않습니다.

checks의 공통 name은 signature / original_hash / protected_fields / current_state / content입니다. content는 요청한 전체 비교 완료 여부를 표시하며 다른 세부 체크를 생략하는 허가가 아닙니다. 항목 상태는 PASSED/FAILED/NOT_RUN/UNAVAILABLE입니다. 검증 시각·실제 chain/contract·조회 blockNumber/hash를 남기고 projection의 과거 ACTIVE로 현재 성공을 만들지 않습니다. 사용자 후보·기대 계좌 전체를 공개 오류에 넣지 않습니다.

## 6. 예정 API와 오류

정확한 요청·응답·필수/null/타입은 생성 OpenAPI와 모델을 따릅니다. 아래 경로는 **미구현 준비 계약**입니다. 기존 `/v1`·`/v2`와 ADR 0003의 제안 URL을 새 경로의 실행 목록으로 안내하지 않습니다.

| 기능 | 경로 | 응답·권한 |
| --- | --- | --- |
| 키 보유 증명 | POST /v3/key-challenges → POST /v3/key-proofs | 201 SigningRequest → 200 KeyProofReceipt; 해당 신청자 |
| 공동승인 준비/조회 | POST /v3/proposals, GET /v3/proposals/{proposal_id} | ProposalView; operator + 실제 approver |
| 제안 등록/승인 tx 접수 | POST /v3/proposals/{proposal_id}/transactions 또는 /approvals | 202 OperationView; 성공 tx와 제안·승인자를 대조 |
| 긴급 정지 tx 접수 | POST /v3/issuers/{issuer_id}/suspensions | 202 OperationView; 해당 기관/approver와 실제 tx 검사 |
| 발행 | POST /v3/document-drafts → POST /v3/publications | 201 SigningRequest → 202 OperationView; 세션 기관의 현재 발행키 |
| 철회 | POST /v3/revoke-drafts → POST /v3/revocations | 해당 기관이 소유한 버전; 정지 중에도 현재 키 서명 허용 |
| 기관 직접 제출 tx 접수 | POST /v3/signing-requests/{signing_request_id}/transactions | 202 OperationView; 원본·서명 요청을 먼저 보존한 뒤 동일 tx 확인 |
| 작업 조회/복구 | GET /v3/operations/{operation_id}, POST …/reconcile | 소유자/기관 범위; 기존 작업 재조회 |
| 문서 조회 | GET /v3/documents/{document_id}?version=1 | 공개 합성 문서; version 생략 시 최신 번호를 응답에 명시 |
| 내용/원본 검사 | POST /v3/verifications | ID/공개 보호 필드 조회 가능; original_ref는 세션 소유권 검사 |
| 분석 | POST /v3/analyses, GET/DELETE /v3/analyses/{analysis_id} | 소유자; 별도 보고서/원본 동의, 삭제 중 늦은 결과 재저장 금지 |
| 저장 이력/보고서/원본 | GET /v3/analyses, GET …/{analysis_id}/report 또는 /original | 자기 보관 자료만; 원본은 binary 다운로드, 만료/미보관 410 |

현재 cookie `originproof_session`·상태 변경의 X-CSRF-Token을 재사용합니다. 기관·소유자·역할을 client body에서 선택하지 않습니다. 비공개/타인 객체는 404로 처리합니다. DB·체인 제안 공개 hash 조회와 심사자료 열람은 별개입니다.

SignedSubmission은 signing_request_id와 signature만 전달합니다. 서버에 저장된 불변 message/domain을 다시 읽고 검사하며 클라이언트가 보낸 변경 payload를 대신 서명하지 않습니다. API 202는 제출 수락이며 체인 확정을 뜻하지 않습니다. Operation 상태는 기존 PENDING_SUBMISSION/SUBMITTED/CONFIRMED/FAILED/UNKNOWN을 사용합니다. UNKNOWN의 next_action=RECONCILE, deadline 경과 시 현재 체인을 확인한 다음 RESIGN을 안내합니다.

| HTTP | detail 예시·의미 |
| --- | --- |
| 401/403 | 세션 없음 / 역할·서명자·체인 승인 권한 불일치 |
| 404 | 문서/작업 미존재 또는 타인 비공개 객체 |
| 409 | REQUEST_ID_CONFLICT, VERSION_CONFLICT, NONCE_ALREADY_USED, PROPOSAL_STALE, DUPLICATE_APPROVAL |
| 410 | SIGNATURE_EXPIRED, PROPOSAL_EXPIRED, RESULT_EXPIRED, ORIGINAL_UNAVAILABLE |
| 422 | MALFORMED_INPUT, DOCUMENT_ID_MISMATCH, CONTENT_SCHEMA_MISMATCH, ORIGINAL_HASH_MISMATCH, PROTECTED_HASH_MISMATCH, SIGNATURE_SCHEMA_UNSUPPORTED, DIRECT_TX_MISMATCH |
| 429/503 | 요청 제한(retry_after_seconds) / 제출용 의존성 장애 |

조회 검사 중 RPC 장애는 HTTP 오류로 가짜/변조 판정을 만들지 않고 200 INCONCLUSIVE·UNAVAILABLE 체크로 응답합니다. error 구조는 `detail`, 선택 request_id/retry_after_seconds, field_paths이며 원본·계좌·서명 요청 전체를 오류/로그에 복제하지 않습니다. 이미 tx를 제출했는지 불명확하면 503으로 단순 재시도를 유도하지 않고 기존 Operation을 조회하도록 합니다.

## 7. 분석·보고서의 공통 경계

input_ref는 소유권·유효기간 검사를 마친 입력 객체 ID입니다. 생성/업로드 경로·허용 형식은 V5-Q01에서 선정한 뒤 구현하며, 이 모델만으로 이미지/PDF/녹음을 활성화하지 않습니다. Decisions API는 포함하지 않습니다.

AnalysisJob은 QUEUED/RUNNING/COMPLETED/FAILED/CANCELLED/EXPIRED입니다. 보고서 위험 수준은 HIGH/CAUTION/NO_CLEAR_INDICATORS/UNDETERMINED입니다. 발행 검사를 실행하지 않았으면 verification=null과 verification_not_run_reason을 남깁니다. NO_CLEAR_INDICATORS는 발행 진위나 행동 안전을 보증하지 않습니다.

근거의 quote는 실제 확인한 짧은 원문을 보존합니다. start_offset/end_offset은 변환 텍스트의 Unicode 코드 포인트 기준 `[start,end)`이며 UTF-16 인덱스가 아닙니다. 선정된 형식에 한해 page는 1부터, start_ms/end_ms는 밀리초입니다. RULE/LLM 출처와 제한을 남기고 범위·인용의 실제 원문 일치는 D/C가 검사합니다. report·original 보관 선택 기본 false와 기간·삭제는 계획서 9장을 유지합니다. 다운로드/이력 화면은 이 보고서와 보관 객체를 사용하고 공개 기관 원본·사용자 보관 원본 권한을 혼합하지 않습니다.

## 8. DB 전환과 구버전 호환

이 절은 migration 설계이며 현재 DB를 변경하거나 삭제하는 명령이 아닙니다.

| 새/재사용 저장 대상 | 키·필수 불변값 / 기존 활용 |
| --- | --- |
| 문서·버전 | UNIQUE(chain/contract, document_id, version), 고정 issuer_id/doc_key·내용·서명·원본 참조·기간; 최신 포인터는 편의 사본 |
| 서명 요청 | signing_request_id, 계정/기관, 불변 domain/message·digest·deadline·원본/보호 내용; 임의 payload 재작성 금지 |
| 제안·승인 사본 | UNIQUE(chain/contract, proposal_id), KeyProof·서명·진행 상태; 승인 주소/nonce·최종 상태는 체인으로 대조 |
| Operation·감사 | 기존 계정/action/request_id UNIQUE·input_hash·tx 상태·복구를 재사용하고 신규 식별자를 추가; 서명/원본은 공개 감사에 복제하지 않음 |
| 키/체인 이력 | issuer/key ID·주소·활성/교체/사고 block·배포 식별; 구배포 manifest와 분리 |
| 분석·입력 객체 | 소유자·보관 동의·절대 만료·삭제/취소 상태; 기관 발행 원본 삭제와 독립 |

정상 경로는 원본·서명·Operation을 먼저 하나의 DB 트랜잭션에 보존한 뒤 제출합니다. receipt 뒤 DB 실패는 동일 이벤트·상태로 재조정합니다. 직접 txHash는 chain/contract·성공 receipt·action·issuer/document/version/hash를 저장 요청과 대조합니다. 문서 버전·서명은 업서트로 덮어쓰지 않습니다.

기존 카드 schema 1.0.0, Proof schema 2.0.0, 정규화/서명·binding·consume·서버 기관키 읽기는 호환 경로에 보존합니다. 새 공개 안내에는 binding/consume을 넣지 않습니다. ADR 0003의 납부 schema 3.0.0 제안을 새 지갑 서명 envelope로 취급하지 않습니다. 새 Registry는 별도 비업그레이드 배포이고 이전 ID·서명·체인 발행 사실을 소급 변환하지 않습니다. DB rollback으로 확정 체인 기록을 되돌릴 수 없습니다. 보존 정책 변경·과거 자료 삭제는 별도 dry-run·의존 검사 후 진행합니다.

## 9. 재생성·검증·인계

저장소 루트에서 실행합니다. Python 모델/서명 원본 → 준비 생성물 → 인터페이스 컴파일 → ABI 생성 순서이며 현재 API를 기동할 필요가 없습니다.

```sh
PYTHONPATH=packages/python uv run --package originproof-core python scripts/generate_wallet_contracts.py
forge build --root packages/contracts --offline
PYTHONPATH=packages/python uv run --package originproof-core python scripts/generate_wallet_contracts.py
PYTHONPATH=packages/python uv run --package originproof-core pytest packages/python/tests/test_wallet_contract.py
forge test --root packages/contracts --offline --match-contract WalletContractGoldenTest
node scripts/ci/check_wallet_browser_hashes.mjs
```

생성기는 Foundry `out`의 컴파일 인터페이스가 있으면 ABI를 갱신합니다. ABI 원본이 바뀌면 먼저 forge build 후 생성하며, out이 없는 A/C 환경은 커밋된 준비 ABI를 소비할 수 있습니다. 기존 `make generate`에도 준비 생성 명령을 연결합니다. 기존 Golden/타입을 수정한 것으로 새 서명 호환을 입증하지 않습니다.

서명 예시는 누구나 아는 합성 테스트 키 1로 생성하고 비밀키는 JSON에 포함하지 않습니다. 실제 계정/기관/가스용 키로 사용하거나 자금을 보내지 않습니다. Python/Solidity의 동일 digest·서명자와 domain/message 변경 거부는 독립 검사하고, 실제 지갑 팝업·API·Registry 동작·DB migration·공개 배포 성공과 구분합니다. SG01~16의 execution_status=NOT_EXECUTED는 실제 새 Registry 연결 뒤 D/B/C가 바꿉니다.

## 10. 리뷰와 현재 완료 범위

| 담당 | 이번에 제공한 기준 | 후속 확인 / 현재 상태 |
| --- | --- | --- |
| C | 모델·생성 Schema/TS/OpenAPI·원본 규칙·멱등/복구·호환·Golden | 준비 구현·독립 검사; 실제 API/DB 구현은 후속 |
| B | 정확한 EIP-712·ABI 구조·제안/업무 nonce·권한·상태·이벤트·교차 검사 | Registry 저장/함수·권한·키 이력·가스/확정 검토; **소유자 리뷰 미확인** |
| A | 타입·서명 요청/거절·수명·원본 재계산·제안 승인/버전 화면 | 지갑 라이브러리/데모 운영 선정·실제 브라우저 검토; **소비 리뷰 미확인** |
| D | 위험/검증 분리·근거 형식·SG01~16·기존 회귀 경계 | 선정 입력·grounding·공격/통합 검사; **독립 소비 리뷰 미확인** |

이번 작성은 사용자가 지시한 공통 준비 작업입니다. B/A/D의 승인·전체 W1 완료를 대신 기록하지 않습니다. 팀원은 이 명세를 소비하고 의견을 원본에 반영하면 되며, 별도의 공유 계약 사본을 새로 정의할 필요가 없습니다. 검토 중 변경된 규격은 revision·Golden·생성물을 함께 갱신합니다. 배포된 서명/내용 규격을 바꾸면 domain/schema 버전을 별도로 올려 구자료를 보존합니다.
