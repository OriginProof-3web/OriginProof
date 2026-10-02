# W2 / D / 여인준 — 독립 QA 기록

- GitHub 계정: `@yijun0330` (저장소 역할표 기준)
- 작업일: 2026-10-02. W2는 개발 단계입니다.
- 상태: D1 disposable PostgreSQL·Anvil live/API 회귀 완료; D2 실제 브라우저 흐름은 A 화면 연결 대기
- 작업 ID: W2-D1, W2-D2. PR: [#34](https://github.com/OriginProof-3web/OriginProof/pull/34)
- 기준: `origin/phase/W2` `1f8ed632ea9c74091abaf2fe2ec32882038f731f`
- 검증 checkout: `feat/w2-d-qa-phase`; 기존 PR 작업을 보존하고 최신 phase/W2를 merge

## 목표와 실제 결과

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

Codex가 최신 phase/W2와 기존 PR 변경을 대조하고, 격리된 로컬 DB/Anvil에서 opt-in 검사를 실행했으며 실제/mock/미실행 범위를 기록했습니다. 작성자 외 리뷰는 아직 받지 않았습니다. 이 D1 결과는 W2 전체 단계 완료 판정이 아닙니다.

다음: A1/A2 UI 연결 후 새 브라우저 세션으로 실제 승인 및 키 lifecycle을 검증하고, API/Anvil 프로세스 재시작 등 표에 남긴 D1 경계도 보완합니다.
