# Analyzer 추출 안전성 보강 — D 검사 기록

- 담당: 여인준님 `@yijun0330` (D), 작업일 2026-10-02.
- 요청: 사용자가 전달한 AI Extraction Safety Review 문서의 D 소유 범위.
  기존 카드 추출의 추가 안전성 보강이며 W3 두 유형 구현이나 W5 P1 채택/완료로 집계하지 않습니다.
- branch: `feat/d-ai-extraction-safety`, PR 대상 `phase/W3`.
- 시작 기준: `1f8ed632ea9c74091abaf2fe2ec32882038f731f`.
- 검토 기준: C `8e57159efed4f3d435ab617b74952b2bbb970ec7`.
  fetch 뒤 해당 SHA가 최신임을 확인했으며 Analyzer/v1 verifier 차이가 없었습니다.
- **검증 코드 SHA: `5dd7e701b8ba7e3261b30c583feb616b91390097`.**
  이후 README·인계·검사 문서만 추가합니다. 최종 PR head는 코드 검증 SHA와 구분합니다.
- 환경: [fingerprint](analyzer-extraction-safety-environment.json), Python 3.13.7,
  Node 22.18.0, uv 0.8.17, pnpm 11.19.0, Docker 29.7.2, Compose v5.5.1.
- 실제 모델 평가·A/C 확인 연결·외부 리뷰는 **대기**입니다. 전체 AI 흐름 완료가 아닙니다.

## 변경과 호환성

1. 기존 성공 JSON 10개 필드·nullable 규칙·오류 코드·HTTP 상태를 유지하고, Analyzer의
   성공 응답과 OpenAPI에 출처/확인 필요/비교 미수행/누락된 보호 필드 헤더를 추가했습니다.
2. `CardPaymentNotice.model_fields`에서 비교 필드를 읽으므로 D가 공유 모델을 복제하지 않습니다.
   null 필드는 계속 후보로 반환하며 `none`이 올바른 추출 또는 전체 원문 일치를 뜻하지 않습니다.
3. Prompt v4는 상충·모호한 필드의 null, 날짜 모호성, confidence와 근거의 차이를 명시합니다.
   v3 파일은 보존했고 Mock 템플릿 파서·기본 mock/gpt-6-luna 설정·timeout/retry는 바꾸지 않았습니다.
4. Mock 평가 결과에도 미확인 후보·비교 미수행 상태를 명시했습니다.
5. [합성 오추출 6건](../../fixtures/mvp/analyzer_safety_cases.json)을 constructor-only 테스트 provider와
   SDK MockTransport로 주입했습니다. HTTP 요청으로 예상값/오류를 주입하는 기능은 추가하지 않았습니다.

**헤더는 소비자에게 상태를 알리며 확인을 강제하지 않습니다.** schema-valid hallucination을
grounding으로 탐지하는 기능은 이번에 추가하지 않았습니다. 잘못된 값도 후보로 반환될 수 있고,
현재 v1 verifier의 null 건너뛰기와 `TAMPERED` 의미는 보존했습니다. 이 차이를 숨기지 않고
[A/C 확인·정정·비교 계약 인계안](../handoffs/analyzer-confirmation-contract.md)에 기록했습니다.
공통 모델·생성 Schema/TypeScript·v1 API·Golden·웹·Contract는 변경하지 않았습니다.
신규 헤더 소비와 새 비교 계약은 C/A의 소유자 리뷰가 필요합니다.

## 사례와 실제 결과

| 요구 사례 | 검사·관찰 결과 | 완료 범위 |
| --- | --- | --- |
| 필수 필드 각각 null | 7개 payload 필드 각각을 헤더에 표시; 확인 필요/비교 미수행 유지 | D 응답 검사 완료; C 전체 비교 보류 처리 대기 |
| 모두 null 후보 | v1 실제 코어가 `VERIFIED`, candidate_match=PASS를 반환하는 공백 재현 | 기존 동작 진단; 안전한 전체 비교 통과로 집계하지 않음 |
| ID-only | 모든 payload 필드 누락, 자료 비교 미수행. 기존 v1은 출처·범위를 분리하지 않음 | D 표시 완료; C/A 별도 scope 결과·표현 대기 |
| invented Proof ID·transaction ID | confidence=0.999에도 미확인 후보; 실제 v1 비교는 FIELD_MISMATCH | Mock/SDK replay·결정론적 비교 확인; 실제 환각률 아님 |
| 잘못된 금액·통화·가맹점 | 고신뢰 후보에 동일 확인 헤더; core는 AMOUNT_MISMATCH/FIELD_MISMATCH | 위와 동일 |
| 모호한 날짜 | 03/09/2026의 잘못된 ISO 후보를 주입, 확인 필요 유지; v4 instructions 전달 검사 | 실제 모델의 날짜 처리 성능은 미평가 |
| 차이 + 다른 필드 누락 | 금액 차이와 currency=null이 동시에 있어도 기존 core는 AMOUNT_MISMATCH 반환 | 실제 차이 우선순위 회귀 보존 |
| AI 유래 차이의 원인 | 기존 core는 TAMPERED를 반환하며 서명/Registry 검사 전 조기 반환함을 검사 | 원인 확정 표현 금지 인계; A 실제 화면 수정 대기 |
| 악성 지시 | Mock는 입력 명령을 수행하지 않음; SDK 요청의 artifact는 user data, v4 instructions는 별도 | Mock/요청 구조 검사; 실제 모델 저항성 증거 아님 |
| 이미지 후보 | 유효한 합성 PNG에 잘못된 고신뢰 후보 주입, 동일 확인/미수행 헤더 | 이미지 grounding/실제 vision 평가 미실행 |
| 명시적 추출 실패 | refusal/incomplete/잘못된 structured output/timeout/rate limit/low-confidence/불가 provider 기존 검사 통과 | 오류 계약 보존 |
| 기존 카드 정상·금액 변조·서명 Golden | 실제 core + in-memory ports; VERIFIED + ACTIVE / TAMPERED + AMOUNT_MISMATCH | v1 회귀·Golden 불변 확인; 신규 실제 EVM E2E 아님 |

검사 파일: `services/analyzer/tests/test_extraction_safety.py`, `test_openai_adapter.py`,
`test_v1_qa_regression.py`, 기존 `test_extraction.py`·`test_evaluation.py`.
새로 추가한 검사는 32개이며 기존 Analyzer 130개와 합쳐 162개입니다.

## 실행 명령과 결과

Makefile·계획서 15.9절을 따랐습니다. 전역 설정은 바꾸지 않고 명령별
`DEVELOPER_DIR=/Library/Developer/CommandLineTools`와 Node 22.18.0 PATH를 적용했습니다.
동일 lockfile로 설치된 기존 가상환경/웹 의존성을 재사용했습니다. uv에는 임시 cache 경로와
`UV_NO_SYNC=true`, `UV_OFFLINE=true`를 적용하고 Make의 `UV_ENV`를 기존 가상환경 경로로
지정했습니다. 웹 의존성은 기존 경로가 없음을 확인한 뒤 symlink만 추가했습니다.

| 실제 실행 명령 | 결과 |
| --- | --- |
| `make test` | **203 passed, 3 skipped**, 기존 Starlette/anyio deprecation warning 1개 |
| `UV_PROJECT_ENVIRONMENT=<재사용 환경> uv run --no-sync pytest -q services/indexer/tests`와 동등한 해당 Python의 `-m pytest` | **60 passed, 1 skipped** |
| `make mvp-test` | 최종 실행 exit 0: API 21 passed/3 skipped, Analyzer 162 passed, Foundry 컨테이너 10 passed, integration 183 passed/3 skipped |
| `make lint` | Ruff·웹 ESLint 통과 |
| `make typecheck` | Python compileall·웹 TypeScript 통과; Python 정적 타입 검사로 표현하지 않음 |
| `make bootstrap-check`, `make env-fingerprint` | 구조 finals-v3·환경 검사 통과; code SHA fingerprint 기록 |
| `python -m originproof_analyzer.evaluation --output build/analyzer-extraction-safety-evaluation.json` | 합성 text 8 + image replay 2, **10/10**; 실제 모델/OCR 성능 아님 |
| 임시 uvicorn `127.0.0.1:14801`, mock, 해당 source PYTHONPATH | 실제 HTTP 정상·transaction ID 누락 2건 통과; JSON·4개 헤더 확인 후 process 종료 |
| `git diff --exit-code`로 v1/v2 Golden·공통 모델·생성물·A/C/B source 비교 | 변경 없음 |
| 문서 상대 링크·JSON·`git diff --check` | 최종 문서 커밋 전 검사 |

고정 Foundry 이미지의 compose test는 별도 `originproof-ai-safety` project name을 사용했습니다.
실행한 컨테이너는 `--rm --no-deps`로 Contract 테스트만 수행했고 DB/Anvil을 기동·배포하지 않았습니다.
호스트 forge는 설치되어 있지 않으며 이 검사에 필수 조건이 아닙니다.

초기 실패도 기록합니다: 신규 검사에서 헤더 누락 실패를 재현한 뒤 구현으로 통과했습니다.
uv 기본 cache sandbox 접근/기존 불완전 venv 문제는 임시 cache·동일 lockfile의 기존 환경으로
해결했습니다. make의 Xcode 선택·uv 명령 재정의 오류는 명령별 환경/정식 Make 변수로 수정했습니다.
웹 lint의 eslint 부재는 동일 lockfile 의존성 symlink로 해결했고, Docker socket sandbox 거부는
네트워크/실행 권한 허용으로 재시도했습니다. 최종 명령은 위 표처럼 통과했습니다.

## 미실행과 남은 작업

- opt-in 실제 DB W1/W2 2건·실제 W2 chain 1건·Indexer local-chain 1건은 이번 범위에서
  별도 환경을 연결하지 않아 skip했습니다. 새 실제 DB/EVM 성공이나 단계 완료로 집계하지 않습니다.
- `make mvp-e2e`는 seed/배포를 포함하므로 보존 환경에 다시 실행하지 않았습니다.
  기본 `make smoke`의 8000/8001도 이번 코드 SHA와 일치하지 않아 증거로 사용하지 않았습니다.
- A/C 확인 기능이 없어 실제 확인·정정·비교 브라우저 E2E와 서버 우회 차단 검사는 대기합니다.
- 라이브 유료 모델 호출·새 OCR/파일 보관·DB 초기화·운영 배포를 하지 않았습니다.
- D는 응답 안내와 독립 사례를 구현했습니다. C는 출처/확인 기록·필수 범위·별도 판정 모델과
  생성물/호환성 전환을, A는 확인/정정 UI·불일치/ID-only 결과 표현을 구현·검사해야 합니다.
- 사용자 로컬 unborn `mvp/ai`의 미추적 작업, 개인 `.env`, W1 PR #41과 W2 작업 branch,
  공유 phase/integration/main은 보존했습니다. 기존 worktree를 D 새 branch에 재사용했습니다.
- 외부 리뷰·A/C 계약 승인·clean clone 재현은 실제 결과가 생긴 뒤 PR에 기록합니다.

## 기여·AI 활용·사실 확인

사용자가 D 역할과 첨부 요청 범위를 지정했고 Codex가 소비 흐름 검토, D 구현·합성 사례·검사,
인계 초안을 작성·실행했습니다. C의 기존 모델/검증 코어/Golden과 A의 기존 입력 화면,
B의 기존 Contract를 재사용했습니다. 다른 담당자의 기능을 D 기여로 기록하지 않습니다.
직접 grounding이나 새 모델/framework 대신 기존 nullable 후보와 명시적 확인 경계를 사용했습니다.
사람의 코드 검토·본인 기여 확인과 소유자 계약 승인은 아직 미확인입니다.
코드 작성·검사 통과·PR 제출을 전체 AI 기능 또는 W3/W5 완료로 표시하지 않습니다.
