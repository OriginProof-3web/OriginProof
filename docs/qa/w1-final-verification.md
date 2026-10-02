# W1 최종 연결 검증과 승격 준비

- 담당: D / `@yijun0330`, 사용자 요청에 따라 Codex가 검사·검토·기록을 수행했습니다.
- 검증일: 2026-10-02 (Asia/Seoul). W1은 개발 단계입니다.
- 공식 기준: `phase/W1@0308cb24f9e4aed157095131e2552243767d16eb`.
- 수정·검증 후보: `f1de961d8f94405d5a143cd853421eee8878b4f1`.
- 후속 문서 커밋은 이 후보의 제품·검사 소스를 변경하지 않습니다. phase에 병합된 최종 SHA의 확인은 별도입니다.
- 승격 초안: [PR #39](https://github.com/OriginProof-3web/OriginProof/pull/39). 이 보고는 integration 승격을 실행한 기록이 아닙니다.

## 실제 연결 결과

기존 PostgreSQL/Compose DB를 사용하지 않고 새 tmpfs PostgreSQL에 공식 W1 migration 0001~0002만 적용했습니다. API와 웹도 별도 loopback 포트에서 같은 checkout으로 실행했습니다. 운영자·두 기관·수신자와 자기 승인 공격용 계정을 매 실행마다 새로 만들고 테스트 행을 정리했습니다. 개인 비밀값은 사용하지 않았습니다.

| W1 사례 | 기대 결과 | 실제 결과 |
| --- | --- | --- |
| 익명·수신자·issuer의 운영자 신청 경로 | 각각 401/403, 권한을 얻지 못함 | PASS, 실제 HTTP |
| login의 role 주입·신청의 issuer_id 주입 | extra 입력 422 | PASS, 실제 HTTP |
| CSRF 없는 신청 | 403, 신청 미생성 | PASS, 실제 HTTP |
| issuer A/B 신청과 본인 조회 | 자기 기관만 조회, 두 계정 격리 | PASS, 실제 브라우저·API·PostgreSQL |
| 운영자 승인·반려·사유 | A는 APPROVED_PENDING_CHAIN, B는 REJECTED | PASS, 실제 브라우저·DB |
| issuer 승인 시도·본인 신청 승인·중복 결정 | 403/403/409, 기존 상태 유지 | PASS, 실제 API 및 자기 승인 오류 화면 |
| 새로고침·logout·재로그인 | 정책대로 세션 복원/폐기, 저장된 결정 재조회 | PASS, 실제 Chromium |
| 8시간 cookie·만료 세션 | HttpOnly/SameSite=Lax/Max-Age=28800, 만료 DB session 401 | PASS; OS 시간을 바꾸지 않고 해당 합성 session expiry만 변경 |
| 결정 이력 | 성공한 승인/반려 AuditEvent 두 행 | PASS, 실제 PostgreSQL; W1에는 감사 조회 endpoint가 없음 |
| 승인 후 기관 상태 표시 | 체인 활성화 대기, 등록 성공으로 오인하지 않음 | PASS, [합성 승인 화면](../portfolio/assets/W1/live-approved.png) |
| 로그인·운영자 승인·issuer 승인 화면 접근성 | axe violation 0 | PASS, 수정 후보에서 재검증 |

API 소스는 공식 W1과 동일합니다. 첫 기준 검사에서 승인 화면의 `<dl>`에 `<p>`가 직접 들어 있어 axe `definition-list` serious 오류가 재현됐습니다. `ApplicationSummary`에서 같은 문구를 `<dl>` 밖으로 옮겨 수정했습니다. 다음 실패는 새 테스트 선택자가 Next의 route announcer까지 선택한 문제였으며, 실제 오류 문구로 선택자를 한정했습니다. 후보 SHA에서 전체 live 흐름을 다시 통과했습니다.

## 실행 검사

| 명령·범위 | 실제 결과 |
| --- | --- |
| `make bootstrap-check`, `make env-fingerprint` | 통과, [후보 환경 기록](w1-final-environment.json) |
| `python -m pytest -q apps/api/tests packages/python/tests services/analyzer/tests services/indexer/tests scripts/ci` | 220 passed, 1 skipped (Indexer 별도 live opt-in), 기존 deprecation warning 1개 |
| `make mvp-test` | API 10, Analyzer 130, Foundry 컨테이너 Contract 10, 통합 Python 140 통과 |
| `ruff check apps packages/python services scripts fixtures/finals/build_cases.py`, Python compileall | 통과 |
| 웹 `lint`, `typecheck`, `test` | 통과, component 6 tests |
| 웹 `test:e2e` (기존 route mock) | 4 passed, 신규 live opt-in 1 skipped |
| `scripts/ci/w1_live_qa.py` (실제 API·DB·웹) | Chromium 1 passed 및 추가 DB/세션 검사 PASS; 후보 SHA에서 재실행 |
| 웹 `build` | 통과; dev 서버 종료 후 순차 실행 |
| 생성 계약 재생성 | 9 JSON Schemas + TypeScript + v2 Golden 2개가 tracked 파일과 byte 일치 |
| Foundry `cast keccak` | 두 v2 signing digest와 각 proof/issuer/key ID hash가 Python과 일치 |
| 두 Golden의 생성 TypeScript 계약 소비 | 컴파일 통과 |
| D 합성 자료·v2 모델 관련 검사 | 39 passed; 모든 unsigned profile이 C 모델의 필드 규칙과 일치 |

넓은 회귀 일부는 코드 커밋 직전의 동일 소스 트리에서 실행했고, commit 뒤 후보 `f1de961`의 실제 브라우저/DB 검사와 fingerprint를 다시 확인했습니다. Node는 임시 설치한 22.18.0, Python 3.13.7, pnpm 11.19.0입니다. pnpm 11의 자동 dependency 재설치는 실행별 환경변수 `pnpm_config_verify_deps_before_run=false`로 끄고 기존 lockfile 의존성을 재사용했습니다. Python 의존성은 Makefile의 uv 명령으로 확인했습니다.

`make mvp-e2e`의 공식 기준 SHA 기존 HTTP 회귀는 PR #39에 이미 기록돼 있습니다. 이번 HTML·QA 자료 수정은 기존 MVP API/Contract를 변경하지 않아 기존 Compose 환경에 migration/seed를 반복하지 않았습니다. 호스트 forge가 없어도 Foundry 컨테이너 검사를 실행했습니다. 기존 autoprefixer/Next/Playwright 환경 경고는 테스트 실패와 구분했습니다. 유료 모델·운영 배포는 수행하지 않았습니다.

## 재현

서비스를 별도 폐기 가능한 환경에 준비한 뒤 다음 명령을 사용합니다. 개인 DB를 지정하지 않습니다. account/password는 runner가 메모리에서 만들며 명령·화면·Git에 저장하지 않습니다.

```sh
# 임시 PostgreSQL에 W1 migration만 적용하고 API를 시작합니다.
API_DATABASE_URL="$TEST_DATABASE_URL" PYTHONPATH=apps/api/src:packages/python \
  .uv-venv/bin/python -m alembic -c apps/api/alembic.ini upgrade head
API_DATABASE_URL="$TEST_DATABASE_URL" API_BLOCKCHAIN_RPC_URL='' API_BLOCKCHAIN_MANIFEST_PATH='' \
  PYTHONPATH=apps/api/src:packages/python .uv-venv/bin/python -m uvicorn \
  originproof_api.main:app --host 127.0.0.1 --port 18081

# 별도 terminal: 같은 SHA의 웹, Node 22.18.0
ORIGINPROOF_API_ORIGIN=http://127.0.0.1:18081 \
  pnpm --filter originproof-demo-web dev --hostname 127.0.0.1 --port 13000

# 별도 terminal: TEST_DATABASE_URL은 해당 임시 DB의 asyncpg URL
W1_QA_DISPOSABLE=1 W1_LIVE_API_URL=http://127.0.0.1:18081 \
  W1_LIVE_BASE_URL=http://127.0.0.1:13000 \
  PYTHONPATH=apps/api/src:packages/python .uv-venv/bin/python scripts/ci/w1_live_qa.py
```

검사 대상 DB/API/웹 주소를 명시했습니다. runner는 합성 계정·관련 신청·세션·이력만 정리합니다. 이번 실행에서는 임시 API/웹을 종료하고 `--rm` tmpfs PostgreSQL도 제거했습니다. 기존 `originproof-*` 서비스 6개는 유지됐습니다.

## 계약·소비자 검토와 남은 사람의 확인

- C 모델/API 구현을 ADR 및 B 계약과 대조했습니다. [PR #23 D 사후 리뷰](https://github.com/OriginProof-3web/OriginProof/pull/23#pullrequestreview-5389645883), [PR #32 D 사후 리뷰](https://github.com/OriginProof-3web/OriginProof/pull/32#pullrequestreview-5389642581)는 실제 `yijun0330` 계정의 승인 리뷰입니다. Codex 수행임을 명시했고 과거 병합 전 승인으로 소급하지 않습니다.
- B/C 기술 경계는 ID keccak 변환, digest/binding 입력, 발행 시각의 키 기간, lifecycle 우선순위, receipt 이전 대기 상태, gateway 책임을 확인했습니다. B의 설계 문서가 언급하는 W4 Proof ABI는 현재 W1 ABI로 취급하지 않았습니다.
- A의 W1 route/field/오류와 C API는 실제 연결로 확인했습니다. 새 v2 TypeScript의 두 유형 소비는 컴파일 검사이며 W3 발행 UI가 구현됐다는 뜻이 아닙니다.
- D profile은 C 모델 전체 필드 검사로 대응했습니다. v2 nonce 부적합을 fixture version 1.1.0에서 수정했습니다. [자료 설명](../../fixtures/finals/README.md)을 참조합니다.
- A/B/C 소유자 본인의 계약·기여 사실 확인과 새 변경 PR의 작성자 외 최종 승인은 아직 받지 않았습니다. 이 보고를 그 확인으로 대체하지 않습니다.

## W1 범위와 승격 조건

[범위 처리 기록](w1-scope-and-reviews.md)은 이미 승인·병합된 W2 선행 구현을 보존하고 단계별 수용 증거를 구분합니다. Proof 발행/소비·실제 키 등록·전체 현재 lifecycle은 W1 완료 요건에 추가하지 않았습니다. F01~F15의 전체 본선 사례는 여전히 후속 단계 검사를 포함합니다.

새 수정·기록 PR을 phase/W1에 반영하고 최종 phase SHA를 확인한 뒤 PR #39 검증을 갱신해야 합니다. 새 PR의 외부 리뷰 및 A/B/C 기여 확인 전에는 W1 단계 완료 또는 integration 승격 완료를 선언하지 않습니다.
