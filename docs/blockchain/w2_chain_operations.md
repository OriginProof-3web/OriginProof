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

Writer는 한 호출에서 transaction을 한 번만 제출한다. receipt의
`transactionHash`가 제출 hash와 같고, receipt block 높이의 현재 canonical block
hash가 receipt `blockHash`와 같을 때만 confirmation과 상태 재조회를 진행한다.
불일치·reorg·canonical 조회 오류는 `UNKNOWN/RECEIPT_NOT_CANONICAL` 또는
`UNKNOWN/DEPENDENCY_UNAVAILABLE`이며 새 transaction을 자동 제출하지 않는다.

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

### 안전한 호출 순서

C 연결은 기존 편의 메서드가 아니라 아래 단계형 경계를 사용한다.

```python
prepared = await writer.prepare_register_issuer(
    sender=issuer_manager_address,
    issuer_id="iss_origin_mock_office",
    issuer_account=issuer_account_address,
    metadata_hash="0x...",
)
await operation_store.save_prepared(prepared.recovery_reference)  # 전송 전에 commit

submitted = await writer.submit_prepared(prepared)
if submitted.tx_hash is not None:
    await operation_store.save_submitted(prepared.recovery_id, submitted.tx_hash)  # polling 전에 commit

result = await writer.confirm_prepared(prepared, submitted.tx_hash)
```

`execute_prepared(prepared, operation_store)`는 이 순서를 수행하는 최소 orchestration
helper다. `save_prepared` 실패 또는 취소 시 RPC 전송을 호출하지 않고 프로세스의
nonce 예약을 해제한 뒤 원래 예외를 전달한다. 저장 commit 결과가 불명확하면 C는
DB의 durable recovery reference를 먼저 재조회하고 기존 nonce 예약을 존중해야 한다.
전송을 시작한 뒤 결과가 불명확하면 nonce 예약을 유지한다. tx hash 저장 실패 시
`UNKNOWN/SUBMISSION_PERSISTENCE_FAILED`를 반환하고 성공으로 진행하지 않는다.
프로세스 재시작 시 원래 Operation 입력과 저장 nonce로 같은 `prepare_*`를 다시
구성하고 `restore_prepared(prepared, recovery_reference)`로 원래 검색 시작 block과
지문 일치를 검증한 뒤 `recover_prepared(prepared, tx_hash)`를 호출한다. tx hash가
저장되지 않은 모호한
전송은 `recover_prepared(prepared)`가 준비 시점 이후 canonical/pending transaction에서
고정 sender·nonce·to·calldata가 같은 제출을 찾는다. 찾기 전에는 재전송하지 않는다.

### 준비·반환 계약

`prepare_*`는 chain/deployment/code를 확인하고 다음 복구 참조를 반환한다.

```text
action, deployment_id, chain_id, sender, contract, data,
nonce, recovery_id, scan_from_block
```

`recovery_id`는 위 deployment/chain/sender/nonce/contract/calldata의 SHA-256 지문이다.
현재 로컬 unlocked-account 방식은 `eth_sendTransaction`을 사용하므로 전송 전 예상
tx hash를 계산하지 못한다. 이 차이는 ADR의 이상적인 `계산된 tx hash`와 다르며,
C는 `(deployment_id, sender, nonce)`를 DB unique constraint로 예약하고 전체 복구
참조를 Operation에 저장해야 한다. Writer의 프로세스 내부 lock/nonce 예약은 같은
인스턴스의 동시 prepare 충돌만 줄이며 다중 프로세스의 내구성 경계가 아니다.
동일 요청 재시도는 새 prepare를 호출하지 않고 저장된 참조로 recover한다.

`submit_prepared`는 receipt를 기다리지 않고 `SUBMITTED + tx_hash`를 반환한다. 명시적
RPC reject는 `FAILED`, 전송 timeout처럼 제출 여부가 불명확하면 tx hash 없이
`UNKNOWN/SUBMISSION_UNKNOWN`이다. `confirm_prepared`만 receipt·canonical block·
confirmation·최종 상태를 확인해 `CONFIRMED`를 반환한다.

| Writer 결과 | C Operation 전이 | 처리 |
| --- | --- | --- |
| `prepare_*` 후, submit 전 | `PENDING_SUBMISSION` | 요청/입력 hash와 전체 `recovery_reference` 저장; `(deployment_id, sender, nonce)` 유일 예약 |
| `submit_prepared`의 tx hash 수신 | `SUBMITTED` | receipt 대기 전 tx hash 저장 |
| `CONFIRMED` | `CONFIRMED` | receipt와 Writer 재조회 증거 저장, API 성공 반영 |
| `FAILED` | `FAILED` | 확실한 revert/실패 receipt; 성공 상태로 바꾸지 않음 |
| `UNKNOWN` | `UNKNOWN` | receipt/상태를 조회하기 전 같은 작업 재전송 금지 |

현재 C 준비 branch의 `reserve_operation`은 PENDING 예약과 입력 충돌 방지를 제공한다.
C2/C3는 nonce 유일 예약, `recovery_reference`/tx hash 저장 commit, 재시작 시
`recover_prepared` 호출, Adapter 결과를 OperationRow/API 상태로 매핑해야 한다.
이 PR은 C의 API·DB migration을 구현하지 않는다.

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
- receipt transaction hash나 canonical block hash 불일치/reorg는 `UNKNOWN`이다.
- manifest/chain/deployment/bytecode 불일치는 `UNKNOWN/DEPENDENCY_UNAVAILABLE`다.
- receipt status 1이어도 상태 재조회가 일치하지 않으면 CONFIRMED가 아니다.
- 미등록과 RPC/ABI/manifest 실패를 같은 결과로 축소하지 않는다.

## 검증 결과

| 검사 | 실제 결과 |
| --- | --- |
| Writer 확정·영속/복구 경계 단위 검사 | 21개 통과 |
| Writer/Reader/projection/API health 회귀 | 62개 통과, opt-in 1개 skip |
| 전체 Python/API/analyzer/indexer 회귀 | 171개 통과, opt-in 1개 skip |
| Foundry Registry 검사 | 10개 통과 |
| 실제 Anvil opt-in 통합 | 1개 통과; 배포·role 분리·비인가 거부·중지/재활성화·키 폐기·MVP 검증 포함 |
| Ruff | 통과 |
| 웹 lint/typecheck | 통과 |

실제 Anvil 검사는 합성 계정과 임시 로컬 deployment만 사용했다. C의 실제 DB Operation,
A의 브라우저 흐름과 D의 독립 재현은 이 결과에 포함되지 않는다.
