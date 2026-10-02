# W2-D1/D2 — 기관 승인·공개키 QA

담당: D / 여인준님 (`@yijun0330`). W2는 개발 단계이며 고정 주간 마감이 아닙니다.

## 기준과 현재 상태

- 최신 `origin/phase/W2`: `1f8ed632ea9c74091abaf2fe2ec32882038f731f` (PR #33 병합 결과).
- D 작업 branch `feat/w2-d-qa-phase`는 기존 PR #34를 이어가며 최신 `phase/W2`를 merge commit `5f0df0d4caddfc6f1f5ba68aa45466413f6b0a3a`로 반영했습니다. 기존 PR 커밋은 유지했습니다.
- W2-B Writer/Indexer 구현은 PR #26에서, A의 키 화면 준비는 PR #28에서, C의 Operation·기관/키 API는 PR #33에서 `phase/W2`에 병합됐습니다. v2 공통 모델과 생성물도 현재 W2 트리에 포함됩니다.
- W2-D1은 독립 mock/API 회귀를 재실행했습니다. 실제 PostgreSQL·Anvil 경계는 disposable 환경 변수가 없어 미실행입니다. W2-D2 브라우저 신청→체인 승인→키 등록/폐기 전체 흐름은 실제 A 연결이 없어 대기입니다.
- W1의 `phase/W1 → integration`은 초안 PR #39로 열려 있으며 아직 승격되지 않았습니다. W2의 독립 QA 준비·검사가 W1 또는 W2 단계 완료를 뜻하지 않습니다.

## 검증 결과

| 실행 | 결과 | 범위·한계 |
| --- | --- | --- |
| `LLM_PROVIDER=mock OPENAI_MODEL=gpt-6-luna PYTHONPATH=apps/api/src:packages/python:services/analyzer/src:services/indexer/src python -m pytest -q apps/api/tests services/analyzer/tests services/indexer/tests packages/python/tests` | **230 passed, 4 skipped**, warning 1개 | `phase/W2` 코드가 포함된 D branch checkout `5f0df0d`; Python 3.13.7. 네 skip은 live PostgreSQL/Anvil 또는 opt-in local-chain 환경 부재 |
| W2 Operations/ChainManagement와 live test 선택 실행 | **11 passed, 4 skipped** | mock API/DB 경계 통과. live PostgreSQL/Anvil 테스트는 설정 부재로 skip |
| `ruff check apps packages/python services scripts` | 통과 | Python 정적 검사 |
| `python -m compileall -q apps packages services scripts` | 통과 | Python 구문 컴파일 |
| PR #33 Quality Gate | 통과 | W2-C PR의 Python quality와 Contract CI |
| Playwright 기존 W2 키 화면 검사 | 소스 확인 | 현 테스트는 기간 입력·접근성만 확인하고 API 요청을 보내지 않는 것을 검사합니다. 실제 키 흐름 증거가 아닙니다. |

테스트는 이전 독립 Python 3.13.7 환경의 pytest/의존성을 사용했습니다. 현재 PR worktree의 `.env`는 없어서 `.env.example`에서 합성 설정을 만들었습니다. 실제 비밀값은 사용하지 않았습니다. opt-in live test에 필요한 `TEST_DATABASE_URL`, `TEST_CHAIN_RPC_URL`, `TEST_CHAIN_MANIFEST`는 설정하지 않았습니다. DB 볼륨 초기화·운영 배포·유료 모델 호출은 하지 않았습니다.

## D1 사례 — API·체인 경계

| 사례 | F | 독립 실행에서 확인한 것 | 남은 실제 검증 |
| --- | --- | --- | --- |
| W2-D1-01 미활성 기관 키 작업 | F09 | mock API가 체인 비활성 상태에서 키 등록을 거부하는 인접 사례 | 정확한 `PENDING_REVIEW` 계정 흐름과 실체인 상태 불변은 미실행 |
| W2-D1-02 무권한 승인/역할 변조 | F10 | issuer의 활성화 요청과 잘못된 CSRF가 거부됨 | 임의 role/issuer ID 주입과 실제 DB·체인 상태 불변은 미실행 |
| W2-D1-03 타 기관 키 조작 | F05 | mock API에서 다른 issuer가 key 상세/폐기를 요청하면 404 | 실제 인증 세션·DB·Contract의 교차 경계는 미실행 |
| W2-D1-04 중복 등록/요청 충돌 | F12 | 같은 request ID 동시 재시도는 제출 1회·같은 Operation, 다른 입력 재사용은 409; 같은 키 재요청은 새 제출을 만들지 않음 | 다른 request ID로 같은 공개키를 등록하는 실체인 경계는 미실행 |
| W2-D1-05 RPC timeout | F12/F13 | mock Writer의 UNKNOWN 상태와 고정 nonce를 재기동 후 재조회하고 재전송하지 않는 단위 검사 | RPC timeout/receipt 손실을 로컬 EVM에서 재현하지 않음 |
| W2-D1-06 실패 receipt | F13 | mock 실패 receipt에서 Operation FAILED, 기관은 `APPROVED_PENDING_CHAIN`에 유지 | 실제 revert receipt·체인 상태는 미실행 |
| W2-D1-07 미확정 중 재시작 | F13 | Writer 인스턴스 교체 후 같은 nonce 복구, 기존 제출 재전송 없음 | 실제 API 프로세스와 Anvil 재시작은 미실행 |
| W2-D1-08 응답 손실/중복 방지 | F12 | 동시 동일 요청은 단일 제출; DB 확정 기록 실패 후 같은 transaction 복구 | 성공 receipt 이후 클라이언트 HTTP 응답 유실은 live 환경에서 미실행 |

관련 자동 검사는 `apps/api/tests/test_w2_c_operations.py`, `apps/api/tests/test_w2_chain_management.py`입니다. 위 결과는 mock Writer/테스트 DB에서 확인한 동작이며 실제 PostgreSQL·RPC·브라우저 결과로 확대 해석하지 않습니다.

## D2 — 브라우저·clean 환경 재현

현재 `apps/web/app/finals/keys/page.tsx`는 세션/역할과 기간 입력을 확인하지만 키 생성·목록·폐기 API 요청을 보내지 않습니다. W2-C API 계약은 PR #33으로 이미 병합됐지만 화면 문구와 Playwright 테스트 이름은 아직 “API 계약 없음”이라고 설명합니다. API 계약 존재와 화면 연결 완료를 구분해 A 담당자에게 전달할 불일치입니다. 계획서의 신청→운영자 승인→체인 반영→키 등록→폐기→새 세션 재조회는 실제 연결 후 실행해야 합니다. 다른 담당자의 Web/API 경로는 이 QA 작업에서 수정하지 않았습니다.

| 항목 | 상태 |
| --- | --- |
| 운영자 승인/반려·기관 활성화 실제 브라우저 흐름 | `NOT_RUN` — W2-A1 연결 대기 |
| 키 등록·목록·폐기 실제 브라우저 흐름 | `NOT_RUN` — W2-A2 API 연결 대기 |
| 실제 PostgreSQL + Anvil 독립 실패 사례 | `NOT_RUN` — disposable test 환경 미설정 |
| clean 환경 로컬 배포/재현 보고 | `NOT_RUN` — 실제 연결·배포 자료 대기 |

## 후속

- W2-D1 mock/API 실패 동작의 독립 회귀 확인을 완료하고, 실제 DB·체인 검증은 분리해 남겼습니다.
- W2-A1/A2가 C API 및 B Adapter에 연결되면 신청부터 키 폐기까지 새 브라우저 세션으로 재검증합니다.
- disposable PostgreSQL·Anvil 검증 환경을 사용할 수 있을 때 opt-in live tests를 실행하고 이 문서의 `NOT_RUN`을 실제 결과로 갱신합니다.
- 작성자 외 리뷰는 아직 미확인입니다. PR #34의 최신 CI와 담당자 리뷰를 기다립니다.
