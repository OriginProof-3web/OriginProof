# W6 / B / 여하민 — 개인 개발 기록

> 초기 기록은 2026-10-02 당시 작업입니다. 최신 v5 보완은 아래 2026-10-24 절을 확인합니다.

- GitHub 계정: `@hamin1228`
- 실제 작업일: 2026-10-02 (W6는 달력 주차가 아님)
- 작업 ID: `W6-B1`, `W6-B2`, `W6-B3`
- 준비 브랜치: `codex/w6-b-recovery-security`; `phase/W6` 생성 전 독립 작업
- 시작 기준: `origin/integration@3295a71` → 본인 W5-B `b7a4107` 반영
- 상태: B의 장애 주입·폐기 가능한 로컬 EVM 재배포·권한/키 노출 점검 실행;
  공유 의존성 취약점 수정, C 보존 DB/API 연결·외부 리뷰·팀 단계 완료는 별도

## 실제 수행과 판단

| 작업 | 개인 작업 | 경계/후속 |
| --- | --- | --- |
| W6-B1 | receipt RPC 단절→복구, 재조회 중 reorg 보류, 실제 Anvil pending receipt 복구와 snapshot/revert 후 checkpoint 복구, 인덱서 reorg·중복 검사 | C Operation 영속 저장·복구 연결 필요 |
| W6-B2 | 임시 Anvil 두 번 기동·재배포해 같은 chain ID의 새 manifest/주소/이벤트 시작점/seed signer 검사 | W5-C3 Compose와 W6-C3 보존 DB 복구는 별도 |
| W6-B3 | Foundry 권한/서명 Golden Vector·coverage, 추적 소스 비밀 패턴, `uv audit --frozen` 실제 실행 | Starlette/pytest 취약점은 API·공유 의존성 소유자와 수정 필요 |
| W6-B1 후속 P1 | 제출 RPC 오류를 UNKNOWN으로 보류하고 nonce/복구 참조 유지, 성공 거래의 sender·nonce·to·input 결합 검사 (`65b041e`) | C의 실제 Operation DB 복구 연결·작성자 외 리뷰 필요 |

임의 재전송을 만들지 않는 기존 Writer 복구 계약을 재사용했다. 같은 chain ID라도
재배포된 체인은 다른 deployment ID로 분리했다. Contract의 issuer/gateway 직접 등록
권한은 ADR 신뢰 경계이며, C가 JSON 서명·세션을 검증해야 한다.

검증: API/Core/Indexer/Analyzer/CI Python `265 passed, 5 skipped`, Ruff 통과,
Foundry `22 passed`, 임시 Anvil 통합 `2 passed`. `uv audit`의 16항목(런타임
Starlette 14·개발 pytest 2)은 실패/미해결로 기록한다. 임시 합성 체인만 사용했고
유료 RPC나 보존 DB 초기화는 하지 않았다. Codex로 장애 주입·runbook 초안을 만들고
검사 결과와 미해결 공유 의존성 위험을 분리해 기록했다.

2026-10-02 후속 수정에서는 Writer mock `54 passed`, 전체 Python
`293 passed, 5 skipped`, Ruff/diff 통과, 임시 Anvil `2 passed`를 확인했다.
기존 `FAILED/CHAIN_REVERTED` 제출 오류를 `UNKNOWN/SUBMISSION_UNKNOWN`으로 바꿔
C가 같은 Operation을 재조회할 수 있게 했다. 실제 canonical 실패 receipt의
`FAILED`는 유지했다. 저장된 tx hash도 준비한 거래와 대조하며 불일치는
`UNKNOWN/TRANSACTION_NOT_MATCHED`다. 확인한 코드 SHA는 `65b041e`; C 보존 DB
재시작 연결은 이 검사에 포함되지 않는다.

- 본인 확인: `@hamin1228` / 2026-10-02 / 기록 확인 대기
- 작성자 외 리뷰: 미확인


## 2026-10-24 — V5-W6-B 이벤트 증거 경계 보완

- 상태: 독립 구현·검사 완료 / 실제 C API 연결·독립 리뷰·W6 단계 완료는 미확인.
- 브랜치: `codex/v5-w6-b-evidence-boundaries`.
- 시작 integration `ec8e15c`, 필요한 W5 선행 코드 `5f3540a` 반영.
- 검증 코드 SHA: `b50cbde1d7b9a25fa8229013d843cb8ca4de779e`.
- phase/W6 미생성으로 준비 Draft이며, 임시 비교 대상 phase/W5에는 병합하지 않는다.

사용자가 두 결함의 최소 수정을 선택했고 Codex가 구현·검사·기록을 수행했다.
기존 B의 WalletRpc/WalletReconciler, 합성 Oracle/Chain, 실제 Anvil 복구 검사를 재사용했다.
정지 receipt와 같은 거래의 canonical 이벤트가 다르면 보류하고, 블록에 없는 거래의 로그를 거부한다.
정상 반복 정지·공동승인·reorg 복구는 유지한다. Contract·ABI·공유 Schema 변경은 없다.

신규 검사는 수정 전 4 failed / 1 passed, 수정 후 관련 226 passed였다.
전체 Python 957 passed / 11 skipped, Foundry 1.4.4 실제 Anvil 복구 1 passed,
변경 Python lint·diff 검사가 통과했다. Python은 기존 설치 환경 재사용이며 fresh lockfile sync가 아니다.
재현·명령·환경·제약은 [실행 기록](../blockchain/w6_fault_recovery_security.md#2026-10-24-v5-w6-b-이벤트-증거-경계-보완)에 있다.

이번 성과는 불일치 RPC 응답을 성공 근거·journal로 수용하지 않는다는 범위다.
실제 C API/DB 영속 복구·공개 체인·다른 장비·작성자 외 리뷰는 후속이다.
사용자의 수정 방향 승인을 사람의 코드 리뷰로 대신하지 않는다.

- 본인: 사용자 지시·선택에 따른 작업. 코드 직접 리뷰·기여 사실 확인은 별도 미확인.
- 작성자 외 리뷰: 미확인. 단계 완료 PR: 미생성.
