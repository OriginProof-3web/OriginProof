# W2-D1/D2 — 기관 승인·공개키 QA

담당: D / 여인준님 (`@yijun0330`). W2는 개발 단계이며 고정 주간 마감이 아닙니다.

## 기준과 현재 상태

- 최신 확인 `origin/phase/W2`: `812265b285b218e004a08b632ac3aa36125add21` (PR #34 병합 결과).
- **후속 최신 검사:** [실제 프로세스 재시작·RPC 장애 보고](w2-d-recovery.md). 아래 수치와 D1 표는 PR #34 당시 기록이며, 후속에서 해소한 항목은 해당 보고를 우선합니다.
- PR #34 당시 D 작업 branch `feat/w2-d-qa-phase`는 `phase/W2`를 merge commit `5f0df0d4caddfc6f1f5ba68aa45466413f6b0a3a`로 반영했습니다. 새 후속 branch는 `test/w2-d-recovery-qa`이며 기존 branch·커밋은 유지했습니다.
- W2-B Writer/Indexer 구현은 PR #26에서, A의 키 화면 준비는 PR #28에서, C의 Operation·기관/키 API는 PR #33에서 `phase/W2`에 병합됐습니다. v2 공통 모델과 생성물도 현재 W2 트리에 포함됩니다.
- D1 API·PostgreSQL·Anvil live 검증과 전체 Python 회귀를 disposable 환경에서 실행했습니다. D2 브라우저 신청→체인 승인→키 등록/폐기 전체 흐름은 실제 A 화면 연결을 기다리고 있습니다.
- W1의 `phase/W1 → integration`은 초안 PR #39로 열려 있으며 아직 승격되지 않았습니다. W2의 독립 QA 준비·검사가 W1 또는 W2 단계 완료를 뜻하지 않습니다.

## PR #34 당시 검증 결과

| 실행 | 결과 | 범위·한계 |
| --- | --- | --- |
| 전체 Python 회귀: `LLM_PROVIDER=mock OPENAI_MODEL=gpt-6-luna PYTHONPATH=apps/api/src:packages/python:services/analyzer/src:services/indexer/src python -m pytest -q apps/api/tests services/analyzer/tests services/indexer/tests packages/python/tests` + disposable DB/Anvil 환경변수 | **233 passed, 1 skipped**, warning 1개 | W2 D branch checkout. skip 1건은 별도 Indexer local-EVM opt-in 검사 (`services/indexer/tests/test_live_chain.py`) |
| `apps/api/tests/test_live_w1_w2.py apps/api/tests/test_live_w2_chain.py` + disposable DB/Anvil 환경변수 | **3 passed** | 실제 PostgreSQL 로그인·신청·승인 대기 상태·operation 격리·advisory lock과 Anvil 계약 실제 제출/receipt·키 흐름 |
| 사전 mock/offline 전체 회귀 | **230 passed, 4 skipped**, warning 1개 | live 환경변수를 주기 전 기준 결과. 4건은 DB/Anvil 및 local-chain opt-in 검사 |
| `ruff check apps packages/python services scripts` | 통과 | Python 정적 검사 |
| `python -m compileall -q apps packages services scripts` | 통과 | Python 구문 컴파일 |
| `git diff --check` | 통과 | 문서 변경 공백 검사 |
| PR #33 Quality Gate | 통과 | W2-C PR의 Python quality와 Contract CI |
| Playwright 기존 W2 키 화면 검사 | 소스 확인 | 현 테스트는 기간 입력·접근성만 확인합니다. 실제 API·키 흐름을 검증하지 않습니다. |

실제 검사는 임시 PostgreSQL 컨테이너(tmpfs 데이터 디렉터리)와 임시 Anvil 컨테이너/전용 Docker 네트워크를 사용했습니다. W2 Contract를 Anvil에 배포하고 `TEST_DATABASE_URL`, `TEST_CHAIN_RPC_URL`, `TEST_CHAIN_MANIFEST`만 해당 폐기 가능한 환경에 지정했습니다. 검사가 끝난 뒤 컨테이너와 네트워크를 제거했습니다. 기존 `originproof` Compose 서비스나 DB 볼륨은 사용·초기화하지 않았습니다. PR worktree에는 `.env.example`에서 만든 합성 `.env`만 두었으며 개인 비밀값은 사용하거나 출력하지 않았습니다. DB 초기화, 운영 배포, 유료 모델 호출은 하지 않았습니다.

## D1 사례 — API·체인 경계

| 사례 | F | 실환경에서 확인한 것 | 남은 검증 |
| --- | --- | --- | --- |
| W2-D1-01 미활성 기관 키 작업 | F09 | 실 DB에서 신청은 `PENDING_REVIEW`, 운영자 승인 뒤 `APPROVED_PENDING_CHAIN`; Anvil 활성화 후에야 키 등록. 기관 suspend 뒤 키 작업 거부 | 반려 경로와 별도 계정의 정확한 `PENDING_REVIEW` 키 요청 거부는 미검증 |
| W2-D1-02 무권한 승인/역할 변조 | F10 | 실제 API에서 CSRF 없는 신청 거부, issuer의 운영자 suspend 거부, 타 issuer 경계 확인 | 임의 role/issuer ID 주입은 이 요청 계약에 입력 필드가 없어 미검증 |
| W2-D1-03 타 기관 키 조작 | F05 | 실제 issuer A 키에 issuer B가 상세/폐기를 요청하면 둘 다 404 | 추가적인 악의적 payload fuzz는 미검증 |
| W2-D1-04 중복 등록/요청 충돌 | F12 | 동시 activation 동일 request ID는 한 Operation/한 제출로 합쳐짐; 바뀐 입력과 같은 ID는 409. 같은 키 요청 ID 재사용은 같은 Operation | 다른 request ID로 같은 공개키를 별도 등록하는 경계는 개별 검증하지 않음 |
| W2-D1-05 RPC timeout/UNKNOWN | F12/F13 | 실제 activation 제출 뒤 응답 hash를 감춘 UNKNOWN을 만들고 manager 재구성 후 저장 nonce로 같은 거래를 복구, 재제출 없이 confirmed receipt 확인 | RPC 연결 timeout/receipt 조회 불능을 별도로 주입하지 않음 |
| W2-D1-06 실패 receipt | F13 | 이미 폐기한 키의 별도 두 번째 revoke가 Anvil에서 revert되고 Operation은 `FAILED`/`CHAIN_REVERTED`로 응답 | 다른 종류의 revert reason은 미검증 |
| W2-D1-07 미확정 중 재시작 | F13 | 같은 프로세스에서 `ChainManagement` 인스턴스를 재구성해 nonce 기반 복구 확인 | API 프로세스와 Anvil 프로세스 자체를 종료·재기동하는 검사는 미실행 |
| W2-D1-08 응답 손실/중복 방지 | F12 | 제출 hash 손실 후 UNKNOWN 복구 및 동일 요청 중복 방지를 확인 | 확정 응답이 서버에서 성공한 뒤 클라이언트 HTTP 응답만 유실되는 별도 시나리오는 미검증 |

관련 자동 검사는 `apps/api/tests/test_live_w1_w2.py`, `apps/api/tests/test_live_w2_chain.py`, `apps/api/tests/test_w2_c_operations.py`, `apps/api/tests/test_w2_chain_management.py`입니다. 실환경 live 검사는 PostgreSQL·Anvil 경계에 한해 실제로 통과했습니다. 위 미검증 항목을 완료된 것으로 간주하지 않습니다.

## D2 — 브라우저·clean 환경 재현

현재 `apps/web/app/finals/keys/page.tsx`는 세션/역할과 기간 입력을 확인하지만 키 생성·목록·폐기 API 요청을 보내지 않습니다. W2-C API 계약은 PR #33으로 이미 병합됐지만 화면 문구와 Playwright 테스트 이름은 아직 “API 계약 없음”이라고 설명합니다. API 계약 존재와 화면 연결 완료를 구분해 A 담당자에게 전달할 불일치입니다. 계획서의 신청→운영자 승인→체인 반영→키 등록→폐기→새 세션 재조회는 실제 연결 후 실행해야 합니다. 다른 담당자의 Web/API 경로는 이 QA 작업에서 수정하지 않았습니다.

| 항목 | 상태 |
| --- | --- |
| 운영자 승인/반려·기관 활성화 실제 브라우저 흐름 | `NOT_RUN` — W2-A1 연결 대기 |
| 키 등록·목록·폐기 실제 브라우저 흐름 | `NOT_RUN` — W2-A2 화면 API 연결 대기 |
| PostgreSQL + Anvil 독립 D1 실패 사례 | [후속 보고](w2-d-recovery.md): 실제 프로세스 재시작·RPC 장애·응답 유실·승인/반려 경계 추가 통과 |
| clean 환경 브라우저 배포/재현 보고 | `NOT_RUN` — 실제 UI 연결 자료 대기 |

## 후속

- W2-D1 disposable PostgreSQL·Anvil live 검증과 전체 Python 회귀를 완료했고 위 표에 검증 경계와 제한을 기록했습니다.
- W2-A1/A2가 C API 및 B Adapter에 연결되면 신청부터 키 폐기까지 새 브라우저 세션으로 재검증합니다.
- 실제 프로세스 재시작, RPC 장애 주입, 승인/반려 키 거부·역할/기관 주입 및 HTTP 응답 유실은 [후속 QA](w2-d-recovery.md)에서 실제 검사했습니다. 과거 표의 미검증 상태와 구분합니다.
- PR #34는 [C의 승인](https://github.com/OriginProof-3web/OriginProof/pull/34#pullrequestreview-5389403389) 뒤 병합됐습니다. 이 승인은 기존 문서·CI 범위이며 새 후속 QA 코드는 별도 C 리뷰 대기입니다.
