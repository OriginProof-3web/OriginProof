# V5-W5-B / 1차 — ABI 조회·이벤트·직접 제출 증거

- 날짜: 2026-10-16, 담당 B / 여하민 `@hamin1228`.
- 브랜치: `codex/v5-w5-b-chain-evidence`, 시작 SHA `a4bfa22bf870f3bd5ae02e439636fbf8204444a7`.
- 기준: 계획서 5.1, v5-shared-0.1, [ADR 0004](../adr/0004-v5-governance-wallet-versioning.md).
- 상태: **B 저수준 증거 경계·journal 독립 구현/합성 검사 완료. W5 전체·C WalletRegistry 연결·실제 배포/직접 제출 검증은 미완료.**

## 동작과 사용 경계

1. `WalletRpc`에 기존 `httpx.AsyncClient`, 신뢰 설정의 chain ID/주소/배포 block·hash/실제 runtime code Keccak hash와 컴파일 ABI를 전달합니다. ABI 원본은 [구현 ABI](../../packages/contracts/abi/OriginProofWalletRegistry.json)이며 ABI·공유 모델을 복제하지 않습니다. constructor immutable이 포함된 실제 배포 runtime hash가 필요합니다. Golden 주소를 배포 주소로 쓰지 않습니다.
2. `snapshot()`이 chain ID, 배포 block hash, 최신 block, 해당 hash의 runtime code를 검사합니다. `read(name, args)`는 새 snapshot에서 ABI view 함수를 호출하고 관측 block과 ABI tuple을 반환합니다. `call(name, args, block)`은 같은 snapshot에서 여러 조회를 묶기 위한 내부 소비 경계이며 `eth_call`에 EIP-1898 `blockHash/requireCanonical`을 사용합니다. 마지막 canonical block 재조회가 어긋나면 실패합니다. RPC가 hash pin을 지원하지 않을 때 latest로 대체하지 않습니다.
3. `logs(start, snapshot)`은 생성 ABI의 승인 생성/승인/실행·기관 정지·문서 발행/철회/대체 7개 이벤트를 해석합니다. 주소·topic/data·중복 위치·범위·removed·canonical block hash를 검사합니다. 관측은 신뢰 설정 RPC에 의존하며 finality 증명 또는 독립 RPC quorum은 아닙니다.
4. `WalletProjection(engine, rpc).initialize()`는 기존 legacy 테이블과 별개인 `wallet_events`, `wallet_checkpoints`를 만듭니다. `sync()`는 chain/address/deployment hash별 이벤트와 체크포인트를 **같은 DB 트랜잭션**에 저장합니다. 기존 체크포인트의 hash 불일치·head 역행을 거부하고, compare-and-swap 또는 최초 cursor PK로 경쟁 worker의 전체 페이지를 rollback합니다. RPC 실패·DB 저장 실패에 체크포인트를 먼저 전진시키지 않습니다. 별도 DB를 권장하며 C의 API DB migration을 대신하지 않습니다.
5. reorg는 자동으로 과거 성공을 유지하지 않습니다. `rewind(safe_block, safe_hash)`는 운영자가 확인한 공통 조상을 요구합니다. 현재 canonical hash, 남겨둘 journal 이벤트의 block hash와 cursor 경쟁을 검사하고 이후 기록 삭제·cursor 변경을 함께 수행합니다. 잘못 고른 조상에서 누락 이벤트를 추측 복원하지 않습니다. 완전 재구축이 필요하면 별도 빈 journal DB에서 배포 block부터 재생합니다.
6. `transaction_evidence(tx_hash)`는 **실제 조회한 calldata**를 ABI로 해석합니다. chain/address/hash/sender/value·receipt block/transaction index·이벤트 위치/주소를 확인합니다. pending/미발견은 `None`, RPC 실패는 dependency 오류, 실패 receipt는 `receipt_status=0`입니다. 응답은 `function`, `arguments`, `sender`, `receipt_status`, `block`, `events`이며 C의 `WalletTransaction` 또는 `CONFIRMED`가 아닙니다. 이 경계는 트랜잭션을 보내지 않습니다.

현재 상태 조회는 journal을 전혀 읽지 않습니다. 오래된 projection을 근거로 현재 유효·확정 성공을 반환하지 않습니다. 그러나 이 증거 모듈 자체는 API에서 아직 호출되지 않습니다. 새 의존성·체인 배포·키 수집·컨트랙트/공유 모델 변경은 없습니다. RPC URL/응답 전문을 로그로 출력하지 않습니다.

## C 소비·남은 B 작업

C Draft [#63](https://github.com/OriginProof-3web/OriginProof/pull/63)의 고정 SHA `6e0e924c77e9a5b83a8522df4d3cfdc797e8822c`에 `wallet_ports.py`가 있지만 이 B 브랜치에는 없습니다. 타 담당 브랜치를 병합하거나 port 사본·C 모델을 만들지 않았습니다. 추후 원본 port가 합의된 기준에 들어온 후 그 원본을 import해 변환해야 합니다. 저수준 결과를 C port의 완성된 구현으로 주입하면 안 됩니다.

- `getIssuer/getKey/getProposal/getDocument`, nonce/latest의 ABI 조회 원리는 준비됐지만 `WalletIssuer/WalletKey/WalletDocument/WalletProposal` 변환·누락 getter의 정확한 custom-error→None 구분은 후속입니다. 현재 RPC revert는 모두 dependency 오류입니다. 임의 실패를 미등록으로 숨기지 않습니다.
- **B-C01:** `is_approver`는 ABI에 없습니다. runtime code/constructor·신뢰 manifest에서 고정 승인자 3개를 검증하는 소비 경계가 남습니다. 임의 getter를 추가하지 않았습니다.
- **B-C02:** canonical `ProposalApproved` 해석·journal은 준비됐습니다. 승인 주소 집합·count·getProposal 대조와 C ProposalView status/경고 변환은 후속입니다. journal만으로 실행 성공을 선언하지 않습니다.
- **B-C03:** calldata·receipt 증거는 준비됐지만 intent별 이벤트/불변값·receipt 당시 상태와 현재 상태 대조, UNKNOWN 원본 검색 범위/재조회, `submit` 중계·C Operation 연결은 후속입니다. tx hash 또는 성공 receipt만으로 CONFIRMED를 반환하지 않습니다. 미발견과 pending의 세부 상태 구분도 C port adapter에서 필요합니다.
- 실제 새 배포 manifest/승인 지갑 provenance·확정 깊이·배포 code hash·로컬 RPC/직접 제출·PostgreSQL 동시 worker 검사가 남습니다. EIP-1898 미지원/과도한 getLogs 범위 제한은 명시 실패하며 운영 chunk 크기·재시도 정책은 후속 실제 환경에서 정합니다.
- **G07은 미해결**입니다. head 역행/배포 혼합/재시작/명시 reorg 방어를 합성 검사한 것이 기존 mixed 실패 원인을 재현·수정했다는 뜻은 아닙니다. D의 같은 후보 SHA 재현과 독립 리뷰가 필요합니다.

## 검사·실패 이력

macOS arm64 / Python 3.13 / SQLite·httpx MockTransport 합성 기준입니다.

```sh
.uv-venv/bin/pytest -q
.uv-venv/bin/ruff check apps packages/python services scripts
.uv-venv/bin/python scripts/ci/validate_structure.py
.uv-venv/bin/python -m compileall -q apps/api/src/infrastructure/blockchain services/indexer/src
node scripts/ci/check_wallet_browser_hashes.mjs
make generate
git diff --exit-code -- packages/schemas/generated fixtures/golden
git diff --check
```

- Python 최종 **229 PASS / 1 live SKIP**, 기존 anyio deprecation warning 1개. 신규 W5 **50 PASS** 포함. 초기 W5 44 PASS 후 경계 6건을 추가했습니다.
- 체인·runtime·배포/ABI·JSON-RPC 오류, hash pin/reorg, 7종 event·orphan/duplicate/removed, 실제 calldata·도메인·receipt/잘린 입력/중복 로그, restart/배포 분리/DB rollback/조상 hash·head 역행 거부를 검사했습니다.
- 공식 lint·구조·문법·Node hash·생성물 diff·공백 검사 PASS. `ruff check apps packages services scripts` 확장 명령은 로컬 설치된 ignored `packages/contracts/lib/` 외부 라이브러리의 기존 오류 **26건**으로 FAIL했습니다. 외부 코드를 수정하지 않았으며 공식 Makefile Python lint 범위로 구분했습니다.
- Solidity·ABI는 변경하지 않아 이번에 Foundry를 다시 실행하지 않았습니다. 이전 W4 Foundry 88 PASS는 W4 근거이며 신규 RPC 실제 검사로 합산하지 않습니다.
- 실제 RPC·EVM 배포·네트워크 직접 제출/receipt·API/DB/브라우저·PostgreSQL 경쟁·D 독립 QA·v2/consume 전체 실환경·G07 재현·공개 체인·유료 AI는 **미실행**입니다. SG01~16 상태를 변경하지 않았습니다.

## 기여·보존

Codex가 B 영역에 저수준 모듈 2개와 합성 검사를 작성했습니다. 기존 B W2~W4 Solidity/컴파일 ABI, baseline httpx·eth-abi·오류 경계, SQLAlchemy 이벤트/checkpoint 설계와 C의 고정 port를 참고했습니다. 공통 모델·API orchestration·A/D 구현을 변경하지 않았고 사람의 직접 작성/리뷰·기여 비율을 추정하지 않습니다.

사용자 미커밋 5개와 과거 phase/legacy 코드를 보존합니다. 기존 projection 테이블을 migration/덮어쓰기하지 않습니다. 계획서 5.1은 5.0 범위 유지·인계 갱신이며 공유 계약 준비는 실제 연결 완료가 아닙니다. 입력 종류·우선순위는 회의 후 결정하고 Decisions API는 범위 밖입니다.
