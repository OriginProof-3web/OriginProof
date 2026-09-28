# M3 M4 실행 문서 체인 신뢰 상태 통합

## 시작 기준과 병합 규칙

작업 기준은 최신 `origin/mvp/integration`입니다. M1 Backend PR은 `c2e4be5`에 병합됐으며,
이후의 통합 문서도 함께 받아야 합니다.

```bash
git fetch origin
git switch -c mvp/chain-ready origin/mvp/integration
make bootstrap-check
```

`mvp/chain-core`와 `mvp/chain-integration`은 이전 기록으로 보존합니다. 특히 기존 M4 브랜치는
Bootstrap과 M1 파일을 삭제하는 차이가 있으므로 그대로 병합하거나 다시 PR base로 사용하지
않습니다. M3와 M4는 최신 기준에서 자기 소유 파일만 옮긴 하나의 정리 PR 또는 순서가 명확한 두
PR을 만듭니다. 모든 PR의 base는 `mvp/integration`이며 M1만 병합합니다.

## 공통 목표

블록체인은 Proof 원문, 카드 정보, 개인정보, API key, private key를 저장하지 않습니다.
온체인에는 opaque identifier, signer address, 상태, 유효 기간, metadata hash만 저장합니다.
M1은 체인 상태와 서명 검증을 결합해 최종 결과를 냅니다. 체인 adapter, indexer, contract가
`VERIFIED`나 `TAMPERED`를 직접 결정해서는 안 됩니다.

현재 M1 포트는 `packages/python/originproof_core/ports.py`의 `BlockchainReader`입니다.

```python
async def get_issuer(issuer_id: str) -> IssuerRecord | None
async def get_key(key_id: str) -> KeyRecord | None
async def is_key_valid(key_id: str, at: datetime) -> bool
```

온체인 ID는 아래와 같이 변환합니다.

```text
keccak256(utf8("iss_origin_mock_bank"))
keccak256(utf8("key_origin_mock_bank_001"))
```

RPC, ABI decode, transport, manifest 오류는 `DependencyUnavailableError`를 발생시켜야 합니다.
`None`은 실제로 등록되지 않은 issuer 또는 key에만 사용합니다. 장애를 `NOT_REGISTERED`나
`TAMPERED`로 바꾸면 안 되며, M1 API는 `INCONCLUSIVE`와 `DEPENDENCY_UNAVAILABLE`를 반환해야 합니다.

## M3 계약 코어 담당

M3 소유 경로는 `packages/contracts/src`와 `packages/contracts/test`입니다. 현재 main에 있는
`IssuerRegistry`와 `IssuerKeyRegistry`를 기준으로 ABI와 이벤트 계약을 확인합니다. 기존 코드를
중복해서 옮기지 말고, M4 통합에 실제로 필요한 인터페이스 불일치가 있을 때만 최소 변경합니다.

계약 요구 사항은 다음과 같습니다.

- issuer 상태: `NONE`, `ACTIVE`, `SUSPENDED`, `REVOKED`
- key 상태: `NONE`, `ACTIVE`, `REVOKED`
- 0 주소·빈 ID·중복 등록·권한 없는 상태 전이를 거부합니다.
- issuer와 key 상태 변경 이벤트는 indexed identifier를 포함합니다.
- key revoke는 되돌릴 수 없습니다.
- key validity는 `valid_from <= timestamp < valid_until`입니다.
- contract interface가 바뀌면 ABI diff, 변경 이유, migration 영향, M4 확인을 PR에 포함합니다.

M3는 `forge test`와 권한·중복·상태 전이·유효 기간 경계·fuzz 테스트를 실행합니다. Contract core를
바꾸지 않는다면, 현재 ABI와 M4 호출의 호환성을 확인한 결과만 정리 PR에 기록합니다.

## M4 배포와 읽기 어댑터 담당

M4 소유 범위는 아래와 같습니다.

```text
services/indexer
packages/contracts/script
packages/contracts/abi
packages/contracts/deployments
apps/api/src/infrastructure/blockchain
```

M4는 배포 스크립트, ABI export, local manifest, JSON RPC reader, event projection을 최신 기준으로
옮기고 M1 포트에 맞춥니다. 예전 M4 구현의 bytes32 기반 `get_issuer`/`get_key` 프로토콜을 그대로
복사하지 않습니다. 사람이 읽는 문자열 ID를 keccak256 bytes32로 변환한 뒤 M1의 문자열 기반
`IssuerRecord`와 `KeyRecord`로 다시 매핑합니다.

필수 매핑은 다음과 같습니다.

| 온체인 값 | M1 반환값 |
| --- | --- |
| issuer `ACTIVE`, `SUSPENDED`, `REVOKED` | `IssuerTrustStatus`의 동명 값 |
| key `ACTIVE`, `REVOKED` | `KeyTrustStatus`의 동명 값 |
| key의 issuer ID, signer, validFrom, validUntil | UTC datetime을 포함한 `KeyRecord` |
| issuer/key `NONE` | 해당 메서드의 `None` |
| RPC·ABI·transport 오류 | `DependencyUnavailableError` |

`is_key_valid`는 registry의 issuer 상태와 key 상태 및 기간을 함께 반영해야 합니다. 배포 manifest에는
chain ID, 배포 블록, 계약 주소, source commit SHA, constructor arguments만 기록합니다. 실제 private
key나 RPC token은 기록하지 않습니다. ABI는 Foundry 산출물에서 생성하며 손으로 작성하지 않습니다.

Indexer는 chain authority가 아닌 projection입니다. block number와 log index를 함께 사용해 event를
idempotent하게 처리하고, restart checkpoint와 명시적 reorg rewind를 테스트합니다.

## 통합 검증과 M1 handoff

로컬 EVM에서 합성 Origin Mock Bank issuer와 Golden Fixture signer key를 배포·등록한 뒤 아래를
검증합니다.

1. `get_issuer("iss_origin_mock_bank")`가 `ACTIVE` record를 반환합니다.
2. `get_key("key_origin_mock_bank_001")`가 issuer ID, signer, 상태, UTC validity를 정확히 반환합니다.
3. `is_key_valid`가 validFrom 포함, validUntil 제외 경계를 정확히 처리합니다.
4. issuer suspension과 key revocation이 M1 lifecycle 결과에 각각 `ISSUER_SUSPENDED`,
   `ISSUER_KEY_REVOKED`로 반영됩니다.
5. RPC를 끈 경우 API가 false negative가 아니라 `INCONCLUSIVE`와
   `DEPENDENCY_UNAVAILABLE`를 반환합니다.
6. `fixtures/golden/card_payment_notice_signing_v1.json`의 signer와 배포된 key가 호환됩니다.
7. 정확한 Candidate는 `VERIFIED + ACTIVE`, 금액만 다른 Candidate는
   `TAMPERED + AMOUNT_MISMATCH`가 됩니다.
8. indexer가 중복 event replay와 restart 뒤에도 중복 projection을 만들지 않습니다.

필수 명령은 `make test-contracts`, deployment·ABI generation smoke, adapter와 indexer의 소유 영역
테스트, `make mvp-test`, `make lint`, `make typecheck`입니다. M4는 deployment manifest 경로, ABI 경로,
RPC URL 형식, chain ID, 실제 실행 결과를 M1 handoff에 기록합니다. M1은 그 handoff와 PR의 파일 범위를
검토한 뒤 통합하고, 마지막으로 전체 E2E를 실행합니다.
