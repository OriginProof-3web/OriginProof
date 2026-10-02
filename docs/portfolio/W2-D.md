# W2 / D / 여인준 — 독립 QA 기록

- GitHub 계정: `@yijun0330` (저장소 역할표 기준)
- 작업일: 2026-10-02. W2는 개발 단계입니다.
- 상태: 부분 완료 — mock/API 독립 회귀 재실행, live DB·Anvil 및 실제 브라우저 연결 대기
- 작업 ID: W2-D1, W2-D2. PR: [#34](https://github.com/OriginProof-3web/OriginProof/pull/34)
- 기준: `origin/phase/W2` `1f8ed632ea9c74091abaf2fe2ec32882038f731f`
- 검증 checkout: `feat/w2-d-qa-phase` `5f0df0d4caddfc6f1f5ba68aa45466413f6b0a3a` (기존 PR 작업을 보존하고 최신 phase/W2를 merge)

## 목표와 실제 결과

독립적으로 재실행할 수 있는 W2 API·Writer 실패/권한 경계를 확인하고, 실제 E2E와 mock 검증을 구분했습니다. 최신 W2 코드의 Python 회귀 **230 passed, 4 skipped**, Ruff와 compileall이 통과했습니다. live PostgreSQL/Anvil 사례는 해당 disposable 환경 변수가 없어 실행하지 않았고, 실제 브라우저 키 관리 연결도 아직 없습니다.

| 작업 | 실제 수행 | 상태 |
| --- | --- | --- |
| W2-D1 | W2 Operations·ChainManagement 및 전체 API/Analyzer/Indexer/core pytest 재실행, 실패 receipt·무권한·cross-issuer·idempotency·UNKNOWN 복구 mock 사례를 근거와 대조 | mock/API 범위 부분 완료; 실체인·PostgreSQL 경계 대기 |
| W2-D2 | 실제 화면과 Playwright 테스트 경로 확인 | 대기: 현 키 화면은 API를 호출하지 않으며 운영 승인→체인→키 등록/폐기 연결 E2E 불가 |

상세 사례와 명령은 [W2-D 검증표](../qa/w2-d-acceptance.md)에 기록했습니다. 테스트는 `phase/W2`의 B/C 구현을 재사용했으며 제품·API·Contract 코드는 수정하지 않았습니다.

## 검증·한계

- `pytest -q apps/api/tests services/analyzer/tests services/indexer/tests packages/python/tests`: 230 passed, 4 skipped, deprecation warning 1개.
- `ruff check apps packages/python services scripts`: 통과.
- `python -m compileall -q apps packages services scripts`: 통과.
- live PostgreSQL/Anvil 검사는 `TEST_DATABASE_URL`, `TEST_CHAIN_RPC_URL`, `TEST_CHAIN_MANIFEST` 미설정으로 skip.
- W2-D2 실제 브라우저 E2E는 A 화면의 실제 API 연결 전까지 수행 불가.
- 개인 `.env`는 원본 작업 저장소에 없었으며, 임시 PR worktree에 `.env.example` 기반 합성 설정만 만들었습니다. 비밀값·실제 기관자료·유료 모델을 사용하지 않았습니다.

## AI 활용·다음 작업

Codex가 최신 phase/W2와 기존 PR을 대조하고 검사를 실행했으며, 실제/mock/미실행 범위를 문서화했습니다. 사용자가 D 역할 W2 진행을 요청했습니다. 작성자 외 리뷰는 아직 받지 않았습니다.

다음: A1/A2 실제 UI 연결과 disposable DB/Anvil 제공 후 D1/D2의 실체인·브라우저 재현을 실행하고 실패 증거를 갱신합니다. 이 기록은 W2 단계 완료 판정이 아닙니다.
