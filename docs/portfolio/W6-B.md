# W6 / B / 여하민 — 개인 개발 기록

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

임의 재전송을 만들지 않는 기존 Writer 복구 계약을 재사용했다. 같은 chain ID라도
재배포된 체인은 다른 deployment ID로 분리했다. Contract의 issuer/gateway 직접 등록
권한은 ADR 신뢰 경계이며, C가 JSON 서명·세션을 검증해야 한다.

검증: API/Core/Indexer/Analyzer/CI Python `265 passed, 5 skipped`, Ruff 통과,
Foundry `22 passed`, 임시 Anvil 통합 `2 passed`. `uv audit`의 16항목(런타임
Starlette 14·개발 pytest 2)은 실패/미해결로 기록한다. 임시 합성 체인만 사용했고
유료 RPC나 보존 DB 초기화는 하지 않았다. Codex로 장애 주입·runbook 초안을 만들고
검사 결과와 미해결 공유 의존성 위험을 분리해 기록했다.

- 본인 확인: `@hamin1228` / 2026-10-02 / 기록 확인 대기
- 작성자 외 리뷰: 미확인
