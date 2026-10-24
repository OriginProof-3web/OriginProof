# W3-B1/B2/B3 체인 신뢰·서명·Proof 상태 인계

- 담당: B / `@hamin1228`
- 기준: `phase/W3@1f8ed632ea9c74091abaf2fe2ec32882038f731f`
- 작업: `W3-B1`, `W3-B2`, `W3-B3`
- C 소비 후보: `feat/w3-c-issuance`의 발행·검증 흐름
- 상태: B 독립 구현·교차검사, C 소비 리뷰와 W4 Contract 구현 대기

## W3-B1 — 발행·검증용 현재 Registry snapshot

`JsonRpcBlockchainReader.get_issuer_key_snapshot(issuer_id, key_id, at)`은 한 번의
호출에서 chain ID, deployment block identity와 두 Registry bytecode를 확인한 뒤
기관과 키를 같은 명시적 block tag에서 읽는다.

```python
snapshot = await reader.get_issuer_key_snapshot(
    issuer_id="iss_origin_mock_bank",
    key_id="key_origin_mock_bank_001",
    at=issued_at,
)
```

반환값은 `deployment_id`, `chain_id`, `block_number`, `block_hash`, `issuer`, `key`,
`key_valid_at`이다. `key_valid_at`은 기관 ACTIVE, 키 ACTIVE, 키의 기관 일치와
`valid_from <= at < valid_until`을 모두 만족할 때만 true다.

| 체인 결과 | Adapter 결과 | C 의미 |
| --- | --- | --- |
| 기관·키 ACTIVE, 소속/기간 일치 | 두 record + `key_valid_at=true` | 해당 snapshot을 발행/검증 근거로 사용 가능 |
| 기관 SUSPENDED/REVOKED | 실제 issuer status, `key_valid_at=false` | 미등록으로 축소하지 않고 발행 거부/검증 reason에 반영 |
| 키 REVOKED/기간 밖 | 실제 key status/기간, `key_valid_at=false` | 과거 서명 검사와 현재 발행 가능 여부를 분리 |
| Registry `NONE` | 해당 record `None` | `NOT_REGISTERED`/발행 불가 |
| RPC·chain·manifest·ABI·block 오류 | `DependencyUnavailableError` | 503 또는 `INCONCLUSIVE/DEPENDENCY_UNAVAILABLE` |
| snapshot 조회 중 같은 높이의 block hash 변경 | `DependencyUnavailableError` | reorg가 안정될 때까지 성공 판정 보류 |

snapshot은 현재 체인을 직접 읽으며 indexer projection을 발행 허가 근거로 사용하지
않는다. C 발행 흐름은 별도 `get_issuer`와 `get_key` 호출 대신 snapshot을 소비해야
두 호출 사이의 중지·폐기 상태 변경을 섞지 않는다. 이 PR은 C 소유 API를 수정하지 않는다.

## W3-B2 — v2 Golden Fixture 교차검증

공개 합성 fixture 두 개를 검증한다.

- `PAYMENT_REQUEST`, `OFFICIAL_DOCUMENT`
- `app_domain=originproof.finals`
- `schema_version=2.0.0`
- `chain_id=31337`
- `ECDSA_SECP256K1_KECCAK256_V1`

Python 검사는 signing payload의 canonical UTF-8 JSON, Keccak-256 digest와 복구 signer가
fixture 값과 같은지 확인한다. chain ID를 바꾸면 digest와 복구 signer가 달라지고,
다른 domain/schema version 또는 payload와 맞지 않는 proof type은 모델 검증에서
거부된다. Solidity 검사는 같은 canonical bytes의 `keccak256`이 fixture digest와
일치하는지 확인한다.

Solidity는 JSON canonicalization이나 envelope 서명을 다시 검증하지 않는다. 이
교차검사는 Python과 EVM의 Keccak 입력·결과가 같다는 경계 검사이며, W4의 trusted
gateway가 C의 canonicalization·서명 검증을 대행한다는 ADR 결정을 바꾸지 않는다.

## W3-B3 — ProofStatusRegistry W4 구현 계약 후보

아래 ABI는 W4-B1/B2 구현과 C 소비 리뷰를 위한 후보이며 아직 배포 ABI가 아니다.

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
function proofStatus(bytes32 proofId) external view returns (uint8);
function isConsumable(bytes32 proofId, uint64 timestamp) external view returns (bool);
```

### 권한과 신뢰 경계

| 호출 | 허용 주체 | Contract가 확인할 것 |
| --- | --- | --- |
| `registerProof` | 해당 기관 account 또는 `GATEWAY_ROLE` | 기관/키 ACTIVE, key issuer, issuedAt 키 기간, Proof 기간, commitment nonzero, 중복 금지 |
| `revokeProof` | commitment의 발행기관 account | 타 기관·gateway 일반 폐기 거부; 반복 폐기는 `false`, event 없음 |
| `consumeProof` | `GATEWAY_ROLE` | actor binding, 기관/키 현재 상태, 발행 당시 키 기간, Proof 기간, single-use, 미폐기·미소비 |
| 조회 함수 | 누구나 | 상태를 바꾸거나 nonce/event를 만들지 않음 |

gateway는 C가 세션 주체, 원본 envelope, domain/network, payload hash, 서명과 Registry
상태를 검증했다는 사실을 신뢰받아 전달한다. Contract는 수신자 로그인을 확인하지
않으며 서버가 전달한 `actorBinding`을 불변 commitment와 비교한다. 계정 ID, token,
salt, 원문 payload와 개인키는 chain/event에 넣지 않는다.

### 상태·event·오류

상태는 `NONE`, `ACTIVE`, `REVOKED`, `CONSUMED`를 사용한다. CONSUMED 뒤 합법적인
issuer 폐기는 허용하며 `consumedAt`은 보존하고 대표 lifecycle은 `PROOF_REVOKED`다.
동시 consume 중 하나만 상태를 바꾸고 event를 남겨야 한다.

```solidity
event ProofRegistered(bytes32 indexed proofId, bytes32 indexed issuerId, bytes32 indexed keyId);
event ProofRevoked(bytes32 indexed proofId, uint64 revokedAt);
event ProofConsumed(bytes32 indexed proofId, ConsumeActorKind actorKind, uint64 consumedAt);
```

필요 custom error는 `ProofAlreadyExists`, `ProofNotFound`, `IssuerNotActive`,
`KeyNotActive`, `KeyIssuerMismatch`, `IssuedOutsideKeyWindow`, `InvalidProofWindow`,
`InvalidCommitment`, `ProofAlreadyConsumed`, `ProofExpired`, `ProofNotSingleUse`,
`ActorBindingMismatch`, `UnauthorizedIssuerOperator`, `UnauthorizedGateway`다.

### 호출·복구 예시

1. C가 envelope와 현재 Registry snapshot을 검증하고 W2 Operation을 전송 전에 저장한다.
2. Writer가 `registerProof`를 제출하고 tx hash를 receipt 대기 전에 저장한다.
3. 성공 receipt의 canonical block/confirmation을 확인한 뒤 `getProof`를 재조회한다.
4. RPC timeout 또는 재시작이면 저장된 deployment/sender/nonce/tx hash로 복구하며
   확인 전에 새 transaction을 만들지 않는다.
5. C는 등록이 CONFIRMED되기 전 Proof lifecycle을 ACTIVE로 응답하지 않는다.

W4에서 Contract·ABI·manifest·Reader/Writer·projection을 함께 구현하고 C가 실제
Operation/API에 연결해야 이 후보가 실행 계약이 된다. W3의 발행·서명 완료나 이 문서
작성만으로 Proof 폐기·consume 또는 단계 완료를 주장하지 않는다.
