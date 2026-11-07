# PR 초안 — Sepolia Wallet Registry 배포 준비 (3회차 멘토 반영)

AI(어벤져스)가 김형준 요청으로 작성한 초안입니다. 대표 결정(2026-10-21)에 따른 멘토 반영 기능 PR이며 B 영역 담당자 여하민님은 **리뷰만** 합니다. 이 PR은 실제 Sepolia 배포를 하지 않았고, 사람 리뷰·CI 결과를 받은 것으로 표시하지 않습니다.

## 작업과 책임

- 구분: 기능(배포 준비) / 문서
- 브랜치 `feat/mentor-sepolia-deploy` → `phase/W5`, 시작 기준 `15c5588f9e96e2f530bb0e891c76af79b22a123c`
- 근거: 3회차 멘토 회신 C-2(13~16쪽)·D 전략②(Sepolia 배포 + Dual-RPC 폴백 + `.env` 스위치), [ADR 0004](../adr/0004-v5-governance-wallet-versioning.md)
- **선행 의존: B PR #64·#68·#69·#78·#79.** `OriginProofWalletRegistry.sol`/`OriginProofWalletGovernance.sol`은 `phase/W5`에 없고 `origin/codex/v5-*-b-*`에만 있습니다. 이 PR은 B 파일을 복사하지 않고 artifact 이름으로만 참조하므로, **실제 배포 명령은 B PR 병합 뒤에만 실행**됩니다.
- 상태 구분: 기존 Reader·projection·설정 계층은 `독립 구현·검사 완료`, 신규 Wallet Registry 경로는 `실제 연결 대기`(아래 B 연결 대기). Sepolia 실제 배포·`연결 검증 완료`는 아닙니다.

## 바뀐 것

| 파일 | 내용 |
| --- | --- |
| `packages/contracts/script/DeployWalletRegistry.s.sol` | `vm.deployCode("OriginProofWalletRegistry.sol:…", abi.encode(approvers))`. import가 없어 phase/W5에서도 컴파일됨. `WALLET_DEPLOY_CHAIN_ID`(31337/11155111만)와 연결 체인이 다르면 revert. 서명자는 CLI가 결정 |
| `packages/contracts/script/deploy_wallet_registry.py` | `CHAIN_TARGET`/`--chain-target`으로 체인 선택 → forge 실행 → `deployments/<chainId>.wallet[.local].json` 작성. **manifest 작성 전 tx input 전체를 로컬 artifact `bytecode.object` + `abi.encode(address[3])`와 바이트 단위로 비교**(접두·접미·승인자만 비교 아님), artifact 생성자 ABI가 `(address[3])`가 아니거나 미링크 bytecode면 거부. forge 배포와 `--deployment-tx`(브라우저 지갑 기록) 모두 같은 검사. 서명은 `--account`·`ETH_KEYSTORE_ACCOUNT`·`--ledger`/`--trezor`·`--unlocked`(Anvil 전용). 개인키 입력 경로 없음. RPC URL은 `CHAIN_RPC_URL` 또는 sepolia일 때 `SEPOLIA_RPC_URL` 환경 변수 → forge에는 `FOUNDRY_ETH_RPC_URL` 환경으로 전달, 출력·오류·명령 인자에 미포함. 기존 Sepolia manifest 덮어쓰기 거부 |
| `packages/contracts/foundry.toml` | `[rpc_endpoints]` `sepolia = "${SEPOLIA_RPC_URL}"`, `anvil = "http://127.0.0.1:8545"` 추가. 기존 profile/fmt/fuzz 설정은 그대로 |
| `apps/api/src/infrastructure/blockchain/network.py` | `CHAIN_TARGETS`(anvil 31337 / sepolia 11155111), 잘못된 값 오류, 주·보조 RPC 검증(anvil은 로컬 호스트, sepolia는 https, 보조≠주), 승인 노드 라벨 3개 + `모델(실제 기관 아님)` |
| `apps/api/src/infrastructure/blockchain/reader.py` (B 경로) | `JsonRpcBlockchainReader`가 URL 하나 또는 (주, 보조) 순서를 받음. 읽기 작업 단위로 주 RPC가 실패하면 보조 RPC에서 chain ID·genesis·배포 블록·코드 검사부터 다시 수행. 모두 실패하면 기존과 같은 `DependencyUnavailableError` |
| `apps/api/src/originproof_api/settings.py` | `CHAIN_TARGET`(기본 anvil) → `blockchain_chain_id`·`wallet_manifest_path` 결정, `API_BLOCKCHAIN_CHAIN_ID` 충돌 시 기동 오류, `blockchain_rpc_fallback_url`·`blockchain_rpc_urls`, `hide_input_in_errors=True` |
| `apps/api/src/originproof_api/main.py` | `configured_blockchain_reader`가 `blockchain_rpc_urls`(주→보조) 사용, `/v1/chain/network` 라우터 등록 |
| `apps/api/src/originproof_api/projection.py` | `verified_rpc_url`: Reader 검사를 통과한 첫 RPC(주→보조)로 `scan` 실행 |
| `apps/api/src/originproof_api/chain_management.py` | `ChainManagement.reader`가 주→보조 사용. `JsonRpcBlockchainWriter`는 의도적으로 주 RPC만(미확인 제출 재전송 방지) |
| `apps/api/src/originproof_api/chain_network.py` | `GET /v1/chain/network`: `chain_target`·`chain_id`·`rpc_fallback_configured`·`approver_nodes[{role,label,notice}]`. RPC URL·manifest 경로는 응답에 없음 |
| `.env.example` | `CHAIN_TARGET=anvil`, `API_BLOCKCHAIN_RPC_FALLBACK_URL=`, `API_WALLET_MANIFEST_PATH=`, `WALLET_APPROVER_1~3_ADDRESS=` 빈 자리. `API_BLOCKCHAIN_CHAIN_ID` 줄 제거 |
| `apps/api/tests/test_chain_target.py`, `services/indexer/tests/test_wallet_deploy_target.py` | 아래 검사 |
| `packages/schemas/generated/openapi.json` | 생성물. `scripts/generate_api_contracts.py` 재생성으로 `/v1/chain/network`·`ApproverNodeView`·`ChainNetworkView` 추가(+90행, 손 수정 없음) |
| `docs/runbooks/sepolia_deploy.md` | 대표 실행 절차, 별칭 기반 RPC 확인, 키·니모닉·RPC 키 비노출, 연결 범위와 B 연결 대기 |

manifest 형식은 B 현행 `deploy_local.py`(`31337.local.json`)와 같은 `chain_id`·`genesis_block_hash`·`deployment_block`·`deployment_block_hash`·`source_commit_sha`·`contracts.<name>.{address,constructor_arguments,abi_sha256}`·`deployment_id`·`roles`이며 `deployment_tx`·`chain_target`·`deployer`·`role_labels`를 추가했습니다. 기존 `31337.local.json`(legacy Registry)과 파일명을 분리해 덮어쓰지 않습니다. 현행 API `load_manifest`는 legacy 3종 계약용이라 이 wallet manifest를 읽지 않습니다.

## CHAIN_TARGET 연결 범위

연결됨(이 브랜치 코드): `Settings` → `configured_blockchain_reader`/`JsonRpcBlockchainReader`(검증·readiness), `ChainManagement.reader`, `projection.verified_rpc_url`/`scan`의 chain ID·주/보조 RPC, `WalletRuntime.domain`의 chainId, 기존 manifest의 chain ID 대조. 기존 manifest 경로(`API_BLOCKCHAIN_MANIFEST_PATH`)는 target별로 운영자가 지정하며 다른 네트워크 manifest는 Reader가 거부합니다.

**B 연결 대기**(B 브랜치 `origin/codex/v5-w5-b-live-recovery` `e7d0bae`의 이름, 이 브랜치에 없음):

| 연결할 곳 (이 브랜치) | 필요한 B 코드 |
| --- | --- |
| `create_app(wallet_chain=…)`(`apps/api/src/originproof_api/main.py`) → `WalletRuntime.rpc`(`wallet_runtime.py`), `check_ready` wallet 분기(`readiness.py`) | `apps/api/src/infrastructure/blockchain/wallet_rpc.py` `WalletRpc(client, rpc_url, *, chain_id, address, deployment_block, deployment_hash, runtime_code_hash, abi)` 생성 함수에 `Settings.blockchain_chain_id`·`blockchain_rpc_urls`·wallet manifest 값을 연결. 신규 경로 주/보조 RPC 전환도 여기 |
| `Settings.wallet_manifest_path`(경로 선택만, 읽는 코드 없음), `API_WALLET_REGISTRY_ADDRESS` 수동 설정 | B-C01 wallet manifest 로더(형식 B 확정). 이 래퍼 manifest에는 `WalletRpc`가 요구하는 `runtime_code_hash`가 아직 없음 |
| `projection.scan`(기존 ProofStatusRegistry 이벤트만) | `services/indexer/src/originproof_indexer/wallet_projection.py` `WalletProjection(engine, rpc)` |
| 신규 경로 복구·대사 | `wallet_recovery.py` `WalletRecovery`, `wallet_reconciliation.py` `WalletReconciler` |

## 승인자 라벨 고지

`승인 노드 #1 공공·도메인 검증원(KISA 모델)`, `승인 노드 #2 금융·산업 자율규제원(금융보안원 모델)`, `승인 노드 #3 통신·인프라 보안컨소시엄`은 멘토 제안의 3각 거버넌스를 보여 주는 **모델(실제 기관 아님)**입니다. manifest `role_labels`, API `approver_nodes[].notice`, 실행 안내에 모두 같은 고지를 붙였습니다. 실제 기관과의 협약·연동·승인은 없습니다.

## 검사 결과

검증 기준: branch `feat/mentor-sepolia-deploy`, `git rev-parse HEAD` = `15c5588f9e96e2f530bb0e891c76af79b22a123c` + 이 PR 변경(작업 트리, 커밋 전). 커밋 SHA는 본부 커밋 후 기록합니다. 실행일 2026-10-21(KST).

실행 환경: 본부가 미리 준비한 저장소 `.uv-venv`를 그대로 사용했습니다(이번 회차에 `uv sync`·설치·네트워크 다운로드 없음). `uv.lock` sha256 `e5122f523c7bc1e1bedf6795244cbdd2baaaeec9dc9c7f3fb088e2f064806dd6`, Python 3.13.15, FastAPI 0.142.2, Starlette 1.7.0, Pydantic 2.13.5, pytest 9.1.1, pytest-asyncio 1.4.0, ruff 0.9.10. `packages/contracts/lib`(gitignore 대상) OpenZeppelin 5.7.0·forge-std 1.16.2, forge 1.8.1-Homebrew, uv 0.12.10. CI는 uv 0.8.17·foundry v1.4.4라서 아래 결과는 **로컬 사전 확인**이고, 최종 판정은 PR CI입니다.

아래 명령은 모두 저장소 루트(`/Users/khj/Desktop/2반/OP-멘토-Sepolia`, forge는 그 아래 `packages/contracts`)에서 실행했습니다. 파이썬 명령 앞에는 모두 `PYTHONPATH=apps/api/src:packages/python:services/analyzer/src:services/indexer/src UV_PROJECT_ENVIRONMENT=.uv-venv uv run --no-sync`를 붙였고(표에서는 `<P>`로 줄임), ruff는 `UV_PROJECT_ENVIRONMENT=.uv-venv uv run --no-sync`(표에서는 `<U>`)로 실행했습니다. 명령마다 첫 줄 `command:`(실행한 명령 그대로), 전체 출력, 마지막 줄 `exit:`를 담은 로그 파일을 하나씩 저장소 밖 작업 폴더(`scratchpad/logs/`)에 남겼고, 표의 번호가 그 로그 파일 번호입니다.

| # | 명령 | 기대 | 실제 (exit) |
| --- | --- | --- | --- |
| 01 | `<P> pytest apps/api/tests` | 실패 0 | 214 passed / 5 skipped / 0 failed (0) |
| 02 | `<P> pytest services/analyzer/tests` | 실패 0 | 237 passed / 0 failed, 경고 1 (0) |
| 03 | `<P> pytest services/indexer/tests` | 실패 0 | 164 passed / 2 skipped / 0 failed (0) |
| 04 | `<P> pytest packages/python/tests` | 실패 0 | 43 passed / 0 failed (0) |
| 05 | `<P> pytest scripts/ci` | 실패 0 | 2 passed / 2 skipped / 0 failed (0) |
| 06 | `<P> pytest`(CI `uv run pytest`, pyproject testpaths 5곳 전체) | 실패 0 | 660 passed / 9 skipped / 0 failed, 경고 1 (0). 01~05 합계와 같음 |
| 33 | `<P> pytest apps/api/tests/test_chain_target.py services/indexer/tests/test_wallet_deploy_target.py` | 신규 통과 | 59 passed (0) |
| 07 | `forge build --offline` | 성공 | `No files changed, compilation skipped`(이전 빌드 캐시) (0) |
| 07b | `forge build --offline --force` | 성공 | `Compiling 41 files with Solc 0.8.26`, `Compiler run successful!` (0). lint note·warning은 기존 B 파일에만 있고 `script/DeployWalletRegistry.s.sol`에는 없음 |
| 08 | `forge test --offline` | 기존 통과 | 5 suites, 26 passed / 0 failed / 0 skipped (0) |
| 09 | `forge fmt --check` | — | **실패 (1)**: `test/IssuerKeyRegistry.t.sol`, `test/IssuerRegistry.t.sol` 2개만 차이. 둘 다 B 영역이고 이 PR이 건드리지 않았습니다. CI에는 fmt 검사가 없습니다 |
| 10 | `forge fmt --check script/DeployWalletRegistry.s.sol` | 통과 | 통과 (0) |
| 11 | 재생성 전 생성 대상(CI 43행과 같은 경로) `git diff` 저장, `git diff --stat -- packages/schemas/generated` | — | `openapi.json` 90 insertions(+) 1 file (0) |
| 12~16 | 1차: `<P> --package originproof-core python scripts/generate_schemas.py`, `<P> --package originproof-core python scripts/generate_golden_fixture.py`, `<P> --package originproof-core python scripts/generate_wallet_contracts.py`, `<P> --package originproof-core python scripts/generate_finals_golden.py`, `<P> --package originproof-api python scripts/generate_api_contracts.py`(Makefile `generate` 5줄과 1:1, 각각 실행) | 성공 | 5개 모두 (0). pnpm이 필요한 단계 없음 |
| 17 | 1차 뒤 생성 대상 `git diff`를 11번과 `cmp`, `git diff --stat -- packages/schemas/generated` | 같음 | 같음 (0). 생성물 변경은 `openapi.json` 1개(+90행)뿐이고 새 생성 파일 없음. 스크립트 출력이 작업 트리 파일과 바이트 단위로 같음(손 수정 없음) |
| 18~22 | 2차: 12~16과 같은 5개 명령 재실행 | 성공 | 5개 모두 (0) |
| 23 | 2차 뒤 `git diff`를 1차와 `cmp`, `git diff --stat -- packages/schemas/generated`를 1차와 `cmp` | 새 변화 없음 | 둘 다 같음 (0). stat은 1차와 동일하게 `openapi.json` 90 insertions(+) |
| 24 | `grep -c '"/v1/chain/network"' packages/schemas/generated/openapi.json`, `git diff --exit-code --stat -- <CI 43행 경로>` | 차이는 커밋 대상인 `openapi.json`뿐 | 경로 1건, `openapi.json` +90행(`/v1/chain/network`, `ApproverNodeView`·`ChainNetworkView`). HEAD 대비 `--exit-code`가 1인 것은 이 파일이 아직 커밋 전이기 때문이며, 커밋에 포함하면 CI 조건을 충족합니다 |
| 25 | `<U> ruff check apps packages services scripts`(CI 명령) | 통과 | 로컬 **실패 (1)**: 26건 모두 `packages/contracts/lib/**/forge-std/scripts/vm.py`(gitignore 대상 외부 라이브러리). CI python-quality job에는 lib이 없어 해당되지 않습니다 |
| 26 | 25번 + `--extend-exclude packages/contracts/lib` | 통과 | `All checks passed!` (0) |
| 27 | `<U> ruff check apps packages/python services scripts`(Makefile `lint`) | 통과 | `All checks passed!` (0) |
| 28 | `<U> ruff check`(변경 파이썬 파일 10개) | 통과 | `All checks passed!` (0) |
| 29 | `<U> ruff format --check`(변경 파이썬 파일 10개) | 통과 | 10 files already formatted (0) |
| 30 | `<U> ruff format --check --exclude packages/contracts/lib apps packages services scripts` | — | **실패 (1)**: 이 PR 밖 3개 파일(아래), 115 files already formatted. CI에는 format 검사가 없습니다 |
| 31 | `<P> python scripts/ci/validate_structure.py` | 통과 | `Repository structure is valid: finals-v3` (0) |
| 32 | `<P> python -m compileall -q apps packages services scripts` | 통과 | (0) |
| — | 웹 lint/typecheck/test/build/e2e(CI python-quality 후반) | — | 미실행(도구 없음: pnpm) |
| — | `make test-contracts`(Docker deployer 이미지), `make test-w6-c-live`(Docker PostgreSQL), `make security`(pip-audit 다운로드) | — | 미실행(Docker 컨테이너 빌드·외부 다운로드가 필요해 이번 금지 범위). CI `c-recovery`·`contracts` job에서 확인 |
| — | Sepolia 호출·배포, 브라우저 지갑, `forge script --broadcast` | 실행 안 함 | 미실행(대표가 직접 실행) |

이번 변경 밖의 기존 형식 차이는 고치지 않았습니다. CI에는 해당 검사가 없습니다. `ruff format --check`에서는 `packages/python/originproof_core/wallet_verification.py`, `services/analyzer/src/originproof_analyzer/main.py`, `services/analyzer/tests/test_analysis_consumer_fixtures.py`, `forge fmt --check`(forge 1.8.1)에서는 `test/IssuerKeyRegistry.t.sol`, `test/IssuerRegistry.t.sol`이 걸립니다.

이전 회차 기록(이번 회차 재실행 안 함, 당시 스크래치 사본·다른 venv 사용): 가짜 `OriginProofWalletRegistry`(`constructor(address[3])`, B 코드 아님)로 로컬 Anvil(31337) `--unlocked` 배포 → manifest 작성, 같은 tx `--deployment-tx` 기록 → 동일 manifest, 승인자 3번만 바꾼 기록 → `deployment input does not match the local Registry artifact`·파일 없음, `cast tx <tx> input` = artifact bytecode + `abi.encode(address[3])` 바이트 동일, `SEPOLIA_RPC_URL=<로컬 Anvil> cast chain-id --rpc-url sepolia` → 31337 / 미설정 시 `environment variable SEPOLIA_RPC_URL not found`. B 브랜치(`e7d0bae`) contracts 사본 Anvil 배포·`approve` 읽기 호출도 이전 회차 기록입니다. 이번 회차에는 Anvil·RPC를 실행하지 않았습니다. 같은 사례의 바이트 비교·거부는 위 07번 신규 테스트 59개가 실행할 때마다 확인합니다(mock RPC, 실제 체인 아님).

신규·변경 테스트가 확인하는 것: (배포 래퍼) 일치 input → manifest 기록, 승인자 인자는 같고 bytecode만 다른 input·생성자 인자 1개만 다른 input·뒤에 바이트를 덧붙인 input·잘린 input 거부와 manifest 미생성을 forge 경로와 `--deployment-tx` 경로 각각에서, 미링크/빈 bytecode·생성자 ABI 불일치·artifact 없음은 RPC 호출 전 거부, `SEPOLIA_RPC_URL` 환경 변수 사용과 anvil에서 무시. (API) anvil→sepolia, sepolia→anvil 순서로 전환하며 `configured_blockchain_reader`의 chain ID·(주, 보조) URL·manifest deployment ID, 주 RPC 거부 시 보조 RPC로 읽기 성공, `projection.verified_rpc_url`이 보조 RPC 선택, `WalletRuntime.domain` chainId, 두 RPC 모두 다른 체인이면 판정 보류, 다른 target manifest면 Reader 비활성. 기존 설정 검증·라벨·키 비노출 검사는 유지.

## 대표가 직접 할 일

[실행 안내](../runbooks/sepolia_deploy.md) 순서대로: 테스트 ETH 받기 → 배포 지갑·승인자 지갑 3개 준비 → `.env` 설정 → B PR 병합 확인 뒤 배포 → `cast … --rpc-url sepolia`(별칭)와 Etherscan 확인 → `API_WALLET_REGISTRY_ADDRESS` 설정 → 필요 시 Anvil 전환(Sepolia 값이 없는 새 터미널, `cast chain-id --rpc-url anvil` 확인) → 모든 RPC 호출이 끝난 마지막 단계에서 `unset SEPOLIA_RPC_URL CHAIN_RPC_URL`(이후 RPC 호출 없음). 개인키·니모닉은 keystore·하드웨어·브라우저 지갑 안에만 둡니다.

## 남은 일과 한계

- `packages/schemas/generated/openapi.json`은 본부가 준비한 `.uv-venv`에서 `scripts/generate_api_contracts.py`로 재생성해 이 PR에 포함했습니다(손 수정 없음). 웹 타입이 필요하면 `ChainNetworkView`를 `scripts/generate_api_contracts.py` 모델 목록에 넣을지는 C가 정합니다(현재 `types/api.ts`에는 없음). 로컬 uv·forge 버전이 CI와 달라 생성물 최신성의 최종 판정은 CI입니다.
- 신규 Wallet Registry 경로의 실제 체인 연결·Dual-RPC·projection은 위 B 연결 대기입니다. G07 해소도 그 뒤입니다.
- `reader.py`(B 경로)에 읽기 작업 단위 failover를 넣었습니다. B 리뷰가 필요합니다.
- 브라우저 지갑 배포는 tx input이 로컬 artifact와 바이트 단위로 같아야 기록됩니다. Remix 등 다른 컴파일 결과는 거부됩니다.
- `.env.example`에서 `API_BLOCKCHAIN_CHAIN_ID`를 뺐습니다. 기존 로컬 `.env`에 31337이 남아 있어도 anvil에서는 동작하지만 `CHAIN_TARGET=sepolia`로 바꾸면 기동 오류로 알려 줍니다.
- `apps/api/src/originproof_api/`(C 소유)의 `settings.py`·`main.py`·`projection.py`·`chain_management.py`·`chain_network.py`를 대표 지시로 변경했습니다. C(사용자님 `@Jordi2801K`) 확인도 필요합니다.

## 리뷰 요청

**리뷰 요청: B 여하민** (`@hamin1228`). 아직 리뷰를 받지 않았습니다.

- **B 여하민님 `@hamin1228`**: 배포 스크립트·래퍼의 bytecode 전체 비교, manifest 필드(`deployment_tx`·`role_labels`·`*.wallet[.local].json`, `runtime_code_hash` 필요 여부), `network.py`·`reader.py` failover, foundry.toml 별칭, B 연결 대기 목록의 연결 방법. B PR 병합 순서와 이 PR의 병합 시점 결정.
- C 사용자님 `@Jordi2801K`: `Settings`의 `CHAIN_TARGET`·`hide_input_in_errors`, projection·ChainManagement 연결, `/v1/chain/network` 응답 계약과 OpenAPI 재생성.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
