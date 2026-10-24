# V5-W5-B — C 원본 모델을 소비하는 읽기 Adapter

- 담당 B 여하민 @hamin1228 / AI(Codex)가 사용자 선택1번으로 구현·검사·기록.
- 브랜치 codex/v5-w5-b-live-recovery / 기존 [#79](https://github.com/OriginProof-3web/OriginProof/pull/79), 시작e7d0bae.
- 실행 코드 SHA `41dc6f5eb704383cb0fa27baed91da05acf579fc`. 기존 B Registry/ABI·WalletRpc·WalletReconciler·Oracle/Anvil 검사와 C 원본 wallet_ports/wallet_contract/factory를 재사용. 공통 DTO 사본·새 의존성·ABI·C 생산 코드 변경 없음.
- **B 읽기 변환·독립 검사 완료 / C 생산 주입·쓰기·Operation/DB 연결·단계 완료·현재 head 독립 리뷰는 대기**. 계획5.1 유지. 모델은 작업 기준에 포함된 C v5-shared-0.2 원본을 소비하며 팀 공동 리뷰 확정을 주장하지 않음.

## 구현된 메서드

| 메서드 | 반환·검증 |
| --- | --- |
| issuer | WalletIssuer. 같은 block의 current key/기관/서명자·은퇴 여부와 업무/governance nonce 대조. nonce는 uint256 decimal string |
| key | WalletKey. 등록·정상 retire·compromise 이력과 관측 block 경계, 미발생 block은 None |
| document | WalletDocument/DocumentView. latest 또는 지정 version, documentId/기관/docKey·버전/state/latest·publication/key history 대조. ACTIVE만 기간에 따라EXPIRED, 철회/대체는 독립 유지. 정지·키 사고는 경고. original_available=False(C DB가 판단) |
| proposal | WalletProposal/ProposalView. 기존 canonical 이벤트 승인자 목록/count/실행 대조를 재사용. governance nonce·deadline으로 PENDING/EXECUTED/EXPIRED/STALE 분리 |
| transaction | WalletTransaction. 실제 tx calldata를 읽고 기존 receipt/event/current-state 검증 재사용. actual ABI uint256만 C decimal string으로 변환하여 C 저장 intent와 같은 타입 유지. 실패는FAILED, pending/missing은None |

getIssuer/getKey/getProposal의 정확한 getter custom error만None. document의 latest0 또는 최신보다 큰 미등록 version은None이고, 있어야 하는 과거/현재 version 누락은 dependency입니다. 불일치·RPC·ABI·모델 오류는 C가 처리하는 DependencyUnavailableError로 번역합니다. C WalletRuntime은 이를503 WALLET_REGISTRY_UNAVAILABLE로 처리하며 오류 상세/민감 payload를 공개하지 않습니다. projection을 현재 상태 근거로 읽지 않습니다.

## C에 넘기는 주입 지점

```python
from infrastructure.blockchain.wallet_adapter import WalletRegistryReadAdapter

# rpc는 검증된 배포 설정과 열린 AsyncClient로 생성한 기존 WalletRpc.
# client의 수명과 생산 설정/DB 준비는 C가 관리해야 합니다.
adapter = WalletRegistryReadAdapter(rpc)
app = create_app(settings=settings, database=database, wallet_chain=adapter)
```

C factory를 호출해 app.state.wallet_runtime.chain과 rpc 결과 모델·503 변환을 검사했습니다. 이 검사는 API 서버를 기동하거나 lifespan/DB 연결·인증된 HTTP workflow를 실행한 것이 아닙니다. 기존 asyncpg 엔진 객체 생성/정리만 수행했고 PostgreSQL에 연결하지 않았습니다. C의 main.py·설정·DB 코드는 수정하지 않았으므로 자동으로 활성화되지 않습니다.

## 2026-10-21 후속 — B-C01 승인자 확인

읽기 변환 이후 `creation_proof`를 설정하면 top-level CREATE·신뢰 build·canonical 배포 증거에서 고정 승인자를 도출하도록 구현했습니다. [승인자 근거 사용법·검사·한계](v5_wallet_approver_provenance.md)를 따릅니다. proof 없는 인스턴스는 기존 거부 동작을 유지합니다. 아래42/788 및41dc6f5 증거는 읽기 Adapter 당시 실행 이력이며 후속 실행은43개 추가·전체831 PASS/11 SKIP·별도 실제 Anvil1 PASS at4292801입니다.

## 안전하게 미연결로 남긴 부분

- is_approver: 검증된 creation_proof가 없는 경우 사용 불가. proof가 있으면 후속 B-C01 검증을 수행하며 임의 세 주소나 DB operator를 승인자로 반환하지 않음.
- submit: 실제 relayer/Operation 저장·dispatch 미연결. 키 수집/자동 전송/가짜 hash 없음.
- find_transaction: B helper는 유지하지만 C port의 페이지 진행점/보관 연결 미합의. 빈None으로 오인시키지 않고 dependency 오류.

proof 없는 is_approver와 나머지 두 메서드는 명시적인 DependencyUnavailableError이며 C 경계에서는503입니다. 모든 write/operator/recovery 흐름을 이 read-only 인스턴스로 완성했다고 주장하지 않습니다. production injection은 C와 위 한계를 확인한 뒤 진행해야 합니다. C/D에게 별도 메시지나 사람 승인 코멘트는 발송하지 않았습니다.

## 검사·근거

| 실제 실행 | 결과·한계 |
| --- | --- |
| test_wallet_adapter.py | 42 PASS. 합성 RPC + 실제 C 모델/factory. 정상/정확한 미등록·타 오류·대조 실패·reorg·키 교체/사고·만료/철회·큰 nonce·실제 calldata 변환·미연결 fail-closed |
| 전체 Python | 788 PASS/11 SKIP, 기존 Starlette TestClient deprecation 경고1. live/환경 의존 skip을 성공으로 집계하지 않음 |
| 실제 폐기 가능한 Anvil | 별도1 PASS at41dc6f5. 기존 응답유실/reorg 시나리오에 다섯 조회의 실제 C DTO·v3 거래의 전체 C 서명 메시지 대조 추가. [새 증거](evidence/v5_wallet_adapter_41dc6f5.json). 종료한 합성 배포를 활성 설정에 사용하지 않음 |
| 공식 Ruff·compileall·구조·Node 해시·make generate | PASS, 생성 Schema/타입/OpenAPI·Golden diff 없음. 패키지 설치/버전·lock 변경 없음 |
| 전체 Foundry fuzz 재실행·웹 lint/typecheck | 이번 미실행. Contract/ABI·웹 변경 없음. 실제 Anvil 하네스 내 기존 forge build는 실행 |
| 실제 API/DB·PostgreSQL migration·브라우저·공개 체인·D mixed QA | 미실행. G07 미해결 |

초기 주입 검사에서 미설치 aiosqlite를 요구해1 FAIL/40 PASS였습니다. 설치하지 않고 기존 asyncpg의 미연결 엔진으로 검사 범위를 바로잡았습니다. fixture import/lint 정리 중 수집 오류도 수정한 뒤42 PASS·전체788 PASS를 확인했습니다. 검사 실패를 숨기거나 제품 검증을 완화하지 않았습니다.

## 다음 담당·인계

B/C: 읽기 mapping/생산 수명주기 소비 리뷰, B-C01 승인자 근거, submit relayer·UNKNOWN 진행점 저장 계약. C: 실제 설정·API/DB/Operation 연결. D: 통합 실패 사례·동일SHA 독립 재현·G07 mixed QA. 기존 v1/v2 서명·권한·consume 회귀 유지, 입력 선정은 회의 후 확정·Decisions API 범위 밖.

기존 PR 담당자 댓글·#83/#86 사람 승인은 각 당시 head의 기록입니다. 새 Adapter head의 작성자 외 리뷰나 승인으로 대신 집계하지 않습니다. 사용자 원본 미커밋5개는 별도 worktree 밖에서 보존했습니다.


## 2026-10-25 — W6 실제 API 연결 검사와 초기화 진입점

작업: V5-W6-B, 브랜치 `codex/v5-w6-b-api-injection`. 선행 #96 `5a3b414` 위의 준비 작업이다.
실행 코드 SHA: `9dc7c7fab80155e96509a0a6b1bd1afddec66ede`.
위 W5 절은 당시 이력으로 보존한다. 이번 연결 범위는 아래와 같으며 전체 생산 주입 완료가 아니다.

### 먼저 연결해 확인한 결과

기존 실제 Anvil 하네스에 추가 opt-in 검사를 붙였다. 신규 Registry/ABI·B Adapter·C ASGI 핸들러·
실제 로그인/세션/CSRF·정식 Alembic migration을 적용한 일회용 PostgreSQL을 연결했다.
인증 dependency override나 합성 Registry port를 사용하지 않았다.
가상 기관의 이메일/내부 승인 행은 seed했으므로 신청 UI·실제 메일/내부 승인 성공으로 세지 않는다.

| 사례 | 실제 결과 |
| --- | --- |
| wallet_chain 미주입 / 주입 후 미등록 문서 | 503 / 404 |
| 비로그인 / 수신자의 발행 / CSRF 누락 | 401 / 403 / 403 |
| 운영자 주소가 실제 생성 증거의 승인자인 경우 / 아닌 경우 | 권한 검사 통과 후 저장 제안 부재 404 / 403 |
| API 발행 초안·기관 EIP-712 서명·서명 저장 | 201 → 202 PENDING_SUBMISSION |
| 저장 발행 요청과 다른 실제 제안 tx 제출 | 422 DIRECT_TX_MISMATCH |
| Anvil automine 중지 후 같은 발행 tx 제출 | 202 UNKNOWN, PostgreSQL 저장 |
| API 앱·DB pool 재생성 후 같은 거래 해시 재조회 | 202 CONFIRMED, 재요청 결과 동일, DB tx hash·확정 상태 일치 |
| 문서·서명 자료·보호 필드 검증 | 200 ACTIVE / 원래 서명 일치 / VERIFIED |
| 해시 없는 Operation 검색 | 503, 안전한 미연결 상태 유지 |

ASGI HTTP 경계는 실제 C 코드를 실행하지만 TCP API 서버 프로세스·브라우저·앱 lifespan은 실행하지 않았다.
앱·pool 재생성은 프로세스 SIGKILL이나 서버 lifespan 재시작 검증을 대신하지 않는다.
서명은 일회용 Anvil의 공개 테스트 계정으로 수행했다. 기관 개인키를 API에 전달하지 않았다.

### 필요한 만큼 보완한 B 진입점

`WalletRegistryReadAdapter.from_deployment`는 기존 WalletRpc 설정과 WalletCreationProof를 받아
snapshot의 chain/배포 block/현재 runtime code, canonical top-level CREATE·신뢰 initcode와
생성자 승인자 근거를 **주입 전에** 검사한다. 오류는 기존 DependencyUnavailableError로 닫힌다.
초기화에 성공해도 각 조회·권한 검사에서 canonical 검증을 계속하며 승인 결과를 캐시하지 않는다.
클라이언트는 닫거나 교체하지 않으며 호출자가 API 실행 기간 동안 유지하고 종료 시 정리한다.

```python
from infrastructure.blockchain.wallet_adapter import WalletRegistryReadAdapter
from infrastructure.blockchain.wallet_creation import WalletCreationProof
from infrastructure.blockchain.wallet_rpc import hex_bytes

# C의 실제 composition/lifespan이 소유한 열린 httpx.AsyncClient를 사용한다.
# ABI·주소·chain·배포 block/hash·runtime_code_hash는 신뢰한 배포 설정에서 읽는다.
# artifact는 검증 대상 tx의 입력이 아니라 별도로 신뢰한 로컬 build다.
proof = WalletCreationProof(
    tx_hash=trusted_deployment_tx,
    creation_bytecode=hex_bytes(trusted_artifact["bytecode"]["object"]),
)
adapter = await WalletRegistryReadAdapter.from_deployment(
    rpc_client, rpc_url, creation_proof=proof, **trusted_deployment,
)
app = create_app(settings=settings, database=database, wallet_chain=adapter)
```

`trusted_deployment` 키는 기존 WalletRpc의 `chain_id`, `address`, `deployment_block`,
`deployment_hash`, `runtime_code_hash`, `abi`다. 새 manifest schema를 정의하거나 자동 신뢰하지 않는다.
특히 #89의 wallet manifest에는 runtime_code_hash가 없으므로 그대로 `**` 전달할 수 없다.
runtime_code_hash를 아무 RPC 응답에서 읽어 신뢰 기준으로 자동 채택하지 않는다.
기존 생성자는 호환 유지한다. C 기본 앱·설정·API·DB·생성 타입·ABI는 변경하지 않았다.

### 재현과 증거

```sh
# 기존 의존성 + Foundry 1.4.4, Docker, postgres:16.4-alpine 필요
ORIGINPROOF_WALLET_LIVE=1 ORIGINPROOF_WALLET_API_LIVE=1 \
  python -m pytest services/indexer/tests/test_wallet_live.py -q
```

두 opt-in을 모두 켜야 한다. PostgreSQL 컨테이너는 무작위 이름·loopback port·tmpfs만 사용하고
정리 시 자기 컨테이너만 제거한다. 기존 Compose/DB/manifest는 건드리지 않는다.
선택 사항 `ORIGINPROOF_WALLET_LIVE_OUTPUT`은 존재하지 않는 새 로컬 보고서 경로를 받는다.
기본 CI/pytest는 opt-in을 skip하므로 CI 초록만으로 이 실제 연결 검사를 실행했다고 간주하지 않는다.

2026-10-25 macOS arm64·Python 3.13.14·Foundry 1.4.4·Solc 0.8.26·PostgreSQL 16.4:

- 초기화/Adapter 합성 검사: 90 passed.
- 기본 전체 Python: 962 passed / 11 skipped, 기존 anyio deprecation warning 1건.
- 위 실제 API 연결 opt-in: 1 passed. 동일 코드 SHA의 별도 clean clone에서도 1 passed.
- 변경 Python lint·diff: 통과.
- 기존 Python 가상환경과 Solidity lib을 재사용했다. fresh lockfile sync/다른 장비 재현은 아니다.
- 합성 실행 증거: [v5_wallet_api_9dc7c7f.json](evidence/v5_wallet_api_9dc7c7f.json).

### 남은 인계

C: 신뢰 배포 설정·client 수명주기를 실제 서버 composition에 연결하고 lifespan/readiness·
TCP 서버·PostgreSQL 프로세스 장애를 같은 SHA로 확인한다.
B/C: hashless 검색 진행점/보관·재시작 계약을 정한 뒤 find_transaction을 연결한다.
submit/relayer는 여전히 미연결이며 직접 지갑 제출 검사를 중계 성공으로 확대하지 않는다.
D: 동일 SHA 독립 실패 검사·다른 환경 재현. 공개 RPC·Sepolia·브라우저·W6 단계 완료는 미검증이다.
phase/W6 미생성으로 이 PR도 준비 Draft이며 작성자 외 리뷰는 미확인이다.
