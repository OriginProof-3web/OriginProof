# W6 B — 로그 조회 구간 제한 수정·소유 경로 리뷰 (2026-10-31)

B 여하민 `@hamin1228`, V5-W6-B. 사용자님이 승인한 High 수정 → #102 의견 반영 → #104/#114 리뷰 범위입니다. 시작 `phase/W6` `f1d7b3c0002f406419d44321aff4cff3e90edd57`, 생산 코드 검증 SHA `ae996c30269f721bd73857ab03062c2f3b121dd6`. [실행 증거 JSON](evidence/v5_log_windows_20261031.json).

## 문제와 변경

#120/#104의 A-2: 제안 대사는 배포부터 현재까지 `WalletRpc.logs()`를 부르고 기존 구현은 `eth_getLogs`를 한 번만 보냈습니다. API 제안 조회·propose/approve 대사와 projection에서 같은 함수를 사용합니다. 확인한 호출부 모두 공통 경계의 수정으로 적용되며 C의 모델/API/포트나 Contract/ABI는 수정하지 않았습니다.

- 요청당 **최대2,000블록**, 동시에 **최대4개 읽기**로 제한합니다. 미완료 batch를 무한히 쌓지 않습니다. 모든 batch 응답을 회수하고 오류가 있으면 전체 조회를 실패시킵니다. 호출 취소도 대기 요청에 전달합니다.
- 각 응답의 블록이 해당 페이지 안에 있는지 확인합니다. 기존 전체 중복·정본 block/hash·거래 포함·ABI 디코딩·끝 snapshot 정본 재조회 검사를 유지합니다. 결과는 전체 순서대로 정렬하며 일부 페이지 성공을 전체 성공으로 반환하지 않습니다.
- 로그 내용과 ABI/발행 판정은 바꾸지 않습니다. checkpoint를 새로 만들지 않고 authoritative 체인 관찰과 projection을 분리합니다. 캐시/새 DB/의존성/환경 설정을 추가하지 않았습니다.
- #104의 200블록 checkpoint 분할은 별도 변경입니다. 이 PR은 공통 `WalletRpc`의 요청 한도를 보장하고, #104는 projection의 중간 저장·재개를 다룹니다. 파일 충돌은 없습니다. #104를 병합하지 않았습니다.

## 실제 provider 관찰과 구현 선택

10-31 공개 읽기6건에서 PublicNode는50,000/50,001블록을 허용했고 ethpandaops는30,000블록 한도를 오류(-32012) data로 반환했습니다. 두 곳 모두200블록 요청을 허용했습니다. 과거50,000 한도/11월3일 초과 예상은 확정하지 않습니다. provider의 설정·부하는 바뀔 수 있으며 모든 provider의 허용 범위를 보장하지 않습니다.

처음200블록 직렬 분할은 합성 회귀를 통과했고 실제 이력154페이지를 완독했습니다. 하지만 API와 같은10초 제한에서200블록·동시16개도 TimeoutError였습니다. 실제 확인한30,000보다 작은2,000블록·동시4개로 요청 수·순간 부하를 줄여 최종16페이지를 읽었습니다. 공개 RPC 정책에 맞는 작은 요청을 유지하며 무제한 병렬 호출이나 C timeout 연장으로 우회하지 않았습니다.

최종 실제 `WalletRegistryReadAdapter.proposal()`을 `asyncio.wait_for(..., timeout=10)`으로 실행: **9.25초 / EXECUTED / 승인자2명 PASS**. 정본 CREATE·생성자3명 검증 후 공개 승인 거래 calldata에서 proposal ID를 읽었고, 서비스 API·공개 체인 쓰기0입니다. 직접 Adapter 결과이며 생산 HTTP API 실행은 아닙니다. 9.25초 한 번은 안정 SLA가 아니며 여유가 작습니다. 이력 증가·provider 지연·더 작은 provider 제한은 여전히503/판정 보류를 낼 수 있습니다. 전체 이력 재조회 비용은 남아 있고 신뢰할 인덱스/범위 축소는 별도 계약·설계가 필요합니다.

## 검사와 재현

기존 Python3.13.14 venv·같은 macOS 장비 재사용. 새 locked install/다른 노트북이 아닙니다.

```sh
uv run pytest -q services/indexer/tests/test_wallet_log_windows.py \
  services/indexer/tests/test_wallet_chain.py \
  services/indexer/tests/test_wallet_reconciliation.py \
  apps/api/tests/infrastructure/blockchain/test_wallet_failover.py
uv run pytest -q
uv run ruff check apps/api/src/infrastructure/blockchain/wallet_rpc.py \
  services/indexer/tests/test_wallet_log_windows.py
git diff --check
```

- 수정 전 실제 WalletRpc/Reconciler 경계의 합성 range-provider:4 FAIL/5 PASS. 최종 관련144 PASS(신규10 포함).
- 100,001블록 제안 이력, 2,000/2,001/4,000/4,001 경계와 실제 경계 이벤트·역순 응답, 페이지 오류·범위 밖·중복·재조직 거부, 최대4개 동시 요청·취소 후 잔여 요청0 확인.
- 최종 생산 코드 SHA에서 전체 **1,434 PASS/20 SKIP/기존 경고1**. 이후 시험 데이터만 경계 이벤트를 보강했고 해당10개 재통과. 기본 전체 suite는 실제 EVM/PostgreSQL 전체 실행으로 소개하지 않습니다.
- 실제 공개 한도 관찰·Adapter 결과의 메서드/범위/참조 block은 증거 JSON에 보존합니다. 개인키·세션·유료 호출 없음.

## #102 의견 반영

기존 B PR #102의 별도 branch에서 HTTP 상태를 JSON 파싱 전에 trace에 남겼습니다. 비JSON429/502도 상태를 보존하되 본문·URL·키는 출력하지 않습니다. 수정 전2 FAIL, 수정 후65 PASS·Ruff/diff PASS. 원본10-27 공개 체인 증거는 보존했습니다. 원본 bytes/content/metadata export는 여전히 A 인계 대기이며 C의 metadata 경로 정정을 문서에 반영했습니다.

## #104 리뷰 — 수정 필요

고정 `b255ac09d4150016b4a9d6f132364530d7470648` source archive에서 projection63 PASS. 고정 Foundry1.4.4·solc0.8.26·Cancun 빌드의 생성 bytecode가 manifest와 일치했습니다. #102 문서와 경로 충돌 없음.

재현한 P2: 첫200블록 chunk의 이벤트 저장 뒤 두 번째 chunk 읽기에서 앞 구간을 재조직하면, 과거 고아 journal이 남고 checkpoint는 새 정본으로 전진합니다. 다음 sync는0이며 최신 checkpoint가 정본이라 기존 recover_reorg도 혼합 이력을 감지하지 못합니다. 각 page 저장 전에 이전 checkpoint와 원래 고정한 head의 정본 연결 재확인·변경 시 새 checkpoint 저장 중단·rewind를 권고했습니다. DB CAS는 체인 연결 검사를 대신하지 않습니다.

[라인 리뷰·REQUEST_CHANGES](https://github.com/OriginProof-3web/OriginProof/pull/104#pullrequestreview-5721838620)를 게시했습니다. PR 작성자의 파일/branch를 수정하지 않았습니다. 원문이 오지 않은 Medium1/Low2는 확인했다고 기록하지 않습니다. 실제 Sepolia projection 재동기화는 미실행입니다.

## #114 리뷰 — B 기술 승인

고정 `7f9931f67b57ec92f54560c73bbb30939e689a62` source archive에서 port `snapshot`·`issuer/document(block=None)`를 실제 Adapter와 C 호출부에 대조했습니다. `test_wallet_adapter.py` + `test_wallet_runtime.py`:110 PASS/1 기존SKIP. 런타임 변경 없이 원본 Protocol을 일치시키는 변경이며 [B/Codex 기술 APPROVED](https://github.com/OriginProof-3web/OriginProof/pull/114)를 게시했습니다. 생산 연결/독립 사람 감사/단계 완료로 확대하지 않습니다.

## 기여·다음 담당

B/Codex: 재현·최소 공통 경계 수정·실제 읽기·검사·리뷰·인계. A의 결함 전달/기존 배포, C의 runtime/포트, 기존 B/D fixture를 재사용했으며 다른 사람 구현을 B 신규 성과로 합산하지 않습니다. 사용자님이1번 작업 범위를 승인했습니다. 새로운 PR의 작성자 외 리뷰는 아직 미확인입니다.

C/D: 공통 경계 변경·실패/취소·provider 증거 리뷰. A/#104 작성자: 재조직 페이지 혼합 결함 수정. A: 원본 export. 팀: 다른 노트북·동일RC 리허설3회·W6 수용은 별도입니다. PR 병합·공개 배포·재발행은 하지 않았습니다.
