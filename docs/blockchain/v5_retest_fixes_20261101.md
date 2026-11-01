# V5-W6-B: 2026-11-01 재시험 결함 후속

- 담당: B 여하민 `@hamin1228`. 사용자 선택 ①(B 관련 중간 2건 + RPC 5건)을 구현했습니다.
- branch: `codex/v5-w6-b-retest-fixes`, 대상 `phase/W6`.
- phase 기준: `f1d7b3c0002f406419d44321aff4cff3e90edd57`.
- 선행: [#124](https://github.com/OriginProof-3web/OriginProof/pull/124) `62b35c33d9127df4fae6f5de0bdb8d13c3aa7658`. 같은 B의 로그 분할을 재사용했습니다.
- 검증 코드 SHA: `cda575c084e9350b06b2d6bc1468bc2afa583132`. 이후 변경은 이 문서·B 기여 기록뿐입니다.
- 상태: B 독립 구현·합성 검사 및 폐기 가능한 로컬 Anvil 연결 검사 완료. 작성자 외 리뷰·RC 합본·공개 RPC 성능 재검사는 미확인입니다. W6 전체 완료가 아닙니다.

## 동작 순서와 결함 대응

| 보고 항목 | 변경과 검증 |
| --- | --- |
| 제안/승인 확정 시 전체 로그 2회 조회 | 현재 snapshot의 이력을 한 번 읽고 receipt 블록 이하만 과거 상태 검사에 사용합니다. 각 시점의 getProposal과 정본 검사·서명자/이벤트/이력 검사는 유지합니다. 서로 다른 시점에 승인 1회/실행 완료가 보이는 사례도 검사합니다. |
| 빈 로그 페이지 후 이벤트 영구 누락 | projection 저장 전에 구간의 모든 블록과 거래 receipt를 확인합니다. 로그 목록이 receipt의 Registry 이벤트와 다르면 checkpoint를 전진시키지 않습니다. 128블록씩 원자 저장하고 전체 확정 tip까지 도달해야 sync가 성공 반환합니다. 다음 구간 실패·취소 시 이미 검증한 진행점부터 재개합니다. |
| 이벤트 블록 조회 직렬 | 중복 블록을 제거하고 최대 4개씩 병렬 조회합니다. block hash·거래 포함·중복 위치 검사는 유지합니다. |
| 실패 페이지가 느린 페이지를 기다림 | 첫 예외를 즉시 전달하고 같은 묶음의 나머지 task를 취소·회수합니다. 외부 취소도 전달합니다. |
| 동시 제한이 호출별 | 같은 AsyncClient를 쓰는 WalletRpc와 primary/fallback이 하나의 semaphore를 공유합니다. 동시 스캔 10개·실제 병렬 페이지와 블록 읽기가 있어도 HTTP 요청은 최대 4개입니다. |
| 중첩 JSON RecursionError가 전환 우회 | RecursionError를 dependency 오류로 바꿔 검증된 fallback을 사용합니다. 이전 SHA에서 100,000단계 합성 JSON의 RecursionError를 별도 확인했습니다. |
| 직접 WalletRpc traceback에 URL 키 | transport/JSON 실패를 handler 밖에서 안정된 오류로 다시 발생시켜 cause/context에 provider URL을 남기지 않습니다. 전체 traceback과 context 검사를 수행합니다. |

Projection 순서:

1. 배포 식별을 검증하고 confirmation 정책에 맞는 head와 기존 checkpoint를 확인합니다.
2. 최대 128블록의 로그를 읽고 정본 블록의 모든 거래 receipt와 이벤트 전체를 대조합니다. empty/부분 응답·receipt 누락/불일치면 실패합니다.
3. 원래 목표 head와 이전 저장 checkpoint의 hash를 다시 확인합니다. 구간 사이 재조직이면 새 checkpoint와 과거 fork 이벤트를 섞지 않습니다.
4. 기존 compare-and-swap DB transaction으로 이벤트와 checkpoint를 함께 저장합니다. 구간 실패는 그 구간을 저장하지 않으며 앞서 검증된 구간은 유지합니다.
5. 전체 확정 tip까지 반복합니다. API의 기존 `sync 성공 = tip 도달` 계약과 정지/재조직 복구 경로는 유지합니다. projection을 현재 발행 상태의 권위로 사용하지 않습니다.

## 검사와 실패 이력

환경: macOS arm64, Python 3.13.14, 기존 uv venv 재사용, SQLite·httpx MockTransport. 실제 연결 검사는 새로 시작해 종료하는 Anvil/Forge 1.8.1·solc 0.8.26이며 기존 로컬 노드·DB·배포 manifest를 변경하지 않았습니다. 원래 작업 폴더의 사용자 변경 5개도 보존했습니다.

```sh
# 해당 SHA의 workspace 의존성이 설치된 환경
.uv-venv/bin/pytest -q
.uv-venv/bin/ruff check apps packages/python services scripts
.uv-venv/bin/python scripts/ci/validate_structure.py
git diff --check

# Foundry와 기존 lock에 맞는 contracts/lib가 준비된 경우, 새 합성 노드만 실행
ORIGINPROOF_WALLET_LIVE=1 .uv-venv/bin/pytest -q services/indexer/tests/test_wallet_live.py
```

- 최초 재시험 회귀 7 FAIL. 최종 신규 회귀 16개 포함 전체 Python **1,450 PASS / 20 SKIP / 기존 anyio deprecation warning 1** (32.31초).
- 승인 대사 30,001블록·16페이지·페이지당 2.2초 합성 지연에서 `asyncio.wait_for(..., 10)` PASS. 이력은 한 번 읽습니다. 실제 공개 provider SLA 측정이 아닙니다.
- 신규 회귀는 중복 스캔, 실패 즉시 취소, 공유 동시 제한, 블록 병렬 조회, nested JSON/traceback, empty/부분 로그, receipt 누락/오류, 검증된 fallback, 페이지 재개, 시점 분리, 구간 사이 재조직을 포함합니다.
- 실제 로컬 EVM opt-in **1 PASS** (최종 1.76초). 기존 거래 응답 유실·UNKNOWN 원본 검색·발행/철회·기관 정지/공동 복구·SQLite 재시작·실제 reorg 경로와 새 receipt 검사가 함께 통과했습니다. 시나리오 수를 pytest 수로 합산하지 않습니다.
- Ruff·구조·diff PASS. Solidity/ABI/Schema/lockfile 무변경. live 검사에서 forge build와 생성 ABI 대조는 실행했고 전체 Foundry fuzz는 재실행하지 않았습니다.
- 중간 검사에서 합성 reorg 데이터가 블록/로그만 바꾸고 receipt를 과거 fork에 남겨 기존 3개 검사가 실패했습니다. receipt도 같은 fork로 갱신했습니다. API lifespan의 합성 RPC에는 receipt 메서드가 없어 4개가 실패했고, 서로 다른 블록에 같은 tx hash를 쓰던 대역을 블록별 hash/receipt로 보완했습니다. WalletRpc(None) 연결 대역도 초기 공유 제한 생성 시 처리합니다. 제품의 정본 검사를 완화하지 않았습니다.

## 비용·호환성과 다음 담당자

- C 생산 코드·외부 API·DB schema·Solidity·ABI·의존성·서명 계약은 변경하지 않았습니다. C 영역에서는 소비 회귀 테스트의 합성 RPC 응답만 갱신했습니다. 새 `verify_logs`는 B 내부 RPC helper이며 FailoverWalletRpc도 같은 검증 경계를 호출합니다.
- receipt 대조는 블록·거래 수에 비례해 RPC 비용을 늘립니다. 오래된 공개 체인의 첫 backfill은 느릴 수 있습니다. 진행점은 128블록마다 보존하며 timeout/취소를 성공으로 바꾸지 않습니다. provider가 관련 역사 블록/receipt를 제공해야 합니다. 이 비용을 숨기거나 실제 공개 환경 처리량을 추정하지 않습니다.
- 공유 제한은 같은 AsyncClient 범위입니다. 별도 client/프로세스까지의 전역 provider quota가 아닙니다. 10초 대사 검사는 단독 합성 조건이고 이력 증가·동시 요청·공개 네트워크에서는 503이 가능합니다.
- **이미 구버전으로 누락된 과거 journal은 이 변경만으로 소급 복구되지 않습니다.** 대상 배포와 누락 구간을 확인해 기존 `rewind(safe_block, safe_hash)`로 누락 이전의 검증된 checkpoint로 되감은 후 새 sync를 실행해야 합니다. 신뢰할 과거 지점이 없으면 별도 projection DB에서 처음부터 재생해 비교합니다. 사용자 DB 삭제/자동 reset은 수행하지 않았습니다. B/C가 실제 대상과 중단 범위를 정한 뒤 복구하고 D가 기록 수·checkpoint를 독립 확인해야 합니다.
- [#104](https://github.com/OriginProof-3web/OriginProof/pull/104)의 projection 구간 저장 수정과 경로가 겹칩니다. 이번 구현은 구간 사이 정본 head/이전 checkpoint 재검사를 포함하며, #104 병합 시 이 검사·receipt 완전성 검사를 보존해 충돌을 해결해야 합니다. #104의 별도 Foundry/런북 수정은 이 작업에 포함하지 않았습니다.
- B/C/D: 실제 PostgreSQL projection·최신 PR 합본·공개 RPC 부하/처리량·독립 리뷰·같은 RC 재현은 후속입니다. 기존 G07·W6 전체 수용·공개 배포 완료로 올리지 않습니다.

## 기여와 AI

사용자가 작업 범위 ①을 선택했습니다. Codex가 B 범위 원인 확인·구현·합성/로컬 EVM 실행·인계 문서를 작성했습니다. 기존 B RPC/Reconciler/Projection과 #124, C API lifespan/테스트와 공유 모델을 재사용했습니다. A/C/D의 다른 결함을 수정하거나 타인 리뷰를 받은 것으로 기록하지 않습니다. 사람의 직접 작성량·기여 비율을 추정하지 않습니다.
