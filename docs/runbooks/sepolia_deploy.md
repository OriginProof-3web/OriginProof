# Sepolia Wallet Registry 배포 실행 안내

대표가 자기 지갑으로 직접 실행하는 절차입니다. AI·팀원은 이 문서를 준비했을 뿐 Sepolia에 배포하거나 거래를 보낸 적이 없습니다. 근거는 3회차 멘토 회신 C-2(13~16쪽)와 D 전략②이며, 공동승인·기관 서명 규칙은 [ADR 0004](../adr/0004-v5-governance-wallet-versioning.md)를 따릅니다.

**전제: B PR(#64/#68/#69/#78/#79) 병합 뒤 실행합니다.** 배포 대상 `OriginProofWalletRegistry`(Governance 상속)는 아직 `phase/W5`에 없고 B 리뷰 중 브랜치(`origin/codex/v5-*-b-*`)에만 있습니다. 병합 전에 실행하면 래퍼가 `B PR(#64/#68/#69/#78/#79) must be merged first`로 멈춥니다.

승인자 3명의 라벨은 시연용 **모델(실제 기관 아님)**입니다. 실제 KISA·금융보안원·통신사와 계약하거나 연동한 것이 아닙니다.

| 역할 | 라벨 | 표기 |
| --- | --- | --- |
| `approver_1` | 승인 노드 #1 공공·도메인 검증원(KISA 모델) | 모델(실제 기관 아님) |
| `approver_2` | 승인 노드 #2 금융·산업 자율규제원(금융보안원 모델) | 모델(실제 기관 아님) |
| `approver_3` | 승인 노드 #3 통신·인프라 보안컨소시엄 | 모델(실제 기관 아님) |

## 실제 배포 결과 (2026-10-27)

| 항목 | 값 |
| --- | --- |
| Registry 주소 | [`0xE540Bf29622AFFf40174B76992b016112f372A2e`](https://sepolia.etherscan.io/address/0xE540Bf29622AFFf40174B76992b016112f372A2e) |
| 배포 거래 | [`0x9e40ba5f…a4bc`](https://sepolia.etherscan.io/tx/0x9e40ba5f455da2a583989d24255c324230bdb804255e249f35cf256f4866a4bc) · 블록 12001755 · status 1 · 19,035,289 gas · 0.0001047 ETH |
| 배포 지갑 | `0xED8ad0A5841451b91883Eac3A9e41982878b3b50` (대표 시험용 지갑, Foundry keystore) |
| 승인자(모델, 실제 기관 아님) | #1 KISA 모델 `0x4f12cb684fbd76962A85E5Bc66fe769597aeCA2a` · #2 금융보안원 모델 `0xE5d0531Ef3c419A5acFB3774B731A2d239ECb240` · #3 통신 컨소시엄 `0x2Efd70f041Fe1b400125e8b99029c5fa0Af4eB1c` |
| 배포 기록 | `packages/contracts/deployments/11155111.wallet.json` (source `72440c0`) |
| 확인 | API `WalletRegistryConnector`로 실제 Sepolia 연결·CREATE/코드/승인자 검증·`getIssuer` 읽기 성공. 주 RPC 장애 시 보조 RPC 연결 성공 |

**가스 주의:** forge 1.8.1 로컬 모의 실행(약 2.7M gas)은 Sepolia의 오른 코드 저장 비용을 모릅니다. 실제 노드 `eth_estimateGas`는 약 19.19M이었고, 130%·200% 배포(`0xa11034…`, `0xc98a4e…`)는 가스 부족으로 실패했습니다. 래퍼의 Sepolia 기본 배율은 800입니다(Anvil 200). 실제 사용 가스만 청구됩니다.

## Sepolia 시연 데이터 (2026-10-27, `scripts/fixtures/wallet_demo_flow.py --signer keystore`)

실제 `/v3` API(일회용 PostgreSQL, `CHAIN_TARGET=sepolia`) → Sepolia Registry 로 끝까지 실행했습니다. 기관은 합성 `iss_origin_mock_bank`, 지갑은 대표 시험용 계정입니다.

| 단계 | 결과 |
| --- | --- |
| 기관 신청·데모 메일·내부 승인·키 증명 | 완료(기관 지갑 `0x2c972C6c390C7742BFd070bC57DDAb539235d161` 서명) |
| 2-of-3 공동승인 | 제안 `0xe796b23d…5cda82` **EXECUTED**, 승인 #1 KISA 모델·#2 금융보안원 모델 → 기관 **ACTIVE**. 제안 tx `0x97a46147…4fa7`, 승인 #1 tx `0xbb451d4a…02e3`, 승인 #2 금융보안원 모델·실행 tx `0x36e27b033c36492863dac98a4a4ba56101c25f4cbaf1d12501e6f16bc4dc3641` · 블록 12001986 |
| 안내문 v1(154,000원) | 발행 확정 tx `0x394f0cce482c61269c8d3bf1d3e95202b3d717b7bfa3f03e18197d20b61a1f88` |
| 안내문 v2(120,000원, 정정) | 발행 확정 tx `0xf7d6b418e9b0f766ee8f985069324ade216e9e87914c060f907e4c67bcb3542d` · document `0x2bc2f605c8b185bc9b1d5d9ed2560a62ccd4e2a6338574c3925752b63c07e8a9` |
| 검증 | 정본 v2 **VERIFIED** · 금액 1원 변조 **TAMPERED**(PROTECTED_FIELDS_MISMATCH) · 정정 전 v1 **SUPERSEDED** |

관찰: 공개 RPC(publicnode)는 읽기가 자주 실패해 보조(tenderly)로 전환됐고, 승인 #2 거래 확인 때 두 노드 모두 잠시 최신 블록을 못 읽어 API가 503을 냈습니다(체인 상태는 EXECUTED 로 정상). 스크립트는 일시적 503을 자동 재시도합니다. 시연 당일은 Alchemy/Infura 같은 키 RPC를 주로 쓰는 것을 권합니다.

## 구성 요소

- `packages/contracts/script/DeployWalletRegistry.s.sol`: B 소스를 import하지 않고 artifact 이름으로 배포합니다. `WALLET_DEPLOY_CHAIN_ID`와 연결된 체인이 다르면 거부합니다.
- `packages/contracts/script/deploy_wallet_registry.py`: `CHAIN_TARGET`(또는 `--chain-target`)으로 31337/11155111을 고르고 forge를 실행한 뒤 `packages/contracts/deployments/<chainId>.wallet[.local].json`을 씁니다. manifest를 쓰기 전에 배포 tx의 input 전체가 로컬 artifact(`out/OriginProofWalletRegistry.sol/OriginProofWalletRegistry.json`)의 creation bytecode + ABI 인코딩한 생성자 인자(`address[3]`)와 **바이트 단위로 같은지** 확인하고, 다르면 manifest를 만들지 않습니다(forge 배포와 `--deployment-tx` 기록 모두). 기존 Sepolia manifest는 덮어쓰지 않습니다.
- `packages/contracts/foundry.toml` `[rpc_endpoints]`: `sepolia = "${SEPOLIA_RPC_URL}"`, `anvil = "http://127.0.0.1:8545"`. `cast … --rpc-url sepolia`처럼 **별칭**만 명령에 쓰고 키가 든 URL은 환경 변수에만 둡니다. `cast`는 `packages/contracts`에서 실행해야 별칭을 읽습니다.
- API: `CHAIN_TARGET=anvil|sepolia`(기본 anvil)가 chain ID, 주/보조 RPC 규칙, wallet manifest 기본 경로를 정하고 잘못된 값은 기동 오류입니다. 실제 소비 경로의 연결 범위는 아래 [연결 범위](#연결-범위와-b-연결-대기)를 봅니다. `GET /v1/chain/network`는 선택된 네트워크와 승인 노드 라벨만 반환합니다(RPC URL·manifest 경로는 반환하지 않음).

## 대표가 할 일

1. **테스트 ETH 받기.** 배포 지갑 주소로 Sepolia faucet에서 테스트 ETH를 받습니다. Anvil 실행에서 forge가 추정한 배포 가스는 약 3.5M gas, 비용은 약 0.007 ETH(최대 수수료 약 2 gwei 기준)였습니다. Sepolia 가스 가격에 따라 달라지므로 여유 있게 받습니다. 승인자 지갑은 이후 승인 거래를 보낼 때 각자 소량이 필요합니다.
2. **지갑 4개 준비.** 배포 지갑 1개와 승인자 지갑 3개를 서로 다른 주소로 준비합니다. 승인자는 배포 시 **공개 주소만** 필요합니다.
   - 배포 지갑은 하드웨어 지갑(`--ledger`/`--trezor`)이나 Foundry keystore를 씁니다. keystore는 `cast wallet import deployer --interactive`로 만들며, 개인키는 숨김 프롬프트에만 입력하고 암호화 파일(`~/.foundry/keystores/deployer`)로만 남깁니다.
   - 승인자 지갑은 브라우저 지갑(MetaMask 등)이나 하드웨어 지갑을 권장합니다. 배포 지갑과 같은 주소를 승인자로 쓰지 않습니다.
3. **API `.env` 설정.** 저장소 루트의 로컬 `.env`(Git 제외)에 다음 이름을 채웁니다. 이름과 빈 자리는 `.env.example`에 있습니다. 이 값은 파일에만 두고 명령 인자로 넘기지 않습니다.
   - `CHAIN_TARGET=sepolia`
   - `API_BLOCKCHAIN_RPC_URL=`(주 RPC, https), `API_BLOCKCHAIN_RPC_FALLBACK_URL=`(보조 RPC, https, 주와 달라야 함)
   - `WALLET_APPROVER_1_ADDRESS=`, `WALLET_APPROVER_2_ADDRESS=`, `WALLET_APPROVER_3_ADDRESS=`(공개 주소)
   - `API_BLOCKCHAIN_CHAIN_ID`는 지웁니다. `CHAIN_TARGET`이 정하며 값이 다르면 API가 기동을 거부합니다.
   - `API_BLOCKCHAIN_MANIFEST_PATH`(기존 Issuer/Key/ProofStatus Registry manifest)는 그 네트워크의 manifest만 가리킵니다. Sepolia에는 기존 Registry를 배포하지 않으므로 비워 두면 기존 Reader는 "설정 없음(503/판정 보류)"이 됩니다. 31337 manifest가 남아 있으면 chain ID 불일치로 역시 사용하지 않습니다.
   - 개인키·니모닉·keystore 비밀번호는 `.env`에 넣지 않습니다.
4. **배포.** B PR 병합 뒤 최신 `phase/W5` 기준에서 실행합니다. 4~5단계는 같은 터미널에서 이어서 합니다.
   1. 의존성과 artifact 준비: `cd packages/contracts && forge build`(필요한 `lib/`은 B의 `script/bootstrap_dependencies.sh` 또는 CI와 같은 버전 OpenZeppelin v5.7.0·forge-std v1.16.2).
   2. RPC URL을 히스토리 없이 현재 셸 환경 변수로만 넣습니다(화면에 표시되지 않음): `read -rs SEPOLIA_RPC_URL && export SEPOLIA_RPC_URL`
   3. 연결 확인(`packages/contracts`에서): `cast chain-id --rpc-url sepolia` → `11155111`이어야 합니다. `sepolia`는 foundry.toml 별칭이며 URL은 환경 변수에서 읽습니다.
   4. 승인자 주소를 셸에 넣습니다: `export WALLET_APPROVER_1_ADDRESS=0x… WALLET_APPROVER_2_ADDRESS=0x… WALLET_APPROVER_3_ADDRESS=0x…`(공개 주소라 기록돼도 무방).
   5. 저장소 루트로 돌아가(`cd ../..`) 실행합니다. 래퍼는 `SEPOLIA_RPC_URL`(또는 `CHAIN_RPC_URL`)을 환경에서 읽어 forge에도 환경으로만 넘깁니다.
      - keystore: `PYTHONPATH=apps/api/src:packages/python uv run --package originproof-api python packages/contracts/script/deploy_wallet_registry.py --chain-target sepolia --account deployer --gas-multiplier 800`(Sepolia 기본값도 800)(비밀번호는 forge가 숨김 프롬프트로 묻습니다)
      - 하드웨어 지갑: 위 명령에서 `--account deployer` 대신 `--ledger --sender 0x<배포주소>` 또는 `--trezor --sender 0x<배포주소>`
      - 브라우저 지갑: 설치된 forge 1.8.1에는 브라우저 지갑 서명 옵션이 없습니다. 브라우저 지갑으로 직접 배포했다면 tx hash로 manifest만 기록합니다: `… deploy_wallet_registry.py --chain-target sepolia --deployment-tx 0x<tx hash>`. 이 경로도 tx input이 **로컬 `forge build` artifact의 `bytecode.object` + `abi.encode(address[3] 승인자)`와 바이트 단위로 같아야** 기록됩니다. Remix 등 다른 컴파일 결과는 metadata가 달라 거부되므로, 배포 데이터는 로컬 artifact의 bytecode 뒤에 `cast abi-encode "f(address[3])" "[승인자1,승인자2,승인자3]"` 결과(앞의 `0x` 제외)를 붙여 만듭니다.
   6. 출력된 `packages/contracts/deployments/11155111.wallet.json`의 `address`·`deployment_tx`·`deployment_block`을 확인합니다. **아직 `SEPOLIA_RPC_URL`을 지우지 않습니다**(5단계 확인에 필요, 지우는 것은 마지막 8단계).
5. **배포 확인.** `packages/contracts`에서 실행합니다(`cd packages/contracts`).
   1. `cast receipt <deployment_tx> status --rpc-url sepolia` → `1 (success)`, `cast receipt <deployment_tx> contractAddress --rpc-url sepolia` → manifest `address`와 같아야 합니다.
   2. `cast code <address> --rpc-url sepolia` → `0x`가 아닌 코드가 나와야 합니다.
   3. 승인자 인식(거래를 보내지 않는 읽기 호출): `cast call <address> "approve(bytes32)" 0x0000000000000000000000000000000000000000000000000000000000000001 --from <승인자 주소> --rpc-url sepolia`. 승인자는 `UnknownProposal`, 다른 주소는 `Unauthorized`로 되돌아오면 정상입니다.
   4. 브라우저에서 `https://sepolia.etherscan.io/tx/<deployment_tx>`(Status Success, From이 배포 지갑, Contract Creation이 `address`)와 `https://sepolia.etherscan.io/address/<address>`(코드 존재, 블록 번호가 `deployment_block`)를 봅니다.
   5. API `.env`에 `API_WALLET_REGISTRY_ADDRESS=<address>`를 설정합니다(API는 이 주소와 `CHAIN_TARGET`의 wallet manifest가 일치할 때만 기동 시 자동 연결합니다. 아래 "API 자동 연결"). `11155111.wallet.json`은 `.gitignore`의 `*.local.json` 규칙에 걸리지 않으므로, 검증된 비로컬 manifest의 커밋 여부는 B 리뷰로 정합니다(현재 `phase/W6`에는 `packages/contracts/deployments/README.md`와 검증된 `11155111.wallet.json`이 커밋되어 있습니다).
6. **실패 시 Anvil 전환.** Anvil 명령은 **새 터미널**에서 실행합니다. 래퍼는 `CHAIN_RPC_URL`을 target과 관계없이 먼저 읽으므로, Sepolia RPC 값이 남은 4~5단계 터미널에서 실행하지 않습니다. 새 터미널에서 값을 출력하지 않고 비어 있는지만 확인합니다: `[ -z "${SEPOLIA_RPC_URL-}${CHAIN_RPC_URL-}" ] && echo clean` → `clean`이어야 합니다. 현장 RPC가 느리거나 끊기면 `.env`에서 `CHAIN_TARGET=anvil`, `API_BLOCKCHAIN_RPC_URL=http://anvil:8545`(호스트 실행이면 `http://127.0.0.1:8545`), `API_BLOCKCHAIN_RPC_FALLBACK_URL=` 비움(또는 다른 로컬 노드), `API_BLOCKCHAIN_MANIFEST_PATH`를 31337 manifest로, `API_WALLET_REGISTRY_ADDRESS`를 Anvil 배포 주소로 바꾸고 API를 재시작합니다. 거꾸로 Anvil→Sepolia도 같은 값들을 되돌리면 됩니다.
   - Anvil은 시작 화면에 개발용 개인키를 출력하므로 **처음부터 출력을 버리는 명령으로만** 띄웁니다: `anvil --chain-id 31337 >/dev/null 2>&1 &`
   - `packages/contracts`에서 `cast chain-id --rpc-url anvil` → `31337`을 확인하고, `cast rpc eth_accounts --rpc-url anvil`로 공개 주소만 보고, 1·2·3번 주소를 `WALLET_APPROVER_1~3_ADDRESS`로, 0번 주소를 `--sender`로 씁니다.
   - 저장소 루트에서 `… deploy_wallet_registry.py --chain-target anvil --unlocked --sender 0x<계정0>` → `deployments/31337.wallet.local.json`(Git 제외). Anvil 대상은 RPC 환경 변수가 없으면 `http://127.0.0.1:8545`를 씁니다. `--unlocked`는 Anvil 전용이며 래퍼가 Sepolia에서 거부합니다.
   - 끝나면 `kill %1`(같은 셸) 또는 `pkill -x anvil`로 멈춥니다. 시연에서는 Anvil 결과가 공개 체인 검증이 아님을 표시합니다.
7. **키·니모닉·RPC 키를 파일·로그·출력·셸 히스토리에 남기지 않기.**
   - `--private-key`, `PRIVATE_KEY=` 환경 변수, `.env`의 개인키를 쓰지 않습니다. 래퍼에는 개인키 입력 경로가 없습니다.
   - 서명은 keystore(`--account`, 또는 `ETH_KEYSTORE_ACCOUNT` 환경 변수에 계정 **이름**만), 하드웨어 지갑(`--ledger`/`--trezor`), 브라우저 지갑 중 하나만 씁니다.
   - 비밀 입력은 `cast wallet import --interactive`나 forge의 숨김 비밀번호 프롬프트, `read -rs`로만 합니다. 명령줄 인자에 비밀을 쓰면 히스토리·프로세스 목록에 남습니다. `--unsafe-password`·`ETH_PASSWORD`·비밀번호 파일은 쓰지 않습니다.
   - RPC URL에 포함된 provider 키도 비밀입니다. `--rpc-url`에는 별칭(`sepolia`, `anvil`)만 쓰고, 환경 변수를 `$` 확장해 URL 값 자체를 명령 인자로 넘기지 않습니다(프로세스 목록에 노출). forge도 래퍼가 환경으로만 URL을 넘깁니다. 별칭 대신 `ETH_RPC_URL` 환경 변수를 export하면 `cast`가 `--rpc-url` 없이 그 값을 읽는 방법도 같습니다.
   - 래퍼와 API 설정 오류는 URL을 출력하지 않지만, forge/cast의 네트워크 오류 메시지에는 URL이 보일 수 있으므로 원본 터미널 로그를 공유하지 않습니다.
   - 실수로 명령줄에 입력했다면 히스토리 파일(`~/.zsh_history` 등)에서 그 줄을 지우고, 그 키는 노출된 것으로 보고 폐기해 새 지갑·새 RPC 키로 바꿉니다.
   - 니모닉은 종이·하드웨어 지갑 백업에만 두고 저장소·메신저·AI 대화에 붙여 넣지 않습니다.
8. **마지막 정리(RPC 호출 없음).** 위 4~6단계의 모든 RPC 호출(4·5단계의 `cast` 연결·배포 확인, 래퍼 실행, 6단계 Anvil 확인·배포)이 끝난 뒤에만, Sepolia RPC 값을 넣은 4~5단계 터미널에서 지웁니다: `unset SEPOLIA_RPC_URL CHAIN_RPC_URL`. 이 뒤에는 RPC 호출을 하지 않습니다. 다시 확인이 필요하면 4단계 2번(`read -rs`)부터 다시 시작합니다. Anvil을 띄운 6단계 터미널에서도 같은 `unset`을 실행해 둡니다(그 터미널에는 Sepolia 값이 없어야 정상).

## 연결 범위와 W5 당시 B 연결 대기 기록

**W5 당시 기록입니다. 현재 W6 연결 상태는 아래 "API 자동 연결" 표를 따릅니다.** 당시 `CHAIN_TARGET` 전환은 **아래 "연결됨" 범위까지만** 실제 코드에 연결되었습니다. 신규 Wallet Registry(공동승인·문서 버전) 경로의 실제 체인 읽기·쓰기·projection은 B 코드가 `phase/W5`에 없어 연결되지 않았습니다. "Sepolia 전환 완료"가 아니라 "기존 Reader·projection과 설정 계층 연결 + B 연결 대기"입니다.

연결됨(이 브랜치 코드, mock RPC 테스트로 양방향 확인):

- `Settings`(`apps/api/src/originproof_api/settings.py`): `blockchain_chain_id`, `blockchain_rpc_urls`(주→보조), `wallet_manifest_path` 기본값.
- `configured_blockchain_reader`(`apps/api/src/originproof_api/main.py`) → `JsonRpcBlockchainReader`(`apps/api/src/infrastructure/blockchain/reader.py`): 읽기 작업 단위로 주 RPC 실패 시 보조 RPC에서 chain ID·genesis·배포 블록·코드 검사부터 다시 수행. 검증·readiness가 이 함수를 씁니다.
- `ChainManagement.reader`(`apps/api/src/originproof_api/chain_management.py`): 같은 주→보조 읽기. `JsonRpcBlockchainWriter`는 **의도적으로 주 RPC만** 씁니다(미확인 제출을 다른 노드로 재전송하지 않도록. Operation 복구 계약 우선).
- `projection.verified_rpc_url`/`scan`(`apps/api/src/originproof_api/projection.py`): Reader 검사를 통과한 첫 RPC로 기존 ProofStatusRegistry 이벤트를 스캔.
- `WalletRuntime.domain`(`apps/api/src/originproof_api/wallet_runtime.py`): EIP-712 domain chainId가 target을 따름.
- 기존 manifest는 `load_manifest(path, CHAIN_TARGET chain ID)`로 다른 네트워크 manifest를 거부.

### API 자동 연결 (W6, `feat/v5-w6-blockchain-completion`)

| 연결할 곳 | 상태 |
| --- | --- |
| `create_app` lifespan → `WalletRuntime.chain` | **연결됨.** `API_WALLET_REGISTRY_ADDRESS`와 RPC가 설정되면 `infrastructure/blockchain/wallet_deployment.py`의 `WalletRegistryConnector`가 wallet manifest를 읽고 `FailoverWalletRpc`(주·보조 RPC)와 `verified_approvers`로 체인 위 CREATE·생성 코드·런타임 코드 해시·고정 승인자 3명을 다시 검증한 뒤에만 주입합니다. 실패하면 주입하지 않고 503을 유지하며, 이후 호출 때 15초 간격으로 다시 시도합니다. |
| 주/보조 RPC | **실행 중 전환(읽기만).** `infrastructure/blockchain/wallet_failover.py`의 `FailoverWalletRpc`가 `WalletRpc`를 주·보조 하나씩 감쌉니다. 주 읽기가 연결 오류·시간 초과·잘못된 chain/배포/코드로 실패하면, 보조가 chain ID·배포 블록 hash·런타임 코드 해시 검사(`snapshot`)를 먼저 통과한 경우에만 같은 호출을 보조로 다시 합니다. 보조 성공 뒤 60초 동안 보조를 쓰고 그 뒤 주부터 다시 시도합니다. 제출(쓰기)은 주로만 보내고 다른 노드로 재전송하지 않습니다. 둘 다 실패하면 `DependencyUnavailableError` → 503이며 로그·오류에는 `primary`/`fallback`만 남깁니다. 요청 URL을 남기는 `httpx`(INFO)·`httpcore`(DEBUG) 로거는 이 모듈이 WARNING으로 고정하므로 루트 로거가 DEBUG여도 URL·호스트·경로의 키가 로그에 나오지 않습니다(루트 DEBUG 전체 캡처 시험, 실제 TCP 전송 포함). 요청당 10초 안에 주 시간 초과 뒤 보조 재시도까지 끝나도록 지갑 RPC 요청 시간 제한은 4초입니다. |
| wallet manifest | **소비됨.** 래퍼가 `runtime_code_hash`·`creation_bytecode`를 함께 기록하고, API는 chain ID·주소·커밋된 ABI(`abi_sha256`)가 맞을 때만 사용합니다. 이 필드가 없는 예전 manifest는 `--deployment-tx`로 다시 기록합니다. |
| 도커 이미지 | `infra/docker/api.Dockerfile`이 `packages/contracts/abi`·`deployments`를 복사합니다(`*.local.json` 제외). |
| 신규 이벤트 projection | **연결됨(기존 projection과 함께).** `API_PROJECTION_ENABLED=true`이면 lifespan이 두 작업을 따로 돌립니다. ① 기존 ProofStatusRegistry projection(`scan`)은 그대로 돌며(지갑 주소만 있고 `API_BLOCKCHAIN_MANIFEST_PATH`가 비어 있는 Sepolia 구성만 제외) 상태는 `app.state.projection`. ② `API_WALLET_REGISTRY_ADDRESS`가 설정되면 `WalletScan`이 지갑 Registry가 연결된 뒤에만 `WalletProjection`을 그 adapter의 전환 RPC 인스턴스로 실행하고(미연결이면 `RECOVERING`), 위에 한 블록이 더 쌓인 확정 블록까지만 `wallet_events`·`wallet_checkpoints`에 반영합니다(기존과 같은 2-확인 규칙). 상태는 `app.state.wallet_projection`. readiness는 도는 projection 모두가 `SYNCED`/`WAITING_CONFIRMATIONS`이고 `projection_poll_seconds`×3 안에 갱신되었을 때만 준비 완료이며(한쪽 장애·지연이면 503), `/v1/chain-sync`는 기존 projection이 돌면 그 상태를, 지갑 전용이면 지갑 상태를 같은 `SyncView`로 냅니다. 지갑 표는 아직 alembic이 아닌 `WalletProjection.initialize()`(create_all)로 만듭니다. |
| 재조직 복구 | **자동.** 지갑 projection이 재조직을 만나면 `WalletProjection.recover_reorg()`가 아직 정본인 가장 최근 저장 블록(없으면 배포 블록)으로 되감고 다시 따라잡습니다. 정본 블록 hash 가 앞 블록 전체를 보증하므로 공통 조상으로 씁니다. `/v1/chain-sync`는 두 projection이 함께 돌면 기존 projection 상태만 보여 주며, 지갑 projection 상태는 readiness 에 반영됩니다. |
| 복구·대사 | 대기. `WalletRecovery`·`WalletReconciler`는 코드·시험이 있으나 API 유지 작업에는 아직 연결하지 않았습니다. |

검증(실행 중 전환·projection): `ORIGINPROOF_WALLET_LIVE=1 uv run pytest apps/api/tests/test_wallet_failover_live.py`가 일회용 Anvil 하나 앞에 로컬 TCP 프록시 두 개(주·보조)를 두고 일회용 PostgreSQL(`postgres:16.4-alpine`, tmpfs)로 `create_app` lifespan을 띄웁니다. 같은 Anvil에 기존 Issuer/Key/ProofStatus Registry도 배포(manifest는 임시 폴더)해 두 projection을 함께 돌립니다. 기존 `ProofRegistered` 이벤트가 `proof_chain_events`에, 지갑 이벤트가 `wallet_events`에 각각 반영되고, 실행 중 주 프록시를 끊은 뒤 새 승인 거래의 결과(기관 ACTIVE)를 보조로 읽고, 그 뒤의 새 지갑·기존 이벤트가 각각 PostgreSQL에 반영되며, 보조 사용 시간이 지나면 주로 돌아오고, 배포가 없는 다른 Anvil은 보조 검증에서 거부되는 것을 확인합니다(1 passed).

검증(연결 시점): `ORIGINPROOF_WALLET_LIVE=1 uv run pytest apps/api/tests/test_wallet_deploy_live.py`가 실제 Anvil에 B 컨트랙트를 배포하고, 주 RPC 장애 시 보조 RPC 연결, `create_app` lifespan 자동 연결·실제 `getIssuer` 읽기·종료 시 연결 정리, 위조 manifest 거부를 확인합니다.

## 현재 한계

- Sepolia 실제 배포는 위 "실제 배포 결과"대로 완료했습니다(keystore 서명). 배포 뒤 기관 등록·2-of-3 승인·v1/v2 발행은 2026-10-27 시연에서 실행했습니다(위 "Sepolia 시연 데이터"). 브라우저 지갑 서명 배포는 미실행입니다.
- 신규 Wallet Registry 경로의 주/보조 RPC 전환은 읽기만 실행 중에 합니다. 자동 전환 시험은 같은 Anvil 앞의 로컬 프록시 두 개 기준이며, 2026-10-27 Sepolia 시연 중 publicnode→tenderly 전환도 관찰했습니다(위 "Sepolia 시연 데이터"의 관찰 기록). 복구·대사 작업의 생산 연결은 위 표의 대기 항목입니다.
- `httpx`·`httpcore` 로거를 WARNING으로 고정한 것은 프로세스 전체에 적용됩니다. 운영 로깅 설정이 이 두 로거의 레벨을 다시 INFO/DEBUG로 내리면 URL이 남으므로 그렇게 설정하지 않습니다.

- 배포된 `0xE540Bf29622AFFf40174B76992b016112f372A2e`의 `_validateProposal`(`OriginProofWalletGovernance.sol:183-189`)은 승인자 주소를 기관 signer로 넣는 직접 온체인 제안을 막지 못합니다. 다음 재배포 때 승인자 제외 검사와 Foundry 거부 시험(예: `test_RevertWhen_SignerIsApprover`)을 추가해야 합니다. API의 승인자 signer 거부(409)는 C 파트 담당 후속이며, 이 변경에서 구현·검증하지 않았습니다. API 거부만으로 직접 온체인 경로의 잔여 위험이 제거되지는 않습니다.
- 배포는 로컬 forge 1.8.1, CI·Docker는 v1.4.4이며 버전은 유지합니다. `foundry.toml`의 `evm_version = "cancun"` 고정으로 컴파일 대상을 맞춥니다. 1.4.4 산출물 대조는 미실행입니다. 1.8.1에서 solc 0.8.26을 지정한 유효 기본값은 `forge config --json`의 `cancun`입니다([해당 forge 커밋의 solc별 기본값 정규화](https://github.com/foundry-rs/foundry/blob/982849d3140c01fd3b72905759581a132df7aa98/crates/config/src/lib.rs#L2516-L2534)). forge 자체의 원시 기본값 Osaka와 구분합니다.
- W6 검토 수정 시 로컬 forge 1.8.1·solc 0.8.26·Cancun 빌드의 Registry 생성 바이트코드가 manifest의 `creation_bytecode`와 완전히 일치했습니다. manifest source `72440c0` 대비 현재 기준 `5f7135b`의 `packages/contracts/src/` 차이는 없습니다. Tenderly 읽기 전용 `eth_getCode`의 Keccak은 manifest `runtime_code_hash`와 일치했고, artifact의 immutable 위치를 해당 배포 값으로 채운 런타임도 동일했습니다(CBOR 메타데이터 포함). immutable이 0인 원시 artifact 런타임 해시는 배포 런타임 해시와 직접 같지 않습니다. 이 확인은 Sepolia 쓰기·projection 실연결 재시험을 뜻하지 않습니다.
