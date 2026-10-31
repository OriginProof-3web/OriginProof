# W6 B — Sepolia 독립 읽기 검증·인계 (2026-10-27)

담당 B 여하민 `@hamin1228`, Codex 보조. V5-W6-B / 공개 체인·서비스 API 밖 검증의 부분 증거입니다. D의 [#101 보고서](../qa/v5-d-connected-review-20261027.md) 요청에 대응합니다. #101과 #99는 이미 병합됐으며 이번 작업에서 다시 병합하거나 타인 승인을 대신하지 않습니다.

## 기준과 결과

- 시작: `phase/W6` `5f7135b` (통합 소스 `649013aa20534212d8cec2fb0af60a9be1f54ccc`와 tree 동일).
- 검증 도구·검사 SHA: `05fdf6ca87810cd549e82322df044dd8860eb4df`. 원본 사용자 workspace는 수정하지 않았습니다.
- 실제 공개 Sepolia RPC·서비스 API 호출 0·체인 쓰기 0. 기존 B/C 검증 함수를 재사용했으며 API·ABI·Schema·Contract 정책을 바꾸지 않았습니다.
- [전체 배포 조회 증거](evidence/v5_sepolia_read_20261027.json): `ethpandaops`에서 **3회 연속 PASS**. 이것은 같은 장비의 배포 조회 반복이며 **동일 RC 전체 리허설 3회가 아닙니다**.

| 검증 | 실제 결과 |
| --- | --- |
| 로컬 Foundry 1.4.4 / solc 0.8.26 / OpenZeppelin 5.7.0 build | 생성 바이트코드와 커밋 manifest 바이트 일치. manifest source `72440c0`와 시작 소스의 Contract·Foundry 설정 diff 없음 |
| 커밋 ABI SHA-256·chain ID·genesis | 일치 |
| 정본 CREATE 거래·receipt 성공·배포 주소·블록 hash·거래 위치 | 일치 |
| 생성 코드+정규 ABI 생성자 인자·고정 승인자 3명 | 일치 |
| 배포 시점 EIP-1898 `eth_getCode`·현재 런타임 hash·재조회 정본 확인 | 통과 |
| `1rpc` | 단일 과거 코드 조회 12,166 bytes 성공 후 전체 검증에서는 HTTP429 / RPC -32029. 보조 검증 통과로 채택하지 않음 |
| PublicNode | 기존 D 실패 재현: HTTP200 / RPC -32000, 배포 시점 코드 조회 실패 |
| 추가 후보 | dRPC는 free plan chain 미지원(HTTP400/code35), rpc.sepolia.org ReadTimeout, BlockVectra 과거 window 제한(-32011). 채택하지 않음 |

`https://rpc.sepolia.ethpandaops.io`는 이번 읽기를 통과한 공개 후보입니다. 장기 안정성·운영 SLA·서로 다른 provider의 독립 검증을 보장하지 않습니다. 다른 provider 2곳의 전체 통과는 확보하지 못했습니다. API 주·보조 환경 설정을 자동 변경하지 않았습니다.

## 배포 식별

- chain ID `11155111`, Registry `0xe540bf29622afff40174b76992b016112f372a2e`
- 배포 block `12001755`, hash `0xf7996737093412ac2d0f7ce64d5f016a60879567a1c456cf7563c8e8e4beaea2`
- 배포 tx `0x9e40ba5f455da2a583989d24255c324230bdb804255e249f35cf256f4866a4bc`
- runtime hash `0x3c4d2045eabed02ce1f4703f30874607950f91ff5a70f58b93357ea031840476`
- 승인자: `0x4f12cb684fbd76962a85e5bc66fe769597aeca2a`, `0xe5d0531ef3c419a5acfb3774b731a2d239ecb240`, `0x2efd70f041fe1b400125e8b99029c5fa0af4eb1c`
- 원본 기준: [manifest](../../packages/contracts/deployments/11155111.wallet.json), [ABI](../../packages/contracts/abi/OriginProofWalletRegistry.json). 새 배포·manifest 덮어쓰기 없음.

## 재현 순서

저장소 root에서 검증 SHA를 확인하고 고정 Foundry 1.4.4를 PATH에 둡니다. Python 의존성은 프로젝트 lock 기준으로 준비합니다. 이번 실행은 기존 Python 3.13.14 환경·로컬 OpenZeppelin 5.7.0 복사본을 재사용했으며 새 locked 설치나 다른 노트북 재현이 아닙니다.

```sh
make bootstrap-contracts FOUNDRY_BIN_DIR="$(dirname "$(command -v forge)")"
(cd packages/contracts && forge build --skip test --skip script)
# 공개 키 없는 후보. 키 RPC를 쓰면 URL은 숨김 입력/환경에만 보관합니다.
export SEPOLIA_RPC_URL=https://rpc.sepolia.ethpandaops.io
PYTHONPATH=apps/api/src:packages/python uv run --package originproof-api python \
  packages/contracts/script/verify_wallet_deployment.py
unset SEPOLIA_RPC_URL
```

도구는 3회 통과할 때 exit0, 최초 실패에서 중단하고 exit1입니다. 오류 메시지·RPC URL 대신 예외 타입과 메서드/HTTP상태/RPC오류 코드만 출력합니다. 읽기 메서드 allowlist가 전송 전에 쓰기를 차단합니다. JSON에는 공개 주소·hash·승인자만 담습니다. 전체 RC나 문서 원본 검증을 실행하는 명령이 아닙니다.

```sh
uv run pytest -q apps/api/tests/test_wallet_deployment.py \
  services/indexer/tests/test_wallet_approvers.py \
  services/indexer/tests/test_wallet_deployment_probe.py
uv run ruff check packages/contracts/script/verify_wallet_deployment.py \
  services/indexer/tests/test_wallet_deployment_probe.py
git diff --check
```

실제 결과: **63 PASS**, Ruff·diff 검사 PASS. 신규5개는 네트워크 없는 mock 검사로 정상3회·잘못된 genesis·잘못된 승인자·쓰기 차단·오류 내 RPC 비밀값 비출력을 확인합니다. 기존58개는 manifest/생성자 검증 회귀입니다. 공개 RPC 실제 결과와 mock 검사를 구분합니다.

## 공개 발행 서명·상태의 부분 검증

[공개 거래 서명 증거](evidence/v5_sepolia_public_signatures_20261027.json)는 v1/v2 실제 publish calldata를 커밋 ABI로 decode→재인코딩 대조하고 EIP-712 서명자를 복구했습니다. 두 receipt status1·정본 block/거래 위치·Registry key signer 일치, 현재 v1 `SUPERSEDED` / v2 `ACTIVE`를 기존 Adapter로 확인했습니다. 서비스 API와 개인키 없이 실행했고 공개 쓰기0입니다. **서명된 hash와 키의 관계를 확인한 부분 검사이며 원본 bytes/보호 필드 내용 전체 비교가 아닙니다.**

수동 검사는 `WalletRpc`의 거래/receipt/block 조회 → `eth_abi.decode/encode`와 `publish` selector·정규 calldata 대조 → `PublishMessage`/`WalletDomain` 원본 모델 → 기존 `wallet_signer` 복구 → 기존 `WalletRegistryReadAdapter.document/key` 대조 순서입니다. 공개 거래·domain/message/signature·관찰 block은 증거 JSON에 보존합니다. 첫 임시 실행기에서 chainId를 정수로 전달한 오류와 Pydantic 결과를 dataclass로 직렬화한 오류를 바로잡은 뒤 통과했으며 제품 소스는 변경하지 않았습니다.

## C/A가 인계할 공개 원본 패키지

[Sepolia 시연 기록](../runbooks/sepolia_deploy.md)의 document `0x2bc2f605c8b185bc9b1d5d9ed2560a62ccd4e2a6338574c3925752b63c07e8a9` v1/v2에 대해 아래 자료가 필요합니다. 공개 합성 자료만 전달하며 세션·계정 비밀번호·개인키는 필요하지 않습니다.

1. 기존 `/v3/documents/{id}/verification-material?version=1|2`의 `VerificationMaterial` JSON: 실제 SigningRequest·원본 base64·보호 content·signature·발행 block/hash를 그대로 export.
2. 동일 원본 bytes 파일과 보호 필드 JSON, 기관 공개 metadata JSON. 원본에서 값을 추정해 새로 작성하거나 조회 시각으로 issuedAt/dueAt을 대체하지 않습니다.
3. 공개 가능 여부·자료 SHA-256·발행 tx·버전·동일 배포 참조. DB 자료가 이미 없어졌다면 원본 미확보로 명시합니다.

자료를 받으면 [기존 독립 검증 명령](../api/v5_c_recovery_runbook.md)을 같은 배포에서 실행합니다. 정상 원본/보호 필드·변조·v1 SUPERSEDED를 확인하고 C/D에 결과를 인계합니다. **현재 원본 전체 비교 완료는 아닙니다.**

## 소유 경로 리뷰·남은 범위

- #101의 B 경계 관련 변경은 `apps/api/tests/test_wallet_failover_live.py`의 `pg_isready -h 127.0.0.1` 추가입니다. 실제 TCP에 연결하는 테스트와 일치하며 Unix socket 임시 initdb ready 오인을 줄입니다. 검증 assertion·프로덕션 Contract/Adapter 변경 없음. A 웹·C API·D 모델 전체 승인으로 확대하지 않습니다. 이번 회차에는 D의 실제 Anvil/PostgreSQL9건을 다시 실행하지 않았습니다.
- C: 제품 기본 AI composition·이미지 API는 별도 담당입니다. 이 도구와 D QA bridge를 제품 자동 연결로 소개하지 않습니다.
- B/C: 공개 원본 export 이후 문서 전체 검증, 두 번째 provider의 전체 검사·운영 RPC 확정이 남습니다.
- 팀/D: 다른 실제 노트북에서 같은 RC SHA·환경 fingerprint 재현, 같은 RC 전체 리허설3회·소유자 리뷰·W6 수용 판정이 남습니다.
- 이번 배포 조회 3회와 같은 장비의 격리 폴더를 위 팀 수용 근거로 대체하지 않습니다.

## 2026-10-31 — C/D 리뷰 반영

C의 비차단 의견을 반영해 JSON 파싱 전에 메서드·HTTP 상태를 trace에 남깁니다. 비JSON HTML 429/502에서도 실패와 상태가 기록되고, 응답 본문·URL·키는 출력하지 않습니다. 신규2개를 포함한 관련 guard/manifest/승인자 검사 **65 PASS**, Ruff·diff PASS. 과거10-27 공개 RPC 증거는 그대로 보존했으며 이번 보완은 네트워크 없는 MockTransport 검증입니다.

C/D의 기술 검토와 D의 10-30 독립 배포 조회3/3 PASS는 #102 리뷰 및 #113 보고서에 있습니다. GitHub APPROVED나 원본 전체 대조/다른 장비/RC 리허설 완료로 확대하지 않습니다. C가 정정한 기관 metadata 원본 경로는 신청 기관 로그인 후 `GET /v3/issuer-applications/{application_id}`의 `metadata`와 `metadata_hash`입니다. 10-30 C가 A에게 실제 시연 DB·원본 export를 요청했으며 아직 자료가 인계됐다는 근거는 없습니다.
