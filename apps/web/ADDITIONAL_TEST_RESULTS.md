# 협업 코드 추가 검사 · 2026-10-02

## 검사 기준

GitHub fetch 후 확인한 고정 SHA를 git archive로 별도 디렉터리에 추출했습니다. 팀원 브랜치를 checkout/merge하지 않았고, 소유자의 제품 구현을 수정하지 않았습니다. 각 스냅샷의 uv.lock을 frozen으로 설치했습니다. AI provider는 mock이며 유료 호출은 없었습니다.

자체 웹 작업은 codex/w3-a-official-web, HEAD 1f8ed632ea9c74091abaf2fe2ec32882038f731f + 기존 미커밋 W3 변경입니다. 기존 디자인과 사용자 변경을 보존했습니다. PR 생성·push·병합은 하지 않았습니다.

## 이번에 직접 실행한 결과

| 대상 | SHA | Python 통과 / 미실행 / 실패 |
| --- | --- | --- |
| C [PR #42](https://github.com/OriginProof-3web/OriginProof/pull/42), 등록·폐기·single-use | 8e57159efed4f3d435ab617b74952b2bbb970ec7 | 269 / 5 / 0 |
| B W6 브랜치, W4·W5 선행 포함 | 3d7c4e73e49229150223a008e73e0769196e4b37 | 265 / 5 / 0 |
| D [PR #41](https://github.com/OriginProof-3web/OriginProof/pull/41), W1 QA 보완 | 94488b13d80df991bc5b861d1d4d44da267355ee | 220 / 1 / 0 |
| D W2 QA phase 브랜치 | e776b7328d016e8f4e1abaf77dae0410fac2d61b | 231 / 4 / 0 |
| C [PR #37](https://github.com/OriginProof-3web/OriginProof/pull/37), W5 권한·요청 보호 draft | b6d7d678f65aac31fac9f031c9ec0e625b629173 | 270 / 5 / 0 |
| C [PR #38](https://github.com/OriginProof-3web/OriginProof/pull/38), W6 세션·서명기 draft | b70bfb93c5c0b5d175925139c5892d62ab0ffed0 | 288 / 5 / 0 |

명령: `PYTHONPATH=apps/api/src:packages/python:services/analyzer/src:services/indexer/src uv run --frozen --all-packages --all-groups pytest -q --tb=short apps/api/tests packages/python/tests services/analyzer/tests services/indexer/tests scripts/ci --junitxml=additional.xml`.
여러 브랜치에서 같은 회귀 사례를 반복하므로 통과 건수를 고유 사례 총수로 합산하지 않습니다.

| 실제 연결·추가 검사 | 결과 | 범위 |
| --- | --- | --- |
| C #42 PostgreSQL 16.4 + Anvil | 1 passed / 0 skipped | 두 유형 등록·정상/변조 비교·키 교체/폐기·기관 중지/복귀·Proof 폐기/만료·동시 consume·동일 tx 복구·RPC 장애 |
| C #42 migration / alembic check | 통과 | 새 임시 DB 0001→0005, 새 schema 변경 없음 |
| B W6 Anvil | 2 passed / 0 skipped | 실제 Reader/Writer·로그·checkpoint, 재배포 후 이전 manifest 거부와 복구 |
| B W6 Foundry | 22 passed / 0 failed | Registry·권한·기간·single-use·서명 경계 |
| 현재 공식 웹 Chromium | 10 passed / 0 skipped, 8.9초 | 기존 화면/mock 회귀 8개 + 실제 API 2개. 두 유형 발행·공개 조회·수신자 비교·변조·기관 분리·모바일/사이드바 |
| B W6 uv audit --frozen | **실패, exit 1** | Starlette 0.46.2 경고 14건, pytest 8.4.2 경고 2건. 중복 식별자를 포함하므로 별개 취약점 16개로 단정하지 않음 |

임시 DB 컨테이너 originproof-additional-c42-postgres(55433)와 임시 Anvil(18546)만 만들고 검사 종료 후 삭제/종료했습니다. 기존 55432/18545/8770/8768 환경을 reset/migration/재배포하지 않았습니다. C #42 실제 API 검사는 HTTP ASGI transport + 실제 PostgreSQL/Anvil이며 브라우저 검사는 아닙니다.

## 이전에 직접 실행한 결과

기존 관리자 화면의 collaboration-results.json과 W3_VALIDATION.md를 확인했습니다.

| 대상 | 결과 | 범위 |
| --- | --- | --- |
| C #35 17c24a3 | 26 passed / 4 skipped | API 독립 검사 |
| B #40 92e0e94 | 78 passed / 1 skipped | Indexer/Adapter 독립 검사 |
| C #36 85e152c | 33 passed / 0 skipped | PostgreSQL/Anvil API·키 교체 |
| 기존 웹 프록시 연결 | 14 passed | 인증·CSRF·역할·발행·비교·공개 범위 |
| 공식 W3 웹 component | 15 passed | 입력·422·중복 클릭·재시도 ID·범위 표시 |
| 공식 W3 lint/typecheck/build | 통과 | 기존 build autoprefixer end 경고 남음 |
| 공식 W3 browser 이전 검사 | 10 passed | 이번에 동일 대상을 재실행해 10 passed |

## 미완료·다음 담당자

- A/김형준: 공식 웹은 C #36 API 연결 상태입니다. C #42의 등록 대기·복구·폐기·single-use 화면 연결과 브라우저 실패/경쟁 검사는 남아 있습니다. 이번 backend 검사 통과는 웹 연결 완료를 뜻하지 않습니다.
- C/공유 의존성 담당자: audit의 Starlette/pytest 경고별 해당 경로·영향을 평가하고 호환 버전으로 업데이트 후 재검사가 필요합니다. 이번에 lockfile/API를 임의 수정하지 않았습니다.
- C/B: #37/#38은 아직 #42를 포함하지 않는 선행 계열입니다. W4 결과 통합 후 보안·복구 검사를 다시 실행해야 합니다.
- D/경로 소유자: #41의 새 W1 live browser runner는 이번에 실행하지 않았습니다. 독립 Python 통과와 작성자의 브라우저 증거를 구분합니다. 다른 opt-in 미실행 사례는 각 XML에 기록했습니다.
- B W4 58e819e와 W5 b7a4107은 W6 스냅샷의 선행으로 포함돼 검사됐습니다. 각 단독 SHA의 전체 검사를 이번에 반복한 결과는 아닙니다.
- 작성자 외 리뷰·phase 반영·팀 전체 단계 완료 판정은 남아 있습니다. AI 유료 provider·QR·LAN 휴대폰 스캔은 이번 검사에 포함하지 않습니다.

## 증거와 재현

qa/2026-10-02/summary.json, 각 SHA의 JUnit XML, live XML, Foundry 결과, audit 결과, browser 로그를 저장했습니다. Python 3.13.15, pytest 8.4.2, Forge/Anvil 1.4.4, macOS입니다. 기존 웹 fingerprint·환경은 W3_VALIDATION.md에 기록돼 있습니다.

B live: `M4_LIVE_TEST=1 W6_LIVE_TEST=1 uv run --frozen --all-packages --all-groups pytest services/indexer/tests/test_live_chain.py services/indexer/tests/test_chain_restart.py`. 테스트가 새 임시 Anvil을 직접 기동·종료합니다.

C live: 폐기 가능한 새 PostgreSQL/Anvil에서 migration·deploy_local.py 실행 후 TEST_DATABASE_URL/TEST_CHAIN_RPC_URL/TEST_CHAIN_MANIFEST를 지정해 `pytest apps/api/tests/test_live_finals.py`를 실행했습니다. 보존 DB/체인에 실행하면 안 됩니다.

웹: `ORIGINPROOF_TEST_ACCOUNTS=로컬_합성_계정파일 pnpm --filter originproof-demo-web test:e2e`. 비밀번호는 보고서/로그에 기록하지 않았으며 live context의 trace/video/screenshot은 비활성화했습니다. 기능 검사는 reducedMotion=reduce로 실행해 모든 GPU의 애니메이션 성능 검사와 구분합니다.
