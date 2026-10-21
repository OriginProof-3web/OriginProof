# OriginProof Blockchain

OriginProof의 **M3 Blockchain Core**와 **M4 Blockchain Integration**을 구현한 로컬 개발 프로젝트입니다.

OriginProof는 피싱 가능성을 추측하는 서비스가 아닙니다. 발행자가 등록한 서명 Proof와 블록체인 신뢰 상태를 이용해 **발행자, 서명 키, 핵심 내용과 현재 유효성**을 규칙 기반으로 검증합니다.

> **핵심 원칙:** Don’t detect the fake. Verify the real.

현재 프로젝트는 팀 저장소에 병합하기 전 로컬 구현본입니다. 실제 은행이나 개인정보 대신 `Origin Mock Bank` 합성 데이터만 사용합니다.

## 현재 구현 상태

### M3 — Blockchain Core

- `IssuerRegistry`
  - Issuer 등록과 조회
  - `ACTIVE`, `SUSPENDED`, `REVOKED` 상태 관리
  - 중지된 Issuer 재활성화 및 폐기 상태 복구 방지
- `IssuerKeyRegistry`
  - 서명 키 등록·조회·유효기간 검사·영구 폐기
  - Issuer 상태와 키 상태를 결합한 유효성 검사
- OpenZeppelin `AccessControl`, `Pausable` 적용
- 관리자, Issuer Manager, Key Manager 권한 분리
- 상태 변경 indexed event
- 정상·권한 실패·중복·zero address·상태 전이·기간 경계 테스트
- 512회 Foundry fuzz test와 gas snapshot

### M4 — Blockchain Integration

- Anvil 로컬 EVM 배포
- `Origin Mock Bank`와 테스트 서명 키 seed
- Contract ABI 자동 생성
- 네트워크별 deployment manifest 생성
- Python 비동기 `BlockchainReader`와 JSON-RPC adapter
- Issuer·키 상태 조회와 안전한 RPC 오류 변환
- 이벤트 중복 방지 projection
- checkpoint 저장과 명시적 reorg rewind

## 동작 흐름

```text
Origin Mock Bank 등록
        ↓
Issuer 서명 키 등록
        ↓
Registry에 신뢰 상태 저장
        ↓
BlockchainReader가 JSON-RPC eth_call 수행
        ↓
Backend가 Issuer·Key 상태를 검증 규칙에 전달
        ↓
VERIFIED / NOT_REGISTERED / TAMPERED / ERROR 판정에 활용
```

블록체인에는 Proof 원문, OCR 결과, 카드 정보 또는 개인정보를 저장하지 않습니다. 저장 대상은 opaque ID, 주소, 상태, 유효기간과 metadata hash로 제한합니다.

## 기술 구성

| 영역 | 기술 | 용도 |
| --- | --- | --- |
| Contract | Solidity 0.8.26 | Registry 구현 |
| Contract library | OpenZeppelin 5.7.0 | 권한과 pause 제어 |
| Toolchain | Foundry 1.8.1 | 컴파일, 테스트, 배포 |
| Local chain | Anvil | 로컬 EVM 환경 |
| Integration | Python 3.11, httpx | 비동기 JSON-RPC 호출 |
| ABI | eth-abi, eth-utils | calldata와 응답 처리 |
| Indexer | SQLite | MVP projection과 checkpoint |
| Python tooling | uv, pytest, Ruff | 의존성, 테스트, 정적 검사 |

정확한 Python 의존성은 `pyproject.toml`, `uv.lock`을 기준으로 합니다. Contract 의존성은 `packages/contracts/dependencies.lock`에 고정되어 있습니다.

## 디렉터리 구조

```text
blockchain/
├── apps/api/
│   ├── src/infrastructure/blockchain/  # BlockchainReader와 RPC adapter
│   └── tests/infrastructure/blockchain/
├── services/indexer/
│   ├── src/originproof_indexer/        # projection과 checkpoint
│   └── tests/
├── packages/contracts/
│   ├── src/                            # M3 Registry contract
│   ├── test/                           # Foundry unit/fuzz test
│   ├── script/                         # M4 배포·ABI·의존성 스크립트
│   ├── abi/                            # Backend 연동 ABI
│   └── deployments/                    # 네트워크별 배포 manifest
├── docs/blockchain/                    # M1/M4 handoff 문서
├── Makefile
├── pyproject.toml
└── uv.lock
```

Foundry 생성물 `lib`, `out`, `cache`, `broadcast`와 Python 가상환경은 Git에 포함하지 않습니다.

## 사전 준비

- macOS 또는 Linux
- Python 3.11 이상
- [uv](https://docs.astral.sh/uv/)
- [Foundry](https://getfoundry.sh/)
- `jq`

```bash
python3 --version
uv --version
$HOME/.foundry/bin/forge --version
$HOME/.foundry/bin/anvil --version
jq --version
```

## 초기 설치

```bash
cd /Users/hamin/Desktop/blockchain
cp .env.example .env
make bootstrap
```

`make bootstrap`은 다음 순서로 동작합니다.

1. 고정된 OpenZeppelin과 forge-std를 설치합니다.
2. `uv.lock` 기준 Python 환경과 의존성을 준비합니다.
3. 실제 secret은 생성하거나 Git에 기록하지 않습니다.

## 테스트

전체 테스트:

```bash
make test
```

개별 테스트와 검사:

```bash
make test-contracts
make test-python
make lint
```

현재 검증 결과:

| 검사 | 결과 |
| --- | --- |
| Foundry test | 10개 통과 |
| Foundry fuzz | 512회 통과 |
| Python pytest | 9개 통과 |
| Python lint/format | 통과 |
| `IssuerRegistry` runtime size | 3,362 bytes |
| `IssuerKeyRegistry` runtime size | 3,984 bytes |

## 로컬 체인 배포

### 1. Anvil 실행

첫 번째 터미널:

```bash
make chain
```

기본 RPC URL은 `http://127.0.0.1:8545`, chain ID는 `31337`입니다.

### 2. 로컬 환경 변수 설정

두 번째 터미널에서 Anvil이 출력한 **로컬 테스트 계정의 private key**를 설정합니다.

```bash
export CHAIN_RPC_URL=http://127.0.0.1:8545
export CHAIN_DEPLOYER_PRIVATE_KEY=<ANVIL_LOCAL_TEST_PRIVATE_KEY>
```

Mock Issuer와 signer를 분리하려면 다음 값을 추가합니다.

```bash
export CHAIN_MOCK_ISSUER_ADDRESS=<ANVIL_LOCAL_TEST_ADDRESS>
export CHAIN_MOCK_SIGNER_ADDRESS=<ANVIL_LOCAL_TEST_ADDRESS>
```

지정하지 않으면 로컬 deployer 주소를 사용합니다. Anvil 키는 로컬 테스트에만 사용하며 실제 운영 키를 `.env`, 로그 또는 Git에 기록하면 안 됩니다.

### 3. 배포와 seed

```bash
make deploy-local-legacy
```

다음 작업이 순서대로 실행됩니다.

1. `IssuerRegistry` 배포
2. `IssuerKeyRegistry` 배포
3. `Origin Mock Bank` 등록
4. Mock Bank 서명 키 등록
5. ABI 생성
6. `packages/contracts/deployments/31337.legacy.local.json` 생성 (legacy 전용; 현행 API loader에 전달하지 않음)

Manifest에는 chain ID, 배포 블록, Git SHA, Contract 주소와 constructor 인자만 기록하며 private key와 RPC token은 기록하지 않습니다.

## 상태 모델

### Issuer

| 값 | 상태 | 의미 |
| ---: | --- | --- |
| 0 | `NONE` | 등록되지 않음 |
| 1 | `ACTIVE` | 정상 활동 중 |
| 2 | `SUSPENDED` | 일시 중지 |
| 3 | `REVOKED` | 영구 폐기 |

### Key

| 값 | 상태 | 의미 |
| ---: | --- | --- |
| 0 | `NONE` | 등록되지 않음 |
| 1 | `ACTIVE` | 등록된 키 |
| 2 | `REVOKED` | 영구 폐기 |

키는 아래 조건을 모두 만족해야 유효합니다.

```text
key.status == ACTIVE
issuer.status == ACTIVE
validFrom <= 검증 시각 < validUntil
```

폐기된 키는 다시 활성화하지 않습니다. 키 회전 시 새로운 `keyId`를 등록합니다.

## BlockchainReader 동작

Backend는 Contract에 직접 결합하지 않고 다음 port를 사용합니다.

```python
class BlockchainReader(Protocol):
    async def get_issuer(self, issuer_id: bytes) -> IssuerRecord | None: ...
    async def get_key(self, key_id: bytes) -> IssuerKeyRecord | None: ...
```

1. ID가 정확히 32 bytes인지 검사합니다.
2. `issuerStatus` 또는 `keyStatus`를 먼저 조회합니다.
3. `NONE`이면 `None`을 반환합니다.
4. 등록된 대상은 전체 구조체를 조회하고 ABI decode합니다.
5. HTTP·RPC·응답 형식 오류는 `BlockchainDependencyError`로 변환합니다.

RPC 장애를 미등록으로 처리하면 안 됩니다. M1 Backend는 이를 `ERROR + DEPENDENCY_UNAVAILABLE`로 매핑해야 합니다.

## Indexer 멱등성과 reorg

이벤트 중복 방지 키:

```text
(chain_id, block_number, log_index)
```

- 같은 이벤트를 다시 받으면 저장하지 않습니다.
- 정상 처리 중 checkpoint를 뒤로 이동할 수 없습니다.
- reorg 시 호출자가 확인한 마지막 안전 블록까지 명시적으로 rewind합니다.
- SQLite는 MVP용이며 팀 통합 시 PostgreSQL repository로 교체할 수 있습니다.

## 역할과 수정 경계

| 역할 | 소유 경로 | 담당 내용 |
| --- | --- | --- |
| M3 | `packages/contracts/src`, `packages/contracts/test` | Contract 로직과 테스트 |
| M4 | Contract `script`, `abi`, `deployments`, Indexer, API blockchain infrastructure | 배포와 연동 |

M3 interface 변경 시 ABI를 다시 생성하고 M4와 M1에 handoff합니다. 공통 Pydantic Schema와 최종 Verification 규칙은 M1 소유이므로 이 프로젝트에서 중복 정의하지 않습니다.

자세한 계약은 [M3/M4 handoff 문서](docs/blockchain/M3_M4_HANDOFF.md)를 참고합니다.

## 보안 원칙

- Proof 원문과 개인정보를 체인에 저장하지 않습니다.
- 실제 은행 상표나 실제 결제 문자를 fixture로 사용하지 않습니다.
- private key, RPC token, API key를 Git에 올리지 않습니다.
- 폐기는 되돌리지 않고 새로운 Issuer 또는 키 등록 절차를 사용합니다.
- 외부 호출과 payable 함수를 최소화합니다.
- 업그레이드 가능 Contract는 MVP에서 사용하지 않습니다.
- 테스트넷 배포 전 역할 분리, Slither, dependency·secret 검사를 수행합니다.

## 현재 제외된 범위

- `PolicyRegistry`, `ProofStatusRegistry`, `EvidenceAnchor`
- 실제 금융기관 연동과 테스트넷 배포
- 최종 Verification Status 판정
- 운영용 PostgreSQL Indexer
- Slither CI와 GitHub Actions

해당 기능은 M1 Schema와 interface 합의 후 별도 작업으로 추가합니다.

## 팀 저장소 병합 체크리스트

- [ ] 팀 Bootstrap commit SHA와 `AGENTS.md` 확인
- [ ] Contract dependency revision 비교
- [ ] 공통 chain 환경 변수 이름 비교
- [ ] Contract ABI diff 검토
- [ ] Deployment manifest 형식 합의
- [ ] M1 `BlockchainReader` port 충돌 확인
- [ ] Contract와 Python 테스트 재실행
- [ ] M1 clean worktree에서 chain integration 교차 테스트
- [ ] secret과 실제 개인정보가 없는지 확인

## 업데이트 기록

기능이 추가되거나 동작 방식이 바뀌면 관련 코드와 이 README를 같은 변경에서 갱신합니다.

| 날짜 | 변경 내용 |
| --- | --- |
| 2026-09-04 | M3 Registry, M4 배포·ABI·BlockchainReader·Indexer 최초 작성 |
