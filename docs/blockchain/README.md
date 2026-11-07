# OriginProof Blockchain — B 개발·실행 안내

B 여하민(`@hamin1228`)의 Contract·배포·Blockchain Adapter·Indexer 작업 안내입니다. **현재 구현은 v5 공동승인·기관 지갑 서명·문서 버전 관리이며, 기존 v1/v2 검증·consume 경로는 호환 대상으로 유지합니다.**

- 문서 기준: 2026-11-03, `phase/W6`의 `fb6e23b`.
- B 시연·검증 준비 환경: **Anvil(chain ID 31337)**. 사용자 선택이며 팀 전체 발표 체인 합의와는 구분합니다.
- [#124 로그 분할](https://github.com/OriginProof-3web/OriginProof/pull/124)·[#125 재시험 결함 수정](https://github.com/OriginProof-3web/OriginProof/pull/125)은 W6에 병합됐습니다. 병합 자체가 W6 전체 수용·공개 검증·발표 준비 완료를 뜻하지 않습니다.
- 저장소 시작은 [START_HERE](../../START_HERE.md), 범위·수용 기준은 [개발 계획서](../development_plan.md), 신규 신뢰 규칙은 [ADR 0004](../adr/0004-v5-governance-wallet-versioning.md), 모델·서명 계약은 [공유 계약](../shared_contract_v5.md)을 따릅니다.

## 담당 범위와 코드 위치

| 영역 | 경로 | B가 제공하는 것 |
| --- | --- | --- |
| 신규 Registry | [contracts/src](../../packages/contracts/src/) | 고정 승인자 3명의 2-of-3 공동승인, 기관 서명·nonce·deadline·소유권 검사, 버전·철회·정지 |
| 배포·ABI | [contracts/script](../../packages/contracts/script/), [abi](../../packages/contracts/abi/), [배포 안내](../../packages/contracts/deployments/README.md) | 생성 ABI, 네트워크별 manifest, CREATE·생성자 승인자·runtime 식별 검증 |
| 체인 연결 | [blockchain infrastructure](../../apps/api/src/infrastructure/blockchain/) | RPC·배포 검증, 공통 모델 변환, receipt/현재 상태 대사, UNKNOWN 원본 검색, 읽기 failover |
| 이벤트 기록 | [indexer](../../services/indexer/src/originproof_indexer/) | 배포별 journal·checkpoint, 중복·재시작·reorg 방어, receipt 기반 누락 검사 |
| 검사 | [Indexer tests](../../services/indexer/tests/), [API blockchain tests](../../apps/api/tests/infrastructure/blockchain/) | 정상·거부·실패·경계 사례와 opt-in 합성 EVM 연결 검사 |

인증·기관 신청·API/DB Operation 조율·공통 Python 모델은 C, 웹은 A, AI 분석·독립 QA는 D 소유입니다. B의 단위 검사와 전체 API·웹 연결 완료를 구분합니다. M3/M4는 과거 MVP 역할명입니다.

## 어떻게 동작하나요?

1. **기관 활성화:** C의 기관 확인·내부 승인·키 보유 증명 흐름 이후 고정 제안을 제출합니다. 컨트랙트는 서로 다른 승인자 2명의 승인을 요구하며 두 번째 승인 거래에서 실행합니다.
2. **문서 발행:** 기관 지갑이 EIP-712 업무 메시지에 서명합니다. 컨트랙트는 등록 기관·활성 키·문서 소유·nonce·deadline·정확한 다음 버전을 검사합니다. API가 기관 업무 개인키를 만들거나 보관하지 않습니다.
3. **버전 변경:** 새 버전 등록·최신 포인터 변경·이전 활성 버전 대체를 원자 처리합니다. 최신 버전을 철회해도 과거 버전이 다시 활성화되지 않습니다. 기관 정지 중에도 허용된 문서 철회 경로는 유지합니다.
4. **현재 상태 조회:** `WalletRegistryReadAdapter`는 검증된 배포의 같은 관측 블록에서 기관·키·문서·제안을 읽습니다. 미등록과 RPC 장애를 구분하고 projection을 현재 유효성의 권위로 사용하지 않습니다.
5. **거래 확정·복구:** tx hash만으로 성공을 선언하지 않습니다. 실제 calldata·sender·receipt·이벤트·당시/현재 상태를 대조하며, 결과 미확인은 UNKNOWN으로 보류합니다. 원본 검색에서 찾지 못했다는 이유만으로 재전송을 허가하지 않습니다.
6. **이벤트 동기화:** 로그를 최대 2,000블록씩 조회하고 같은 HTTP client의 RPC 호출을 동시 4개로 제한합니다. Projection은 최대 128블록마다 모든 거래 receipt의 Registry 이벤트와 로그를 대조하고 정본을 재확인한 뒤 journal·checkpoint를 함께 저장합니다. `sync()` 성공은 목표 확정 tip까지 도달한 뒤 반환합니다.

공개 안내의 조회·비교는 consume과 분리합니다. 원문·개인정보·전체 업무 payload·기관 개인키를 온체인에 저장하지 않습니다. AI 위험 설명은 발행 검증과 독립이며, `NOT_REGISTERED`를 가짜라고 단정하지 않습니다.

## Anvil에서 확인하기

아래 명령은 **저장소 루트**에서 실행합니다. Python 3.13, uv, Foundry(Forge·Anvil·Cast), jq가 필요합니다. API·PostgreSQL 통합 검사는 Docker도 필요합니다. 정확한 의존성은 `uv.lock`과 [Contract lock](../../packages/contracts/dependencies.lock)을 따릅니다.

### 1. 의존성 준비

```sh
UV_PROJECT_ENVIRONMENT=.uv-venv uv sync --all-packages --all-groups --frozen
make bootstrap-contracts
```

`bootstrap-contracts`는 Contract 라이브러리가 없으면 고정 태그를 설치합니다. 기존 라이브러리를 교체·감사하는 명령은 아닙니다. 스크립트는 기본적으로 `$HOME/.foundry/bin/forge`를 사용하므로 다른 설치 경로라면 실제 forge 디렉터리를 `FOUNDRY_BIN_DIR`로 지정합니다. 공유 lockfile을 임의로 재생성하지 않습니다.

### 2. 권장: 새 합성 노드로 자동 연결 검사

```sh
ORIGINPROOF_WALLET_LIVE=1 \
  .uv-venv/bin/pytest -q services/indexer/tests/test_wallet_live.py
```

검사가 직접 임시 Anvil을 시작해 배포·공동승인·발행·버전·철회·UNKNOWN 검색·SQLite 재시작·실제 reorg를 확인하고 종료합니다. 기존 8545 노드·DB·배포 manifest를 시연 환경으로 덮어쓰지 않습니다. **이 검사 통과는 서비스용 노드가 계속 실행 중이거나 브라우저 시연이 완료됐다는 뜻이 아닙니다.**

### 3. 수동 배포가 필요한 경우

자동 검사와 별도 절차입니다. 8545 포트를 사용 중인 노드를 임의로 종료하지 말고 먼저 대상 환경을 확인합니다. 첫 터미널에서 개발용 키가 화면·로그에 출력되지 않도록 실행하며 종료는 그 터미널의 `Ctrl+C`로 합니다.

```sh
anvil --host 127.0.0.1 --chain-id 31337 >/dev/null 2>&1
```

두 번째 터미널에서 아래를 실행합니다. 이 예시는 새 로컬 개발 노드만 대상으로 하며 `--unlocked`는 Anvil 전용입니다. 조회하는 값은 공개 계정 주소이고 개인키 입력은 없습니다.

```sh
export CHAIN_TARGET=anvil
export CHAIN_RPC_URL=http://127.0.0.1:8545
ANVIL_PUBLIC_ACCOUNTS=$(cast rpc eth_accounts --rpc-url "$CHAIN_RPC_URL")
ANVIL_DEPLOYER=$(printf '%s' "$ANVIL_PUBLIC_ACCOUNTS" | jq -r '.[0]')
export WALLET_APPROVER_1_ADDRESS=$(printf '%s' "$ANVIL_PUBLIC_ACCOUNTS" | jq -r '.[1]')
export WALLET_APPROVER_2_ADDRESS=$(printf '%s' "$ANVIL_PUBLIC_ACCOUNTS" | jq -r '.[2]')
export WALLET_APPROVER_3_ADDRESS=$(printf '%s' "$ANVIL_PUBLIC_ACCOUNTS" | jq -r '.[3]')
```

기존 manifest가 있으면 먼저 배포 식별·현재 노드·보존 필요를 확인합니다. 아래 명령은 새 배포를 만들므로 기존 주소를 계속 쓰는 API/DB와 섞으면 안 됩니다.

```sh
# 새 로컬 배포 경로가 비어 있을 때만 다음 단계 실행
if test ! -e packages/contracts/deployments/31337.wallet.local.json; then
  PYTHONPATH=apps/api/src:packages/python \
    UV_PROJECT_ENVIRONMENT=.uv-venv uv run --all-packages --all-groups --frozen \
    python packages/contracts/script/deploy_wallet_registry.py \
      --chain-target anvil --unlocked --sender "$ANVIL_DEPLOYER"
else
  printf '%s\n' 'Existing local manifest: verify the deployment before proceeding.'
fi
```

manifest의 주소·배포 블록·hash·생성 코드·승인자 검증이 실패하면 해당 배포를 연결 완료로 처리하지 않습니다. API에는 실제 배포 주소와 해당 manifest를 연결해야 합니다.

| 설정 | 로컬 호스트에서 API 실행 | Compose 내부 API |
| --- | --- | --- |
| `CHAIN_TARGET` | `anvil` | `anvil` |
| `API_BLOCKCHAIN_RPC_URL` | `http://127.0.0.1:8545` | `http://anvil:8545` |
| `API_BLOCKCHAIN_RPC_FALLBACK_URL` | 미설정 또는 별도 검증된 로컬 RPC | 동일 원칙 |
| `API_WALLET_REGISTRY_ADDRESS` | 해당 Anvil의 실제 새 Registry 주소 | 동일 원칙 |
| `API_WALLET_MANIFEST_PATH` | 기본 `packages/contracts/deployments/31337.wallet.local.json` 또는 명시 경로 | 컨테이너에서 읽을 수 있는 같은 배포의 경로 |

같은 chain ID라도 Anvil을 새로 띄우면 기존 DB·manifest와 동일 배포라고 가정하지 않습니다. 호스트에서 실행한 위 노드와 Compose의 `anvil` 서비스도 서로 다른 환경입니다. API·DB·로그인·원본 보관까지 포함한 시연은 [W6 개인 재현 안내](../runbooks/w6_rc_personal_reproduction.md)와 [C runtime 안내](../api/v5_c_runtime.md)를 따릅니다. `make demo`·`make deploy-local`은 기존 MVP 경로도 포함하며 신규 Wallet Registry 배포를 자동 대체하지 않습니다. `make demo-reset`은 DB 볼륨을 삭제하므로 일반 시작 절차로 사용하지 않습니다.

## 검사 명령과 근거

```sh
# 합성 RPC·코어·API 등을 포함한 Python 검사. opt-in 검사는 기본 생략됩니다.
make test

# B 중심 합성 회귀
.uv-venv/bin/pytest -q services/indexer/tests apps/api/tests/infrastructure/blockchain
.uv-venv/bin/ruff check apps/api/src/infrastructure/blockchain services/indexer

# Contract 정상·권한·fuzz 검사: Docker 기반 기존 명령
make test-contracts
```

실제 API/DB·failover 검사는 별도 환경을 요구합니다. [Anvil failover 검사](../../apps/api/tests/test_wallet_failover_live.py)는 opt-in Anvil·로컬 프록시·일회용 PostgreSQL로 두 Registry projection을 함께 확인합니다. `make typecheck`의 Python 부분은 compileall이며 정적 타입 검사와 구분합니다. MVP 검사 통과를 v5 전체 수용 성공으로 올리지 않습니다.

| 근거 | 실제 확인 범위 | 한계 |
| --- | --- | --- |
| [#125 재시험 수정](v5_retest_fixes_20261101.md) | 코드 `cda575c`: 전체 Python 1,450 PASS/20 SKIP, 새 Anvil 검사 1 PASS | 당시 SHA 결과이며 현재 README 기준의 전체 재검사 수치가 아님 |
| [#125 CI](https://github.com/OriginProof-3web/OriginProof/actions/runs/41278452016) | HEAD `57af5be`: Quality Gate, 실제 API/DB 복구·Contract 검사 통과 | 합본·다른 장비·발표 리허설 완료와 구분 |
| [Anvil 선택·재확인](v5_retest_fixes_20261101.md#2026-11-02-사용자-b의-anvil-선택) | 같은 코드 HEAD `57af5be`: 새 Anvil 검사 1 PASS(1.93초) | B 사용자 선택이며 공개 체인·서비스 상시 기동 증거가 아님 |

이 README 정리는 문서 변경입니다. 링크·경로·명령·정책 일관성·diff를 확인하며, 기능 검사나 실제 배포를 새로 실행한 것으로 기록하지 않습니다.

## 상세 인계와 과거 기록

| 문서 | 용도 |
| --- | --- |
| [읽기 Adapter·실제 API 연결 보완](v5_wallet_read_adapter.md) | C 원본 모델 소비, 주입·실제 연결 검사 이력 |
| [고정 승인자 provenance](v5_wallet_approver_provenance.md) | 임의 설정값이 아닌 CREATE·신뢰 build 근거 검증 |
| [receipt·상태 대사](v5_w5_reconciliation.md) | 저장 intent와 실제 거래·과거/현재 상태 비교 |
| [UNKNOWN 원본 검색](v5_w5_live_recovery.md) | bounded 검색·checkpoint·재전송 보류와 실제 로컬 검사 |
| [로그 분할](v5_log_windows_20261031.md), [재시험 결함·Anvil 선택](v5_retest_fixes_20261101.md) | 조회 비용·누락 방지·공유 동시 제한·실패/복구·검사 근거 |
| [Sepolia 실행 기록](../runbooks/sepolia_deploy.md) | 과거 공개 배포·설정 전환 기록. Anvil 선택으로 공개 목표 달성을 주장하지 않음 |
| [W6 B 개인 기여](../portfolio/W6-B.md) | 실제 기여·재사용·AI 활용·검증 SHA·미완료 |
| [M3 기록](M3_README.md), [M4 기록](M4_README.md), [과거 handoff](M3_M4_HANDOFF.md) | MVP 당시 구현. 현재 실행 명령·연결 상태로 재해석하지 않음 |

## 남은 확인과 인계 경계

- **과거 누락 복구:** 새 누락 방지는 이미 빠진 journal을 소급 복원하지 않습니다. B/C가 대상 배포·누락 이전 안전 지점을 확인한 뒤 기존 rewind 또는 별도 빈 projection DB에서 재생하고 D가 독립 확인해야 합니다. 자동 DB 삭제는 하지 않습니다.
- **공개 RPC 비용:** receipt 완전성 검사는 블록·거래 수에 비례합니다. Sepolia를 주 환경으로 바꾸려면 `logsBloom` 등 최적화와 실제 provider 부하 검사를 별도 판단해야 합니다. 같은 client의 동시 4개 제한은 프로세스 전체 provider quota나 10초 SLA가 아닙니다.
- **실제 연결·단계 판정:** 최종 RC·배포·DB·브라우저·다른 장비 재현과 전체 리허설은 각 실행 근거로 확인합니다. 과거 G07 mixed 실패 해결·W6 전체 완료·W7 동결은 해당 단계 기록과 독립 검토 없이 선언하지 않습니다.
- **공통 계약·소유권:** API/DB orchestration은 C, 화면은 A, 독립 QA는 D와 조율합니다. 과거 #104의 projection 대안은 #125와 겹치므로 receipt·정본 재검사를 유지하지 않는 병합을 피합니다. 최신 PR 상태는 GitHub를 확인합니다.

기능·환경에 대한 계획 승인, 코드 리뷰, 실제 연결 완료는 별개입니다. 개인 기여는 기록된 작업·SHA·검사 근거로 설명하며 전체 팀 구현이나 타인 승인으로 확대하지 않습니다.
