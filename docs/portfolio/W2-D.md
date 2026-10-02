# W2 / D / 여인준 — 독립 QA 기록

- GitHub 계정: `@yijun0330` (저장소 역할표 기준)
- 작업일: 2026-10-02. W2는 개발 단계입니다.
- 상태: D1 실제 RPC 장애·API/Anvil 프로세스 재시작·응답 유실 후속 검사 통과; 새 QA 코드 리뷰 대기. D2 실제 브라우저 흐름은 A 화면 연결 대기
- 작업 ID: W2-D1, W2-D2. PR: [#34](https://github.com/OriginProof-3web/OriginProof/pull/34)
- 후속 기준: `origin/phase/W2@812265b285b218e004a08b632ac3aa36125add21`; 이전 PR #34 검사는 `1f8ed632` 기준
- 검증 checkout: `feat/w2-d-qa-phase`; 기존 PR 작업을 보존하고 최신 phase/W2를 merge

## PR #34 당시 목표와 실제 결과

W2 API·Writer 실패/권한 경계를 mock과 disposable 실환경으로 나누어 확인했습니다. API·Analyzer·Indexer·공통 Python 전체 회귀는 **233 passed, 1 skipped**, 경고 1개였고, W1/W2 PostgreSQL·Anvil opt-in live 검사는 **3 passed**였습니다. 단 하나의 skip은 별도 Indexer local-EVM opt-in 검사입니다.

| 작업 | 실제 수행 | 상태 |
| --- | --- | --- |
| W2-D1 | 전체 Python 회귀, 실제 PostgreSQL 로그인/신청/승인 대기/operation 경계, Anvil activation·UNKNOWN nonce 복구·키 등록/회전/폐기·revert receipt 검사 | 주요 API·DB·chain 경계 통과; 실제 프로세스 재시작·일부 장애 주입 사례는 후속 |
| W2-D2 | 키 관리 화면과 Playwright 경로 확인 | 대기: 현 키 화면은 API를 호출하지 않아 신청→운영 승인→체인→키 관리 브라우저 E2E 불가 |

상세 범위·명령·남은 사례는 [W2-D 검증표](../qa/w2-d-acceptance.md)에 기록했습니다. 검사에는 임시 tmpfs PostgreSQL과 임시 Anvil만 사용하고 끝난 뒤 제거했습니다. 기존 Compose DB/볼륨은 건드리지 않았습니다. 제품·API·Contract 코드는 수정하지 않았습니다.

## 검증·한계

- 전체 Python pytest: 233 passed, 1 skipped, warning 1개.
- `test_live_w1_w2.py` 및 `test_live_w2_chain.py`: 3 passed.
- `ruff check apps packages/python services scripts`: 통과.
- `python -m compileall -q apps packages services scripts`: 통과.
- `.env.example` 기반 임시 합성 `.env`만 사용했습니다. 개인 비밀값·운영 서비스·유료 모델은 사용하지 않았습니다.
- W2-D2 실제 브라우저 E2E는 A 화면의 API 연결 전까지 미실행입니다. API 계약은 PR #33으로 존재하지만 UI는 아직 호출하지 않습니다.

## AI 활용·다음 작업

Codex가 최신 phase/W2와 기존 PR 변경을 대조하고, 격리된 로컬 DB/Anvil에서 opt-in 검사를 실행했으며 실제/mock/미실행 범위를 기록했습니다. PR #34는 C의 실제 승인을 받았습니다. 이번 후속 QA 코드는 별도 리뷰 대기입니다. 이 D1 결과는 W2 전체 단계 완료 판정이 아닙니다.

다음: A1/A2 UI 연결 후 새 브라우저 세션으로 실제 승인 및 키 lifecycle을 검증하고 다른 컴퓨터에서 재현합니다. D1 후속 실환경 결과는 아래와 같습니다.

## W2-D1 후속 검사 — 2026-10-02

- 작업 branch: `test/w2-d-recovery-qa`; 검사 코드 SHA: `dd5fc7479b71610be7d53ebbcd94a4b7f8d19342`.
- D 기여: 공유 `scripts/ci`에 격리 QA 추가, RPC/HTTP 장애 relay, 실제 API·Anvil 프로세스 재시작, 실패 원인 분석·재검사·증거 기록. 지정 리뷰어는 C이며 후속 코드는 리뷰 대기입니다.
- B/C의 기존 Contract·Adapter·Operation·인증/감사·키 관리 구현을 재사용했습니다. 제품 소스와 공유 모델은 수정하지 않았습니다.
- 실환경 QA 파일 3 passed. 내부에서 기존 C live 3건과 B local-EVM 1건도 실제 실행했습니다. Python 기본 회귀 171 passed/6 skipped, Indexer 60 passed/1 skipped, Contract 10 passed. 구조·환경·lint·compileall/tsc 통과.
- 미승인/반려 기관, 역할/기관 주입, 제출 전 RPC 단절, 제출 후 hash 유실, receipt timeout, PID가 바뀐 API 복구, Anvil state 재시작과 동일 signer, 새 로그인, HTTP 응답 손실 중복 방지를 확인했습니다.
- 기존 PR #34의 [C 승인](https://github.com/OriginProof-3web/OriginProof/pull/34#pullrequestreview-5389403389)은 문서/CI만을 대상으로 합니다. 새 QA 승인으로 재사용하지 않습니다.
- 실제 실패·수정·재현 명령·환경·검사별 제한: [후속 보고](../qa/w2-d-recovery.md), [fingerprint](../qa/w2-d-recovery-environment.json).
- W2-A 기록과 전체 브라우저 E2E/다른 컴퓨터 재현 및 이번 후속 코드 리뷰가 남았습니다. W2 전체 단계 완료로 표시하지 않습니다. 본인 기여 사실 확인은 사용자님 확인 대기입니다.
