# W5 / B / 여하민 — V5-W5-B 1차 체인 증거·이벤트 journal

- `@hamin1228`, 2026-10-16. W5는 개발 단계입니다.
- 브랜치 `codex/v5-w5-b-chain-evidence`, 시작 `a4bfa22bf870f3bd5ae02e439636fbf8204444a7`.
- **B 저수준 독립 구현/합성 검사 완료 / C port adapter·실제 연결·W5 전체 완료는 대기**입니다.

Codex가 B의 생성 ABI 기반 hash-pinned RPC 조회, 직접 제출 calldata/receipt 증거, 승인·정지·버전 이벤트 7종 해석과 배포별 SQLAlchemy journal을 구현했습니다. 이벤트와 cursor의 원자적 저장·재시작·명시 reorg 복구·오래된 projection과 현재 상태 조회 분리를 검사했습니다. 기존 W2~W4 컨트랙트/ABI, httpx·eth-abi·SQLAlchemy·오류 경계를 재사용했습니다. C Draft port는 고정 SHA로 읽기만 했고 사본이나 C/A/D 생산 코드 수정은 없습니다. 사람의 작성·리뷰 승인·기여 비율을 추정하지 않습니다.

최종 Python **229 PASS / 1 live SKIP**에 신규 W5 **50 PASS**가 포함됩니다. 공식 lint·구조·문법·Node hash·생성물 일관성 통과. 외부 Foundry 라이브러리까지 포함한 lint는 기존 외부 코드 26건으로 실패했으며 공식 범위 검사와 구분합니다. 초기 44 PASS 뒤 경계 검사를 6개 추가했습니다. Solidity는 이번 변경이 없어 재검사하지 않았습니다.

실제 새 배포·RPC·직접 제출·API·지갑·PostgreSQL·D 독립 재현은 미실행입니다. 성공 receipt를 C의 CONFIRMED로 취급하지 않습니다. B-C01 고정 승인자 provenance, B-C02 승인 목록/count 대조, B-C03 UNKNOWN 검색/중계·작업별 상태 대조, custom-error 누락 구분과 C 원본 port 변환이 남습니다. **G07은 미해결**입니다. 상세 흐름·명령·한계는 [B 인계](../blockchain/v5_w5_chain_evidence.md)에 기록합니다.

기존 사용자 변경 5개·legacy 경로와 과거 기록을 보존했습니다. 팀 Draft PR·개인 비공개 포트폴리오에 검증한 커밋을 공유하며, 작성자 외 리뷰/실제 연결 완료는 주장하지 않습니다.


## 2026-10-17 · W5 2차 B 대조 로직

`codex/v5-w5-b-reconciliation`에서 자기 1차 `7666bb9bf2d85804b9abe9be5a87ea122e1d914d`를 이어 getter별 정확한 미등록 분류, canonical 승인 목록/count·동일 tx 실행 검증, 전체 intent·이벤트·receipt/현재 상태 대조를 구현했습니다. 발행·철회·제안·승인·정지 5개 경로와 나중 철회/대체/정지/재활성화를 구분합니다. 동일 블록의 정지/재활성화를 분리할 수 없으면 dependency 오류를 반환합니다. 상세 흐름/한계는 [2차 인계](../blockchain/v5_w5_reconciliation.md)입니다.

최종 전체 Python **281 PASS/1 live SKIP**, 2차 신규 52 PASS·1차 50 PASS 포함입니다. 공식 lint·구조·Node hash·생성물 일관성 통과. 최초 37 PASS 뒤 경계 15건을 추가했고 줄길이/변수명 lint 경고를 수정했습니다. Solidity/ABI는 무변경이라 로컬 Foundry를 재실행하지 않았습니다. 원격 CI 결과는 새 Draft PR에서 별도로 확인합니다.

Codex가 B 코드·검사·기록을 작성하고 기존 RPC/ABI·W2~W4 구현·합성 fixture·설치 의존성을 재사용했습니다. 사람의 직접 작성/리뷰·기여 비율을 추정하지 않습니다. 사용자 변경 5개를 보존합니다. C/A/D 생산 코드·공통 계약 변경은 없으며 타 담당 브랜치를 임의 병합하지 않았습니다. 원격 integration `4a9b92d`의 D 추가 반영은 이번 자기 W5 작업 트리 검사에 합산하지 않습니다.

독립 구현·합성 검사 결과이며 W5 단계 전체 완료는 아닙니다. C 원본 port 변환·승인자 배포 provenance·UNKNOWN 검색/중계·최종성/Operation 연결·실제 RPC/DB/지갑·D 리뷰가 남습니다. **G07은 미해결**이며 SG01~16 공유 상태를 바꾸지 않습니다. 팀 Draft PR과 개인 비공개 포트폴리오에 실제 검증한 커밋을 보관합니다.

## 이전 계획의 개발 기록 보존

아래는 C의 재사용 기준에 포함된 이전 개발 기록입니다. 당시 검사·연결·리뷰 상태를 보존하며, 위 V5 작업의 완료 근거로 합산하지 않습니다.

### W5 / B / 여하민 — 개인 개발 기록

- GitHub 계정: `@hamin1228`
- 실제 작업일: 2026-10-02 (W5는 달력 주차가 아님)
- 작업 ID: `W5-B1`, `W5-B2`, `W5-B3`
- 준비 브랜치: `codex/w5-b-indexer-recovery`; `phase/W5` 생성 전 독립 작업
- 시작 기준: `origin/integration@3295a71` → 본인 W4-B `58e819e` 반영
- 상태: B의 저장·복구 경계와 권한 검사는 독립 검증; C의 스캐너/API 연결·작성자 외 리뷰 대기

#### 수행한 작업

| 작업 | 개인 구현·검증 | 재사용·협업 |
| --- | --- | --- |
| W5-B1 | 블록/이벤트/checkpoint 원자 저장, 빈 블록·중복 replay·순서/공백·DB 실패/재시작 검사 | W4 Proof event decoder와 SQLAlchemy projection 재사용 |
| W5-B2 | 2-confirmation 블록 동기화, 실제 공통 조상 rewind, 분기 이벤트 삭제·검증된 projection 조회 | C가 백그라운드 실행·복구 중 상태를 API에 연결해야 함 |
| W5-B3 | constructor/manifest 역할 일치와 실제 Anvil `hasRole`, 직접 Contract 호출 권한 점검 | W4 manifest/Registry/Adapter 및 ADR의 서버 대행 경계 재사용 |

#### 주요 판단과 한계

- 저장 완료 전 checkpoint가 앞서지 않도록 블록 단위 transaction을 사용했다.
- reorg 시 호출자가 제시한 블록 hash를 신뢰하지 않고 저장 hash와 현재 체인 hash를
  모두 대조한다. 공통 조상이 없으면 보존 데이터에 덧쓰지 않고 재구축을 요구한다.
- event projection은 현재 사용 가능 판정의 권위가 아니다. B의 확인 블록 처리와
  검증된 조회 경계는 준비됐고, C의 상시 실행·복구 중 응답 연결은 아직 남았다.
- Contract는 서버가 검증한 서명·세션을 다시 검사하지 않는다. gateway 직접 제출에
  대한 접근 통제는 C가 지켜야 한다.

#### 검증 근거

| 검사 | 실제 결과 |
| --- | --- |
| Indexer/API/Core Python 회귀 | 131 passed, opt-in 4 skipped |
| Foundry 전체 | 22 passed, 0 failed; admin/issuer 직접 호출 거부 확인 |
| 임시 Anvil 통합 | 1 passed; 배포 역할 → 실제 eth_getLogs → 미확정 tip 보류 → 다음 블록 후 저장 |
| Ruff | 변경 경로 check와 format 확인 통과 |

CI·외부 리뷰·C 실제 API/DB 연결은 아직 확인하지 않았다. 유료 RPC와 보존 DB 초기화는
실행하지 않았다. Codex로 코드·검사·문서 초안을 만들고, 기존 계약을 재사용하며
재시작·reorg의 데이터 손실 경계와 직접 호출 권한을 검토했다.

- 본인 확인: `@hamin1228` / 2026-10-02 / 기록 확인 대기
- 작성자 외 리뷰: 미확인
