# W1-B1/B2 Registry·Adapter 계약

- 작업 ID: `W1-B1`, `W1-B2`
- 담당: B / `@hamin1228`
- 기준: `origin/integration@3295a71c10a1a99c523d3cfefde91b5737b737ac`
- 정책 원본: [ADR 0001](../adr/0001-finals-contracts.md)
- 상태: B 독립 설계·기존 구현 조사 완료, C의 W1-C3 구현과 소유자 리뷰 대기

이 문서는 현재 배포된 Issuer/Key Registry와 Reader를 기준으로 W2 체인 쓰기와
W4 Proof 상태 구현에 사용할 B/C 경계를 고정한다. 함수명이 현재 ABI인지 향후
초안인지 구분하며, 문서만으로 새 ABI가 배포되었다고 간주하지 않는다.

## 1. 현재 구현과 재사용 범위

### IssuerRegistry — 현재 ABI 재사용

| 목적 | 실제 함수 | 쓰기 주체 | 결과 확인 |
| --- | --- | --- | --- |
| 기관 활성 등록 | `registerIssuer(bytes32,address,bytes32)` | `ISSUER_MANAGER_ROLE` | 성공 receipt 뒤 `getIssuer` 재조회 |
| 기관 일시 중지 | `suspendIssuer(bytes32)` | `ISSUER_MANAGER_ROLE` | `issuerStatus == SUSPENDED` |
| 기관 재활성화 | `reactivateIssuer(bytes32)` | `ISSUER_MANAGER_ROLE` | `issuerStatus == ACTIVE` |
| 기관 영구 폐기 | `revokeIssuer(bytes32)` | `ISSUER_MANAGER_ROLE` | `issuerStatus == REVOKED` |
| 기관 운영 계정 변경 | `changeIssuerAccount(bytes32,address)` | `ISSUER_MANAGER_ROLE` | `issuerAccount` 재조회 |
| 조회 | `getIssuer`, `issuerStatus`, `issuerAccount` | 제한 없음 | 같은 block tag에서 읽기 |

`NONE → ACTIVE → SUSPENDED → ACTIVE`는 허용한다. `ACTIVE` 또는 `SUSPENDED`에서
`REVOKED`로 이동할 수 있으며 REVOKED는 되돌리지 않는다. 현재 계약은 등록과
활성화를 한 호출로 처리하므로 C의 `APPROVED_PENDING_CHAIN`은 성공 receipt와
재조회가 끝나기 전까지 `ACTIVE`로 승격하지 않는다.

### IssuerKeyRegistry — 현재 ABI 재사용

| 목적 | 실제 함수 | 쓰기 주체 | 결과 확인 |
| --- | --- | --- | --- |
| 발행 공개키 등록 | `registerKey(bytes32,bytes32,address,uint64,uint64)` | 해당 기관 account 또는 `KEY_MANAGER_ROLE` | `getKey`와 `isKeyValid` 재조회 |
| 유출 키 폐기 | `revokeKey(bytes32)` | 해당 기관 account 또는 `KEY_MANAGER_ROLE` | `keyStatus == REVOKED` |
| 조회 | `getKey`, `keyStatus`, `isKeyValid` | 제한 없음 | 같은 block tag에서 읽기 |

키 상태는 `NONE → ACTIVE → REVOKED`이며 재활성화하지 않는다. `validFrom`은 포함,
`validUntil`은 제외한다. 등록 시 기관이 ACTIVE여야 한다. 정상 교체는 새 키를 먼저
등록·확정한 뒤 C의 발행 키 선택을 바꾸며 기존 키를 자동 폐기하지 않는다.

### 변경이 필요한 항목

W1에서는 기존 ABI를 변경하지 않는다. 다음 항목은 후속 구현에서 새 ABI 또는
배포 절차가 필요하다.

1. W2: 배포자, Registry 운영자, 키 관리자, 기관 account를 서로 다른 합성 계정으로
   배치하고 role grant/revoke 결과를 manifest와 실행 증거에 남긴다.
2. W2: write Adapter와 Operation receipt 복구를 추가한다.
3. W4: `ProofStatusRegistry`를 새 계약으로 구현하고 ABI를 생성한다.
4. W4: Proof 등록·폐기·consume Reader/Writer를 추가한다.

## 2. ID와 호출 입력

API 문자열 ID는 UTF-8 문자열의 `keccak256`인 `bytes32`로 전달한다. 현재 Reader와
배포 fixture가 사용하는 `iss_...`, `key_...` 규칙을 유지한다. 공개 envelope나 API의
원문 ID와 체인의 hash를 Adapter에서 명시적으로 변환하며 이미 hash인 값에 다시
hash를 적용하지 않는다.

```text
issuer_id_hash = keccak256(utf8(issuer_id))
key_id_hash    = keccak256(utf8(key_id))
proof_id_hash  = keccak256(utf8(proof_id))
```

`metadataHash`에는 합성 기관 표시 정보의 canonical hash만 넣는다. 원문 payload,
계정 ID, recipient token, salt, 개인키와 인증 token은 체인 호출과 event에 넣지 않는다.

## 3. B/C Adapter 계약

### 공통 반환

쓰기 Adapter는 제출 성공만으로 완료를 반환하지 않는다.

```text
ChainOperationResult {
  operation_id: string
  state: PENDING_SUBMISSION | SUBMITTED | CONFIRMED | FAILED | UNKNOWN
  tx_hash: optional 0x-prefixed bytes32
  chain_id: integer
  deployment_id: string
  submitted_at: optional UTC timestamp
  confirmed_at: optional UTC timestamp
  block_number: optional integer
  confirmation_count: integer
  reread_block_number: optional integer
  error_code: optional stable code
}
```

`CONFIRMED`는 로컬 EVM에서 성공 receipt, receipt block 이후 1 confirmation, 같은
deployment의 최종 상태 재조회를 모두 만족할 때만 사용한다. receipt status가 0이면
`FAILED`다. 전송 여부나 receipt가 불명확하면 `UNKNOWN`이며 같은 입력을 즉시 다시
전송하지 않는다.

### 명령

| Adapter 명령 | 입력 | 확정 재조회 |
| --- | --- | --- |
| `register_issuer` | request_id, issuer_id, issuer_account, metadata_hash | account/hash/status ACTIVE |
| `suspend_issuer` | request_id, issuer_id | status SUSPENDED |
| `reactivate_issuer` | request_id, issuer_id | status ACTIVE |
| `revoke_issuer` | request_id, issuer_id | status REVOKED |
| `register_key` | request_id, key_id, issuer_id, signer, valid_from, valid_until | 전체 key record와 ACTIVE |
| `revoke_key` | request_id, key_id | status REVOKED |

C는 인증 세션에서 account·role·issuer를 결정하고 body의 role/issuer 주장을 권한
근거로 사용하지 않는다. B Adapter는 chain ID, deployment ID, 계약 주소, ABI hash를
검증하고 계약 revert를 안정된 오류로 변환한다.

### 조회

한 API 작업 안의 기관·키 조회는 동일한 명시적 block tag를 사용한다. `NONE`만
미등록으로 반환한다. RPC 오류, 잘못된 ABI 길이, chain 불일치, bytecode 부재,
manifest 불일치는 미등록으로 축소하지 않고 `DEPENDENCY_UNAVAILABLE`로 반환한다.

### 오류 매핑

| 분류 | 계약/환경 예 | Adapter 코드 | API 의미 |
| --- | --- | --- | --- |
| 입력 | zero address, empty ID, 잘못된 기간 | `INVALID_ARGUMENT` | 422 |
| 미등록 | issuer/key/proof not found | `NOT_FOUND` | 권한에 따라 404 |
| 중복 | already exists, request input 충돌 | `CONFLICT` | 409 |
| 권한 | AccessControl, issuer operator 불일치 | `FORBIDDEN` | 403 |
| 상태 전이 | revoked 재활성화, 중지 기관 키 등록 | `INVALID_STATE` | 409 |
| 체인 실패 | status 0 receipt | `CHAIN_REVERTED` | Operation FAILED |
| 불명확 | timeout/connection loss 후 제출 여부 불명 | `SUBMISSION_UNKNOWN` | Operation UNKNOWN |
| 구성/조회 | chain/address/ABI/code/manifest 불일치 | `DEPENDENCY_UNAVAILABLE` | 503 또는 보류 결과 |

계약의 상세 revert 문자열이나 provider 원문은 공개 응답에 노출하지 않는다.

## 4. 권한과 키 분리

| 주체 | 허용 | 금지 |
| --- | --- | --- |
| Registry admin | role 부여·회수, emergency pause | 발행 서명키로 사용 |
| Issuer manager | 기관 등록·중지·재활성화·폐기 | Proof 서명, consume |
| Key manager | 비상 키 등록·폐기 | 기관 승인, Proof 서명 |
| 기관 account | 자기 기관 키 등록·폐기, 향후 자기 Proof 폐기 | 타 기관 변경 |
| 기관 signing key | envelope 서명 | Registry 관리 transaction |
| trusted gateway | 승인된 Proof 등록과 consume 대행 | Registry admin, signing key 역할 |

로컬 배포 직후 deployer가 여러 role을 가진 현재 상태는 bootstrap 편의다. W2부터
운영 role을 별도 합성 계정에 부여하고 배포자에게서 일상 role을 회수한다. gateway는
`ProofStatusRegistry`에만 별도 role을 받는다.

## 5. ProofStatusRegistry ABI 초안 — W4 입력

다음은 새 계약의 설계 초안이며 현재 생성 ABI가 아니다.

```solidity
enum ConsumeActorKind { ISSUER, RECIPIENT }

struct ProofCommitment {
    bytes32 issuerId;
    bytes32 keyId;
    bytes32 signingDigest;
    bytes32 subjectBindingHash;
    uint64 issuedAt;
    uint64 expiresAt;
    bool singleUse;
    uint64 revokedAt;
    uint64 consumedAt;
}

function registerProof(
    bytes32 proofId,
    bytes32 issuerId,
    bytes32 keyId,
    bytes32 signingDigest,
    bytes32 subjectBindingHash,
    uint64 issuedAt,
    uint64 expiresAt,
    bool singleUse
) external;

function revokeProof(bytes32 proofId) external returns (bool changed);

function consumeProof(
    bytes32 proofId,
    ConsumeActorKind actorKind,
    bytes32 actorBinding
) external;

function getProof(bytes32 proofId) external view returns (ProofCommitment memory);
function isConsumable(bytes32 proofId, uint64 timestamp) external view returns (bool);
```

예정 event는 `ProofRegistered`, `ProofRevoked`, `ProofConsumed`이며 proof/issuer/key ID를
indexed 값으로 둔다. event에 digest·subject binding·원문은 넣지 않는다. 예정 오류는
`ProofAlreadyExists`, `ProofNotFound`, `IssuerNotActive`, `KeyNotActive`,
`KeyIssuerMismatch`, `IssuedOutsideKeyWindow`, `InvalidProofWindow`, `ProofAlreadyRevoked`,
`ProofAlreadyConsumed`, `ProofExpired`, `ProofNotSingleUse`, `ActorBindingMismatch`,
`UnauthorizedIssuerOperator`다.

등록자는 해당 기관 account 또는 명시적으로 위임된 gateway여야 한다. 등록 시 기관
ACTIVE, 키 ACTIVE, 키의 issuer 일치, `issuedAt`이 키 유효 구간 안, Proof 기간과
비어 있지 않은 commitment를 검사한다. 동일 proof ID를 덮어쓰지 않는다.

폐기는 해당 Proof의 발행기관 account만 가능하다. 이미 폐기된 Proof의 합법적 반복
호출은 `changed=false`를 반환하고 event를 추가하지 않는다. CONSUMED 뒤 폐기는
허용하되 `consumedAt`을 보존한다.

consume은 gateway role만 호출한다. `ISSUER` actor는 전달된 issuer ID가 commitment와
같아야 하고, `RECIPIENT` actor는 서버가 인증 계정·보호된 token/salt로 재계산한
binding이 `subjectBindingHash`와 같아야 한다. 기관·키 현재 상태, 발행 당시 키 기간,
Proof 기간, single-use, 폐기·소비 여부를 transaction 안에서 다시 검사한다. 경쟁
호출은 하나만 `consumedAt`을 기록한다.

## 6. 상태 전이와 판정

| 대상 | 전이 | 조건 |
| --- | --- | --- |
| Issuer | NONE → ACTIVE | manager 등록 receipt와 재조회 확정 |
| Issuer | ACTIVE ↔ SUSPENDED | manager; REVOKED에서는 불가 |
| Issuer | ACTIVE/SUSPENDED → REVOKED | manager; 영구 상태 |
| Key | NONE → ACTIVE | 자기 기관/operator, 기관 ACTIVE, 유효 기간 정상 |
| Key | ACTIVE → REVOKED | 자기 기관/operator; 영구 상태 |
| Proof | NONE → ACTIVE | commitment 등록 확정 |
| Proof | ACTIVE/CONSUMED → REVOKED | 자기 발행기관; consume 기록 유지 |
| Proof | ACTIVE → CONSUMED | single-use, gateway, actor·기간·현재 신뢰 검사 통과 |

정상 키 교체나 단순 key validity 종료는 과거 Proof를 자동 폐기하지 않는다. 과거
Proof 서명은 `issuedAt`이 해당 키 기간 안인지 검사한다. 현재 키가 REVOKED이면 기존
Proof도 현재 사용 불가다. lifecycle 대표 우선순위는 ADR의
`PROOF_REVOKED → ISSUER_KEY_REVOKED → ISSUER_SUSPENDED → CONSUMED → EXPIRED → ACTIVE`
를 따른다.

## 7. gateway와 recipient binding 경계

gateway는 C가 세션, 원본 envelope, domain/network, canonical hash, 서명, 기관/키,
기간을 검증했다는 사실을 P0에서 신뢰받아 체인 호출을 대행한다. Contract는 JSON을
다시 직렬화하지 않으며 gateway 침해에 대한 무신뢰 보증을 제공하지 않는다.

수신자 token과 Proof별 32-byte salt는 서버 전용 저장에만 둔다. 체인에는 최종
`subjectBindingHash`만 저장한다. consume request body의 account ID, role, issuer ID,
binding 값을 인증 근거로 사용하지 않는다. gateway가 세션에서 actor를 만들고,
Contract는 그 actor 값이 불변 commitment와 일치하는지 확인한다.

## 8. receipt·재시작·재배포

Operation 유일 키는 `(account_id, action, request_id)`다. 전송 전에 입력 hash,
issuer, signer, nonce, 예상 tx hash와 deployment ID를 영속 저장한다. 동일 request ID와
동일 입력은 기존 Operation을 반환하며 다른 입력은 `REQUEST_ID_CONFLICT`다.

재시작 시 `SUBMITTED`와 `UNKNOWN`은 tx hash·sender/nonce·receipt·현재 상태를 조회해
복구한다. 결과가 불명확한 동안 새 transaction을 만들지 않는다. 예상 상태가 이미
존재하면 원래 Operation과 일치하는지 확인한 뒤 확정한다.

manifest에는 최소 다음을 둔다.

```text
chain_id, genesis_block_hash, deployment_id,
deployment_block, deployment_block_hash, source_commit_sha,
contracts.{name}.address, constructor_arguments, abi_sha256
```

`deployment_id`가 바뀌면 이전 checkpoint, receipt와 projection을 새 배포의 성공
근거로 재사용하지 않는다. Reader는 chain ID뿐 아니라 deployment block hash와
bytecode를 확인한다.

## 9. 읽기 불변 조건과 검증 목록

`getIssuer`, `getKey`, `getProof`, status 조회와 public verification은 transaction을
만들거나 nonce를 소비하거나 `consumedAt`을 바꾸지 않는다. single-use 상태 변화는
오직 권한 있는 `consumeProof` 성공 transaction에서 발생한다.

후속 구현은 다음을 검사한다.

- 무권한 Registry/gateway 직접 호출과 타 기관 변경 거부
- zero/duplicate/기간 경계와 irreversible revoke
- 정상 교체 후 과거 Proof 유효성, 유출 폐기 후 현재 사용 불가
- 위조 digest·issuer/key 관계·subject binding 등록/consume 거부
- 경쟁 consume 성공 1건, 재사용 거부, 반복 조회 전후 동일 상태
- status 0 receipt, RPC 단절, UNKNOWN 복구, 재시작, 재배포 격리
- 기존 CARD_PAYMENT_NOTICE 정상/금액 변조 회귀

## 10. C 인계와 현재 한계

C의 W1 계약 초안의 `APPROVED_PENDING_CHAIN`은 이 문서와 일치한다. W2 연결에서
`register_issuer`가 CONFIRMED되고 ACTIVE 재조회가 끝난 뒤에만 chain-active 상태로
바꾼다. W1-C3는 이 문서의 hash 입력·gateway 책임·lifecycle 우선순위를 검토하고
Python 원본 모델, OpenAPI와 fixture를 한 원본에서 생성해야 한다.

이 문서는 B의 W1 독립 산출물이다. C 구현 연결, A 화면, D 독립 재현, 작성자 외
리뷰와 phase 병합 전에는 W1 단계 전체 완료로 표시하지 않는다.
