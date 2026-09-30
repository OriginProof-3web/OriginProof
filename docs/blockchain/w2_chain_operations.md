# W2-B1/B2 체인 작업·배포·projection 인계

- 작업 ID: `W2-B1`, `W2-B2`
- 담당: B / `@hamin1228`
- 작업 branch: `codex/w2-b-chain-operations`
- 선행 계약: [W1-B Registry·Adapter 계약](w1_registry_adapter_contract.md)
- 통합 방식: 사용자 지시에 따라 W1/W2 B 변경을 PR #26 한 개로 공유
- 상태: B 독립 구현·로컬 EVM 검증 완료, C Operation/API 연결과 작성자 외 리뷰 대기

## 구현 결과

`JsonRpcBlockchainWriter`가 기존 Issuer/Key Registry ABI로 다음 작업을 수행한다.

- 기관 등록, 중지, 재활성화, 영구 폐기
- 키 등록과 영구 폐기
- transaction hash 수신, receipt 확인, 포함 block 기준 1 confirmation 계산
- 같은 deployment의 명시적 block에서 최종 상태 재조회
- `CONFIRMED`, 확실한 revert인 `FAILED`, 결과가 불명확한 `UNKNOWN` 구분

Writer는 한 호출에서 transaction을 한 번만 제출한다. C는 transaction 전 Operation을
영속 예약하고 `UNKNOWN`을 즉시 재전송하지 않으며 tx hash와 상태를 먼저 복구한다.

```python
result = await writer.register_issuer(
    sender=issuer_manager_address,
    issuer_id="iss_origin_mock_office",
    issuer_account=issuer_account_address,
    metadata_hash="0x...",
)
```

반환값은 `state`, `deployment_id`, `chain_id`, `tx_hash`, receipt block/hash,
confirmation count, 재조회 block과 안정된 `error_code`를 포함한다. provider의 상세
오류나 revert 원문은 공개 응답 계약이 아니다.

## C Operation 연결

| Writer 결과 | C Operation 전이 | 처리 |
| --- | --- | --- |
| submit 전 예약 | `PENDING_SUBMISSION` | `(account_id, action, request_id)`와 입력 hash 저장 |
| tx hash 수신 | `SUBMITTED` | tx hash·deployment ID·sender/nonce 복구 정보 저장 |
| `CONFIRMED` | `CONFIRMED` | receipt와 Writer 재조회 증거 저장, API 성공 반영 |
| `FAILED` | `FAILED` | 확실한 revert/실패 receipt; 성공 상태로 바꾸지 않음 |
| `UNKNOWN` | `UNKNOWN` | receipt/상태를 조회하기 전 같은 작업 재전송 금지 |

현재 C 준비 branch의 `reserve_operation`은 PENDING 예약과 입력 충돌 방지를 제공한다.
C2/C3는 Writer 결과 필드를 OperationRow에 연결하고 재시작 복구를 추가해야 한다.

## 권한 분리와 로컬 배포

로컬 배포는 Anvil의 서로 다른 네 unlocked 합성 계정을 사용한다.

| manifest role | 권한 |
| --- | --- |
| `registry_admin` | role 관리와 pause; 일상 issuer/key 변경 권한 회수 |
| `issuer_manager` | 기관 등록·중지·재활성화·폐기 |
| `key_manager` | 비상 키 관리 |
| `issuer_account` | 자기 기관 공개키 등록·폐기 |

기관 signing key는 위 transaction 계정과 별도다. 배포자는 계약 생성 후 manager role을
별도 계정에 부여하고 자신에게 자동 부여된 일상 manager role을 회수한다. 실제 Anvil
검사에서 `registry_admin`의 기관 중지 직접 호출은 revert되고 `issuer_manager` 호출만
확정되는 것을 확인했다.

## 배포 manifest

`packages/contracts/deployments/31337.local.json`은 로컬 생성물이며 Git에 넣지 않는다.
새 manifest는 다음 공개 재현 정보가 모두 있어야 Reader/Writer가 시작된다.

```text
chain_id
genesis_block_hash
deployment_id
deployment_block
deployment_block_hash
source_commit_sha
contracts.{name}.address
contracts.{name}.constructor_arguments
contracts.{name}.abi_sha256
roles.registry_admin / issuer_manager / key_manager / issuer_account
```

`deployment_id`는 chain·genesis·배포 block/hash·source SHA·계약 주소/인자/ABI hash의
canonical JSON SHA-256으로 만든 `dep_<64 hex>` 값이다. Reader와 Writer는 chain ID,
genesis hash, deployment block hash와 bytecode를 매 작업 전에 확인한다. 다른 Anvil
재기동이나 재배포의 주소·receipt·checkpoint를 현재 성공 근거로 재사용하지 않는다.

배포 명령은 기존 `make deploy-local` 흐름을 유지한다. 명령이 전달하는 source SHA는
40자리 Git commit이어야 하며 signer는 공개 주소만 받는다. 개인키는 manifest, 로그,
Git에 기록하지 않는다.

## Indexer 저장 계약

event와 checkpoint identity는 이제 `(chain_id, deployment_id, ...)`를 사용한다.
동일 deployment의 같은 block/log event는 idempotent replay로 무시하고 내용이 다른
중복은 명시적 reorg 복구를 요구한다. `verified_checkpoint`는 재시작 시 저장된 block
hash를 현재 deployment의 canonical block hash와 비교한다.

새 `deployment_id`는 별도 event/checkpoint 공간을 사용한다. 이전 deployment의
projection은 이력·표시 용도일 뿐 현재 Registry 상태의 권위가 아니며, 현재 유효성은
항상 Reader의 체인 재조회로 판정한다.

## 오류와 안전 조건

- 잘못된 ID, 주소, bytes32, 기간은 제출 전에 `ValueError`로 거부한다.
- JSON-RPC가 명시적으로 transaction을 거부하면 `FAILED/CHAIN_REVERTED`다.
- 전송 중 연결 단절, receipt 미확인, 재조회 불일치는 `UNKNOWN`이다.
- manifest/chain/deployment/bytecode 불일치는 `UNKNOWN/DEPENDENCY_UNAVAILABLE`다.
- receipt status 1이어도 상태 재조회가 일치하지 않으면 CONFIRMED가 아니다.
- 미등록과 RPC/ABI/manifest 실패를 같은 결과로 축소하지 않는다.

## 검증 결과

| 검사 | 실제 결과 |
| --- | --- |
| Writer/Reader/projection 단위 검사 | 48개 통과 |
| 전체 Python/API/analyzer/indexer 회귀 | 161개 통과, opt-in 1개 skip |
| Foundry Registry 검사 | 10개 통과 |
| 실제 Anvil opt-in 통합 | 1개 통과; 배포·role 분리·비인가 거부·중지/재활성화·키 폐기·MVP 검증 포함 |
| Ruff | 통과 |
| 웹 lint/typecheck | 통과 |

실제 Anvil 검사는 합성 계정과 임시 로컬 deployment만 사용했다. C의 실제 DB Operation,
A의 브라우저 흐름과 D의 독립 재현은 이 결과에 포함되지 않는다.
