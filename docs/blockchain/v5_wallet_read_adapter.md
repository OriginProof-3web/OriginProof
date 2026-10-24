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
