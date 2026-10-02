# W5 / B / 여하민 — 개인 개발 기록

- GitHub 계정: `@hamin1228`
- 실제 작업일: 2026-10-02 (W5는 달력 주차가 아님)
- 작업 ID: `W5-B1`, `W5-B2`, `W5-B3`
- 준비 브랜치: `codex/w5-b-indexer-recovery`; `phase/W5` 생성 전 독립 작업
- 시작 기준: `origin/integration@3295a71` → 본인 W4-B `58e819e` 반영
- 상태: B의 저장·복구 경계와 권한 검사는 독립 검증; C의 스캐너/API 연결·작성자 외 리뷰 대기

## 수행한 작업

| 작업 | 개인 구현·검증 | 재사용·협업 |
| --- | --- | --- |
| W5-B1 | 블록/이벤트/checkpoint 원자 저장, 빈 블록·중복 replay·순서/공백·DB 실패/재시작 검사 | W4 Proof event decoder와 SQLAlchemy projection 재사용 |
| W5-B2 | 2-confirmation 블록 동기화, 실제 공통 조상 rewind, 분기 이벤트 삭제·검증된 projection 조회 | C가 백그라운드 실행·복구 중 상태를 API에 연결해야 함 |
| W5-B3 | constructor/manifest 역할 일치와 실제 Anvil `hasRole`, 직접 Contract 호출 권한 점검 | W4 manifest/Registry/Adapter 및 ADR의 서버 대행 경계 재사용 |

## 주요 판단과 한계

- 저장 완료 전 checkpoint가 앞서지 않도록 블록 단위 transaction을 사용했다.
- reorg 시 호출자가 제시한 블록 hash를 신뢰하지 않고 저장 hash와 현재 체인 hash를
  모두 대조한다. 공통 조상이 없으면 보존 데이터에 덧쓰지 않고 재구축을 요구한다.
- event projection은 현재 사용 가능 판정의 권위가 아니다. B의 확인 블록 처리와
  검증된 조회 경계는 준비됐고, C의 상시 실행·복구 중 응답 연결은 아직 남았다.
- Contract는 서버가 검증한 서명·세션을 다시 검사하지 않는다. gateway 직접 제출에
  대한 접근 통제는 C가 지켜야 한다.

## 검증 근거

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
