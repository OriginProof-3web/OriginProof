# V5-W5-B / 3차 — 실제 로컬 RPC와 UNKNOWN 원본 검색

- 날짜 2026-10-17 / B 여하민 `@hamin1228`.
- 브랜치 `codex/v5-w5-b-live-recovery`, 시작 `691622407d424b46a50d1bd8946798647b24c6ba` / [Draft #78](https://github.com/OriginProof-3web/OriginProof/pull/78).
- 구현 코드 `5a51e4be68dc860180a863ba7c03c5aab777db06`, 최종 live 코드 `a064b63f9b44e5f9ccf5a6c9a4f237612d03e0e3`.
- 계획서5.1·v5-shared-0.1·ADR0004 유지. **B 독립 구현/합성 검사와 폐기 가능한 로컬 EVM 연결 검사 완료. C API/DB/Operation·브라우저·W5 전체 수용/독립 리뷰는 대기.**

## UNKNOWN의 동작

1. C가 제출 **이전 저장한** 전체 ABI 인자·function·업무 nonce/서명·대상 chain/deployment와 검색 시작 block을 B에 전달합니다. `WalletRecovery(rpc).find_transaction(...)`은 B의 내부 증거 경계이며 C `WalletRegistry` port의 완성 구현이 아닙니다.
2. 알려진 tx hash가 있으면 2차 `WalletReconciler`로 먼저 조회합니다. pending/미발견을 성공이나 전송 실패로 바꾸지 않습니다. 다른 intent의 tx hash를 자기 거래로 채택하지 않습니다.
3. 검색 범위는 top-level `tx.to == Registry` 거래입니다. relay contract 내부 호출(`tx.to != Registry`)은 trace 검색을 하지 않아 찾지 못합니다. 빈 결과는 재전송 허가가 아닙니다. 없거나 추가 재조회가 필요하면 canonical block의 실제 transaction 목록을 읽고 **전체 calldata**·대상 주소·필요 제출자가 일치하는 후보를 찾습니다. 제안/승인/정지는 저장한 sender가 필수입니다. 발행/철회는 relay sender를 선택적으로 제한할 수 있습니다. type/누락 인자·혼합 block/hash/index·잘못된 배포·불일치 receipt는 거부합니다.
4. 각 후보를 2차의 이벤트/receipt 블록·현재 상태 대조로 재검증합니다. 성공과 실패 시도가 모두 있을 수 있으므로 `attempts` 목록을 반환하며 첫 실패만 보고 전체 요청을 FAILED로 만들지 않습니다. tx hash가 알려진 경우에도 중복 항목은 추가하지 않습니다.
5. 후보 탐색 페이지 기본128/max1024 block, 기본4096/max16384 transaction 제한입니다. 예산 초과·RPC 불가·mined 후보 receipt 누락은 dependency 오류이며 진행점을 반환하지 않습니다. 이 제한은 후보 탐색용이고 승인 대조의 기존 배포 이후 canonical 이벤트 replay까지 합산한 전역 RPC 예산은 아닙니다. 운영 provider의 getLogs chunk/보존 범위 대응은 후속입니다.
6. `checkpoint=(block, hash)`, `next_block`으로 C가 진행점을 저장할 수 있습니다. 다음 호출에 `previous_checkpoint`를 전달하면 바로 앞 block/height/hash를 검증합니다. reorg 시 계속 진행하지 않고 UNKNOWN을 유지하여 canonical 재검색해야 합니다. B helper는 Operation/DB·자동 재시도 스케줄을 변경하지 않습니다.
7. 발행/철회는 같은 관측 head의 `observed_next_nonce`도 반환합니다. nonce 소비와 원본 거래 발견은 다릅니다. 다른 intent가 nonce를 소비했을 수 있고 pending/mempool/provider 검색 제약도 있으므로 **빈 attempts·reached_snapshot=True는 NOT_SENT/재전송 허가가 아닙니다.**

출력은 `attempts/head/scanned_from/scanned_to/checkpoint/next_block/reached_snapshot/observed_next_nonce`입니다. `reached_snapshot`은 그 snapshot까지의 페이지가 끝났다는 뜻이며 확정 깊이·최종성·미전송 증명이 아닙니다. 실제 제출 또는 새 nonce/문서 생성 메서드는 없습니다. product의 중복 전송 방지는 C의 Operation 저장/잠금·dispatcher 정책과 연결 검증 후 판정해야 합니다.

## 실제 검사와 배포 근거

[실행 증거 JSON](evidence/v5_w5_live_a064b63.json)에 코드 SHA·새 배포 주소/chain/block/hash/tx·constructor 승인자·runtime/ABI hash·compiler/lock fingerprint와 receipt를 보관했습니다. **실행이 끝나 종료한 폐기 가능한 합성 체인의 증거이며 backend의 활성 배포 설정으로 사용하면 안 됩니다.** 기존 `packages/contracts/deployments/31337.json`·legacy 배포/사용자 변경을 읽어 덮어쓰지 않았습니다.

검사는 Anvil을 `127.0.0.1` 임의 포트에서 직접 시작하고 종료합니다. 신규 Registry를 실제 배포하고 unlocked **개발 지갑**의 `eth_signTypedData_v4`로 서명합니다. 서비스가 기관 개인키를 수집/생성/보관하는 구현이 아니며 개인키·mnemonic을 출력/기록하지 않습니다. EIP-712 필드·original/protected SHA256은 C 공통 모델·canonical bytes·서명 helper를 그대로 사용해 Python 복구 주소와 Solidity 검증을 대조합니다. 원본/서명 전문은 증거 JSON에 저장하지 않습니다.

최종 `a064b63`에서 **실제 RPC opt-in 1 PASS**: Anvil/Forge1.8.1, solc0.8.26, SQLite. 다음 8개 시나리오 묶음과 receipt 기록14개(고의 실패/나중 orphan 포함)를 확인했습니다.

- 실제 KeyProof·서로 다른2승인·canonical 승인 목록/실행.
- 공유 원본/보호 canonical SHA256과 실제 지갑 서명 검증.
- 노드가 실제 발행을 수락한 뒤 클라이언트 응답을 의도적으로 유실. 최초 검색은 아직 채굴 전이라 matches0, 채굴 뒤 **tx hash 없이 v2를 검색/검증**. 반복 재조회에도 중계자 tx nonce는 최초 제출1개만 증가.
- v1→v2 원자 대체·v2 철회·실패 replay와 원 성공을 모두 구분. 업무 nextNonce=3 확인.
- 기관 정지 중 과거 버전 철회·공동 재활성화.
- SQLite checkpoint 재시작, 실제 `evm_snapshot/revert` reorg 후 sync 거부·명시 rewind·새 branch 재생, old checkpoint/old-fork tx 거부와 compromise 이력 복구.
- automine 중단으로 실제 pending tx를 만든 뒤 UNKNOWN 유지, 채굴된 실패 receipt와 구분.
- 다른 chain 설정 및 실제 노드 종료 뒤 dependency 오류.

8개 묶음/14개 receipt를 별도 pytest 8개/14개 또는 독립 수용 검사 성공 수로 합산하지 않습니다. 최종 live 실행은 새로운 합성 노드 한 개의 검사이며 G07 mixed 환경·공개 체인·다른 PC/독립 검증이 아닙니다.

## 명령·검사와 실패 이력

```sh
# 일반 검사는 실제 EVM opt-in 2개를 생략합니다.
.uv-venv/bin/pytest -q
.uv-venv/bin/ruff check apps packages/python services scripts
.uv-venv/bin/python scripts/ci/validate_structure.py
.uv-venv/bin/python -m compileall -q apps/api/src/infrastructure/blockchain services/indexer
node scripts/ci/check_wallet_browser_hashes.mjs
make generate
git diff --exit-code -- packages/schemas/generated fixtures/golden

# Foundry가 PATH에 있을 때, 오직 새로 시작하는 합성 노드만 사용합니다.
ORIGINPROOF_WALLET_LIVE=1 \
ORIGINPROOF_WALLET_LIVE_OUTPUT=/absolute/new/output/report.json \
.uv-venv/bin/pytest -q services/indexer/tests/test_wallet_live.py
```

- 일반 Python **306 PASS/2 opt-in SKIP**, 기존 anyio warning1. 신규 recovery 합성25 PASS 포함. 실제 wallet RPC는 별도 **1 PASS**, 구 M4 live/API 검사1개는 계속 미실행입니다.
- 공식 lint·구조·compileall·Node hash·재생성 뒤 생성물 diff·공백 검사 PASS. Solidity/ABI는 무변경이며 live의 forge build/컴파일 ABI 일치 검사는 실행했고 로컬 전체 Foundry fuzz 재실행은 생략했습니다. 원격 CI 결과는 PR에서 별도로 기록합니다.
- 최초 recovery 합성19 PASS/1 FAIL: 검사에서 signature가 아니라 이미0인 ABI padding을 바꿔 원본과 다른 calldata를 만들지 못했습니다. 실제 signature byte를 바꾸고 fixture import lint를 수정한 뒤20 PASS, checkpoint/중복 위치 경계5개 추가 후25 PASS입니다.
- 최초 live1 FAIL: 수락 직후 무조건 채굴됐다고 가정했습니다. 실제 accepted 응답을 검증한 뒤 응답만 버리도록 하고 채굴 대기를 분리했습니다. `5a51e4b` live1 PASS 후 SHA256 canonical fixture/fingerprint 보강, 최종 `a064b63` live1 PASS입니다. pending/missing을 즉시 성공으로 바꾸도록 제품 로직을 완화하지 않았습니다.

## 남은 인계와 기여

B-C03의 bounded 원본 검색·receipt/nonce 재조회와 실제 로컬 UNKNOWN 복구 근거를 추가했습니다. C 원본 port 변환·Operation/DB/dispatcher 연결·전체 재전송 동시성 정책, production 중계 submit, B-C01 고정 승인자 manifest 소비, 최종성/공개 네트워크·실제 재배포 운영·PostgreSQL·브라우저·D 독립 QA는 후속입니다. 동일 블록 정지/재활성화의 2차 보류 경계도 유지합니다.

**G07은 미해결**이며 fresh 로컬 reorg 성공을 mixed 과거 실패 해결로 올리지 않습니다. SG01~16, W5 전체 단계/리뷰 상태를 일괄 PASS로 바꾸지 않습니다. 계획서5.1은5.0 범위 유지·인계 갱신이며 입력은 회의 후 결정하고 Decisions API는 범위 밖입니다.

Codex가 B의 Recovery·합성/실제 검사를 작성하고 B1·2차 RPC/Reconciler/Indexer, W2~W4 Registry·생성 ABI와 C 공통 모델/hash/서명 코드를 재사용했습니다. C/A/D 생산 코드·공통 계약·의존성·운영 배포를 변경하지 않았습니다. 사용자 원본5개와 고정 과거/legacy를 보존하고 사람의 직접 작성·리뷰/기여 비율을 추정하지 않습니다. 팀 Draft PR과 비공개 개인 GitHub에 실제 커밋·검사 근거를 함께 보관합니다.

## 2026-10-21 재검증

실행 SHA `b92be2e30de20576933622dae2fbff88354808be`, [새 실제 EVM 증거](evidence/v5_w5_live_b92be2e.json): 실제 Anvil 1 PASS. fresh HTTP/RPC 클라이언트의 응답 유실 복구와 REVOKED v2 뒤 v3 발행을 추가 확인했습니다. API/DB 프로세스 재시작은 미실행입니다. 최신 일반 검사는 745 PASS/11 SKIP이며 이전 306 PASS 기록은 당시 실행 이력입니다. 자세한 수정·검사·미완료는 [PR 후속 확인](pr_followup_20261021.md)을 따릅니다.
