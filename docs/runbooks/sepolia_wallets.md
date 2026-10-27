# Sepolia 시연 지갑 준비 (2026-10-27)

시연용 **시험 지갑** 다섯 개를 만들고 Sepolia 배포·공동승인·발행에 쓴 절차와 공개 주소입니다. 모두 대표(A 김형준)가 직접 만들고 서명했습니다.

> **이 문서와 저장소에는 개인키·니모닉(비밀 복구 문구)·keystore 파일·비밀번호가 없습니다.** 공개 주소와 절차만 있습니다. 시험용 지갑이며 실제 자산을 두지 않습니다. 승인자 이름은 역할 **모델**이고 실제 기관이 참여한 것이 아닙니다.

## 1. 지갑과 역할

| 역할 | 메타마스크 이름 | Foundry keystore 이름 | 공개 주소 |
| --- | --- | --- | --- |
| 배포 지갑 | OP-배포 | `op-deployer` | `0xED8ad0A5841451b91883Eac3A9e41982878b3b50` |
| 승인 노드 #1 공공·도메인 검증원(KISA 모델) | OP-승인1-KISA | `op-approver1` | `0x4f12cb684fbd76962A85E5Bc66fe769597aeCA2a` |
| 승인 노드 #2 금융·산업 자율규제원(금융보안원 모델) | OP-승인2-금보원 | `op-approver2` | `0xE5d0531Ef3c419A5acFB3774B731A2d239ECb240` |
| 승인 노드 #3 통신·인프라 보안 컨소시엄 | OP-승인3-통신 | (보관함 없음, 이번 시연에서 서명 안 함) | `0x2Efd70f041Fe1b400125e8b99029c5fa0Af4eB1c` |
| 합성 기관 `iss_origin_mock_bank`의 기관 지갑 | OP-기관-은행 | `op-institution` | `0x2c972C6c390C7742BFd070bC57DDAb539235d161` |

- 승인자 3명은 Registry 배포 때 생성자에 **고정**됩니다(`deployments/11155111.wallet.json`의 `roles`). 바꾸려면 새로 배포해야 합니다.
- 서버(API)의 `API_WALLET_OPERATOR_ADDRESSES`에서 운영자 계정 `v5_operator1~3`을 위 승인자 주소 1~3에 연결합니다.
- 기관 지갑은 키 보유 증명(KeyProof) 서명과 2-of-3 승인으로 등록되며, 안내문을 직접 서명·발행합니다.

## 2. 만든 순서

1. **메타마스크**(크롬 확장)를 설치하고 새 지갑을 만듭니다. 비밀 복구 문구는 종이에만 적습니다.
2. 계정을 위 이름대로 추가하고, 네트워크 관리에서 **테스트 네트워크 표시**를 켜 Sepolia를 씁니다.
3. 배포 지갑에 **Google Cloud Web3 faucet**(`cloud.google.com/application/web3/faucet/ethereum/sepolia`)으로 0.05 SepoliaETH를 받습니다.
4. 맥 터미널에서 서명할 지갑만 **Foundry keystore**로 가져옵니다. 개인키는 숨김 입력창에만 넣고, 대화·메신저·파일에 남기지 않습니다.
   ```sh
   cast wallet import op-deployer --interactive
   cast wallet import op-approver1 --interactive
   cast wallet import op-approver2 --interactive
   cast wallet import op-institution --interactive
   ```
   끝에 나오는 `Address`가 위 표의 주소와 같은지 꼭 확인합니다(2026-10-27에 다른 계정 키를 넣은 경우가 한 번 있었고, 그 keystore는 휴지통으로 옮긴 뒤 다시 넣었습니다).
5. 배포 지갑에서 수수료용 ETH를 나눠 보냅니다(비밀번호는 cast가 직접 묻습니다).
   ```sh
   for a in 0x4f12cb684fbd76962A85E5Bc66fe769597aeCA2a 0xE5d0531Ef3c419A5acFB3774B731A2d239ECb240 0x2c972C6c390C7742BFd070bC57DDAb539235d161; do
     ETH_RPC_URL=https://ethereum-sepolia-rpc.publicnode.com cast send $a --value 0.005ether --account op-deployer
   done
   ```

## 3. 어디에 썼나 (Sepolia)

| 단계 | 서명한 지갑 | 결과 |
| --- | --- | --- |
| Registry 배포 | 배포 | `0xE540Bf29622AFFf40174B76992b016112f372A2e` (tx `0x9e40ba5f…a4bc`) |
| 수수료 송금 3건 | 배포 | 각 0.005 ETH, status 1 |
| 기관 키 보유 증명 | 기관(서명만) | API 확인 완료 |
| 공동승인 제안·승인 | 승인1(제안·승인), 승인2(승인) | 제안 EXECUTED 2/2, 기관 ACTIVE |
| 안내문 v1·v2 서명·발행 | 기관 | v1 tx `0x394f0cce…1f88`, v2 tx `0xf7d6b418…542d` |

상세 결과는 [sepolia_deploy.md](sepolia_deploy.md)와 [레고 조립 안내](../handoffs/lego_assembly_guide_20261027.md)를 봅니다.

## 4. 잔액과 비용 (2026-10-27 확인)

| 지갑 | 잔액(SepoliaETH) |
| --- | --- |
| 배포 | 약 0.0349 |
| 승인1 | 약 0.0050 |
| 승인2 | 약 0.0050 |
| 승인3 | 0 |
| 기관 | 약 0.0050 |

- Sepolia는 코드 저장·계정 생성 비용이 올라 일반 송금도 204,600 gas가 들었습니다. 가스 가격이 매우 낮아 실제 쓴 시험 ETH는 아주 적습니다.
- 배포 실패 2건(가스 부족)은 [sepolia_deploy.md](sepolia_deploy.md)의 "가스 주의"를 봅니다.

## 5. 보안 규칙

- 개인키·니모닉·keystore 비밀번호는 **저장소·대화·메신저·AI 도구에 붙이지 않습니다.** 서명은 keystore(`--account`) 또는 하드웨어 지갑만 씁니다.
- keystore 파일은 각자 컴퓨터의 `~/.foundry/keystores/`에만 있습니다(저장소 밖).
- 시연 지갑에 실제 자산을 넣지 않습니다. 유출이 의심되면 새 지갑을 만들고, 승인자가 바뀌면 Registry를 다시 배포합니다.
- 서버는 기관·승인자 개인키를 받거나 보관하지 않습니다. 가스비 대납(Relayer)은 꺼져 있어 기관 지갑이 직접 보내고 가스비를 냅니다.
